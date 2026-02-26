"""
External Safety Check Service Layer
====================================
يحتوي على منطق الأعمال الخاص بفحوصات السلامة الخارجية للمركبات

المسؤوليات:
- استرجاع بيانات الفحوصات والمركبات
- معالجة الصور والملفات (ضغط، رفع، حذف)
- إرسال الإشعارات (Email, WhatsApp, In-app)
- عمليات PDF (إنشاء، تحميل)
- التحقق من البيانات (الموظفين، المركبات)
- عمليات موافقة/رفض/حذف الفحوصات

يتم استدعاء هذه الخدمة من Controllers فقط، ولا تحتوي على أي Flask route decorators
"""

from flask import current_app, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
from pillow_heif import register_heif_opener
import os
import uuid
import resend
from sqlalchemy import func, select
from sqlalchemy.orm import aliased, contains_eager

# Database Models
from models import (
    VehicleExternalSafetyCheck, VehicleSafetyImage, Vehicle, 
    Employee, User, UserRole, VehicleHandover, Notification
)
from src.core.extensions import db
from src.utils.audit_logger import log_audit
from src.utils.storage_helper import upload_image, delete_image
from src.utils.vehicle_drive_uploader import VehicleDriveUploader

# تسجيل plugin الـ HEIC/HEIF للتعامل مع صور الآيفون
register_heif_opener()

# Constants
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}


class ExternalSafetyService:
    """
    خدمة فحوصات السلامة الخارجية - تحتوي على منطق الأعمال فقط
    """
    
    # ===============================
    # Data Retrieval Methods
    # ===============================
    
    @staticmethod
    def get_all_current_drivers_with_email():
        """
        استرجاع السائقين الحاليين مع بريدهم الإلكتروني
        Returns: dict {vehicle_id: {'driver_name': str, 'email': str}}
        """
        delivery_handover_types = ['delivery', 'تسليم', 'handover']
        
        # Window Function للحصول على آخر تسليم لكل مركبة
        subq = select(
            VehicleHandover.id,
            func.row_number().over(
                partition_by=VehicleHandover.vehicle_id,
                order_by=VehicleHandover.handover_date.desc()
            ).label('row_num')
        ).where(
            VehicleHandover.handover_type.in_(delivery_handover_types)
        ).subquery()

        # Eager loading للموظف لتقليل الاستعلامات
        employee_alias = aliased(Employee)
        stmt = (
            select(VehicleHandover)
            .options(contains_eager(VehicleHandover.employee.of_type(employee_alias)))
            .outerjoin(employee_alias, VehicleHandover.employee_id == employee_alias.id)
            .join(subq, VehicleHandover.id == subq.c.id)
            .where(subq.c.row_num == 1)
        )

        latest_handovers = db.session.execute(stmt).scalars().unique().all()
        
        # بناء القاموس للوصول السريع
        current_drivers_map = {}
        for record in latest_handovers:
            email = record.employee.email if record.employee else None
            current_drivers_map[record.vehicle_id] = {
                'driver_name': record.person_name,
                'email': email
            }
        
        return current_drivers_map
    
    @staticmethod
    def get_all_current_drivers():
        """
        استرجاع السائقين الحاليين فقط (بدون بريد إلكتروني)
        Returns: dict {vehicle_id: driver_name}
        """
        delivery_handover_types = ['delivery', 'تسليم', 'handover']
        
        subq = select(
            VehicleHandover.id,
            func.row_number().over(
                partition_by=VehicleHandover.vehicle_id,
                order_by=VehicleHandover.handover_date.desc()
            ).label('row_num')
        ).where(
            VehicleHandover.handover_type.in_(delivery_handover_types)
        ).subquery()

        stmt = select(VehicleHandover).join(
            subq, VehicleHandover.id == subq.c.id
        ).where(subq.c.row_num == 1)

        latest_handovers = db.session.execute(stmt).scalars().all()
        
        current_drivers_map = {
            record.vehicle_id: record.person_name for record in latest_handovers
        }
        
        return current_drivers_map
    
    @staticmethod
    def get_safety_checks_with_filters(filters=None):
        """
        استرجاع فحوصات السلامة مع الفلاتر
        
        Args:
            filters (dict): {
                'status': str,
                'vehicle_id': int,
                'start_date': datetime,
                'end_date': datetime,
                'driver_name': str
            }
        
        Returns:
            list[VehicleExternalSafetyCheck]
        """
        query = VehicleExternalSafetyCheck.query.order_by(
            VehicleExternalSafetyCheck.check_date.desc()
        )
        
        if not filters:
            return query.all()
        
        if filters.get('status'):
            query = query.filter_by(approval_status=filters['status'])
        
        if filters.get('vehicle_id'):
            query = query.filter_by(vehicle_id=filters['vehicle_id'])
        
        if filters.get('start_date'):
            query = query.filter(VehicleExternalSafetyCheck.check_date >= filters['start_date'])
        
        if filters.get('end_date'):
            query = query.filter(VehicleExternalSafetyCheck.check_date <= filters['end_date'])
        
        if filters.get('driver_name'):
            query = query.filter(
                VehicleExternalSafetyCheck.driver_name.ilike(f"%{filters['driver_name']}%")
            )
        
        return query.all()
    
    @staticmethod
    def get_safety_check_by_id(check_id):
        """استرجاع فحص سلامة محدد مع الصور"""
        check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
        return check
    
    @staticmethod
    def verify_employee_by_national_id(national_id):
        """
        التحقق من وجود موظف بواسطة رقم الهوية
        
        Returns:
            dict: {'exists': bool, 'employee': Employee|None, 'name': str|None}
        """
        employee = Employee.query.filter_by(national_id=national_id).first()
        
        if employee:
            return {
                'exists': True,
                'employee': employee,
                'name': f"{employee.first_name} {employee.father_name} {employee.grandfather_name} {employee.family_name}"
            }
        
        return {'exists': False, 'employee': None, 'name': None}
    
    # ===============================
    # Image & File Handling Methods
    # ===============================
    
    @staticmethod
    def allowed_file(filename):
        """التحقق من امتداد الملف"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @staticmethod
    def compress_image(image_path, max_size=1200, quality=85):
        """
        ضغط الصورة لتقليل حجمها مع دعم HEIC من الآيفون
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                # تحويل RGBA أو أي تنسيق آخر إلى RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # تغيير حجم الصورة إذا كانت أكبر من الحد المسموح
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # حفظ الصورة المضغوطة
                img.save(image_path, 'JPEG', quality=quality, optimize=True)
                return True
        except Exception as e:
            current_app.logger.error(f"خطأ في ضغط الصورة: {str(e)}")
            return False
    
    @staticmethod
    def process_uploaded_images(files, safety_check_id):
        """
        معالجة ورفع الصور للسحابة
        
        Args:
            files: ملفات الصور من request.files
            safety_check_id: معرف الفحص
        
        Returns:
            dict: {'success': bool, 'uploaded_count': int, 'errors': list}
        """
        uploaded_count = 0
        errors = []
        
        for key in files:
            file = files[key]
            if file and file.filename and ExternalSafetyService.allowed_file(file.filename):
                try:
                    # حفظ مؤقت
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(temp_path)
                    
                    # ضغط الصورة
                    ExternalSafetyService.compress_image(temp_path)
                    
                    # رفع للسحابة
                    cloud_url = upload_image(temp_path, 'safety_checks')
                    
                    if cloud_url:
                        # حفظ في قاعدة البيانات
                        image = VehicleSafetyImage(
                            safety_check_id=safety_check_id,
                            image_url=cloud_url
                        )
                        db.session.add(image)
                        uploaded_count += 1
                    else:
                        errors.append(f"فشل رفع {filename}")
                    
                    # حذف الملف المؤقت
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
                except Exception as e:
                    errors.append(f"خطأ في معالجة {filename}: {str(e)}")
                    current_app.logger.error(f"خطأ في رفع الصورة: {str(e)}")
        
        if uploaded_count > 0:
            db.session.commit()
        
        return {
            'success': uploaded_count > 0,
            'uploaded_count': uploaded_count,
            'errors': errors
        }
    
    @staticmethod
    def delete_safety_check_images(check_id, image_ids):
        """
        حذف صور من فحص السلامة
        
        Args:
            check_id: معرف الفحص
            image_ids: قائمة معرفات الصور للحذف
        
        Returns:
            dict: {'success': bool, 'deleted_count': int, 'message': str}
        """
        try:
            deleted_count = 0
            for image_id in image_ids:
                image = VehicleSafetyImage.query.filter_by(
                    id=image_id,
                    safety_check_id=check_id
                ).first()
                
                if image:
                    # حذف من السحابة
                    delete_image(image.image_url)
                    # حذف من قاعدة البيانات
                    db.session.delete(image)
                    deleted_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'تم حذف {deleted_count} صورة بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في حذف الصور: {str(e)}")
            return {
                'success': False,
                'deleted_count': 0,
                'message': f'حدث خطأ: {str(e)}'
            }
    
    # ===============================
    # Notification Methods
    # ===============================
    
    @staticmethod
    def create_safety_check_notification(user_id, vehicle_plate, supervisor_name, check_status, check_id):
        """
        إنشاء إشعار داخلي لفحص السلامة
        
        Returns:
            Notification object
        """
        status_labels = {
            'pending': 'قيد الانتظار',
            'under_review': 'قيد المراجعة',
            'approved': 'موافق عليه',
            'rejected': 'مرفوض'
        }
        
        priority_map = {
            'pending': 'high',
            'under_review': 'normal',
            'approved': 'normal',
            'rejected': 'critical'
        }
        
        status_label = status_labels.get(check_status, check_status)
        
        notification = Notification(
            user_id=user_id,
            notification_type='safety_check',
            title=f'فحص السلامة - السيارة {vehicle_plate}',
            description=f'طلب فحص السلامة الخارجية للسيارة {vehicle_plate} من قبل {supervisor_name} - الحالة: {status_label}',
            related_entity_type='safety_check',
            related_entity_id=check_id,
            priority=priority_map.get(check_status, 'normal'),
            action_url=url_for('external_safety.admin_external_safety_checks')
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def create_safety_check_review_notification(user_id, vehicle_plate, action, reviewer_name, check_id):
        """
        إشعار بمراجعة/موافقة فحص السلامة
        
        Returns:
            Notification object
        """
        action_labels = {
            'approved': 'تمت الموافقة على',
            'rejected': 'تم رفض',
            'under_review': 'قيد المراجعة'
        }
        
        priority = 'high' if action in ['rejected'] else 'normal'
        action_label = action_labels.get(action, action)
        
        notification = Notification(
            user_id=user_id,
            notification_type='safety_check_review',
            title=f'{action_label} فحص السلامة - {vehicle_plate}',
            description=f'تمت مراجعة فحص السلامة للسيارة {vehicle_plate} بواسطة {reviewer_name}: {action_label}',
            related_entity_type='safety_check',
            related_entity_id=check_id,
            priority=priority,
            action_url=url_for('external_safety.admin_external_safety_checks')
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def send_supervisor_notification_email(safety_check):
        """
        إرسال بريد إلكتروني للمشرف عند إنشاء فحص جديد
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            supervisor_email = os.environ.get("SAFETY_CHECK_SUPERVISOR_EMAIL")
            company_name = os.environ.get("COMPANY_NAME", "الشركة")
            
            if not supervisor_email:
                return {'success': False, 'message': 'لم يتم تحديد بريد المشرف'}
            
            resend.api_key = os.environ.get("RESEND_API_KEY")
            
            # بناء محتوى البريد
            check_url = url_for('external_safety.admin_view_safety_check', 
                              check_id=safety_check.id, _external=True)
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; direction: rtl; text-align: right;">
                <h2 style="color: #2c3e50;">إشعار فحص السلامة الخارجية</h2>
                <p>تم تقديم فحص سلامة خارجية جديد يتطلب المراجعة:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>رقم اللوحة:</strong> {safety_check.vehicle_plate_number or 'غير محدد'}</p>
                    <p><strong>السائق:</strong> {safety_check.driver_name or 'غير محدد'}</p>
                    <p><strong>تاريخ الفحص:</strong> {safety_check.check_date.strftime('%Y-%m-%d %H:%M') if safety_check.check_date else 'غير محدد'}</p>
                    <p><strong>الحالة:</strong> قيد الانتظار</p>
                </div>
                
                <a href="{check_url}" 
                   style="display: inline-block; background-color: #007bff; color: white; 
                          padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                    عرض التفاصيل
                </a>
                
                <p style="margin-top: 30px; color: #6c757d; font-size: 12px;">
                    هذا بريد تلقائي من نظام {company_name}
                </p>
            </div>
            """
            
            response = resend.Emails.send({
                "from": f"نظام السلامة <safety@{company_name.lower()}.com>",
                "to": supervisor_email,
                "subject": f"فحص سلامة جديد - {safety_check.vehicle_plate_number}",
                "html": html_content
            })
            
            return {'success': True, 'message': 'تم إرسال البريد بنجاح'}
        
        except Exception as e:
            current_app.logger.error(f"خطأ في إرسال البريد: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def send_whatsapp_notification(phone_number, vehicle_plate, check_url):
        """
        إرسال إشعار WhatsApp للسائق
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # استدعاء خدمة WhatsApp (يتم تنفيذها في app.py)
            from src.app import whatsapp_service
            
            if not whatsapp_service:
                return {'success': False, 'message': 'خدمة WhatsApp غير متاحة'}
            
            message = f"""
مرحباً، تم استلام فحص السلامة الخارجية للسيارة {vehicle_plate}
يمكنك متابعة حالة الفحص من خلال الرابط:
{check_url}
            """
            
            result = whatsapp_service.send_message(phone_number, message)
            return result
        
        except Exception as e:
            current_app.logger.error(f"خطأ في إرسال WhatsApp: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    # ===============================
    # CRUD Operations
    # ===============================
    
    @staticmethod
    def create_safety_check(data, current_user_id=None):
        """
        إنشاء فحص سلامة جديد
        
        Args:
            data (dict): {
                'vehicle_id': int,
                'vehicle_plate_number': str,
                'driver_name': str,
                'driver_national_id': str,
                'tires_ok': bool,
                'lights_ok': bool,
                'mirrors_ok': bool,
                'body_ok': bool,
                'cleanliness_ok': bool,
                'notes': str,
                'latitude': float,
                'longitude': float
            }
            current_user_id: معرف المستخدم الحالي
        
        Returns:
            dict: {'success': bool, 'check': VehicleExternalSafetyCheck, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck(
                vehicle_id=data.get('vehicle_id'),
                vehicle_plate_number=data.get('vehicle_plate_number'),
                driver_name=data.get('driver_name'),
                driver_national_id=data.get('driver_national_id'),
                check_date=datetime.utcnow(),
                tires_ok=data.get('tires_ok', False),
                lights_ok=data.get('lights_ok', False),
                mirrors_ok=data.get('mirrors_ok', False),
                body_ok=data.get('body_ok', False),
                cleanliness_ok=data.get('cleanliness_ok', False),
                notes=data.get('notes', ''),
                approval_status='pending',
                submitted_by_user_id=current_user_id,
                latitude=data.get('latitude'),
                longitude=data.get('longitude')
            )
            
            db.session.add(check)
            db.session.commit()
            
            # Audit log
            if current_user_id:
                log_audit(
                    user_id=current_user_id,
                    event_type='create',
                    description=f'إنشاء فحص سلامة جديد للسيارة {check.vehicle_plate_number}',
                    entity_type='safety_check',
                    entity_id=check.id
                )
            
            return {
                'success': True,
                'check': check,
                'message': 'تم إنشاء الفحص بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في إنشاء فحص السلامة: {str(e)}")
            return {
                'success': False,
                'check': None,
                'message': str(e)
            }
    
    @staticmethod
    def update_safety_check(check_id, data, current_user_id=None):
        """
        تحديث فحص سلامة موجود
        
        Returns:
            dict: {'success': bool, 'check': VehicleExternalSafetyCheck, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
            
            # تحديث الحقول
            if 'tires_ok' in data:
                check.tires_ok = data['tires_ok']
            if 'lights_ok' in data:
                check.lights_ok = data['lights_ok']
            if 'mirrors_ok' in data:
                check.mirrors_ok = data['mirrors_ok']
            if 'body_ok' in data:
                check.body_ok = data['body_ok']
            if 'cleanliness_ok' in data:
                check.cleanliness_ok = data['cleanliness_ok']
            if 'notes' in data:
                check.notes = data['notes']
            if 'driver_name' in data:
                check.driver_name = data['driver_name']
            
            db.session.commit()
            
            # Audit log
            if current_user_id:
                log_audit(
                    user_id=current_user_id,
                    event_type='update',
                    description=f'تحديث فحص السلامة للسيارة {check.vehicle_plate_number}',
                    entity_type='safety_check',
                    entity_id=check.id
                )
            
            return {
                'success': True,
                'check': check,
                'message': 'تم تحديث الفحص بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في تحديث فحص السلامة: {str(e)}")
            return {
                'success': False,
                'check': None,
                'message': str(e)
            }
    
    @staticmethod
    def approve_safety_check(check_id, reviewer_id, reviewer_name):
        """
        الموافقة على فحص السلامة
        
        Returns:
            dict: {'success': bool, 'check': VehicleExternalSafetyCheck, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
            
            check.approval_status = 'approved'
            check.reviewed_by_user_id = reviewer_id
            check.review_date = datetime.utcnow()
            check.review_notes = 'تمت الموافقة على الفحص'
            
            db.session.commit()
            
            # Audit log
            log_audit(
                user_id=reviewer_id,
                event_type='approve',
                description=f'الموافقة على فحص السلامة للسيارة {check.vehicle_plate_number}',
                entity_type='safety_check',
                entity_id=check.id
            )
            
            # إرسال إشعار للسائق
            if check.submitted_by_user_id:
                ExternalSafetyService.create_safety_check_review_notification(
                    user_id=check.submitted_by_user_id,
                    vehicle_plate=check.vehicle_plate_number,
                    action='approved',
                    reviewer_name=reviewer_name,
                    check_id=check.id
                )
            
            return {
                'success': True,
                'check': check,
                'message': 'تمت الموافقة على الفحص بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في الموافقة على فحص السلامة: {str(e)}")
            return {
                'success': False,
                'check': None,
                'message': str(e)
            }
    
    @staticmethod
    def reject_safety_check(check_id, reviewer_id, reviewer_name, rejection_reason):
        """
        رفض فحص السلامة
        
        Returns:
            dict: {'success': bool, 'check': VehicleExternalSafetyCheck, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
            
            check.approval_status = 'rejected'
            check.reviewed_by_user_id = reviewer_id
            check.review_date = datetime.utcnow()
            check.review_notes = rejection_reason or 'تم رفض الفحص'
            
            db.session.commit()
            
            # Audit log
            log_audit(
                user_id=reviewer_id,
                event_type='reject',
                description=f'رفض فحص السلامة للسيارة {check.vehicle_plate_number}: {rejection_reason}',
                entity_type='safety_check',
                entity_id=check.id
            )
            
            # إرسال إشعار للسائق
            if check.submitted_by_user_id:
                ExternalSafetyService.create_safety_check_review_notification(
                    user_id=check.submitted_by_user_id,
                    vehicle_plate=check.vehicle_plate_number,
                    action='rejected',
                    reviewer_name=reviewer_name,
                    check_id=check.id
                )
            
            return {
                'success': True,
                'check': check,
                'message': 'تم رفض الفحص'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في رفض فحص السلامة: {str(e)}")
            return {
                'success': False,
                'check': None,
                'message': str(e)
            }
    
    @staticmethod
    def delete_safety_check(check_id, user_id):
        """
        حذف فحص السلامة ونجميع الصور المرتبطة
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
            vehicle_plate = check.vehicle_plate_number
            
            # حذف جميع الصور من السحابة
            for image in check.images:
                delete_image(image.image_url)
                db.session.delete(image)
            
            # حذف الفحص
            db.session.delete(check)
            db.session.commit()
            
            # Audit log
            log_audit(
                user_id=user_id,
                event_type='delete',
                description=f'حذف فحص السلامة للسيارة {vehicle_plate}',
                entity_type='safety_check',
                entity_id=check_id
            )
            
            return {
                'success': True,
                'message': 'تم حذف الفحص بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في حذف فحص السلامة: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def bulk_delete_safety_checks(check_ids, user_id):
        """
        حذف فحوصات متعددة دفعة واحدة
        
        Returns:
            dict: {'success': bool, 'deleted_count': int, 'message': str}
        """
        try:
            deleted_count = 0
            
            for check_id in check_ids:
                check = VehicleExternalSafetyCheck.query.get(check_id)
                if check:
                    # حذف الصور
                    for image in check.images:
                        delete_image(image.image_url)
                        db.session.delete(image)
                    
                    # حذف الفحص
                    db.session.delete(check)
                    deleted_count += 1
            
            db.session.commit()
            
            # Audit log
            log_audit(
                user_id=user_id,
                event_type='bulk_delete',
                description=f'حذف {deleted_count} فحص سلامة',
                entity_type='safety_check',
                entity_id=None
            )
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'تم حذف {deleted_count} فحص بنجاح'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في الحذف الجماعي: {str(e)}")
            return {
                'success': False,
                'deleted_count': 0,
                'message': str(e)
            }
    
    # ===============================
    # Google Drive Integration
    # ===============================
    
    @staticmethod
    def upload_to_google_drive(check_id, user_id):
        """
        رفع فحص السلامة إلى Google Drive
        
        Returns:
            dict: {'success': bool, 'drive_url': str|None, 'message': str}
        """
        try:
            check = VehicleExternalSafetyCheck.query.get_or_404(check_id)
            uploader = VehicleDriveUploader()
            
            # إنشاء مجلد للفحص
            folder_name = f"Safety_Check_{check.vehicle_plate_number}_{check.id}"
            folder_id = uploader.create_folder(folder_name)
            
            if not folder_id:
                return {
                    'success': False,
                    'drive_url': None,
                    'message': 'فشل إنشاء مجلد Google Drive'
                }
            
            # رفع الصور
            uploaded_count = 0
            for image in check.images:
                # تحميل الصورة من السحابة مؤقتاً
                # (يحتاج تنفيذ حسب خدمة التخزين المستخدمة)
                file_uploaded = uploader.upload_file(image.image_url, folder_id)
                if file_uploaded:
                    uploaded_count += 1
            
            # حفظ رابط Drive في قاعدة البيانات
            check.drive_folder_id = folder_id
            check.drive_folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            db.session.commit()
            
            # Audit log
            log_audit(
                user_id=user_id,
                event_type='drive_upload',
                description=f'رفع فحص السلامة {check.vehicle_plate_number} إلى Google Drive',
                entity_type='safety_check',
                entity_id=check.id
            )
            
            return {
                'success': True,
                'drive_url': check.drive_folder_url,
                'message': f'تم رفع {uploaded_count} ملف إلى Google Drive'
            }
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في رفع Google Drive: {str(e)}")
            return {
                'success': False,
                'drive_url': None,
                'message': str(e)
            }
    
    # ===============================
    # Statistics & Analytics
    # ===============================
    
    @staticmethod
    def get_safety_check_statistics(start_date=None, end_date=None):
        """
        احصائيات فحوصات السلامة
        
        Returns:
            dict: {
                'total_checks': int,
                'pending': int,
                'approved': int,
                'rejected': int,
                'approval_rate': float
            }
        """
        query = VehicleExternalSafetyCheck.query
        
        if start_date:
            query = query.filter(VehicleExternalSafetyCheck.check_date >= start_date)
        if end_date:
            query = query.filter(VehicleExternalSafetyCheck.check_date <= end_date)
        
        total_checks = query.count()
        pending = query.filter_by(approval_status='pending').count()
        approved = query.filter_by(approval_status='approved').count()
        rejected = query.filter_by(approval_status='rejected').count()
        
        approval_rate = (approved / total_checks * 100) if total_checks > 0 else 0
        
        return {
            'total_checks': total_checks,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': round(approval_rate, 2)
        }
