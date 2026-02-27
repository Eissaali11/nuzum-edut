"""
Payroll Admin Routes
مسارات إدارة الرواتب
"""
from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload
from io import BytesIO
from core.extensions import db
from models import Employee, User, Module, Permission, Department
from modules.payroll.domain.models import PayrollRecord, PayrollConfiguration, BankTransferFile
from modules.payroll.application.payroll_processor import PayrollProcessor
from modules.payroll.application.bank_transfer_generator import BankTransferGenerator


payroll_bp = Blueprint('payroll', __name__)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_default_departments():
    """التأكد من وجود الأقسام الافتراضية"""
    if Department.query.count() > 0:
        return  # الأقسام موجودة بالفعل
    
    default_departments = [
        {'name': 'الموارد البشرية', 'code': 'HR'},
        {'name': 'المبيعات', 'code': 'SALES'},
        {'name': 'التسويق', 'code': 'MARKETING'},
        {'name': 'تكنولوجيا المعلومات', 'code': 'IT'},
        {'name': 'العمليات', 'code': 'OPS'},
        {'name': 'التمويل', 'code': 'FINANCE'},
        {'name': 'الإدارة', 'code': 'ADMIN'},
        {'name': 'خدمة العملاء', 'code': 'CS'},
    ]
    
    try:
        for dept_data in default_departments:
            dept = Department(
                name=dept_data['name'],
                code=dept_data['code'],
                status='active'
            )
            db.session.add(dept)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # لا نرفع الخطأ، نترك التطبيق يعمل


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE & PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_payroll_access():
    """التحقق من صلاحيات الوصول لقسم الرواتب"""
    if not current_user.is_authenticated:
        return False

    role_value = getattr(current_user.role, 'value', current_user.role)
    if getattr(current_user, 'is_admin', False) or str(role_value).lower() == 'admin':
        return True
    
    # التحقق من الصلاحية
    payroll_module = Module.query.filter_by(name='payroll').first()
    if not payroll_module:
        return False
    
    permission = Permission.query.filter(
        and_(
            Permission.user_id == current_user.id,
            Permission.module_id == payroll_module.id
        )
    ).first()
    
    return permission is not None


# ═══════════════════════════════════════════════════════════════════════════════
# PAYROLL MANAGEMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@payroll_bp.route('/dashboard')
@login_required
def dashboard():
    """لوحة معلومات الرواتب"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية للوصول لقسم الرواتب', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # التأكد من وجود الأقسام الافتراضية
    _ensure_default_departments()
    
    # إحصائيات عامة
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    total_employees = Employee.query.filter_by(status='active').count()
    
    # آخر معالجة رواتب
    latest_payroll = PayrollRecord.query.filter_by(
        pay_period_month=current_month,
        pay_period_year=current_year
    ).order_by(PayrollRecord.calculated_at.desc()).first()
    
    # ✅ FIXED: Use joinedload to prevent N+1 queries on employee relationships
    month_payrolls = PayrollRecord.query.options(
        db.joinedload(PayrollRecord.employee).joinedload(Employee.departments)
    ).filter_by(
        pay_period_month=current_month,
        pay_period_year=current_year
    ).order_by(PayrollRecord.calculated_at.desc()).all()

    # الإحصائيات حسب الحالة
    pending_count = sum(1 for payroll in month_payrolls if payroll.payment_status == 'pending')
    approved_count = sum(1 for payroll in month_payrolls if payroll.payment_status == 'approved')
    rejected_count = sum(1 for payroll in month_payrolls if payroll.payment_status == 'rejected')
    paid_count = sum(1 for payroll in month_payrolls if payroll.payment_status == 'paid')

    # مجاميع المبالغ (None-safe)
    total_gross_salary = sum((payroll.gross_salary or Decimal('0')) for payroll in month_payrolls)
    total_deductions = sum((payroll.total_deductions or Decimal('0')) for payroll in month_payrolls)
    total_net_payable = sum((payroll.net_payable or Decimal('0')) for payroll in month_payrolls)
    total_gosi_company = sum((payroll.gosi_company or Decimal('0')) for payroll in month_payrolls)

    dept_salary_map = {}
    for p in month_payrolls:
        dept_name = 'غير محدد'
        if p.employee and p.employee.department:
            dept_name = p.employee.department.name
        if dept_name not in dept_salary_map:
            dept_salary_map[dept_name] = {'gross': Decimal('0'), 'net': Decimal('0'), 'count': 0}
        dept_salary_map[dept_name]['gross'] += (p.gross_salary or Decimal('0'))
        dept_salary_map[dept_name]['net'] += (p.net_payable or Decimal('0'))
        dept_salary_map[dept_name]['count'] += 1

    dept_labels = list(dept_salary_map.keys())
    dept_net_values = [float(dept_salary_map[k]['net']) for k in dept_labels]
    dept_counts = [dept_salary_map[k]['count'] for k in dept_labels]

    return render_template('payroll/dashboard.html',
        total_employees=total_employees,
        latest_payroll=latest_payroll,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        paid_count=paid_count,
        total_gross_salary=float(total_gross_salary),
        total_deductions=float(total_deductions),
        total_net_payable=float(total_net_payable),
        total_gosi_company=float(total_gosi_company),
        recent_payrolls=month_payrolls,
        current_month=current_month,
        current_year=current_year,
        dept_labels=dept_labels,
        dept_net_values=dept_net_values,
        dept_counts=dept_counts,
    )


@payroll_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process():
    """معالجة رواتب الموظفين"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        try:
            month_value = (request.form.get('month') or '').strip()
            year_value = request.form.get('year') or request.form.get('fiscal_year')

            if month_value and '-' in month_value:
                parsed_year, parsed_month = month_value.split('-', 1)
                year = int(parsed_year)
                month = int(parsed_month)
            else:
                month = int(month_value) if month_value else datetime.now().month
                year = int(year_value) if year_value else datetime.now().year
            
            processor = PayrollProcessor(year, month)
            payrolls = processor.process_all_employees()

            total_gross = sum((p.gross_salary or Decimal('0')) for p in payrolls)
            total_deductions = sum((p.total_deductions or Decimal('0')) for p in payrolls)
            total_net_payable = sum((p.net_payable or Decimal('0')) for p in payrolls)

            wants_json = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('Accept', '')
            )
            if wants_json:
                return jsonify({
                    'success': True,
                    'processed_count': len(payrolls),
                    'total_gross_salary': float(total_gross),
                    'total_deductions': float(total_deductions),
                    'total_net_payable': float(total_net_payable)
                })
            
            flash(f'تم معالجة رواتب {len(payrolls)} موظف بنجاح', 'success')
            return redirect(url_for('payroll.review', month=month, year=year))
        
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)}), 400
            flash(f'خطأ: {str(e)}', 'danger')
    
    return render_template('payroll/process.html',
        current_month=datetime.now().month,
        current_year=datetime.now().year
    )


@payroll_bp.route('/review')
@login_required
def review():
    """مراجعة رواتب الموظفين قبل الموافقة"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # التأكد من وجود الأقسام الافتراضية
    _ensure_default_departments()
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    status = request.args.get('status', 'pending')
    department_id = request.args.get('department_id', type=int)
    
    # جلب الرواتب
    query = PayrollRecord.query.join(Employee, PayrollRecord.employee_id == Employee.id).filter(
        and_(
            PayrollRecord.pay_period_month == month,
            PayrollRecord.pay_period_year == year,
            PayrollRecord.payment_status == status
        )
    )

    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    payrolls = query.all()
    
    # الإحصائيات
    total_gross = sum(p.gross_salary for p in payrolls)
    total_deductions = sum(p.total_deductions for p in payrolls)
    total_net = sum(p.net_payable for p in payrolls)
    departments = Department.query.order_by(Department.name.asc()).all()
    
    return render_template('payroll/review.html',
        payrolls=payrolls,
        month=month,
        year=year,
        status=status,
        departments=departments,
        selected_department_id=department_id,
        total_gross=float(total_gross),
        total_deductions=float(total_deductions),
        total_net=float(total_net),
        payroll_count=len(payrolls)
    )


@payroll_bp.route('/<int:payroll_id>/details')
@payroll_bp.route('/payroll/<int:payroll_id>/details')
@login_required
def payroll_details(payroll_id):
    """عرض تفاصيل الراتب الكامل"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    payroll = PayrollRecord.query.get_or_404(payroll_id)
    
    return render_template('payroll/details.html',
        payroll=payroll
    )


@payroll_bp.route('/payroll/<int:payroll_id>/details/legacy')
@login_required
def payroll_details_legacy(payroll_id):
    return redirect(url_for('payroll.payroll_details', payroll_id=payroll_id))


@payroll_bp.route('/<int:payroll_id>/approve', methods=['POST'])
@payroll_bp.route('/payroll/<int:payroll_id>/approve', methods=['POST'])
@login_required
def approve_payroll(payroll_id):
    """الموافقة على الراتب"""
    if not check_payroll_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    try:
        payroll = PayrollRecord.query.get_or_404(payroll_id)
        processor = PayrollProcessor(payroll.pay_period_year, payroll.pay_period_month)
        
        notes = request.form.get('notes', '')
        processor.approve_payroll(payroll_id, current_user.id, notes)
        
        return jsonify({'success': True, 'message': 'تمت الموافقة على الراتب'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@payroll_bp.route('/<int:payroll_id>/reject', methods=['POST'])
@payroll_bp.route('/payroll/<int:payroll_id>/reject', methods=['POST'])
@login_required
def reject_payroll(payroll_id):
    """رفض الراتب"""
    if not check_payroll_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    try:
        reason = request.form.get('reason', 'لم يتم تحديد السبب')
        processor = PayrollProcessor(None, None)
        processor.reject_payroll(payroll_id, reason)
        
        return jsonify({'success': True, 'message': 'تم رفض الراتب'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@payroll_bp.route('/payroll/<int:payroll_id>/approve/legacy', methods=['POST'])
@login_required
def approve_payroll_legacy(payroll_id):
    return redirect(url_for('payroll.approve_payroll', payroll_id=payroll_id), code=307)


@payroll_bp.route('/payroll/<int:payroll_id>/reject/legacy', methods=['POST'])
@login_required
def reject_payroll_legacy(payroll_id):
    return redirect(url_for('payroll.reject_payroll', payroll_id=payroll_id), code=307)


@payroll_bp.route('/batch-approve', methods=['POST'])
@login_required
def batch_approve():
    """الموافقة على مجموعة من الرواتب"""
    if not check_payroll_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    try:
        payroll_ids = request.json.get('payroll_ids', [])
        processor = PayrollProcessor(None, None)
        
        for payroll_id in payroll_ids:
            processor.approve_payroll(payroll_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': f'تمت الموافقة على {len(payroll_ids)} راتب'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# ═══════════════════════════════════════════════════════════════════════════════
# BANK TRANSFER & EXPORT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@payroll_bp.route('/bank-transfer/create', methods=['POST'])
@login_required
def create_bank_transfer():
    """إنشاء ملف التحويل البنكي"""
    if not check_payroll_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    try:
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))
        bank_code = request.form.get('bank_code', 'NCB')
        file_format = request.form.get('format', 'txt')
        
        generator = BankTransferGenerator(year, month, bank_code)
        transfer_file = generator.create_transfer_file(file_format)
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء ملف التحويل بنجاح',
            'file_id': transfer_file.id,
            'file_name': transfer_file.file_name
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@payroll_bp.route('/bank-transfer/<int:file_id>/download')
@login_required
def download_bank_transfer(file_id):
    """تنزيل ملف التحويل البنكي"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    transfer_file = BankTransferFile.query.get_or_404(file_id)
    
    try:
        return send_file(
            transfer_file.file_path,
            as_attachment=True,
            download_name=transfer_file.file_name
        )
    except Exception as e:
        flash(f'خطأ في التحميل: {str(e)}', 'danger')
        return redirect(url_for('payroll.dashboard'))


@payroll_bp.route('/export/excel')
@login_required
def export_to_excel():
    """تصدير الرواتب إلى Excel"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # جلب الرواتب
        payrolls = PayrollRecord.query.filter_by(
            pay_period_month=month,
            pay_period_year=year,
            payment_status='approved'
        ).all()
        
        # إنشاء Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Payroll_Details'
        
        # الرؤوس
        headers = ['رقم الموظف', 'اسم الموظف', 'الراتب الأساسي', 'المزايا', 'الراتب الإجمالي', 
                   'الخصومات', 'الراتب الصافي', 'الحالة']
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        
        # البيانات
        row = 2
        for payroll in payrolls:
            employee = payroll.employee
            
            ws.cell(row=row, column=1).value = employee.employee_id
            ws.cell(row=row, column=2).value = employee.name
            ws.cell(row=row, column=3).value = float(payroll.basic_salary)
            ws.cell(row=row, column=4).value = float(payroll.housing_allowance + payroll.transportation + payroll.meal_allowance)
            ws.cell(row=row, column=5).value = float(payroll.gross_salary)
            ws.cell(row=row, column=6).value = float(payroll.total_deductions)
            ws.cell(row=row, column=7).value = float(payroll.net_payable)
            ws.cell(row=row, column=8).value = payroll.payment_status
            
            row += 1
        
        # حفظ الملف
        file_path = f'static/payroll_exports/payroll_{month:02d}_{year}.xlsx'
        wb.save(file_path)
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'danger')
        return redirect(url_for('payroll.dashboard'))


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@payroll_bp.route('/configuration')
@login_required
def configuration():
    """إعدادات الرواتب"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))
    
    config = PayrollConfiguration.query.filter_by(is_active=True).first()
    if not config:
        config = PayrollConfiguration()
    
    return render_template('payroll/configuration.html', config=config)


@payroll_bp.route('/configuration/save', methods=['POST'])
@login_required
def save_configuration():
    """حفظ إعدادات الرواتب"""
    if not check_payroll_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    try:
        config = PayrollConfiguration.query.filter_by(is_active=True).first()
        if not config:
            config = PayrollConfiguration()
        
        config.gosi_employee_percentage = Decimal(request.form.get('gosi_employee', 10))
        config.gosi_company_percentage = Decimal(request.form.get('gosi_company', 13))
        config.working_days_per_month = int(request.form.get('working_days', 22))
        config.minimum_wage = Decimal(request.form.get('minimum_wage', 2000))
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم حفظ الإعدادات بنجاح'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@payroll_bp.route('/review/export-excel')
@login_required
def export_review_excel():
    """تصدير كشف مراجعة الرواتب إلى Excel احترافي"""
    if not check_payroll_access():
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('dashboard.index'))

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    status = request.args.get('status', 'pending')
    department_id = request.args.get('department_id', type=int)

    query = PayrollRecord.query.join(Employee, PayrollRecord.employee_id == Employee.id).options(
        joinedload(PayrollRecord.employee).joinedload(Employee.departments)
    ).filter(
        and_(
            PayrollRecord.pay_period_month == month,
            PayrollRecord.pay_period_year == year,
            PayrollRecord.payment_status == status
        )
    )
    if department_id:
        query = query.filter(Employee.department_id == department_id)

    payrolls = query.order_by(Employee.name).all()

    STATUS_AR = {
        'pending': 'قيد الانتظار',
        'approved': 'معتمدة',
        'rejected': 'مرفوضة',
        'paid': 'مدفوعة',
    }

    MONTH_AR = [
        '', 'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "كشف الرواتب"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.sheet_view.rightToLeft = True

    navy = "1A237E"
    navy_fill = PatternFill(start_color=navy, end_color=navy, fill_type="solid")
    white_font_xl = Font(bold=True, color="FFFFFF", size=18)
    white_font_md = Font(bold=True, color="FFFFFF", size=12)
    white_font_sm = Font(bold=True, color="FFFFFF", size=10)

    teal = "18B2B0"
    teal_fill = PatternFill(start_color=teal, end_color=teal, fill_type="solid")

    green_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    red_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    orange_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    blue_fill = PatternFill(start_color="D1ECF1", end_color="D1ECF1", fill_type="solid")
    light_gray_fill = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")

    green_font = Font(bold=True, color="155724", size=11)
    red_font = Font(bold=True, color="721C24", size=11)
    blue_font = Font(bold=True, color="0C5460", size=11)
    orange_font = Font(bold=True, color="856404", size=11)

    thin_border = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0')
    )

    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    right_align = Alignment(horizontal='right', vertical='center', wrap_text=True)

    total_gross = sum(float(p.gross_salary or 0) for p in payrolls)
    total_deductions = sum(float(p.total_deductions or 0) for p in payrolls)
    total_net = sum(float(p.net_payable or 0) for p in payrolls)

    ws.merge_cells('A1:N1')
    title_cell = ws['A1']
    title_cell.value = "كشف مراجعة الرواتب"
    title_cell.font = white_font_xl
    title_cell.fill = navy_fill
    title_cell.alignment = center
    ws.row_dimensions[1].height = 40

    ws.merge_cells('A2:N2')
    subtitle_cell = ws['A2']
    status_label = STATUS_AR.get(status, status)
    month_label = MONTH_AR[month] if 1 <= month <= 12 else str(month)
    dept_obj = Department.query.get(department_id) if department_id else None
    dept_label = dept_obj.name if dept_obj else 'جميع الأقسام'
    subtitle_cell.value = f"الفترة: {month_label} {year}  |  الحالة: {status_label}  |  القسم: {dept_label}  |  تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    subtitle_cell.font = Font(bold=True, color="FFFFFF", size=11)
    subtitle_cell.fill = PatternFill(start_color="283593", end_color="283593", fill_type="solid")
    subtitle_cell.alignment = center
    ws.row_dimensions[2].height = 28

    kpi_row = 4
    kpi_data = [
        ('A', 'C', 'عدد الموظفين', str(len(payrolls)), blue_fill, blue_font),
        ('D', 'F', 'إجمالي الراتب', f'{total_gross:,.2f} ر.س', green_fill, green_font),
        ('G', 'I', 'إجمالي الخصومات', f'{total_deductions:,.2f} ر.س', red_fill, red_font),
        ('J', 'L', 'صافي المستحقات', f'{total_net:,.2f} ر.س', orange_fill, orange_font),
    ]
    for start_col, end_col, label, value, fill, font in kpi_data:
        ws.merge_cells(f'{start_col}{kpi_row}:{end_col}{kpi_row}')
        label_cell = ws[f'{start_col}{kpi_row}']
        label_cell.value = label
        label_cell.font = Font(bold=True, size=10, color="555555")
        label_cell.alignment = center
        label_cell.fill = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")

        val_row = kpi_row + 1
        ws.merge_cells(f'{start_col}{val_row}:{end_col}{val_row}')
        val_cell = ws[f'{start_col}{val_row}']
        val_cell.value = value
        val_cell.font = font
        val_cell.alignment = center
        val_cell.fill = fill

    ws.row_dimensions[kpi_row].height = 22
    ws.row_dimensions[kpi_row + 1].height = 30

    header_row = 7
    headers = [
        ('#', 5),
        ('رقم الموظف', 14),
        ('اسم الموظف', 28),
        ('القسم', 18),
        ('الراتب الأساسي', 16),
        ('بدل السكن', 14),
        ('بدل المواصلات', 14),
        ('بدل الطعام', 13),
        ('الراتب الإجمالي', 16),
        ('خصم الغياب', 13),
        ('خصم التأخير', 13),
        ('GOSI', 12),
        ('إجمالي الخصومات', 16),
        ('الراتب الصافي', 16),
    ]

    for col_idx, (header_text, width) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = header_text
        cell.font = white_font_sm
        cell.fill = teal_fill
        cell.alignment = center
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[header_row].height = 30

    row_num = header_row + 1
    for idx, p in enumerate(payrolls, 1):
        emp = p.employee
        emp_name = emp.name if emp else 'غير متاح'
        dept_name = ''
        if emp:
            if hasattr(emp, 'departments') and emp.departments:
                dept_name = ', '.join(d.name for d in emp.departments)
            elif hasattr(emp, 'department') and emp.department:
                dept_name = emp.department.name

        row_data = [
            idx,
            emp.employee_id if emp else '-',
            emp_name,
            dept_name or '-',
            float(p.basic_salary or 0),
            float(p.housing_allowance or 0),
            float(p.transportation or 0),
            float(p.meal_allowance or 0),
            float(p.gross_salary or 0),
            float(p.absence_deduction or 0),
            float(p.late_deduction or 0),
            float(p.gosi_employee or 0),
            float(p.total_deductions or 0),
            float(p.net_payable or 0),
        ]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = value
            cell.alignment = center
            cell.border = thin_border

            if idx % 2 == 0:
                cell.fill = light_gray_fill

            if col_idx == 3:
                cell.font = Font(bold=True, size=10)
                cell.alignment = right_align
            elif col_idx >= 5:
                cell.number_format = '#,##0.00'
                if col_idx == 9:
                    cell.font = green_font
                elif col_idx in (10, 11, 12, 13):
                    cell.font = red_font
                elif col_idx == 14:
                    cell.font = blue_font

        ws.row_dimensions[row_num].height = 24
        row_num += 1

    if payrolls:
        total_row = row_num
        ws.merge_cells(f'A{total_row}:D{total_row}')
        total_label = ws.cell(row=total_row, column=1)
        total_label.value = "الإجمالي"
        total_label.font = Font(bold=True, color="FFFFFF", size=12)
        total_label.fill = navy_fill
        total_label.alignment = center

        for col in range(2, 5):
            c = ws.cell(row=total_row, column=col)
            c.fill = navy_fill

        total_cols = {
            5: sum(float(p.basic_salary or 0) for p in payrolls),
            6: sum(float(p.housing_allowance or 0) for p in payrolls),
            7: sum(float(p.transportation or 0) for p in payrolls),
            8: sum(float(p.meal_allowance or 0) for p in payrolls),
            9: total_gross,
            10: sum(float(p.absence_deduction or 0) for p in payrolls),
            11: sum(float(p.late_deduction or 0) for p in payrolls),
            12: sum(float(p.gosi_employee or 0) for p in payrolls),
            13: total_deductions,
            14: total_net,
        }

        for col_idx, total_val in total_cols.items():
            cell = ws.cell(row=total_row, column=col_idx)
            cell.value = total_val
            cell.number_format = '#,##0.00'
            cell.font = Font(bold=True, color="FFFFFF", size=11)
            cell.fill = navy_fill
            cell.alignment = center
            cell.border = thin_border

        ws.row_dimensions[total_row].height = 30
        row_num = total_row + 1

    sign_row = row_num + 3
    ws.merge_cells(f'A{sign_row}:D{sign_row}')
    ws.cell(row=sign_row, column=1).value = "المحاسب: ________________"
    ws.cell(row=sign_row, column=1).font = Font(size=11, bold=True)
    ws.cell(row=sign_row, column=1).alignment = right_align

    ws.merge_cells(f'F{sign_row}:I{sign_row}')
    ws.cell(row=sign_row, column=6).value = "مدير الموارد البشرية: ________________"
    ws.cell(row=sign_row, column=6).font = Font(size=11, bold=True)
    ws.cell(row=sign_row, column=6).alignment = right_align

    ws.merge_cells(f'K{sign_row}:N{sign_row}')
    ws.cell(row=sign_row, column=11).value = "المدير العام: ________________"
    ws.cell(row=sign_row, column=11).font = Font(size=11, bold=True)
    ws.cell(row=sign_row, column=11).alignment = right_align

    ws.row_dimensions[sign_row].height = 35

    date_row = sign_row + 1
    ws.merge_cells(f'A{date_row}:D{date_row}')
    ws.cell(row=date_row, column=1).value = f"التاريخ: ____/____/________"
    ws.cell(row=date_row, column=1).font = Font(size=9, color="777777")
    ws.cell(row=date_row, column=1).alignment = right_align

    ws.merge_cells(f'F{date_row}:I{date_row}')
    ws.cell(row=date_row, column=6).value = f"التاريخ: ____/____/________"
    ws.cell(row=date_row, column=6).font = Font(size=9, color="777777")
    ws.cell(row=date_row, column=6).alignment = right_align

    ws.merge_cells(f'K{date_row}:N{date_row}')
    ws.cell(row=date_row, column=11).value = f"التاريخ: ____/____/________"
    ws.cell(row=date_row, column=11).font = Font(size=9, color="777777")
    ws.cell(row=date_row, column=11).alignment = right_align

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    status_en = status.capitalize()
    filename = f"Payroll_Review_{status_en}_{month}_{year}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
