"""
خدمة إدارة الورشة للمركبات — CRUD operations + معالجة الصور والإيصالات.
تُستخدم من: presentation/api/mobile/vehicle_routes.py
المعاملات تُمرَّر من طبقة العرض؛ لا استخدام لـ request أو Flask globals.
"""
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from core.extensions import db
from modules.vehicles.domain.models import Vehicle, VehicleWorkshop, VehicleWorkshopImage
from modules.operations.domain.models import OperationRequest
from utils.vehicle_helpers import log_audit
from utils.audit_logger import log_activity


# قوائم الخيارات الثابتة
WORKSHOP_REASONS = [
    ('maintenance', 'صيانة دورية'),
    ('breakdown', 'عطل'),
    ('accident', 'حادث'),
    ('periodic_inspection', 'فحص دوري'),
    ('other', 'أخرى')
]

REPAIR_STATUSES = [
    ('in_progress', 'قيد التنفيذ'),
    ('completed', 'تم الإصلاح'),
    ('pending_approval', 'بانتظار الموافقة')
]


def _save_workshop_image(
    file: FileStorage,
    workshop_id: int,
    image_type: str,
    upload_base_path: str,
) -> Optional[str]:
    """
    حفظ صورة ورشة واحدة مع الضغط التلقائي.
    
    Args:
        file: كائن الملف المرفوع.
        workshop_id: معرف سجل الورشة.
        image_type: نوع الصورة (before, after, delivery, pickup, notes).
        upload_base_path: المسار الأساسي (static_folder).
    
    Returns:
        str أو None: المسار النسبي للصورة المحفوظة، أو None عند الفشل.
    """
    if not file or not file.filename:
        return None
    
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return None
    
    try:
        # إنشاء اسم ملف فريد
        filename = secure_filename(file.filename)
        unique_filename = f"workshop_{image_type}_{workshop_id}_{uuid.uuid4().hex[:8]}_{filename}"
        
        # إنشاء المجلد
        folder_path = os.path.join(upload_base_path, 'uploads', 'workshop')
        os.makedirs(folder_path, exist_ok=True)
        
        # حفظ الملف
        file_path = os.path.join(folder_path, unique_filename)
        file.save(file_path)
        
        # ضغط الصورة إذا كانت كبيرة
        try:
            with Image.open(file_path) as img:
                if img.width > 1200 or img.height > 1200:
                    img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
        except Exception as e:
            print(f"تعذر ضغط الصورة {unique_filename}: {str(e)}")
        
        return f'uploads/workshop/{unique_filename}'
    
    except Exception as e:
        print(f"خطأ في حفظ صورة الورشة: {str(e)}")
        return None


def _save_receipt_file(
    file: FileStorage,
    workshop_id: int,
    field_name: str,
    upload_base_path: str,
) -> Optional[str]:
    """
    حفظ إيصال (PDF أو صورة).
    
    Args:
        file: كائن الملف المرفوع.
        workshop_id: معرف سجل الورشة.
        field_name: اسم الحقل (delivery, pickup).
        upload_base_path: المسار الأساسي.
    
    Returns:
        str أو None: المسار النسبي للإيصال، أو None عند الفشل.
    """
    if not file or not file.filename:
        return None
    
    try:
        # التحقق من نوع الملف
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            return None
        
        # إنشاء اسم ملف فريد
        unique_filename = f"receipt_{field_name}_{workshop_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        
        # إنشاء المجلد
        folder_path = os.path.join(upload_base_path, 'uploads', 'workshop', 'receipts')
        os.makedirs(folder_path, exist_ok=True)
        
        # حفظ الملف
        file_path = os.path.join(folder_path, unique_filename)
        file.save(file_path)
        
        # ضغط الصورة إذا كانت صورة وكبيرة
        if file_ext in {'png', 'jpg', 'jpeg', 'gif'}:
            try:
                with Image.open(file_path) as img:
                    if img.width > 1200 or img.height > 1200:
                        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                        img.save(file_path, optimize=True, quality=85)
            except Exception as e:
                print(f"تعذر ضغط الإيصال {unique_filename}: {str(e)}")
        
        return f"uploads/workshop/receipts/{unique_filename}"
    
    except Exception as e:
        print(f"خطأ في حفظ الإيصال: {str(e)}")
        return None


def create_workshop_record(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files: Dict[str, Any],
    upload_base_path: str,
    current_user_id: int,
) -> Tuple[bool, str, Optional[int]]:
    """
    إنشاء سجل ورشة جديد مع معالجة الصور.
    
    Args:
        vehicle_id: معرف المركبة.
        form_data: بيانات النموذج (entry_date, exit_date, reason, description, ...).
        files: قاموس الملفات المرفوعة (before_images, after_images).
        upload_base_path: المسار الأساسي لحفظ الملفات.
        current_user_id: معرف المستخدم الحالي.
    
    Returns:
        (success, message, workshop_id)
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, "المركبة غير موجودة.", None
    
    # التحقق من قيود العمليات
    from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
    restrictions = check_vehicle_operation_restrictions(vehicle)
    if restrictions['blocked']:
        return False, restrictions['message'], None
    
    try:
        # استخراج البيانات
        entry_date = datetime.strptime(form_data.get('entry_date'), '%Y-%m-%d').date()
        exit_date_str = form_data.get('exit_date')
        exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
        
        # إنشاء سجل الورشة
        workshop_record = VehicleWorkshop(
            vehicle_id=vehicle_id,
            entry_date=entry_date,
            exit_date=exit_date,
            reason=form_data.get('reason'),
            description=form_data.get('description'),
            repair_status=form_data.get('repair_status'),
            cost=float(form_data.get('cost') or 0),
            workshop_name=form_data.get('workshop_name'),
            technician_name=form_data.get('technician_name'),
            notes=form_data.get('notes'),
            delivery_link=form_data.get('delivery_form_link'),
            reception_link=form_data.get('pickup_form_link'),
        )
        
        db.session.add(workshop_record)
        db.session.flush()  # للحصول على workshop_record.id
        
        # معالجة الصور قبل الإصلاح
        before_images = files.get('before_images', [])
        for image in before_images:
            image_path = _save_workshop_image(image, workshop_record.id, 'before', upload_base_path)
            if image_path:
                workshop_image = VehicleWorkshopImage(
                    workshop_record_id=workshop_record.id,
                    image_path=image_path,
                    image_type='before',
                    notes='صورة قبل الإصلاح',
                )
                db.session.add(workshop_image)
        
        # معالجة الصور بعد الإصلاح
        after_images = files.get('after_images', [])
        for image in after_images:
            image_path = _save_workshop_image(image, workshop_record.id, 'after', upload_base_path)
            if image_path:
                workshop_image = VehicleWorkshopImage(
                    workshop_record_id=workshop_record.id,
                    image_path=image_path,
                    image_type='after',
                    notes='صورة بعد الإصلاح',
                )
                db.session.add(workshop_image)
        
        # تحديث حالة السيارة
        if not exit_date:
            vehicle.status = 'in_workshop'
        vehicle.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # تسجيل النشاط
        log_activity(
            'create',
            'vehicle_workshop',
            workshop_record.id,
            f'تم إضافة سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال'
        )
        
        # إنشاء طلب عملية تلقائياً
        try:
            from routes.operations import create_operation_request
            
            operation_title = f"ورشة جديدة - {vehicle.plate_number}"
            operation_description = f"تم إنشاء سجل ورشة جديد: {workshop_record.reason} - {workshop_record.description}"
            
            create_operation_request(
                operation_type='workshop_record',
                related_record_id=workshop_record.id,
                vehicle_id=vehicle_id,
                title=operation_title,
                description=operation_description,
                requested_by=current_user_id,
                priority='normal'
            )
            
            db.session.commit()
        except Exception as e:
            print(f"خطأ في إنشاء طلب العملية للورشة: {str(e)}")
            # لا نوقف العملية
        
        return True, "تم إضافة سجل الورشة بنجاح!", workshop_record.id
    
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء إضافة سجل الورشة: {str(e)}", None


def update_workshop_record(
    workshop_id: int,
    form_data: Dict[str, Any],
    files: Dict[str, Any],
    upload_base_path: str,
    current_user_id: int,
) -> Tuple[bool, str, Optional[int]]:
    """
    تحديث سجل ورشة موجود مع معالجة الصور والإيصالات.
    
    Args:
        workshop_id: معرف سجل الورشة.
        form_data: بيانات النموذج المحدثة.
        files: قاموس الملفات المرفوعة الجديدة.
        upload_base_path: المسار الأساسي لحفظ الملفات.
        current_user_id: معرف المستخدم الحالي.
    
    Returns:
        (success, message, vehicle_id)
    """
    workshop_record = VehicleWorkshop.query.get(workshop_id)
    if not workshop_record:
        return False, "سجل الورشة غير موجود.", None
    
    vehicle = workshop_record.vehicle
    
    try:
        # تحديث البيانات الأساسية
        workshop_record.entry_date = datetime.strptime(form_data.get('entry_date'), '%Y-%m-%d').date()
        exit_date_str = form_data.get('exit_date')
        workshop_record.exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
        workshop_record.reason = form_data.get('reason')
        workshop_record.description = form_data.get('description')
        workshop_record.repair_status = form_data.get('repair_status')
        workshop_record.cost = float(form_data.get('cost') or 0)
        workshop_record.workshop_name = form_data.get('workshop_name')
        workshop_record.technician_name = form_data.get('technician_name')
        workshop_record.delivery_link = form_data.get('delivery_form_link')
        workshop_record.reception_link = form_data.get('pickup_form_link')
        workshop_record.notes = form_data.get('notes')
        workshop_record.updated_at = datetime.utcnow()
        
        uploaded_count = 0
        receipt_updates = []
        
        # معالجة إيصالات التسليم والاستلام
        if 'delivery_receipt' in files.keys():
            delivery_receipt = files['delivery_receipt']
            delivery_path = _save_receipt_file(delivery_receipt, workshop_id, 'delivery', upload_base_path)
            if delivery_path:
                workshop_record.delivery_receipt = delivery_path
                receipt_updates.append('إيصال تسليم الورشة')
        
        if 'pickup_receipt' in files.keys():
            pickup_receipt = files['pickup_receipt']
            pickup_path = _save_receipt_file(pickup_receipt, workshop_id, 'pickup', upload_base_path)
            if pickup_path:
                workshop_record.pickup_receipt = pickup_path
                receipt_updates.append('إيصال استلام من الورشة')
        
        # معالجة الصور الجديدة
        image_types = {
            'delivery_images': ('delivery', 'صورة إيصال التسليم للورشة'),
            'pickup_images': ('pickup', 'صورة إيصال الاستلام من الورشة'),
            'notes_images': ('notes', 'صورة ملاحظات السيارة قبل التسليم'),
            'before_images': ('before', 'صورة قبل الإصلاح'),
            'after_images': ('after', 'صورة بعد الإصلاح'),
        }
        
        for file_key, (img_type, notes) in image_types.items():
            if file_key in files.keys():
                images_list = files[file_key]
                for img_file in images_list:
                    image_path = _save_workshop_image(img_file, workshop_id, img_type, upload_base_path)
                    if image_path:
                        workshop_image = VehicleWorkshopImage(
                            workshop_record_id=workshop_id,
                            image_type=img_type,
                            image_path=image_path,
                            notes=f"{notes} - تم الرفع في {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        )
                        db.session.add(workshop_image)
                        uploaded_count += 1
        
        db.session.commit()
        
        # تسجيل النشاط
        log_activity(
            action='update',
            entity_type='vehicle_workshop',
            details=f'تم تعديل سجل دخول الورشة للسيارة: {vehicle.plate_number} من الجوال وإضافة {uploaded_count} صورة'
        )
        
        # إنشاء طلب عملية تلقائياً
        try:
            from routes.operations import create_operation_request
            from utils.vehicle_route_helpers import update_vehicle_state
            
            operation_title = f"تحديث ورشة - {vehicle.plate_number}"
            operation_description = f"تم تحديث سجل الورشة: {workshop_record.reason} - {workshop_record.description}"
            
            create_operation_request(
                operation_type="workshop_update",
                related_record_id=workshop_id,
                vehicle_id=vehicle.id,
                title=operation_title,
                description=operation_description,
                requested_by=current_user_id,
                priority="normal"
            )
            
            db.session.commit()
            update_vehicle_state(vehicle.id)
        except Exception as e:
            print(f"خطأ في إنشاء طلب العملية لتحديث الورشة: {str(e)}")
        
        # بناء رسالة النجاح
        success_message = 'تم تحديث سجل الورشة بنجاح!'
        if receipt_updates:
            success_message += f' تم رفع {" و ".join(receipt_updates)}.'
        if uploaded_count > 0:
            success_message += f' تم رفع {uploaded_count} صورة جديدة.'
        
        return True, success_message, vehicle.id
    
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء تحديث سجل الورشة: {str(e)}", None


def delete_workshop_record(workshop_id: int) -> Tuple[bool, str, Optional[int]]:
    """
    حذف سجل ورشة.
    
    Args:
        workshop_id: معرف سجل الورشة.
    
    Returns:
        (success, message, vehicle_id)
    """
    workshop_record = VehicleWorkshop.query.get(workshop_id)
    if not workshop_record:
        return False, "سجل الورشة غير موجود.", None
    
    vehicle = workshop_record.vehicle
    vehicle_id = vehicle.id
    plate_number = vehicle.plate_number
    description = workshop_record.description[:50] if workshop_record.description else ""
    
    try:
        # تسجيل العملية قبل الحذف
        log_activity(
            action='delete',
            entity_type='vehicle_workshop',
            details=f'تم حذف سجل دخول الورشة للسيارة: {plate_number} - الوصف: {description} من الجوال'
        )
        
        db.session.delete(workshop_record)
        db.session.commit()
        
        return True, "تم حذف سجل الورشة بنجاح!", vehicle_id
    
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء حذف سجل الورشة: {str(e)}", vehicle_id


def get_workshop_details_context(
    workshop_id: int,
    upload_base_path: str,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على سياق تفاصيل سجل ورشة مع التحقق من وجود الصور.
    
    Args:
        workshop_id: معرف سجل الورشة.
        upload_base_path: المسار الأساسي للملفات الثابتة.
    
    Returns:
        Dict أو None: قاموس يحتوي على workshop_record، vehicle، valid_images.
    """
    from sqlalchemy.orm import joinedload
    
    workshop_record = (
        VehicleWorkshop.query
        .options(joinedload(VehicleWorkshop.images))
        .get(workshop_id)
    )
    
    if not workshop_record:
        return None
    
    vehicle = workshop_record.vehicle
    
    # التحقق من وجود الصور الفعلي
    valid_images = []
    if workshop_record.images:
        for image in workshop_record.images:
            image_path = os.path.join(upload_base_path, image.image_path)
            
            # البحث عن الملف إذا لم يوجد في المسار المحفوظ
            if not os.path.exists(image_path):
                filename = os.path.basename(image.image_path)
                workshop_dir = os.path.join(upload_base_path, 'uploads/workshop')
                if os.path.exists(workshop_dir):
                    for file in os.listdir(workshop_dir):
                        if filename in file:
                            image.image_path = f'uploads/workshop/{file}'
                            image_path = os.path.join(upload_base_path, image.image_path)
                            break
            
            if os.path.exists(image_path):
                valid_images.append(image)
    
    return {
        'workshop_record': workshop_record,
        'vehicle': vehicle,
        'valid_images': valid_images,
    }


def get_workshop_form_context() -> Dict[str, Any]:
    """
    الحصول على سياق نموذج إنشاء/تعديل ورشة.
    
    Returns:
        Dict: قاموس يحتوي على workshop_reasons، repair_statuses، now.
    """
    return {
        'workshop_reasons': WORKSHOP_REASONS,
        'repair_statuses': REPAIR_STATUSES,
        'now': datetime.now(),
    }
