"""Auto-split from vehicle_lifecycle_routes.py: mobile vehicle lifecycle subdomain routes."""

"""Auto-split from vehicle_routes.py: mobile vehicle domain routes."""

"""
مسارات المركبات (السيارات، الورشة، التسليم/الاستلام، التصريحات الخارجية) للجوال.
مستخرجة من routes/mobile.py. تُسجّل على mobile_bp عبر register_vehicle_routes(mobile_bp).
"""
import base64
import io
import os
import uuid
from datetime import datetime, timedelta, date

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from models import (
    Department,
    Employee,
    ExternalAuthorization,
    GeofenceSession,
    OperationNotification,
    OperationRequest,
    Vehicle,
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
    employee_departments,
)
from core.extensions import db
from routes.operations import create_operation_request
from modules.vehicles.application.vehicle_service import update_vehicle_driver
from utils.audit_logger import log_activity
from utils.decorators import module_access_required, permission_required
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state

def register_vehicle_workshop_routes(bp):
    @bp.route('/vehicles/<int:vehicle_id>/workshop/test', methods=['GET'])
    @login_required
    def test_workshop_save(vehicle_id):
        """اختبار حفظ سجل الورشة تجريبياً"""
        try:
            # إنشاء سجل ورشة تجريبي
            workshop_record = VehicleWorkshop(
                vehicle_id=vehicle_id,
                entry_date=datetime.now().date(),
                reason='maintenance',
                description='اختبار تجريبي من النظام',
                repair_status='in_progress',
                cost=500.0,
                workshop_name='ورشة الاختبار',
                technician_name='فني الاختبار',
                delivery_link='https://example.com/delivery',
                reception_link='https://example.com/pickup',
                notes='سجل تجريبي للاختبار - تم إنشاؤه تلقائياً'
            )
    
            db.session.add(workshop_record)
            db.session.commit()
    
            flash(f'تم إضافة سجل الورشة التجريبي رقم {workshop_record.id} بنجاح!', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في الاختبار التجريبي للسيارة {vehicle_id}: {str(e)}")
            flash(f'فشل الاختبار التجريبي: {str(e)}', 'danger')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    # إضافة سجل ورشة جديد - النسخة المحمولة
    @bp.route('/vehicles/<int:vehicle_id>/workshop/add', methods=['GET', 'POST'])
    @login_required
    def add_workshop_record(vehicle_id):
        """إضافة سجل ورشة جديد للسيارة من النسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        # فحص قيود العمليات للسيارات خارج الخدمة
        from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        if request.method == 'POST':
            try:
                current_app.logger.debug(f"تجهيز بيانات النموذج لسجل الورشة للسيارة {vehicle_id}")
    
                # استخراج البيانات من النموذج
                entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
                exit_date_str = request.form.get('exit_date')
                exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
                reason = request.form.get('reason')
                description = request.form.get('description')
                repair_status = request.form.get('repair_status')
                cost = float(request.form.get('cost') or 0)
                workshop_name = request.form.get('workshop_name')
                technician_name = request.form.get('technician_name')
                notes = request.form.get('notes')
                delivery_link = request.form.get('delivery_form_link')
                reception_link = request.form.get('pickup_form_link')
    
                current_app.logger.debug(f"البيانات المستخرجة: {reason}, {description}, {repair_status}")
    
                # إنشاء سجل ورشة جديد
                workshop_record = VehicleWorkshop(
                    vehicle_id=vehicle_id,
                    entry_date=entry_date,
                    exit_date=exit_date,
                    reason=reason,
                    description=description,
                    repair_status=repair_status,
                    cost=cost,
                    workshop_name=workshop_name,
                    technician_name=technician_name,
                    notes=notes,
                    delivery_link=delivery_link,
                    reception_link=reception_link
                )
    
                db.session.add(workshop_record)
                db.session.flush()  # للحصول على معرف سجل الورشة
    
                # معالجة الصور قبل الإصلاح
                before_images = request.files.getlist('before_images')
                for image in before_images:
                    if image and image.filename:
                        # حفظ الصورة
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        folder_path = os.path.join(current_app.static_folder, 'uploads', 'workshop')
                        os.makedirs(folder_path, exist_ok=True)
                        image_path = os.path.join(folder_path, unique_filename)
                        image.save(image_path)
    
                        # إنشاء سجل الصورة
                        workshop_image = VehicleWorkshopImage(
                            workshop_record_id=workshop_record.id,
                            image_path=f'uploads/workshop/{unique_filename}',
                            image_type='before',
                            notes='صورة قبل الإصلاح'
                        )
                        db.session.add(workshop_image)
    
                # معالجة الصور بعد الإصلاح
                after_images = request.files.getlist('after_images')
                for image in after_images:
                    if image and image.filename:
                        # حفظ الصورة
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        folder_path = os.path.join(current_app.static_folder, 'uploads', 'workshop')
                        os.makedirs(folder_path, exist_ok=True)
                        image_path = os.path.join(folder_path, unique_filename)
                        image.save(image_path)
    
                        # إنشاء سجل الصورة
                        workshop_image = VehicleWorkshopImage(
                            workshop_record_id=workshop_record.id,
                            image_path=f'uploads/workshop/{unique_filename}',
                            image_type='after',
                            notes='صورة بعد الإصلاح'
                        )
                        db.session.add(workshop_image)
    
                # تحديث حالة السيارة
                if not exit_date:
                    vehicle.status = 'in_workshop'
                vehicle.updated_at = datetime.utcnow()
    
                db.session.commit()
    
                # تسجيل الإجراء
                log_activity('create', 'vehicle_workshop', workshop_record.id, 
                           f'تم إضافة سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال')
    
                
                # إنشاء طلب عملية تلقائياً لإدارة العمليات
                try:
                    operation_title = f"ورشة جديدة - {vehicle.plate_number}"
                    operation_description = f"تم إنشاء سجل ورشة جديد: {reason} - {description}"
                    
                    operation = create_operation_request(
                        operation_type='workshop_record',
                        related_record_id=workshop_record.id,
                        vehicle_id=vehicle_id,
                        title=operation_title,
                        description=operation_description,
                        requested_by=current_user.id,
                        priority='normal'
                    )
                    
                    # حفظ طلب العملية والإشعارات
                    db.session.commit()
                    
                    current_app.logger.debug(f"تم إنشاء طلب عملية للورشة: {workshop_record.id} برقم عملية: {operation.id}")
                    
                except Exception as e:
                    current_app.logger.error(f"خطأ في إنشاء طلب العملية للورشة: {str(e)}")
                    import traceback
                    current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
                    # لا نوقف العملية إذا فشل إنشاء طلب العملية
                
    
                flash('تم إضافة سجل الورشة بنجاح!', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"خطأ في إضافة سجل الورشة للسيارة {vehicle_id}: {str(e)}")
                flash(f'حدث خطأ أثناء إضافة سجل الورشة: {str(e)}', 'danger')
    
        # قوائم الخيارات
        workshop_reasons = [
            ('maintenance', 'صيانة دورية'),
            ('breakdown', 'عطل'),
            ('accident', 'حادث')
        ]
    
        repair_statuses = [
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'تم الإصلاح'),
            ('pending_approval', 'بانتظار الموافقة')
        ]
    
        return render_template('mobile/add_workshop_record.html',
                             vehicle=vehicle,
                             workshop_reasons=workshop_reasons,
                             repair_statuses=repair_statuses,
                             now=datetime.now())
    
    # تعديل سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_workshop_record(workshop_id):
        """تعديل سجل ورشة موجود للنسخة المحمولة"""
        workshop_record = VehicleWorkshop.query.get_or_404(workshop_id)
        vehicle = workshop_record.vehicle
    
        # تسجيل debug للبيانات الحالية
        current_app.logger.debug(f"تحرير سجل الورشة {workshop_id} - البيانات الحالية:")
        current_app.logger.debug(f"السبب: {workshop_record.reason}")
        current_app.logger.debug(f"الحالة: {workshop_record.repair_status}")
        current_app.logger.debug(f"الوصف: {workshop_record.description}")
        current_app.logger.debug(f"اسم الورشة: {workshop_record.workshop_name}")
        current_app.logger.debug(f"اسم الفني: {workshop_record.technician_name}")
        current_app.logger.debug(f"التكلفة: {workshop_record.cost}")
        current_app.logger.debug(f"رابط التسليم: {workshop_record.delivery_link}")
        current_app.logger.debug(f"رابط الاستلام: {workshop_record.reception_link}")
        current_app.logger.debug(f"الملاحظات: {workshop_record.notes}")
        
        current_app.logger.info(f"★ WORKSHOP EDIT - Method: {request.method}, Workshop ID: {workshop_id}")
        print(f"★ WORKSHOP EDIT - Method: {request.method}, Workshop ID: {workshop_id}")
        
        if request.method == 'POST':
            current_app.logger.info(f"★ POST data received: {dict(request.form)}")
            print(f"★ POST data received: {dict(request.form)}")
    
        if request.method == 'POST':
            try:
                # تحديث البيانات
                workshop_record.entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
                exit_date_str = request.form.get('exit_date')
                workshop_record.exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
                workshop_record.reason = request.form.get('reason')
                workshop_record.description = request.form.get('description')
                workshop_record.repair_status = request.form.get('repair_status')
                workshop_record.cost = float(request.form.get('cost') or 0)
                workshop_record.workshop_name = request.form.get('workshop_name')
                workshop_record.technician_name = request.form.get('technician_name')
                workshop_record.delivery_link = request.form.get('delivery_form_link')
                workshop_record.reception_link = request.form.get('pickup_form_link')
                workshop_record.notes = request.form.get('notes')
                workshop_record.updated_at = datetime.utcnow()
    
                # معالجة الصور المرفوعة
                import os
                from PIL import Image
                import uuid
    
                uploaded_images = []
    
                
                # دالة مساعدة لرفع الصور
                def process_workshop_images(files_list, image_type, type_name):
                    uploaded_count = 0
                    if files_list:
                        for file in files_list:
                            if file and file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                try:
                                    # إنشاء اسم ملف فريد
                                    filename = f"workshop_{image_type}_{workshop_record.id}_{uuid.uuid4().hex[:8]}_{file.filename}"
                                    
                                    # إنشاء المجلد إذا لم يكن موجوداً
                                    upload_dir = os.path.join('static', 'uploads', 'workshop')
                                    os.makedirs(upload_dir, exist_ok=True)
                                    
                                    # حفظ الملف
                                    file_path = os.path.join(upload_dir, filename)
                                    file.save(file_path)
                                    
                                    # ضغط الصورة إذا كانت كبيرة
                                    try:
                                        with Image.open(file_path) as img:
                                            if img.width > 1200 or img.height > 1200:
                                                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                                                img.save(file_path, optimize=True, quality=85)
                                    except Exception as e:
                                        current_app.logger.warning(f"تعذر ضغط الصورة {filename}: {str(e)}")
                                    
                                    # إضافة سجل الصورة لقاعدة البيانات
                                    image_record = VehicleWorkshopImage(
                                        workshop_record_id=workshop_record.id,
                                        image_type=image_type,
                                        image_path=f"uploads/workshop/{filename}",
                                        notes=f"{type_name} - تم الرفع في {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                                    )
                                    db.session.add(image_record)
                                    uploaded_images.append(filename)
                                    uploaded_count += 1
                                    
                                except Exception as e:
                                    current_app.logger.error(f"خطأ في رفع {type_name}: {str(e)}")
                    return uploaded_count
    
                # دالة مساعدة لرفع الإيصالات (PDF وصور)
                def save_receipt_file(file, field_name, type_name):
                    """رفع وحفظ إيصال (PDF أو صورة)"""
                    if file and file.filename:
                        try:
                            # التحقق من نوع الملف
                            allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
                            file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
                            
                            if file_ext in allowed_extensions:
                                # إنشاء اسم ملف فريد
                                filename = f"receipt_{field_name}_{workshop_record.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
                                
                                # إنشاء المجلد إذا لم يكن موجوداً
                                upload_dir = os.path.join('static', 'uploads', 'workshop', 'receipts')
                                os.makedirs(upload_dir, exist_ok=True)
                                
                                # حفظ الملف
                                file_path = os.path.join(upload_dir, filename)
                                file.save(file_path)
                                
                                # ضغط الصورة إذا كانت صورة وكبيرة
                                if file_ext in {'png', 'jpg', 'jpeg', 'gif'}:
                                    try:
                                        with Image.open(file_path) as img:
                                            if img.width > 1200 or img.height > 1200:
                                                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                                                img.save(file_path, optimize=True, quality=85)
                                    except Exception as e:
                                        current_app.logger.warning(f"تعذر ضغط الصورة {filename}: {str(e)}")
                                
                                return f"uploads/workshop/receipts/{filename}"
                            
                        except Exception as e:
                            current_app.logger.error(f"خطأ في رفع {type_name}: {str(e)}")
                            flash(f'خطأ في رفع {type_name}: {str(e)}', 'warning')
                    
                    return None
    
                # معالجة إيصالات التسليم والاستلام
                receipt_updates = []
                
                # إيصال تسليم الورشة
                if 'delivery_receipt' in request.files:
                    delivery_receipt_file = request.files['delivery_receipt']
                    delivery_receipt_path = save_receipt_file(delivery_receipt_file, 'delivery', 'إيصال تسليم الورشة')
                    if delivery_receipt_path:
                        workshop_record.delivery_receipt = delivery_receipt_path
                        receipt_updates.append('إيصال تسليم الورشة')
                
                # إيصال استلام من الورشة
                if 'pickup_receipt' in request.files:
                    pickup_receipt_file = request.files['pickup_receipt']
                    pickup_receipt_path = save_receipt_file(pickup_receipt_file, 'pickup', 'إيصال استلام من الورشة')
                    if pickup_receipt_path:
                        workshop_record.pickup_receipt = pickup_receipt_path
                        receipt_updates.append('إيصال استلام من الورشة')
    
                # معالجة الصور الجديدة
                delivery_count = 0
                pickup_count = 0
                notes_count = 0
                
                # صور إيصال التسليم للورشة
                if 'delivery_images' in request.files:
                    delivery_files = request.files.getlist('delivery_images')
                    delivery_count = process_workshop_images(delivery_files, 'delivery', 'صورة إيصال التسليم للورشة')
                
                # صور إيصال الاستلام من الورشة
                if 'pickup_images' in request.files:
                    pickup_files = request.files.getlist('pickup_images')
                    pickup_count = process_workshop_images(pickup_files, 'pickup', 'صورة إيصال الاستلام من الورشة')
                
                # صور ملاحظات السيارة قبل التسليم للورشة
                if 'notes_images' in request.files:
                    notes_files = request.files.getlist('notes_images')
                    notes_count = process_workshop_images(notes_files, 'notes', 'صورة ملاحظات السيارة قبل التسليم')
                
                # معالجة الصور القديمة (للتوافق مع النظام القديم)
                if 'before_images' in request.files:
                    before_files = request.files.getlist('before_images')
                    process_workshop_images(before_files, 'before', 'صورة قبل الإصلاح')
                
                if 'after_images' in request.files:
                    after_files = request.files.getlist('after_images')
                    process_workshop_images(after_files, 'after', 'صورة بعد الإصلاح')
                
    
                db.session.commit()
    
                # تسجيل العملية
                log_activity(
                    action='update',
                    entity_type='vehicle_workshop',
                    details=f'تم تعديل سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال وإضافة {len(uploaded_images)} صورة'
                )
    
                # إنشاء طلب عملية تلقائياً لإدارة العمليات
                try:
                    operation_title = f"تحديث ورشة - {vehicle.plate_number}"
                    operation_description = f"تم تحديث سجل الورشة: {workshop_record.reason} - {workshop_record.description}"
                    
                    operation = create_operation_request(
                        operation_type="workshop_update",
                        related_record_id=workshop_record.id,
                        vehicle_id=vehicle.id,
                        title=operation_title,
                        description=operation_description,
                        requested_by=current_user.id,
                        priority="normal"
                    )
                    
                    # حفظ طلب العملية والإشعارات
                    db.session.commit()
    
                    # update_vehicle_driver(vehicle.id)
                    update_vehicle_state(vehicle.id)
                    
                    print(f"تم تسجيل عملية التحديث بنجاح: {operation.id}")
                    current_app.logger.debug(f"تم إنشاء طلب عملية لتحديث الورشة: {workshop_record.id} برقم عملية: {operation.id}")
                    
                    # التحقق من وجود العملية في قاعدة البيانات
                    saved_operation = OperationRequest.query.get(operation.id)
                    if saved_operation:
                        print(f"تأكيد: عملية التحديث {operation.id} محفوظة في قاعدة البيانات")
                    else:
                        print(f"تحذير: عملية التحديث {operation.id} غير موجودة في قاعدة البيانات!")
                    
                except Exception as e:
                    print(f"خطأ في إنشاء طلب العملية لتحديث الورشة: {str(e)}")
                    current_app.logger.error(f"خطأ في إنشاء طلب العملية لتحديث الورشة: {str(e)}")
                    import traceback
                    current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
                    # لا نوقف العملية إذا فشل إنشاء طلب العملية
    
                success_message = f'تم تحديث سجل الورشة بنجاح!'
                
                # إضافة تفاصيل الملفات المرفوعة
                updates = []
                
                # إضافة الإيصالات المرفوعة
                if receipt_updates:
                    updates.extend(receipt_updates)
                if uploaded_images:
    
    
    
                    details = []
                    if delivery_count > 0:
                        details.append(f'{delivery_count} صورة إيصال تسليم')
                    if pickup_count > 0:
                        details.append(f'{pickup_count} صورة إيصال استلام')
                    if notes_count > 0:
                        details.append(f'{notes_count} صورة ملاحظات')
                    
                    if details:
                        success_message += f' تم رفع {" و ".join(details)}.'
                    else:
                        success_message += f' تم رفع {len(uploaded_images)} صورة جديدة.'
                
    
                flash(success_message, 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"خطأ في تعديل سجل الورشة {workshop_id}: {str(e)}")
                flash(f'حدث خطأ أثناء تحديث سجل الورشة: {str(e)}', 'danger')
    
        
        
        
        
        
        
        
        
        
        
        
        # خيارات النموذج
        workshop_reasons = [
            ('maintenance', 'صيانة دورية'),
            ('breakdown', 'عطل'),
            ('accident', 'حادث'),
            ('periodic_inspection', 'فحص دوري'),
            ('other', 'أخرى')
        ]
    
        repair_statuses = [
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'تم الإصلاح'),
            ('pending_approval', 'بانتظار الموافقة')
        ]
    
        return render_template('mobile/edit_workshop_record_simple.html',
                               workshop_record=workshop_record,
                               vehicle=vehicle,
                               workshop_reasons=workshop_reasons,
                               repair_statuses=repair_statuses,
                               now=datetime.now())
    
    # حذف سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/delete', methods=['POST'])
    @login_required
    def delete_workshop_record(workshop_id):
        """حذف سجل ورشة للنسخة المحمولة"""
        try:
            workshop_record = VehicleWorkshop.query.get_or_404(workshop_id)
            vehicle = workshop_record.vehicle
    
            # تسجيل العملية قبل الحذف
            log_activity(
                action='delete',
                entity_type='vehicle_workshop',
                details=f'تم حذف سجل دخول الورشة للسيارة: {vehicle.plate_number} - الوصف: {workshop_record.description[:50]} من الجوال'
            )
    
            db.session.delete(workshop_record)
            db.session.commit()
    
            flash('تم حذف سجل الورشة بنجاح!', 'success')
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في حذف سجل الورشة {workshop_id}: {str(e)}")
            flash(f'حدث خطأ أثناء حذف سجل الورشة: {str(e)}', 'danger')
    
        return redirect(url_for('mobile.vehicle_details', vehicle_id=workshop_record.vehicle.id))
    
    # عرض تفاصيل سجل الورشة - النسخة المحمولة
    @bp.route('/vehicles/workshop/<int:workshop_id>/details')
    @login_required
    def view_workshop_details(workshop_id):
        """عرض تفاصيل سجل ورشة للنسخة المحمولة"""
        workshop_record = VehicleWorkshop.query.options(
            joinedload(VehicleWorkshop.images)
        ).get_or_404(workshop_id)
        vehicle = workshop_record.vehicle
    
        # فحص وجود الصور الفعلي على الخادم مع البحث في مسارات متعددة
        valid_images = []
        if workshop_record.images:
            for image in workshop_record.images:
                # محاولة أولى: المسار المحفوظ في قاعدة البيانات
                image_path = os.path.join(current_app.static_folder, image.image_path)
    
                # إذا لم يوجد، نبحث عن نفس الملف في مجلد الورشة
                if not os.path.exists(image_path):
                    filename = os.path.basename(image.image_path)
                    # البحث عن أي ملف يحتوي على اسم مشابه
                    workshop_dir = os.path.join(current_app.static_folder, 'uploads/workshop')
                    if os.path.exists(workshop_dir):
                        for file in os.listdir(workshop_dir):
                            # البحث عن الجزء المميز من اسم الملف
                            if 'WhatsApp_Image_2025-07-14_at_11.29.07_ef6d7df0' in file:
                                # تحديث المسار ليشير للملف الموجود
                                image.image_path = f'uploads/workshop/{file}'
                                image_path = os.path.join(current_app.static_folder, image.image_path)
                                break
    
                if os.path.exists(image_path):
                    valid_images.append(image)
                    current_app.logger.info(f"الصورة موجودة: {image.image_path}")
                else:
                    current_app.logger.warning(f"الصورة غير موجودة: {image_path}")
    
        # تحديث قائمة الصور بالصور الموجودة فقط
        workshop_record.valid_images = valid_images
    
        return render_template('mobile/workshop_details.html',
                               workshop_record=workshop_record,
                               vehicle=vehicle)
    
    # # تعديل سجل التسليم والاستلام - النسخة المحمولة
    # @bp.route('/vehicles/handover/<int:handover_id>/edit', methods=['GET', 'POST'])
    # @login_required
    # def edit_handover_mobile(handover_id):
    #     """تعديل سجل التسليم والاستلام للنسخة المحمولة"""
    #     handover = VehicleHandover.query.get_or_404(handover_id)
    #     vehicle = handover.vehicle
    
    #     if request.method == 'POST':
    #         try:
    #             # تحديث البيانات
    #             handover.handover_type = request.form.get('handover_type')
    #             handover.person_name = request.form.get('person_name')
    #             handover.person_phone = request.form.get('person_phone')
    #             handover.person_national_id = request.form.get('person_national_id')
    #             handover.notes = request.form.get('notes')
    
    #             # تحديث التاريخ إذا تم تقديمه
    #             handover_date = request.form.get('handover_date')
    #             if handover_date:
    #                 handover.handover_date = datetime.strptime(handover_date, '%Y-%m-%d').date()
    
    #             # تحديث الحقول الاختيارية
    #             handover.mileage = request.form.get('mileage', type=int)
    #             handover.vehicle_condition = request.form.get('vehicle_condition')
    #             handover.fuel_level = request.form.get('fuel_level')
    
    #             # تسجيل النشاط
    #             log_activity(
    #                 action='update',
    #                 entity_type='vehicle_handover',
    #                 details=f'تم تعديل سجل {handover.handover_type} للسيارة: {vehicle.plate_number} - الشخص: {handover.person_name} من الجوال'
    #             )
    
    #             db.session.commit()
    #             flash('تم تحديث سجل التسليم والاستلام بنجاح!', 'success')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         except Exception as e:
    #             db.session.rollback()
    #             current_app.logger.error(f"خطأ في تعديل سجل التسليم والاستلام {handover_id}: {str(e)}")
    #             flash(f'حدث خطأ أثناء تحديث السجل: {str(e)}', 'danger')
    
    #     return render_template('mobile/edit_handover.html',
    #                            handover=handover,
    #                            vehicle=vehicle)
    
    
    
    # مسارات التفويضات الخارجية للموبايل

    @bp.route('/vehicles/workshop/<int:workshop_id>/edit', methods=['GET', 'POST'])
    @login_required  
    def edit_workshop_mobile(workshop_id):
        """تعديل سجل الورشة للنسخة المحمولة"""
        return redirect(url_for('vehicles.edit_workshop', id=workshop_id))
