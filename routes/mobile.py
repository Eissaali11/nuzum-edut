"""
مسارات ومعالجات الواجهة المحمولة
نُظم - النسخة المحمولة

يحتوي هذا الملف على مسارات: الموظفين، الأقسام، الوثائق، المركبات، التقارير، الرسوم، الإشعارات، الإعدادات، والمستخدمين.
مسارات المصادقة، الحضور/الرواتب، التتبع، واللوحة الرئيسية مُسجّلة من presentation.api.mobile.
"""

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, date

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import Markup
from sqlalchemy import Date, cast, extract, func, or_
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from models import (
    Department,
    Document,
    Employee,
    EmployeeLocation,
    ExternalAuthorization,
    MobileDevice,
    Module,
    Nationality,
    OperationNotification,
    OperationRequest,
    Permission,
    Project,
    SystemAudit,
    User,
    UserPermission,
    UserRole,
    Vehicle,
    employee_departments,
    VehicleAccident,
    VehicleChecklist,
    VehicleChecklistImage,
    VehicleChecklistItem,
    VehicleDamageMarker,
    VehicleFuelConsumption,
    VehicleHandover,
    VehicleHandoverImage,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehiclePeriodicInspection,
    VehicleProject,
    VehicleRental,
    VehicleSafetyCheck,
    VehicleWorkshop,
    VehicleWorkshopImage,
    Attendance,
    FeesCost as Fee,
    Salary,
    db,
)
from routes.operations import create_operation_request
from modules.vehicles.application.vehicle_service import update_vehicle_driver
from utils.vehicle_route_helpers import update_vehicle_state
from utils.audit_logger import log_activity
from utils.decorators import module_access_required, permission_required
from utils.hijri_converter import convert_gregorian_to_hijri, format_hijri_date

mobile_bp = Blueprint("mobile", __name__)

# مسارات المصادقة والفحوصات والحضور/الرواتب (مستخرجة إلى presentation/api/mobile)
from presentation.api.mobile.auth_routes import register_auth_routes
from presentation.api.mobile.inspection_routes import register_inspection_routes
from presentation.api.mobile.hr_routes import register_hr_routes
from presentation.api.mobile.tracking_routes import register_tracking_routes
from presentation.api.mobile.dashboard_routes import register_dashboard_routes
from presentation.api.mobile.vehicle_routes import register_vehicle_routes
register_auth_routes(mobile_bp)
register_inspection_routes(mobile_bp)
register_hr_routes(mobile_bp)
register_tracking_routes(mobile_bp)
register_dashboard_routes(mobile_bp)
register_vehicle_routes(mobile_bp)


# تسجيل الدخول باستخدام Google - النسخة المحمولة
@mobile_bp.route('/login/google')
def google_login():
    """تسجيل الدخول باستخدام Google للنسخة المحمولة"""
    # هنا يتم التعامل مع تسجيل الدخول باستخدام Google
    # يمكن استخدام نفس الكود الموجود في النسخة الأصلية مع تعديل مسار التوجيه
    return redirect(url_for('auth.google_login', next=url_for('mobile.index')))

# صفحة الموظفين - النسخة المحمولة
@mobile_bp.route('/employees')
@login_required
def employees():
    """صفحة الموظفين للنسخة المحمولة"""
    page = request.args.get('page', 1, type=int)
    per_page = 20  # عدد العناصر في الصفحة الواحدة

    # إنشاء الاستعلام الأساسي
    query = Employee.query
    
    # التحقق من وجود فلتر القسم
    department_id = request.args.get('department_id')
    search_query = request.args.get('search', '').strip()
    
    # إذا كان هناك فلتر قسم، نطبق الـ join أولاً
    if department_id:
        dept_id = int(department_id)
        query = query.join(Employee.departments).filter(Department.id == dept_id)
    
    # ثم نطبق البحث إذا كان موجوداً
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Employee.name.like(search_term)) |
            (Employee.employee_id.like(search_term)) |
            (Employee.national_id.like(search_term)) |
            (Employee.job_title.like(search_term))
        )

    # ترتيب النتائج حسب الاسم
    query = query.order_by(Employee.name)

    # تنفيذ الاستعلام مع الصفحات
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    employees = pagination.items

    # الحصول على قائمة الأقسام للفلترة
    departments = Department.query.order_by(Department.name).all()

    return render_template('mobile/employees.html',
                           employees=employees,
                           pagination=pagination,
                           departments=departments)

# صفحة إضافة موظف جديد - النسخة المحمولة
@mobile_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    """صفحة إضافة موظف جديد للنسخة المحمولة"""
    
    # معالجة الـ POST request لحفظ الموظف الجديد
    if request.method == 'POST':
        try:
            # التحقق من عدم تكرار رقم الموظف
            employee_id_value = request.form.get('employee_id')
            if employee_id_value:
                existing_employee = Employee.query.filter_by(employee_id=employee_id_value).first()
                if existing_employee:
                    flash('رقم الموظف موجود بالفعل، يرجى استخدام رقم آخر', 'danger')
                    departments = Department.query.order_by(Department.name).all()
                    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
                    available_mobile_devices = MobileDevice.query.filter(
                        MobileDevice.employee_id == None
                    ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
                    return render_template('mobile/add_employee.html',
                                         departments=departments,
                                         nationalities=nationalities,
                                         available_mobile_devices=available_mobile_devices)
            
            # إنشاء موظف جديد
            employee = Employee(
                name=request.form.get('name'),
                employee_id=employee_id_value,
                national_id=request.form.get('national_id'),
                mobile=request.form.get('mobile'),
                email=request.form.get('email'),
                job_title=request.form.get('job_title'),
                nationality_id=int(request.form.get('nationality_id')) if request.form.get('nationality_id') else None,
                department_id=int(request.form.get('department_id')) if request.form.get('department_id') else None,
                contract_status=request.form.get('contract_status'),
                license_status=request.form.get('license_status'),
                employee_type=request.form.get('employee_type'),
                status=request.form.get('status', 'active'),
                has_mobile_custody=request.form.get('has_mobile_custody') == 'yes',
                sponsorship_status=request.form.get('sponsorship_status'),
                residence_details=request.form.get('residence_details'),
                pants_size=request.form.get('pants_size'),
                shirt_size=request.form.get('shirt_size'),
                location=request.form.get('location'),
                project=request.form.get('project'),
                join_date=datetime.strptime(request.form.get('join_date'), '%Y-%m-%d').date() if request.form.get('join_date') else None,
                birth_date=datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date() if request.form.get('birth_date') else None,
                basic_salary=float(request.form.get('basic_salary')) if request.form.get('basic_salary') else 0,
                attendance_bonus=float(request.form.get('attendance_bonus')) if request.form.get('attendance_bonus') else 0
            )
            
            db.session.add(employee)
            db.session.flush()  # للحصول على ID الموظف
            
            # تعيين الأقسام
            department_ids = request.form.getlist('department_ids')
            if department_ids:
                employee.departments = Department.query.filter(Department.id.in_(department_ids)).all()
            
            # تعيين الجهاز المحمول إذا تم اختياره
            if request.form.get('mobile_device_id'):
                mobile_device = MobileDevice.query.get(int(request.form.get('mobile_device_id')))
                if mobile_device:
                    mobile_device.employee_id = employee.id
                    mobile_device.assigned_date = datetime.now()
                    mobile_device.is_assigned = True
            
            db.session.commit()
            flash('تم إضافة الموظف بنجاح', 'success')
            return redirect(url_for('mobile.employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة الموظف: {str(e)}', 'danger')
    
    # جلب البيانات المطلوبة
    departments = Department.query.order_by(Department.name).all()
    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
    
    # جلب الأجهزة المحمولة المتاحة (غير المخصصة لموظف)
    available_mobile_devices = MobileDevice.query.filter(
        MobileDevice.employee_id == None
    ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
    
    return render_template('mobile/add_employee.html',
                         departments=departments,
                         nationalities=nationalities,
                         available_mobile_devices=available_mobile_devices)

# صفحة تفاصيل الموظف - النسخة المحمولة
@mobile_bp.route('/employees/<int:employee_id>')
@login_required
def employee_details(employee_id):
    """صفحة تفاصيل الموظف للنسخة المحمولة"""
    employee = Employee.query.get_or_404(employee_id)

    # الحصول على التاريخ الحالي وتاريخ بداية ونهاية الشهر الحالي
    current_date = datetime.now().date()
    current_month_start = date(current_date.year, current_date.month, 1)
    next_month = current_date.month + 1 if current_date.month < 12 else 1
    next_year = current_date.year if current_date.month < 12 else current_date.year + 1
    current_month_end = date(next_year, next_month, 1) - timedelta(days=1)

    # استعلام سجلات الحضور للموظف خلال الشهر الحالي
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= current_month_start.strftime('%Y-%m-%d'),
        Attendance.date <= current_month_end.strftime('%Y-%m-%d')
    ).order_by(Attendance.date.desc()).all()

    # استعلام أحدث راتب للموظف
    # ترتيب حسب السنة ثم الشهر بترتيب تنازلي
    salary = Salary.query.filter_by(employee_id=employee_id).order_by(Salary.year.desc(), Salary.month.desc()).first()

    # استعلام الوثائق الخاصة بالموظف
    documents = Document.query.filter_by(employee_id=employee_id).all()

    # استعلام السيارات المرتبطة بالموظف (كسائق أو مشرف)
    from models import VehicleHandover, Vehicle
    from sqlalchemy import or_
    
    # جلب السيارة النشطة الحالية في المشروع
    current_vehicle = VehicleHandover.query.join(Vehicle).filter(
        or_(VehicleHandover.employee_id == employee_id, VehicleHandover.supervisor_employee_id == employee_id),
        VehicleHandover.handover_type == 'delivery',
        Vehicle.status == 'in_project'  # السيارات في المشاريع فقط
    ).order_by(VehicleHandover.handover_date.desc()).first()
    
    # جلب جميع السيارات التي تم ربطها بالموظف (تاريخ كامل)
    all_vehicle_handovers = VehicleHandover.query.join(Vehicle).filter(
        or_(VehicleHandover.employee_id == employee_id, VehicleHandover.supervisor_employee_id == employee_id)
    ).order_by(VehicleHandover.handover_date.desc()).all()

    return render_template('mobile/employee_details.html', 
                          employee=employee,
                          attendance_records=attendance_records,
                          salary=salary,
                          documents=documents,
                          current_vehicle=current_vehicle,
                          all_vehicle_handovers=all_vehicle_handovers,
                          current_date=current_date)

# صفحة تعديل موظف - النسخة المحمولة
@mobile_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    """صفحة تعديل موظف للنسخة المحمولة"""
    employee = Employee.query.get_or_404(employee_id)
    
    # معالجة الـ POST request لحفظ التعديلات
    if request.method == 'POST':
        try:
            # التحقق من عدم تكرار رقم الموظف (إذا تم تغييره)
            employee_id_value = request.form.get('employee_id')
            if employee_id_value and employee_id_value != employee.employee_id:
                existing_employee = Employee.query.filter_by(employee_id=employee_id_value).first()
                if existing_employee:
                    flash('رقم الموظف موجود بالفعل، يرجى استخدام رقم آخر', 'danger')
                    departments = Department.query.order_by(Department.name).all()
                    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
                    available_mobile_devices = MobileDevice.query.filter(
                        (MobileDevice.employee_id == None) | (MobileDevice.employee_id == employee.id)
                    ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
                    return render_template('mobile/edit_employee.html',
                                         employee=employee,
                                         departments=departments,
                                         nationalities=nationalities,
                                         available_mobile_devices=available_mobile_devices)
            
            # تحديث بيانات الموظف
            employee.name = request.form.get('name')
            employee.employee_id = employee_id_value
            employee.national_id = request.form.get('national_id')
            employee.mobile = request.form.get('mobile')
            employee.email = request.form.get('email')
            employee.job_title = request.form.get('job_title')
            employee.nationality_id = int(request.form.get('nationality_id')) if request.form.get('nationality_id') else None
            employee.department_id = int(request.form.get('department_id')) if request.form.get('department_id') else None
            employee.contract_status = request.form.get('contract_status')
            employee.license_status = request.form.get('license_status')
            employee.employee_type = request.form.get('employee_type')
            employee.status = request.form.get('status', 'active')
            employee.has_mobile_custody = request.form.get('has_mobile_custody') == 'yes'
            employee.sponsorship_status = request.form.get('sponsorship_status')
            employee.residence_details = request.form.get('residence_details')
            employee.pants_size = request.form.get('pants_size')
            employee.shirt_size = request.form.get('shirt_size')
            employee.location = request.form.get('location')
            employee.project = request.form.get('project')
            employee.join_date = datetime.strptime(request.form.get('join_date'), '%Y-%m-%d').date() if request.form.get('join_date') else None
            employee.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date() if request.form.get('birth_date') else None
            employee.basic_salary = float(request.form.get('basic_salary')) if request.form.get('basic_salary') else 0
            employee.attendance_bonus = float(request.form.get('attendance_bonus')) if request.form.get('attendance_bonus') else 0
            employee.residence_location_url = request.form.get('residence_location_url')
            employee.housing_drive_links = request.form.get('housing_drive_links')
            employee.current_sponsor_name = request.form.get('current_sponsor_name')
            
            # تحديث الأقسام
            department_ids = request.form.getlist('department_ids')
            if department_ids:
                employee.departments = Department.query.filter(Department.id.in_(department_ids)).all()
            else:
                employee.departments = []
            
            # تحديث تعيين الجهاز المحمول
            old_device = MobileDevice.query.filter_by(employee_id=employee.id).first()
            if old_device:
                old_device.employee_id = None
                old_device.assigned_date = None
                old_device.is_assigned = False
            
            if request.form.get('mobile_device_id'):
                mobile_device = MobileDevice.query.get(int(request.form.get('mobile_device_id')))
                if mobile_device:
                    mobile_device.employee_id = employee.id
                    mobile_device.assigned_date = datetime.now()
                    mobile_device.is_assigned = True
            
            db.session.commit()
            flash('تم تحديث بيانات الموظف بنجاح', 'success')
            return redirect(url_for('mobile.employee_details', employee_id=employee.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث الموظف: {str(e)}', 'danger')
    
    # جلب البيانات المطلوبة
    departments = Department.query.order_by(Department.name).all()
    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
    
    # جلب الأجهزة المحمولة المتاحة (غير المخصصة لموظف أو المخصصة للموظف الحالي)
    available_mobile_devices = MobileDevice.query.filter(
        (MobileDevice.employee_id == None) | (MobileDevice.employee_id == employee.id)
    ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
    
    return render_template('mobile/edit_employee.html',
                         employee=employee,
                         departments=departments,
                         nationalities=nationalities,
                         available_mobile_devices=available_mobile_devices)

# صفحة الأقسام - النسخة المحمولة
@mobile_bp.route('/departments')
@login_required
def departments():
    """صفحة الأقسام للنسخة المحمولة"""
    # الحصول على قائمة الأقسام
    departments = Department.query.all()
    employees_count = Employee.query.count()

    return render_template('mobile/departments.html',
                          departments=departments,
                          employees_count=employees_count)

# صفحة إضافة قسم جديد - النسخة المحمولة
@mobile_bp.route('/departments/add', methods=['GET', 'POST'])
@login_required
def add_department():
    """صفحة إضافة قسم جديد للنسخة المحمولة"""
    # الموظفين كمديرين محتملين للقسم
    employees = Employee.query.order_by(Employee.name).all()

    # ستتم إضافة وظيفة إضافة قسم جديد لاحقاً
    return render_template('mobile/add_department.html', 
                          employees=employees)

# صفحة تفاصيل القسم - النسخة المحمولة
@mobile_bp.route('/departments/<int:department_id>')
@login_required
def department_details(department_id):
    """صفحة تفاصيل القسم للنسخة المحمولة"""
    department = Department.query.get_or_404(department_id)
    return render_template('mobile/department_details.html', department=department)

# داش بورد الوثائق - النسخة المحمولة
@mobile_bp.route('/documents/dashboard')
@login_required
def documents_dashboard():
    """داش بورد لعرض إحصائيات الوثائق"""
    current_date = datetime.now().date()
    
    # حساب تواريخ الفترات
    expiring_date = current_date + timedelta(days=60)
    warning_date = current_date + timedelta(days=30)
    
    # إحصائيات الوثائق
    total_documents = Document.query.count()
    expired_documents = Document.query.filter(Document.expiry_date < current_date).count()
    expiring_soon = Document.query.filter(
        Document.expiry_date >= current_date,
        Document.expiry_date <= warning_date
    ).count()
    expiring_later = Document.query.filter(
        Document.expiry_date > warning_date,
        Document.expiry_date <= expiring_date
    ).count()
    valid_documents = Document.query.filter(Document.expiry_date > expiring_date).count()
    
    # الوثائق المنتهية (آخر 10)
    expired_docs = Document.query.join(Employee)\
        .filter(Document.expiry_date < current_date)\
        .order_by(Document.expiry_date.desc())\
        .limit(10).all()
    
    # الوثائق القريبة من الانتهاء (30 يوم)
    expiring_docs = Document.query.join(Employee)\
        .filter(Document.expiry_date >= current_date, Document.expiry_date <= warning_date)\
        .order_by(Document.expiry_date)\
        .limit(10).all()
    
    # إحصائيات حسب نوع الوثيقة
    document_types_stats = db.session.query(
        Document.document_type,
        func.count(Document.id).label('count')
    ).group_by(Document.document_type).all()
    
    # إحصائيات حسب القسم
    department_stats = db.session.query(
        Department.name,
        func.count(Document.id).label('count')
    ).select_from(Department)\
     .join(Employee, Employee.department_id == Department.id)\
     .join(Document, Document.employee_id == Employee.id)\
     .group_by(Department.name)\
     .order_by(func.count(Document.id).desc())\
     .limit(5).all()
    
    return render_template('mobile/documents_dashboard.html',
                         total_documents=total_documents,
                         expired_documents=expired_documents,
                         expiring_soon=expiring_soon,
                         expiring_later=expiring_later,
                         valid_documents=valid_documents,
                         expired_docs=expired_docs,
                         expiring_docs=expiring_docs,
                         document_types_stats=document_types_stats,
                         department_stats=department_stats,
                         current_date=current_date)

# صفحة الوثائق - النسخة المحمولة
@mobile_bp.route('/documents')
@login_required
def documents():
    """صفحة الوثائق للنسخة المحمولة"""
    # فلترة الوثائق بناءً على البارامترات
    employee_id_str = request.args.get('employee_id', '')
    employee_id = int(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
    document_type = request.args.get('document_type')
    status = request.args.get('status')  # valid, expiring, expired
    page = request.args.get('page', 1, type=int)
    per_page = 20  # عدد العناصر في الصفحة الواحدة

    # قم باستعلام قاعدة البيانات للحصول على قائمة الموظفين
    employees = Employee.query.order_by(Employee.name).all()

    # إنشاء استعلام أساسي للوثائق مع جلب بيانات الموظف
    query = Document.query.join(Employee)

    # إضافة فلاتر إلى الاستعلام إذا تم توفيرها
    if employee_id:
        query = query.filter(Document.employee_id == employee_id)

    # معالجة نوع الوثيقة - تحويل من العربية إلى الإنجليزية للبحث في قاعدة البيانات
    if document_type:
        document_type_mapping = {
            'هوية': 'national_id',
            'جواز سفر': 'passport',
            'رخصة قيادة': 'driving_license',
            'إقامة': 'residence_permit',
            'تأمين صحي': 'health_insurance',
            'شهادة عمل': 'work_certificate',
            'أخرى': 'other'
        }
        english_type = document_type_mapping.get(document_type, document_type)
        query = query.filter(Document.document_type == english_type)

    # الحصول على التاريخ الحالي
    current_date = datetime.now().date()

    # إضافة فلتر حالة الوثيقة
    if status:
        if status == 'valid':
            # وثائق سارية المفعول (تاريخ انتهاء الصلاحية بعد 60 يوم على الأقل من اليوم)
            valid_date = current_date + timedelta(days=60)
            query = query.filter(Document.expiry_date >= valid_date)
        elif status == 'expiring':
            # وثائق على وشك الانتهاء (تاريخ انتهاء الصلاحية خلال 60 يوم من اليوم)
            expiring_min_date = current_date
            expiring_max_date = current_date + timedelta(days=60)
            query = query.filter(Document.expiry_date >= expiring_min_date, 
                                Document.expiry_date <= expiring_max_date)
        elif status == 'expired':
            # وثائق منتهية الصلاحية (تاريخ انتهاء الصلاحية قبل اليوم)
            query = query.filter(Document.expiry_date < current_date)

    # تنفيذ الاستعلام مع ترتيب النتائج حسب تاريخ انتهاء الصلاحية
    query = query.order_by(Document.expiry_date)

    # تقسيم النتائج إلى صفحات
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items

    # إضافة حالة الوثيقة لكل وثيقة
    for document in documents:
        if document.expiry_date:
            if document.expiry_date >= current_date + timedelta(days=60):
                document.status = 'valid'
            elif document.expiry_date >= current_date:
                document.status = 'expiring'
            else:
                document.status = 'expired'
        else:
            document.status = 'no_expiry'

        # تحويل نوع الوثيقة من الإنجليزية للعربية للعرض
        document_type_display = {
            'national_id': 'هوية وطنية',
            'passport': 'جواز سفر',
            'driving_license': 'رخصة قيادة',
            'residence_permit': 'إقامة',
            'health_insurance': 'تأمين صحي',
            'work_certificate': 'شهادة عمل',
            'other': 'أخرى'
        }
        document.document_type_display = document_type_display.get(document.document_type, document.document_type)

    # حساب إحصائيات الوثائق
    valid_count = Document.query.filter(Document.expiry_date >= current_date + timedelta(days=60)).count()
    expiring_count = Document.query.filter(Document.expiry_date >= current_date, 
                                          Document.expiry_date <= current_date + timedelta(days=60)).count()
    expired_count = Document.query.filter(Document.expiry_date < current_date).count()
    total_count = Document.query.count()

    document_stats = {
        'valid': valid_count,
        'expiring': expiring_count,
        'expired': expired_count,
        'total': total_count
    }

    return render_template('mobile/documents.html',
                          employees=employees,
                          documents=documents,
                          current_date=current_date,
                          document_stats=document_stats,
                          pagination=pagination)

# إضافة وثيقة جديدة - النسخة المحمولة
@mobile_bp.route('/documents/add', methods=['GET', 'POST'])
@login_required
def add_document():
    """إضافة وثيقة جديدة للنسخة المحمولة"""
    # قائمة الموظفين للاختيار
    employees = Employee.query.order_by(Employee.name).all()
    current_date = datetime.now().date()

    # أنواع الوثائق المتاحة
    document_types = [
        'هوية وطنية',
        'إقامة',
        'جواز سفر',
        'رخصة قيادة',
        'شهادة صحية',
        'شهادة تأمين',
        'أخرى'
    ]

    # يمكن تنفيذ هذه الوظيفة لاحقًا
    return render_template('mobile/add_document.html',
                          employees=employees,
                          document_types=document_types,
                          current_date=current_date)

# تفاصيل وثيقة - النسخة المحمولة
@mobile_bp.route('/documents/<int:document_id>')
@login_required
def document_details(document_id):
    """تفاصيل وثيقة للنسخة المحمولة"""
    # الحصول على بيانات الوثيقة من قاعدة البيانات
    document = Document.query.get_or_404(document_id)

    # الحصول على التاريخ الحالي للمقارنة مع تاريخ انتهاء الصلاحية
    current_date = datetime.now().date()

    # حساب المدة المتبقية (أو المنقضية) لصلاحية الوثيقة
    days_remaining = None
    if document.expiry_date:
        days_remaining = (document.expiry_date - current_date).days

    return render_template('mobile/document_details.html',
                          document=document,
                          current_date=current_date,
                          days_remaining=days_remaining)

# تحديث تاريخ انتهاء الوثيقة - النسخة المحمولة
@mobile_bp.route('/documents/<int:document_id>/update-expiry', methods=['POST'])
@login_required
def update_document_expiry(document_id):
    """تحديث تاريخ انتهاء الوثيقة"""
    document = Document.query.get_or_404(document_id)
    
    try:
        # الحصول على التاريخ الجديد
        expiry_date_str = request.form.get('expiry_date')
        notes = request.form.get('notes', '').strip()
        
        if expiry_date_str:
            # تحويل النص إلى تاريخ
            from datetime import datetime
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            # تحديث تاريخ الانتهاء
            document.expiry_date = expiry_date
            
            # تحديث الملاحظات إذا وُجدت
            if notes:
                if document.notes:
                    document.notes = f"{document.notes}\n\n[تحديث {datetime.now().strftime('%Y-%m-%d')}]: {notes}"
                else:
                    document.notes = f"[تحديث {datetime.now().strftime('%Y-%m-%d')}]: {notes}"
            
            db.session.commit()
            flash('تم تحديث تاريخ انتهاء الوثيقة بنجاح', 'success')
        else:
            flash('يرجى إدخال تاريخ الانتهاء', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تحديث الوثيقة: {str(e)}', 'error')
    
    return redirect(url_for('mobile.document_details', document_id=document_id))

# صفحة التقارير - النسخة المحمولة
@mobile_bp.route('/reports')
@login_required
def reports():
    """صفحة التقارير للنسخة المحمولة"""
    # قائمة التقارير الأخيرة (يمكن جلبها من قاعدة البيانات لاحقًا)
    recent_reports = []
    return render_template('mobile/reports.html', recent_reports=recent_reports)

# تقرير الموظفين - النسخة المحمولة
@mobile_bp.route('/reports/employees')
@login_required
def report_employees():
    """تقرير الموظفين للنسخة المحمولة"""
    departments = Department.query.order_by(Department.name).all()

    # استخراج معلمات الاستعلام
    department_id = request.args.get('department_id')
    status = request.args.get('status')
    search = request.args.get('search')
    export_format = request.args.get('export')

    # إنشاء الاستعلام الأساسي
    query = Employee.query

    # تطبيق الفلترة
    if department_id:
        query = query.filter_by(department_id=department_id)

    if status:
        query = query.filter_by(status=status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.name.like(search_term)) |
            (Employee.employee_id.like(search_term)) |
            (Employee.national_id.like(search_term)) |
            (Employee.job_title.like(search_term))
        )

    # الحصول على جميع الموظفين المطابقين
    employees = query.order_by(Employee.name).all()

    # معالجة طلبات التصدير
    if export_format:
        try:
            if export_format == 'pdf':
                # استدعاء مسار التصدير PDF في النسخة الرئيسية
                return redirect(url_for('reports.export_employees_report', 
                                       export_type='pdf',
                                       department_id=department_id,
                                       status=status,
                                       search=search))

            elif export_format == 'excel':
                # استدعاء مسار التصدير Excel في النسخة الرئيسية
                return redirect(url_for('reports.export_employees_report',
                                       export_type='excel',
                                       department_id=department_id,
                                       status=status,
                                       search=search))
        except Exception as e:
            # تسجيل الخطأ في السجل
            print(f"خطأ في تصدير تقرير الموظفين: {str(e)}")

    # عرض الصفحة مع نتائج التقرير
    return render_template('mobile/report_employees.html', 
                         departments=departments,
                         employees=employees)

# تقرير الحضور - النسخة المحمولة
@mobile_bp.route('/reports/attendance')
@login_required
def report_attendance():
    """تقرير الحضور للنسخة المحمولة"""
    # الحصول على قائمة الأقسام للفلترة
    departments = Department.query.order_by(Department.name).all()

    # استخراج معلمات الاستعلام
    department_id = request.args.get('department_id')
    employee_id = request.args.get('employee_id')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    export_format = request.args.get('export')

    # استخراج الموظفين المطابقين للفلترة
    employees_query = Employee.query
    if department_id:
        employees_query = employees_query.filter_by(department_id=department_id)
    employees = employees_query.order_by(Employee.name).all()

    # إنشاء استعلام سجلات الحضور
    attendance_query = Attendance.query

    # تطبيق الفلترة على سجلات الحضور
    if employee_id:
        attendance_query = attendance_query.filter_by(employee_id=employee_id)
    elif department_id:
        # فلترة حسب القسم عن طريق الانضمام مع جدول الموظفين
        attendance_query = attendance_query.join(Employee).filter(Employee.department_id == department_id)

    if status:
        attendance_query = attendance_query.filter_by(status=status)

    if start_date:
        attendance_query = attendance_query.filter(Attendance.date >= start_date)

    if end_date:
        attendance_query = attendance_query.filter(Attendance.date <= end_date)

    # الحصول على سجلات الحضور المرتبة حسب التاريخ (تنازلياً)
    attendance_records = attendance_query.order_by(Attendance.date.desc()).all()

    # معالجة طلبات التصدير
    if export_format:
        try:
            if export_format == 'pdf':
                # استدعاء مسار التصدير PDF في النسخة الرئيسية
                return redirect(url_for('reports.attendance_pdf',
                                       department_id=department_id,
                                       employee_id=employee_id,
                                       status=status,
                                       start_date=start_date,
                                       end_date=end_date))

            elif export_format == 'excel':
                # استدعاء مسار التصدير Excel في النسخة الرئيسية
                return redirect(url_for('reports.attendance_excel',
                                       department_id=department_id,
                                       employee_id=employee_id,
                                       status=status,
                                       start_date=start_date,
                                       end_date=end_date))
        except Exception as e:
            # تسجيل الخطأ في السجل
            print(f"خطأ في تصدير تقرير الحضور: {str(e)}")

    # عرض الصفحة مع نتائج التقرير
    return render_template('mobile/report_attendance.html',
                         departments=departments,
                         employees=employees,
                         attendance_records=attendance_records)

# تقرير الرواتب - النسخة المحمولة
@mobile_bp.route('/reports/salaries')
@login_required
def report_salaries():
    """تقرير الرواتب للنسخة المحمولة"""
    # الحصول على قائمة الأقسام والموظفين للفلترة
    departments = Department.query.order_by(Department.name).all()

    # استخراج معلمات البحث
    department_id = request.args.get('department_id')
    employee_id = request.args.get('employee_id')
    is_paid = request.args.get('is_paid')
    year = request.args.get('year')
    month = request.args.get('month')
    export_format = request.args.get('export')

    # استخراج الموظفين المطابقين للفلترة
    employees_query = Employee.query
    if department_id:
        employees_query = employees_query.filter_by(department_id=department_id)
    employees = employees_query.order_by(Employee.name).all()

    # إنشاء استعلام الرواتب
    query = Salary.query

    # تطبيق الفلترة على الرواتب
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    elif department_id:
        # فلترة حسب القسم عن طريق الانضمام مع جدول الموظفين
        query = query.join(Employee).filter(Employee.department_id == department_id)

    if is_paid:
        is_paid_bool = (is_paid.lower() == 'true' or is_paid == '1')
        query = query.filter(Salary.is_paid == is_paid_bool)

    if year:
        query = query.filter(Salary.year == year)

    if month:
        query = query.filter(Salary.month == month)

    # الحصول على سجلات الرواتب المرتبة حسب التاريخ (تنازلياً)
    salaries = query.order_by(Salary.year.desc(), Salary.month.desc()).all()

    # معالجة طلبات التصدير
    if export_format:
        try:
            if export_format == 'pdf':
                # استدعاء مسار التصدير PDF في النسخة الرئيسية
                return redirect(url_for('reports.salaries_pdf',
                                      department_id=department_id,
                                      employee_id=employee_id,
                                      is_paid=is_paid,
                                      year=year,
                                      month=month))

            elif export_format == 'excel':
                # استدعاء مسار التصدير Excel في النسخة الرئيسية
                return redirect(url_for('reports.salaries_excel',
                                      department_id=department_id,
                                      employee_id=employee_id,
                                      is_paid=is_paid,
                                      year=year,
                                      month=month))
        except Exception as e:
            # تسجيل الخطأ في السجل
            print(f"خطأ في تصدير تقرير الرواتب: {str(e)}")

    # استخراج قائمة بالسنوات والأشهر المتاحة
    years_months = db.session.query(Salary.year, Salary.month)\
                  .order_by(Salary.year.desc(), Salary.month.desc())\
                  .distinct().all()

    # تجميع السنوات والأشهر
    available_years = sorted(list(set([ym[0] for ym in years_months])), reverse=True)
    available_months = sorted(list(set([ym[1] for ym in years_months])))

    return render_template('mobile/report_salaries.html',
                         departments=departments,
                         employees=employees,
                         salaries=salaries,
                         available_years=available_years,
                         available_months=available_months)

# تقرير الوثائق - النسخة المحمولة
@mobile_bp.route('/reports/documents')
@login_required
def report_documents():
    """تقرير الوثائق للنسخة المحمولة"""
    # الحصول على قائمة الأقسام والموظفين للفلترة
    departments = Department.query.order_by(Department.name).all()
    current_date = datetime.now().date()

    # استخراج معلمات البحث
    department_id = request.args.get('department_id')
    employee_id = request.args.get('employee_id')
    document_type = request.args.get('document_type')
    status = request.args.get('status')  # valid, expiring, expired
    export_format = request.args.get('export')

    # استخراج الموظفين المطابقين للفلترة
    employees_query = Employee.query
    if department_id:
        employees_query = employees_query.filter_by(department_id=department_id)
    employees = employees_query.order_by(Employee.name).all()

    # إنشاء استعلام الوثائق
    query = Document.query

    # تطبيق الفلترة على الوثائق
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    elif department_id:
        # فلترة حسب القسم عن طريق الانضمام مع جدول الموظفين
        query = query.join(Employee).filter(Employee.department_id == department_id)

    if document_type:
        query = query.filter_by(document_type=document_type)

    # فلترة حسب حالة الوثيقة (صالحة، على وشك الانتهاء، منتهية)
    if status:
        if status == 'valid':
            # وثائق سارية المفعول (تاريخ انتهاء الصلاحية بعد 60 يوم من الآن)
            valid_date = current_date + timedelta(days=60)
            query = query.filter(Document.expiry_date >= valid_date)
        elif status == 'expiring':
            # وثائق على وشك الانتهاء (تنتهي خلال 60 يوم)
            expiring_min_date = current_date
            expiring_max_date = current_date + timedelta(days=60)
            query = query.filter(Document.expiry_date >= expiring_min_date, 
                               Document.expiry_date <= expiring_max_date)
        elif status == 'expired':
            # وثائق منتهية الصلاحية
            query = query.filter(Document.expiry_date < current_date)

    # الحصول على الوثائق المرتبة حسب تاريخ انتهاء الصلاحية
    documents = query.order_by(Document.expiry_date).all()

    # معالجة طلبات التصدير
    if export_format:
        if export_format == 'pdf':
            # استدعاء مسار التصدير PDF في النسخة الرئيسية
            return redirect(url_for('reports.documents_pdf',
                                  department_id=department_id,
                                  employee_id=employee_id,
                                  document_type=document_type,
                                  status=status))

        elif export_format == 'excel':
            # استدعاء مسار التصدير Excel في النسخة الرئيسية
            return redirect(url_for('reports.documents_excel',
                                  department_id=department_id,
                                  employee_id=employee_id,
                                  document_type=document_type,
                                  status=status))

    # استخراج أنواع الوثائق المتاحة
    document_types = db.session.query(Document.document_type)\
                    .distinct().order_by(Document.document_type).all()
    document_types = [d[0] for d in document_types if d[0]]

    # إضافة عدد الأيام المتبقية لكل وثيقة
    for doc in documents:
        if doc.expiry_date:
            doc.days_remaining = (doc.expiry_date - current_date).days
        else:
            doc.days_remaining = None

    return render_template('mobile/report_documents.html',
                         departments=departments,
                         employees=employees,
                         documents=documents,
                         document_types=document_types,
                         current_date=current_date)

# تقرير السيارات - النسخة المحمولة 
@mobile_bp.route('/reports/vehicles')
@login_required
def report_vehicles():
    """تقرير السيارات للنسخة المحمولة"""
    # استخراج معلمات البحث
    vehicle_type = request.args.get('vehicle_type')
    status = request.args.get('status')
    search = request.args.get('search')
    export_format = request.args.get('export')

    # إنشاء استعلام المركبات
    query = Vehicle.query

    # تطبيق الفلترة على المركبات
    if vehicle_type:
        query = query.filter_by(make=vehicle_type)  # نستخدم make بدلاً من vehicle_type

    if status:
        query = query.filter_by(status=status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Vehicle.plate_number.like(search_term)) |
            (Vehicle.make.like(search_term)) |
            (Vehicle.model.like(search_term)) |
            (Vehicle.color.like(search_term))
        )

    # الحصول على المركبات المرتبة حسب الترتيب
    vehicles = query.order_by(Vehicle.plate_number).all()

    # معالجة طلبات التصدير
    if export_format:
        try:
            if export_format == 'pdf':
                # استدعاء مسار التصدير PDF في النسخة الرئيسية
                return redirect(url_for('reports.export_vehicles_report',
                                      export_type='pdf',
                                      vehicle_type=vehicle_type,
                                      status=status,
                                      search=search))

            elif export_format == 'excel':
                # استدعاء مسار التصدير Excel في النسخة الرئيسية
                return redirect(url_for('reports.export_vehicles_report',
                                      export_type='excel',
                                      vehicle_type=vehicle_type,
                                      status=status,
                                      search=search))
        except Exception as e:
            # تسجيل الخطأ في السجل
            print(f"خطأ في تصدير تقرير المركبات: {str(e)}")

    # استخراج انواع المركبات وحالات المركبات المتاحة
    # استخراج الشركات المصنعة من قاعدة البيانات
    vehicle_types = db.session.query(Vehicle.make)\
                    .distinct().order_by(Vehicle.make).all()
    vehicle_types = [vt[0] for vt in vehicle_types if vt[0]]

    vehicle_statuses = db.session.query(Vehicle.status)\
                      .distinct().order_by(Vehicle.status).all()
    vehicle_statuses = [vs[0] for vs in vehicle_statuses if vs[0]]

    # إحصائيات تفصيلية للماركات
    make_stats = db.session.query(Vehicle.make, func.count(Vehicle.id))\
                .filter(Vehicle.make.isnot(None))\
                .group_by(Vehicle.make)\
                .order_by(func.count(Vehicle.id).desc()).all()

    # إحصائيات تفصيلية للألوان
    color_stats = db.session.query(Vehicle.color, func.count(Vehicle.id))\
                 .filter(Vehicle.color.isnot(None))\
                 .group_by(Vehicle.color)\
                 .order_by(func.count(Vehicle.id).desc()).all()

    # إحصائيات عامة
    total_vehicles = len(vehicles)
    active_vehicles = len([v for v in vehicles if v.status in ['نشط', 'متاح', 'available']])
    maintenance_vehicles = len([v for v in vehicles if 'صيانة' in (v.status or '') or 'maintenance' in (v.status or '')])

    return render_template('mobile/report_vehicles.html',
                         vehicles=vehicles,
                         vehicle_types=vehicle_types,
                         vehicle_statuses=vehicle_statuses,
                         make_stats=make_stats,
                         color_stats=color_stats,
                         total_vehicles=total_vehicles,
                         active_vehicles=active_vehicles,
                         maintenance_vehicles=maintenance_vehicles)

# تقرير الرسوم - النسخة المحمولة
@mobile_bp.route('/reports/fees')
@login_required
def report_fees():
    """تقرير الرسوم للنسخة المحمولة"""
    # استخراج معلمات البحث
    fee_type = request.args.get('fee_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status')  # paid/unpaid
    export_format = request.args.get('export')

    # إنشاء استعلام الرسوم
    query = Fee.query

    # تطبيق الفلترة على الرسوم
    if fee_type:
        query = query.filter_by(fee_type=fee_type)

    if date_from:
        query = query.filter(Fee.due_date >= date_from)

    if date_to:
        query = query.filter(Fee.due_date <= date_to)

    if status:
        is_paid_bool = (status.lower() == 'paid')
        query = query.filter(Fee.is_paid == is_paid_bool)

    # الحصول على قائمة الرسوم المرتبة حسب تاريخ الاستحقاق
    fees = query.order_by(Fee.due_date).all()

    # معالجة طلبات التصدير
    if export_format:
        try:
            if export_format == 'pdf':
                # استدعاء مسار التصدير PDF في النسخة الرئيسية
                return redirect(url_for('reports.export_fees_report',
                                      export_type='pdf',
                                      fee_type=fee_type,
                                      date_from=date_from,
                                      date_to=date_to,
                                      status=status))

            elif export_format == 'excel':
                # استدعاء مسار التصدير Excel في النسخة الرئيسية
                return redirect(url_for('reports.export_fees_report',
                                      export_type='excel',
                                      fee_type=fee_type,
                                      date_from=date_from,
                                      date_to=date_to,
                                      status=status))
        except Exception as e:
            # تسجيل الخطأ في السجل
            print(f"خطأ في تصدير تقرير الرسوم: {str(e)}")

    # استخراج أنواع الرسوم المتاحة
    fee_types = db.session.query(Fee.fee_type)\
                .distinct().order_by(Fee.fee_type).all()
    fee_types = [f[0] for f in fee_types if f[0]]

    # احتساب إجماليات الرسوم
    total_fees = sum(fee.amount for fee in fees if fee.amount)
    total_paid = sum(fee.amount for fee in fees if fee.amount and fee.is_paid)
    total_unpaid = sum(fee.amount for fee in fees if fee.amount and not fee.is_paid)

    # الحصول على التاريخ الحالي
    current_date = datetime.now().date()

    return render_template('mobile/report_fees.html',
                         fees=fees,
                         fee_types=fee_types,
                         total_fees=total_fees,
                         total_paid=total_paid,
                         total_unpaid=total_unpaid,
                         current_date=current_date)


# ======================== روتات إدارة العمليات المحمولة ========================

@mobile_bp.route('/operations')
@login_required
def operations_dashboard():
    """لوحة إدارة العمليات الرئيسية للنسخة المحمولة"""
    
    # التحقق من صلاحيات المدير فقط
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('mobile.dashboard'))

    # استلام قيمة البحث من رابط URL
    search_plate = request.args.get('search_plate', '').strip()

    # بناء استعلام العمليات المعلقة
    pending_query = OperationRequest.query.filter_by(status='pending')

    # تطبيق فلتر البحث (إذا تم إدخال قيمة)
    if search_plate:
        pending_query = pending_query.join(Vehicle).filter(Vehicle.plate_number.ilike(f"%{search_plate}%"))

    # تنفيذ الاستعلام النهائي
    pending_requests = pending_query.order_by(
        OperationRequest.priority.desc(),
        OperationRequest.requested_at.desc()
    ).limit(10).all()

    # إحصائيات العمليات
    stats = {
        'pending': OperationRequest.query.filter_by(status='pending').count(),
        'under_review': OperationRequest.query.filter_by(status='under_review').count(),
        'approved': OperationRequest.query.filter_by(status='approved').count(),
        'rejected': OperationRequest.query.filter_by(status='rejected').count(),
        'unread_notifications': OperationNotification.query.filter_by(user_id=current_user.id, is_read=False).count() if hasattr(current_user, 'id') else 0
    }

    return render_template('mobile/operations.html', 
                         stats=stats, 
                         pending_requests=pending_requests)

@mobile_bp.route('/operations/list')
@login_required
def operations_list():
    """قائمة جميع العمليات مع فلترة للنسخة المحمولة"""
    
    # التحقق من صلاحيات المدير فقط
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('mobile.dashboard'))
    
    # فلترة العمليات
    status_filter = request.args.get('status', 'all')
    operation_type_filter = request.args.get('operation_type', 'all')
    priority_filter = request.args.get('priority', 'all')
    vehicle_search = request.args.get('vehicle_search', '').strip()
    
    query = OperationRequest.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if operation_type_filter != 'all':
        query = query.filter_by(operation_type=operation_type_filter)
    
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    # البحث حسب السيارة أو المحتوى
    if vehicle_search:
        query = query.filter(
            or_(
                OperationRequest.title.contains(vehicle_search),
                OperationRequest.description.contains(vehicle_search)
            )
        )
    
    # ترتيب العمليات
    operations = query.order_by(
        OperationRequest.priority.desc(),
        OperationRequest.requested_at.desc()
    ).all()
    
    return render_template('mobile/operations_list.html', 
                         operations=operations,
                         status_filter=status_filter,
                         operation_type_filter=operation_type_filter,
                         priority_filter=priority_filter,
                         vehicle_search=vehicle_search)

@mobile_bp.route('/operations/<int:operation_id>')
@login_required
def operation_details(operation_id):
    """عرض تفاصيل العملية للنسخة المحمولة"""
    
    # التحقق من صلاحيات المدير فقط
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('mobile.dashboard'))
    
    operation = OperationRequest.query.get_or_404(operation_id)
    related_record = operation.get_related_record()
    
    # جلب الصور المرتبطة إذا كانت العملية من نوع الورشة
    workshop_images = []
    if operation.operation_type == 'workshop_record' and related_record:
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT id, image_type, image_path, notes, uploaded_at FROM vehicle_workshop_images WHERE workshop_record_id = :workshop_id ORDER BY uploaded_at DESC"),
                {'workshop_id': related_record.id}
            )
            workshop_images = [
                {
                    'id': row[0],
                    'image_type': row[1],
                    'image_path': row[2],
                    'notes': row[3],
                    'uploaded_at': row[4]
                } 
                for row in result
            ]
        except Exception as e:
            current_app.logger.error(f"خطأ في جلب صور الورشة: {str(e)}")
    
    return render_template('mobile/operation_details.html', 
                         operation=operation,
                         related_record=related_record,
                         workshop_images=workshop_images)

@mobile_bp.route('/operations/notifications')
@login_required
def operations_notifications():
    """صفحة الإشعارات للنسخة المحمولة"""
    
    # التحقق من صلاحيات المدير فقط
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('mobile.dashboard'))
    
    # جلب الإشعارات مرتبة بالتاريخ
    notifications = OperationNotification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        OperationNotification.is_read.asc(),  # غير المقروءة أولاً
        OperationNotification.created_at.desc()
    ).limit(50).all()  # أحدث 50 إشعار
    
    # عدد الإشعارات غير المقروءة
    unread_count = OperationNotification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).count()
    
    return render_template('mobile/operations_notifications.html',
                         notifications=notifications,
                         unread_count=unread_count)
