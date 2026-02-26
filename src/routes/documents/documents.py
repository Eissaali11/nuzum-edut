from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime

from src.services.document_service import DocumentService
from models import Employee, Department
from src.utils.date_converter import parse_date


documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        stats = DocumentService.get_dashboard_stats()
        return render_template(
            'documents/dashboard.html',
            total_documents=stats.get('total_documents', 0),
            expired_documents=stats.get('expired_documents', 0),
            expiring_soon=stats.get('expiring_soon', 0),
            expiring_later=stats.get('expiring_later', 0),
            valid_documents=stats.get('valid_documents', 0),
            expired_docs=stats.get('expired_docs', []),
            expiring_docs=stats.get('expiring_docs', []),
            document_types_stats=stats.get('document_types_stats', []),
            department_stats=stats.get('department_stats', []),
            current_date=datetime.now().date(),
        )
    except Exception as e:
        flash(f'حدث خطأ في تحميل الإحصائيات: {str(e)}', 'danger')
        return redirect(url_for('documents.index'))


@documents_bp.route('/')
@login_required
def index():
    try:
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status')
        status_filter = request.args.get('expiring')
        search_query = request.args.get('search_query', '').strip() or None
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        documents, total_count = DocumentService.get_documents(
            document_type=document_type,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status,
            status_filter=status_filter,
            search_query=search_query,
            page=page,
            per_page=per_page,
        )

        today = datetime.now().date()
        for doc in documents:
            doc.days_to_expiry = (doc.expiry_date - today).days if doc.expiry_date else None

        total_pages = (total_count + per_page - 1) // per_page if per_page else 1

        return render_template(
            'documents/index.html',
            documents=documents,
            employees=Employee.query.all(),
            departments=Department.query.all(),
            document_types=DocumentService.get_document_types(),
            selected_type=document_type,
            selected_employee=employee_id,
            selected_department=department_id,
            selected_sponsorship=sponsorship_status,
            status_filter=status_filter,
            search_query=search_query or '',
            page=page,
            per_page=per_page,
            total_count=total_count,
            total_pages=total_pages,
        )
    except Exception as e:
        flash(f'حدث خطأ في تحميل الوثائق: {str(e)}', 'danger')
        return redirect(url_for('documents.dashboard'))


@documents_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        document_type = request.form.get('document_type')
        document_number = request.form.get('document_number', '')
        issue_date = parse_date(request.form.get('issue_date')) if request.form.get('issue_date') else None
        expiry_date = parse_date(request.form.get('expiry_date')) if request.form.get('expiry_date') else None
        notes = request.form.get('notes', '')

        success, message, _document = DocumentService.create_document(
            employee_id=employee_id,
            document_type=document_type,
            document_number=document_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=notes,
            user_id=current_user.id if current_user.is_authenticated else None,
        )

        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('documents.index'))

    return render_template(
        'documents/create.html',
        employees=Employee.query.all(),
        departments=Department.query.all(),
        document_types=DocumentService.get_document_types(),
    )


@documents_bp.route('/expiring')
@login_required
def expiring():
    try:
        status = request.args.get('status', 'expiring')
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status')

        documents, _ = DocumentService.get_documents(
            document_type=document_type,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status,
            status_filter='expired' if status == 'expired' else 'expiring',
            per_page=2000,
        )

        today = datetime.now().date()
        for doc in documents:
            doc.days_to_expiry = (doc.expiry_date - today).days if doc.expiry_date else None

        return render_template(
            'documents/expiring.html',
            documents=documents,
            days=30,
            document_types=DocumentService.get_document_types(),
            employees=Employee.query.all(),
            departments=Department.query.all(),
            selected_type=document_type or '',
            selected_employee=employee_id,
            selected_department=department_id,
            selected_sponsorship=sponsorship_status or '',
            status=status,
        )
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('documents.dashboard'))


@documents_bp.route('/expiry_stats')
@login_required
def expiry_stats():
    return jsonify(DocumentService.get_expiry_stats())


@documents_bp.route('/update_expiry_date/<int:document_id>', methods=['POST'])
@login_required
def update_expiry_date(document_id):
    expiry_date_str = request.form.get('new_expiry_date') or request.form.get('expiry_date')
    expiry_date = parse_date(expiry_date_str) if expiry_date_str else None

    if not expiry_date:
        flash('تنسيق التاريخ غير صحيح', 'danger')
        return redirect(request.referrer or url_for('documents.expiring'))

    success, message = DocumentService.update_document(document_id=document_id, expiry_date=expiry_date)
    flash(message, 'success' if success else 'danger')
    return redirect(request.referrer or url_for('documents.expiring'))


@documents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    success, message = DocumentService.delete_document(id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('documents.index'))


@documents_bp.route('/<int:id>/confirm-delete')
@login_required
def confirm_delete(id):
    document = DocumentService.get_document_by_id(id)
    if not document:
        flash('الوثيقة غير موجودة', 'danger')
        return redirect(url_for('documents.index'))
    return render_template('documents/confirm_delete.html', document=document)


@documents_bp.route('/<int:id>/update-expiry', methods=['GET', 'POST'])
@login_required
def update_expiry(id):
    document = DocumentService.get_document_by_id(id)
    if not document:
        flash('الوثيقة غير موجودة', 'danger')
        return redirect(url_for('documents.index'))

    if request.method == 'POST':
        expiry_date_str = request.form.get('expiry_date')
        expiry_date = parse_date(expiry_date_str) if expiry_date_str else None
        if not expiry_date:
            flash('يجب إدخال تاريخ الانتهاء', 'danger')
            return redirect(request.referrer or url_for('documents.expiring'))

        success, message = DocumentService.update_document(document_id=id, expiry_date=expiry_date)
        flash(message, 'success' if success else 'danger')
        return redirect(request.referrer or url_for('documents.expiring'))

    return render_template('documents/update_expiry.html', document=document)


@documents_bp.route('/upload/<int:document_id>', methods=['POST'])
@login_required
def upload_document_file(document_id):
    if 'file' not in request.files:
        flash('لم يتم اختيار ملف', 'danger')
        return redirect(request.referrer or url_for('documents.index'))

    success, message, _data = DocumentService.upload_document_file(document_id, request.files['file'])
    flash(message, 'success' if success else 'danger')
    return redirect(request.referrer or url_for('documents.index'))


@documents_bp.route('/preview/<int:document_id>')
@login_required
def preview_file(document_id):
    success, message, data = DocumentService.get_document_download_info(document_id)
    if not success:
        flash(message, 'danger')
        return redirect(request.referrer or url_for('documents.index'))

    return send_file(data['file_path'], download_name=data['download_name'], as_attachment=False)


@documents_bp.route('/download/<int:document_id>')
@login_required
def download_file(document_id):
    success, message, data = DocumentService.get_document_download_info(document_id)
    if not success:
        flash(message, 'danger')
        return redirect(request.referrer or url_for('documents.index'))

    return send_file(data['file_path'], download_name=data['download_name'], as_attachment=True)


@documents_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_excel():
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('documents.import_excel'))

            file = request.files['file']
            if not file or file.filename == '':
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('documents.import_excel'))

            success, message, _success_count, error_count = DocumentService.import_from_excel(file.stream)
            flash(f'{message} ({error_count} فشل)' if error_count > 0 else message, 'warning' if error_count > 0 else 'success')
            return redirect(url_for('documents.index'))
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('documents.import_excel'))

    return render_template('documents/import.html')


@documents_bp.route('/export-excel')
@login_required
def export_excel():
    try:
        document_type = request.args.get('document_type')
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        sponsorship_status = request.args.get('sponsorship_status')
        status_filter = request.args.get('expiring')

        documents, _ = DocumentService.get_documents(
            document_type=document_type if document_type else None,
            employee_id=employee_id,
            department_id=department_id,
            sponsorship_status=sponsorship_status if sponsorship_status else None,
            status_filter=status_filter if status_filter else None,
            per_page=10000,
        )

        output = DocumentService.export_to_excel(documents, include_employee_data=True)
        filename = f'تقرير_الوثائق_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception as e:
        flash(f'حدث خطأ في التصدير: {str(e)}', 'danger')
        return redirect(url_for('documents.index'))


@documents_bp.route('/excel-dashboard', methods=['GET', 'POST'])
@login_required
def excel_dashboard():
    if request.method == 'POST':
        if 'excel_file' not in request.files or not request.files['excel_file'] or request.files['excel_file'].filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        flash('هذه الميزة قيد التطوير. استخدم صفحة الاستيراد', 'info')
        return redirect(url_for('documents.import_excel'))

    return render_template('documents/excel_dashboard.html', uploaded=False)


@documents_bp.route('/template/pdf')
@login_required
def document_template_pdf():
    buffer = DocumentService.generate_document_template_pdf()
    return send_file(buffer, download_name='document_template.pdf', mimetype='application/pdf', as_attachment=False)


@documents_bp.route('/test-notifications', methods=['GET', 'POST'])
@login_required
def test_expiry_notifications():
    success, message, count = DocumentService.create_bulk_expiry_notifications()
    status = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'count': count}), status
