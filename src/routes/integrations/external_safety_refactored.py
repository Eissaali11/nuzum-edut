"""
External Safety Check Routes (Slim Controller)
===============================================
يحتوي فقط على:
- Route definitions
- Request/Response handling
- Input validation & sanitization
- Calling service layer methods
- Rendering templates

لا يحتوي على:
- منطق الأعمال (Business Logic) - موجود في services/external_safety_service.py
- Database queries مباشرة - يتم عن طريق Service
- معالجة ملفات معقدة - موجود في Service

الهيكلة:
--------
1. Public Routes (للسائقين):
   - /external-safety-check/<vehicle_id> - نموذج الفحص
   - /success/<check_id> - صفحة النجاح
   - /status/<check_id> - حالة الفحص
   
2. Admin Routes (للمشرفين):
   - /admin/external-safety-checks - قائمة الفحوصات
   - /admin/external-safety-check/<check_id> - عرض فحص محدد
   - /admin/external-safety-check/<check_id>/approve - موافقة
   - /admin/external-safety-check/<check_id>/reject - رفض
   - /admin/external-safety-check/<check_id>/edit - تعديل
   - /admin/external-safety-check/<check_id>/delete - حذف
   - /admin/external-safety-check/<check_id>/pdf - تصدير PDF

3. Share & Export Routes:
   - /share-links - روابط المشاركة
   - /share-links/export-excel - تصدير Excel
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_file
from flask_login import current_user, login_required
from datetime import datetime
import base64

# Import Service Layer
from src.services.external_safety_service import ExternalSafetyService

# Import Models (for template rendering and basic queries only)
from models import Vehicle, VehicleExternalSafetyCheck, User, Employee, Department, employee_departments, VehicleHandover
from src.core.extensions import db

# Blueprint Definition
external_safety_bp = Blueprint('external_safety', __name__)


# ===============================
# Public Routes (Driver Access)
# ===============================

@external_safety_bp.route('/external-safety-check/<int:vehicle_id>', methods=['GET', 'POST'])
def external_safety_check_form(vehicle_id):
    """
    عرض نموذج فحص السلامة الخارجي أو معالجة البيانات
    
    GET: عرض النموذج
    POST: حفظ البيانات
    """
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'GET':
        return render_template('external_safety_check.html', vehicle=vehicle)
    
    # POST: معالجة الإرسال
    try:
        # 1. Input Validation
        driver_name = request.form.get('driver_name', '').strip()
        driver_national_id = request.form.get('driver_national_id', '').strip()
        driver_department = request.form.get('driver_department', '').strip()
        driver_city = request.form.get('driver_city', '').strip()
        
        if not all([driver_name, driver_national_id, driver_department, driver_city]):
            return jsonify({'success': False, 'error': 'يرجى ملء جميع الحقول المطلوبة'}), 400
        
        # 2. Build data object for service
        check_data = {
            'vehicle_id': vehicle.id,
            'vehicle_plate_number': request.form.get('vehicle_plate_number', vehicle.plate_number),
            'vehicle_make_model': request.form.get('vehicle_make_model', f"{vehicle.make} {vehicle.model}"),
            'driver_name': driver_name,
            'driver_national_id': driver_national_id,
            'driver_department': driver_department,
            'driver_city': driver_city,
            'current_delegate': request.form.get('current_delegate', ''),
            'notes': request.form.get('notes', ''),
            'tires_ok': request.form.get('tires_ok') == 'on',
            'lights_ok': request.form.get('lights_ok') == 'on',
            'mirrors_ok': request.form.get('mirrors_ok') == 'on',
            'body_ok': request.form.get('body_ok') == 'on',
            'cleanliness_ok': request.form.get('cleanliness_ok') == 'on'
        }
        
        # 3. Create safety check via service
        current_user_id = current_user.id if current_user.is_authenticated else None
        result = ExternalSafetyService.create_safety_check(check_data, current_user_id)
        
        if not result['success']:
            flash(f'حدث خطأ: {result["message"]}', 'danger')
            return redirect(url_for('external_safety.external_safety_check_form', vehicle_id=vehicle.id))
        
        safety_check = result['check']
        
        # 4. Process uploaded images (from file input)
        uploaded_files = request.files.getlist('file_images')
        if uploaded_files and uploaded_files[0].filename:
            img_result = ExternalSafetyService.process_uploaded_images(uploaded_files, safety_check.id)
            if img_result['errors']:
                current_app.logger.warning(f"بعض الصور فشلت: {img_result['errors']}")
        
        # 5. Process camera images (from base64)
        camera_images = request.form.get('camera_images', '')
        if camera_images:
            image_list = camera_images.split('|||')
            image_notes_list = request.form.get('image_notes', '').split('|||')
            
            # استخدام service method مخصص لمعالجة base64
            _process_base64_images(safety_check.id, image_list, image_notes_list)
        
        # 6. Send notifications to admins
        _notify_all_users_of_new_check(safety_check)
        
        # 7. Send supervisor email
        ExternalSafetyService.send_supervisor_notification_email(safety_check)
        
        # 8. Auto-upload to Google Drive (non-blocking)
        try:
            ExternalSafetyService.upload_to_google_drive(safety_check.id, current_user_id)
        except Exception as e:
            current_app.logger.error(f'خطأ في الرفع التلقائي إلى Drive: {str(e)}')
        
        # 9. Redirect to success page
        return redirect(url_for('external_safety.success_page', safety_check_id=safety_check.id))
    
    except Exception as e:
        current_app.logger.error(f'خطأ في معالجة فحص السلامة: {str(e)}')
        flash('حدث خطأ أثناء معالجة الطلب', 'danger')
        return redirect(url_for('external_safety.external_safety_check_form', vehicle_id=vehicle.id))


@external_safety_bp.route('/success/<int:safety_check_id>')
def success_page(safety_check_id):
    """صفحة تأكيد إرسال طلب فحص السلامة"""
    safety_check = ExternalSafetyService.get_safety_check_by_id(safety_check_id)
    return render_template('external_safety_success.html', safety_check=safety_check)


@external_safety_bp.route('/status/<int:safety_check_id>')
def check_status(safety_check_id):
    """
    API: التحقق من حالة طلب فحص السلامة
    
    Returns:
        JSON: {'type': 'success|error|pending', 'title': str, 'text': str}
    """
    safety_check = ExternalSafetyService.get_safety_check_by_id(safety_check_id)
    
    status_messages = {
        'approved': {
            'type': 'success',
            'title': 'تم اعتماد الطلب',
            'text': 'تم اعتماد طلب فحص السلامة بنجاح من قبل الإدارة.'
        },
        'rejected': {
            'type': 'error',
            'title': 'تم رفض الطلب',
            'text': f'نرجو المحاولة مرة أخرى.\nسبب الرفض: {safety_check.review_notes or "لم يتم تحديد السبب"}'
        },
        'pending': {
            'type': 'pending',
            'title': 'قيد المراجعة',
            'text': 'طلبك قيد المراجعة من قبل الإدارة المختصة.'
        }
    }
    
    message = status_messages.get(safety_check.approval_status, status_messages['pending'])
    return jsonify(message)


@external_safety_bp.route('/api/verify-employee/<national_id>')
def verify_employee(national_id):
    """
    API: التحقق من وجود موظف بواسطة رقم الهوية
    
    Returns:
        JSON: {'exists': bool, 'name': str|null}
    """
    result = ExternalSafetyService.verify_employee_by_national_id(national_id)
    return jsonify({
        'exists': result['exists'],
        'name': result['name']
    })


# ===============================
# Admin Routes
# ===============================

@external_safety_bp.route('/admin/external-safety-checks')
@login_required
def admin_external_safety_checks():
    """
    صفحة إدارة فحوصات السلامة مع الفلاتر
    """
    # استخراج الفلاتر من Query Parameters
    filters = {
        'status': request.args.get('status', ''),
        'vehicle_id': request.args.get('vehicle_id', type=int),
        'driver_name': request.args.get('driver_name', ''),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date')
    }
    
    # تنظيف الفلاتر الفارغة
    filters = {k: v for k, v in filters.items() if v}
    
    # Convert date strings to datetime if provided
    if 'start_date' in filters:
        try:
            filters['start_date'] = datetime.strptime(filters['start_date'], '%Y-%m-%d')
        except ValueError:
            filters.pop('start_date')
    
    if 'end_date' in filters:
        try:
            filters['end_date'] = datetime.strptime(filters['end_date'], '%Y-%m-%d')
        except ValueError:
            filters.pop('end_date')
    
    # استرجاع الفحوصات من Service
    checks = ExternalSafetyService.get_safety_checks_with_filters(filters)
    
    # استرجاع احصائيات
    stats = ExternalSafetyService.get_safety_check_statistics()
    
    # استرجاع قائمة المركبات للفلتر
    vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    
    return render_template(
        'admin_external_safety_checks.html',
        checks=checks,
        stats=stats,
        vehicles=vehicles,
        filters=filters
    )


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>')
@login_required
def admin_view_safety_check(check_id):
    """عرض تفاصيل فحص السلامة"""
    check = ExternalSafetyService.get_safety_check_by_id(check_id)
    return render_template('admin_view_safety_check.html', check=check)


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/approve', methods=['POST'])
@login_required
def approve_safety_check(check_id):
    """
    الموافقة على فحص السلامة
    """
    result = ExternalSafetyService.approve_safety_check(
        check_id=check_id,
        reviewer_id=current_user.id,
        reviewer_name=current_user.username
    )
    
    if result['success']:
        flash('تم اعتماد فحص السلامة بنجاح', 'success')
    else:
        flash(f'حدث خطأ: {result["message"]}', 'danger')
    
    return redirect(url_for('external_safety.admin_external_safety_checks'))


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/reject', methods=['GET', 'POST'])
@login_required
def reject_safety_check_page(check_id):
    """
    صفحة رفض فحص السلامة
    
    GET: عرض نموذج الرفض
    POST: تنفيذ الرفض
    """
    check = ExternalSafetyService.get_safety_check_by_id(check_id)
    
    if request.method == 'GET':
        return render_template('reject_safety_check.html', check=check)
    
    # POST: تنفيذ الرفض
    rejection_reason = request.form.get('rejection_reason', '').strip()
    
    if not rejection_reason:
        flash('يرجى إدخال سبب الرفض', 'warning')
        return render_template('reject_safety_check.html', check=check)
    
    result = ExternalSafetyService.reject_safety_check(
        check_id=check_id,
        reviewer_id=current_user.id,
        reviewer_name=current_user.username,
        rejection_reason=rejection_reason
    )
    
    if result['success']:
        flash('تم رفض فحص السلامة', 'info')
    else:
        flash(f'حدث خطأ: {result["message"]}', 'danger')
    
    return redirect(url_for('external_safety.admin_external_safety_checks'))


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_safety_check(check_id):
    """
    تعديل فحص السلامة
    
    GET: عرض نموذج التعديل
    POST: حفظ التعديلات
    """
    check = ExternalSafetyService.get_safety_check_by_id(check_id)
    
    if request.method == 'GET':
        return render_template('edit_safety_check.html', check=check)
    
    # POST: حفظ التعديلات
    update_data = {
        'driver_name': request.form.get('driver_name'),
        'notes': request.form.get('notes'),
        'tires_ok': request.form.get('tires_ok') == 'on',
        'lights_ok': request.form.get('lights_ok') == 'on',
        'mirrors_ok': request.form.get('mirrors_ok') == 'on',
        'body_ok': request.form.get('body_ok') == 'on',
        'cleanliness_ok': request.form.get('cleanliness_ok') == 'on'
    }
    
    result = ExternalSafetyService.update_safety_check(
        check_id=check_id,
        data=update_data,
        current_user_id=current_user.id
    )
    
    if result['success']:
        flash('تم تحديث فحص السلامة بنجاح', 'success')
        return redirect(url_for('external_safety.admin_view_safety_check', check_id=check_id))
    else:
        flash(f'حدث خطأ: {result["message"]}', 'danger')
        return render_template('edit_safety_check.html', check=check)


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_external_safety_check(check_id):
    """
    حذف فحص السلامة
    
    GET: عرض صفحة التأكيد
    POST: تنفيذ الحذف
    """
    check = ExternalSafetyService.get_safety_check_by_id(check_id)
    
    if request.method == 'GET':
        return render_template('delete_safety_check_confirm.html', check=check)
    
    # POST: تنفيذ الحذف
    result = ExternalSafetyService.delete_safety_check(
        check_id=check_id,
        user_id=current_user.id
    )
    
    if result['success']:
        flash('تم حذف فحص السلامة بنجاح', 'success')
    else:
        flash(f'حدث خطأ: {result["message"]}', 'danger')
    
    return redirect(url_for('external_safety.admin_external_safety_checks'))


@external_safety_bp.route('/admin/bulk-delete-safety-checks', methods=['POST'])
@login_required
def bulk_delete_safety_checks():
    """
    حذف فحوصات متعددة دفعة واحدة
    """
    check_ids = request.form.getlist('check_ids[]', type=int)
    
    if not check_ids:
        return jsonify({'success': False, 'message': 'لم يتم تحديد أي فحوصات'}), 400
    
    result = ExternalSafetyService.bulk_delete_safety_checks(
        check_ids=check_ids,
        user_id=current_user.id
    )
    
    return jsonify(result)


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/delete-images', methods=['POST'])
@login_required
def delete_safety_check_images(check_id):
    """
    حذف صور من فحص السلامة
    """
    image_ids = request.form.getlist('image_ids[]', type=int)
    
    if not image_ids:
        return jsonify({'success': False, 'message': 'لم يتم تحديد أي صور'}), 400
    
    result = ExternalSafetyService.delete_safety_check_images(
        check_id=check_id,
        image_ids=image_ids
    )
    
    return jsonify(result)


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/upload-file', methods=['POST'])
@login_required
def upload_safety_check_file(check_id):
    """
    رفع ملف إضافي لفحص السلامة
    """
    check = ExternalSafetyService.get_safety_check_by_id(check_id)
    
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or not uploaded_files[0].filename:
        return jsonify({'success': False, 'message': 'لم يتم اختيار ملفات'}), 400
    
    result = ExternalSafetyService.process_uploaded_images(uploaded_files, check_id)
    
    if result['success']:
        flash(f'تم رفع {result["uploaded_count"]} ملف بنجاح', 'success')
    else:
        flash('فشل رفع الملفات', 'danger')
    
    return redirect(url_for('external_safety.admin_view_safety_check', check_id=check_id))


@external_safety_bp.route('/admin/external-safety-check/<int:check_id>/upload-to-drive', methods=['POST'])
@login_required
def upload_safety_check_to_drive(check_id):
    """
    رفع فحص السلامة إلى Google Drive
    """
    result = ExternalSafetyService.upload_to_google_drive(
        check_id=check_id,
        user_id=current_user.id
    )
    
    if result['success']:
        flash('تم رفع الفحص إلى Google Drive بنجاح', 'success')
    else:
        flash(f'حدث خطأ: {result["message"]}', 'danger')
    
    return redirect(url_for('external_safety.admin_view_safety_check', check_id=check_id))


# ===============================
# Share & Export Routes
# ===============================

@external_safety_bp.route('/')
def external_safety_index():
    """الصفحة الرئيسية لنظام فحص السلامة الخارجية"""
    return redirect(url_for('external_safety.share_links'))


@external_safety_bp.route('/share-links')
@login_required
def share_links():
    """
    صفحة مشاركة روابط النماذج الخارجية لجميع السيارات مع الفلاتر
    """
    # استخراج الفلاتر
    status_filter = request.args.get('status', '')
    make_filter = request.args.get('make', '')
    search_plate = request.args.get('search_plate', '')
    project_filter = request.args.get('project', '')
    
    # قاعدة الاستعلام
    query = Vehicle.query
    
    # فلترة حسب القسم المحدد للمستخدم
    if current_user.assigned_department_id:
        dept_employee_ids = db.session.query(Employee.id).join(
            employee_departments
        ).join(Department).filter(
            Department.id == current_user.assigned_department_id
        ).all()
        
        dept_employee_ids = [emp[0] for emp in dept_employee_ids]
        
        if dept_employee_ids:
            latest_handover_subq = db.session.query(
                VehicleHandover.vehicle_id,
                func.max(VehicleHandover.handover_date).label('latest_date')
            ).filter(
                VehicleHandover.handover_type.in_(['delivery', 'تسليم', 'handover'])
            ).group_by(VehicleHandover.vehicle_id).subquery()
            
            assigned_vehicles_subq = db.session.query(
                VehicleHandover.vehicle_id
            ).join(
                latest_handover_subq,
                db.and_(
                    VehicleHandover.vehicle_id == latest_handover_subq.c.vehicle_id,
                    VehicleHandover.handover_date == latest_handover_subq.c.latest_date
                )
            ).filter(
                VehicleHandover.employee_id.in_(dept_employee_ids)
            ).subquery()
            
            query = query.filter(Vehicle.id.in_(assigned_vehicles_subq))
    
    # تطبيق الفلاتر
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if make_filter:
        query = query.filter_by(make=make_filter)
    
    if search_plate:
        query = query.filter(Vehicle.plate_number.ilike(f'%{search_plate}%'))
    
    if project_filter:
        from models import Project
        query = query.join(Project).filter(Project.name.ilike(f'%{project_filter}%'))
    
    # ترتيب النتائج
    query = query.order_by(Vehicle.plate_number)
    
    vehicles = query.all()
    
    # استرجاع السائقين الحاليين
    current_drivers_map = ExternalSafetyService.get_all_current_drivers()
    
    # استرجاع قوائم للفلاتر
    all_makes = db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
    all_makes = [make[0] for make in all_makes if make[0]]
    
    return render_template(
        'external_safety_share_links.html',
        vehicles=vehicles,
        current_drivers_map=current_drivers_map,
        all_makes=all_makes,
        filters={
            'status': status_filter,
            'make': make_filter,
            'search_plate': search_plate,
            'project': project_filter
        }
    )


@external_safety_bp.route('/share-links/export-excel')
@login_required
def export_share_links_excel():
    """
    تصدير روابط المشاركة إلى Excel
    """
    # TODO: تنفيذ تصدير Excel
    # يمكن استخدام openpyxl أو pandas
    flash('ميزة التصدير قيد التطوير', 'info')
    return redirect(url_for('external_safety.share_links'))


# ===============================
# API Routes (for mobile/external)
# ===============================

@external_safety_bp.route('/api/send-whatsapp', methods=['POST'])
def send_vehicle_whatsapp():
    """
    API: إرسال رابط الفحص عبر WhatsApp
    """
    data = request.get_json()
    phone_number = data.get('phone_number')
    vehicle_plate = data.get('vehicle_plate')
    check_url = data.get('check_url')
    
    if not all([phone_number, vehicle_plate, check_url]):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    result = ExternalSafetyService.send_whatsapp_notification(
        phone_number=phone_number,
        vehicle_plate=vehicle_plate,
        check_url=check_url
    )
    
    return jsonify(result)


@external_safety_bp.route('/api/send-email', methods=['POST'])
@login_required
def send_vehicle_email():
    """
    API: إرسال رابط الفحص عبر البريد الإلكتروني
    """
    data = request.get_json()
    email = data.get('email')
    vehicle_plate = data.get('vehicle_plate')
    check_url = data.get('check_url')
    
    if not all([email, vehicle_plate, check_url]):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    # TODO: استخدام service method لإرسال البريد
    flash('ميزة إرسال البريد قيد التطوير', 'info')
    return jsonify({'success': False, 'message': 'الميزة غير متاحة حالياً'})


@external_safety_bp.route('/test-notifications', methods=['GET', 'POST'])
def test_safety_check_notifications():
    """
    اختبار إنشاء إشعارات فحص السلامة لجميع المستخدمين
    """
    try:
        # الحصول على آخر فحص سلامة
        last_check = VehicleExternalSafetyCheck.query.order_by(
            VehicleExternalSafetyCheck.id.desc()
        ).first()
        
        if not last_check:
            return jsonify({'success': False, 'message': 'لا توجد فحوصات سلامة'}), 404
        
        all_users = User.query.all()
        notification_count = 0
        
        for user in all_users:
            try:
                ExternalSafetyService.create_safety_check_notification(
                    user_id=user.id,
                    vehicle_plate=last_check.vehicle_plate_number or 'غير محدد',
                    supervisor_name=last_check.driver_name or 'غير محدد',
                    check_status=last_check.approval_status or 'pending',
                    check_id=last_check.id
                )
                notification_count += 1
            except Exception as e:
                current_app.logger.error(f'خطأ في إنشاء إشعار للمستخدم {user.id}: {str(e)}')
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء {notification_count} إشعار للفحص رقم {last_check.id}'
        })
    
    except Exception as e:
        current_app.logger.error(f'خطأ في اختبار الإشعارات: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ===============================
# Helper Functions (Controller Level)
# ===============================

def _process_base64_images(safety_check_id, image_list, notes_list):
    """
    معالجة الصور من base64 (camera images)
    
    Note: هذه دالة مساعدة محلية - يمكن نقلها للـ service إذا تكررت
    """
    from models import VehicleSafetyImage
    import uuid
    import os
    from werkzeug.utils import secure_filename
    from src.utils.storage_helper import upload_image
    
    for i, image_data in enumerate(image_list):
        if not image_data or not image_data.startswith('data:image'):
            continue
        
        try:
            # استخراج البيانات من base64
            header, data = image_data.split(',', 1)
            image_bytes = base64.b64decode(data)
            
            # تحديد التنسيق
            ext = 'jpg'  # افتراضي
            if 'png' in header:
                ext = 'png'
            elif 'heic' in header or 'heif' in header:
                ext = 'heic'
            
            # إنشاء اسم ملف آمن
            filename = f"{uuid.uuid4()}.{ext}"
            
            # حفظ مؤقتaً
            temp_dir = os.path.join(current_app.static_folder, '.temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, filename)
            
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)
            
            # ضغط الصورة
            ExternalSafetyService.compress_image(temp_path)
            
            # قراءة الصورة المضغوطة
            with open(temp_path, 'rb') as f:
                compressed_data = f.read()
            
            # رفع إلى السحابة
            cloud_url = upload_image(temp_path, 'safety_checks')
            
            if cloud_url:
                # حفظ في قاعدة البيانات
                description = notes_list[i] if i < len(notes_list) else None
                
                safety_image = VehicleSafetyImage(
                    safety_check_id=safety_check_id,
                    image_url=cloud_url,
                    image_description=description
                )
                db.session.add(safety_image)
            
            # حذف الملف المؤقت
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        except Exception as e:
            current_app.logger.error(f"خطأ في معالجة صورة base64 {i}: {str(e)}")
            continue
    
    db.session.commit()


def _notify_all_users_of_new_check(safety_check):
    """
    إرسال إشعارات لجميع المستخدمين عند إنشاء فحص جديد
    """
    try:
        all_users = User.query.all()
        current_app.logger.info(f"Found {len(all_users)} users for safety check notifications")
        
        for user in all_users:
            try:
                ExternalSafetyService.create_safety_check_notification(
                    user_id=user.id,
                    vehicle_plate=safety_check.vehicle_plate_number,
                    supervisor_name=safety_check.driver_name,
                    check_status='pending',
                    check_id=safety_check.id
                )
            except Exception as e:
                current_app.logger.error(f'خطأ في إنشاء إشعار للمستخدم {user.id}: {str(e)}')
    
    except Exception as e:
        current_app.logger.error(f'خطأ في إنشاء إشعارات فحص السلامة: {str(e)}')
