"""
مسارات النسخ الاحتياطي لقاعدة البيانات
يوفر واجهات لتصدير واستيراد النسخ الاحتياطية
"""
import json
import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, current_app
from flask_login import login_required
from sqlalchemy import inspect
from io import BytesIO
from core.extensions import db
from utils.decorators import permission_required

database_backup_bp = Blueprint('database_backup', __name__)


@database_backup_bp.route('/')
@login_required
@permission_required('admin', 'view')
def backup_page():
    """صفحة النسخ الاحتياطي الرئيسية"""
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    
    # حساب عدد السجلات لكل جدول
    table_stats = {}
    total_records = 0
    
    for table_name in sorted(table_names):
        try:
            # تجنب الجداول النظامية
            if table_name.startswith('_') or table_name in ['alembic_version']:
                continue
            
            count = db.session.execute(
                db.text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
            
            table_stats[table_name] = count
            total_records += count
        except Exception as e:
            current_app.logger.warning(f"Could not count records in {table_name}: {str(e)}")
            table_stats[table_name] = 0
    
    return render_template('backup/index.html',
                          table_stats=table_stats,
                          total_records=total_records)


@database_backup_bp.route('/export', methods=['POST'])
@login_required
@permission_required('admin', 'edit')
def export_backup():
    """تصدير النسخة الاحتياطية كملف JSON"""
    try:
        selected_tables = request.form.getlist('tables')
        
        if not selected_tables:
            flash('يجب اختيار جدول واحد على الأقل', 'warning')
            return redirect(url_for('database_backup.backup_page'))
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'tables': {}
        }
        
        inspector = inspect(db.engine)
        
        for table_name in selected_tables:
            try:
                # التحقق من وجود الجدول
                if table_name not in inspector.get_table_names():
                    continue
                
                import re as _re
                if not _re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
                    continue
                result = db.session.execute(db.text(f'SELECT * FROM "{table_name}"'))
                columns = result.keys()
                rows = result.fetchall()
                
                # تحويل البيانات إلى قاموس
                table_data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # تحويل التواريخ إلى نص
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        elif isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        row_dict[col] = value
                    table_data.append(row_dict)
                
                backup_data['tables'][table_name] = {
                    'columns': list(columns),
                    'rows': table_data,
                    'count': len(table_data)
                }
                
            except Exception as e:
                current_app.logger.error(f"Error exporting table {table_name}: {str(e)}")
                flash(f'خطأ في تصدير جدول {table_name}: {str(e)}', 'danger')
        
        # إنشاء ملف JSON
        json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
        
        # إنشاء ملف للتحميل
        buffer = BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)
        
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Error creating backup: {str(e)}")
        flash(f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}', 'danger')
        return redirect(url_for('database_backup.backup_page'))


@database_backup_bp.route('/import', methods=['POST'])
@login_required
@permission_required('admin', 'edit')
def import_backup():
    """استيراد نسخة احتياطية من ملف JSON"""
    import re
    _IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

    def _safe_identifier(name):
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid identifier: {name}")
        return f'"{name}"'

    _TABLE_NAME_MAP = {
        'employees': 'employee',
        'vehicles': 'vehicle',
        'departments': 'department',
        'users': 'user',
        'salaries': 'salary',
        'vehicle_handovers': 'vehicle_handover',
        'vehicle_workshops': 'vehicle_workshop',
        'documents': 'document',
        'vehicle_accidents': 'vehicle_accident',
        'external_safety_checks': 'vehicle_external_safety_check',
        'safety_images': 'vehicle_safety_image',
    }

    try:
        if 'backup_file' not in request.files:
            flash('يجب اختيار ملف النسخة الاحتياطية', 'warning')
            return redirect(url_for('database_backup.backup_page'))

        file = request.files['backup_file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'warning')
            return redirect(url_for('database_backup.backup_page'))

        import_mode = request.form.get('import_mode', 'add')
        if import_mode not in ('add', 'replace'):
            import_mode = 'add'

        backup_data = json.load(file)

        if 'tables' in backup_data:
            tables_dict = {}
            for tname, tdata in backup_data['tables'].items():
                tables_dict[tname] = tdata.get('rows', [])
        elif 'data' in backup_data:
            tables_dict = backup_data['data']
        else:
            flash('ملف النسخة الاحتياطية غير صالح — لا يحتوي على tables أو data', 'danger')
            return redirect(url_for('database_backup.backup_page'))

        inspector = inspect(db.engine)
        valid_tables = set(inspector.get_table_names())
        valid_columns_cache = {}

        imported_count = 0
        skipped_count = 0
        table_results = []

        for backup_table_name, rows in tables_dict.items():
            db_table = _TABLE_NAME_MAP.get(backup_table_name, backup_table_name)
            if db_table not in valid_tables:
                current_app.logger.warning(f"Skipping unknown table: {backup_table_name} (mapped: {db_table})")
                table_results.append(f'{backup_table_name}: تم تخطيه (غير موجود)')
                continue

            if not isinstance(rows, list):
                continue

            try:
                safe_table = _safe_identifier(db_table)

                if db_table not in valid_columns_cache:
                    valid_columns_cache[db_table] = set(c['name'] for c in inspector.get_columns(db_table))

                if import_mode == 'replace':
                    db.session.execute(db.text(f"DELETE FROM {safe_table}"))

                table_imported = 0
                table_skipped = 0

                for row in rows:
                    try:
                        filtered_row = {k: v for k, v in row.items() if k in valid_columns_cache[db_table]}
                        if not filtered_row:
                            table_skipped += 1
                            continue

                        safe_cols = [_safe_identifier(k) for k in filtered_row.keys()]
                        columns = ', '.join(safe_cols)
                        placeholders = ', '.join([f":{key}" for key in filtered_row.keys()])
                        query = f"INSERT INTO {safe_table} ({columns}) VALUES ({placeholders})"

                        db.session.execute(db.text(query), filtered_row)
                        table_imported += 1
                    except ValueError:
                        table_skipped += 1
                    except Exception as row_err:
                        db.session.rollback()
                        if import_mode == 'add':
                            table_skipped += 1
                        else:
                            raise

                db.session.commit()
                imported_count += table_imported
                skipped_count += table_skipped
                table_results.append(f'{backup_table_name}: {table_imported} سجل')
                current_app.logger.info(f"Imported {table_imported} rows into {db_table} (skipped {table_skipped})")

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error importing table {db_table}: {str(e)}")
                table_results.append(f'{backup_table_name}: خطأ')
                flash(f'خطأ في استيراد جدول {backup_table_name}: {str(e)}', 'danger')

        summary = ' | '.join(table_results[:10])
        flash(f'تم استيراد {imported_count} سجل بنجاح. تم تخطي {skipped_count} سجل. ({summary})', 'success')

    except json.JSONDecodeError:
        flash('ملف النسخة الاحتياطية تالف أو ليس بصيغة JSON صحيحة', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing backup: {str(e)}")
        flash(f'حدث خطأ أثناء استيراد النسخة الاحتياطية: {str(e)}', 'danger')

    return redirect(url_for('database_backup.backup_page'))


@database_backup_bp.route('/export/<table_name>')
@login_required
@permission_required('admin', 'view')
def export_single_table(table_name):
    """تصدير جدول واحد كملف JSON"""
    try:
        inspector = inspect(db.engine)
        
        if table_name not in inspector.get_table_names():
            flash(f'الجدول {table_name} غير موجود', 'danger')
            return redirect(url_for('database_backup.backup_page'))
        
        import re
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
            flash('اسم جدول غير صالح', 'danger')
            return redirect(url_for('database_backup.backup_page'))
        result = db.session.execute(db.text(f'SELECT * FROM "{table_name}"'))
        columns = result.keys()
        rows = result.fetchall()
        
        # تحويل البيانات إلى قاموس
        table_data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                row_dict[col] = value
            table_data.append(row_dict)
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'table': table_name,
            'columns': list(columns),
            'rows': table_data,
            'count': len(table_data)
        }
        
        # إنشاء ملف JSON
        json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
        
        buffer = BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)
        
        filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting table {table_name}: {str(e)}")
        flash(f'حدث خطأ أثناء تصدير الجدول: {str(e)}', 'danger')
        return redirect(url_for('database_backup.backup_page'))
