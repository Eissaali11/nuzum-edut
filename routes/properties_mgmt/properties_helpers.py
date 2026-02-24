"""
دوال مساعدة وثابتات لإدارة العقارات المستأجرة
معالجة الملفات والصور والتحقق
"""

import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import pillow_heif

# إعدادات رفع الملفات
UPLOAD_FOLDER = 'static/uploads/properties'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'webp'}


def allowed_file(filename):
    """التحقق من امتداد الملف المسموح به"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_and_save_image(file, property_id):
    """معالجة وحفظ الصورة مع دعم HEIC"""
    try:
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # إنشاء مجلد التخزين
        property_folder = os.path.join(UPLOAD_FOLDER, str(property_id))
        os.makedirs(property_folder, exist_ok=True)
        filepath = os.path.join(property_folder, unique_filename)
        
        # معالجة صور HEIC
        if file_ext == 'heic':
            heif_file = pillow_heif.read_heif(file)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
            # حفظ كـ JPG
            unique_filename = f"{uuid.uuid4()}.jpg"
            filepath = os.path.join(property_folder, unique_filename)
            image.save(filepath, "JPEG", quality=85)
        else:
            file.save(filepath)
        
        # إرجاع المسار النسبي (يجب أن يبدأ بـ static/)
        return filepath
    except Exception as e:
        print(f"خطأ في معالجة الصورة: {e}")
        return None


def process_and_save_contract(file, property_id):
    """معالجة وحفظ ملف العقد (PDF أو صورة)"""
    try:
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = f"contract_{uuid.uuid4()}.{file_ext}"
        
        # إنشاء مجلد التخزين
        property_folder = os.path.join(UPLOAD_FOLDER, str(property_id))
        os.makedirs(property_folder, exist_ok=True)
        filepath = os.path.join(property_folder, unique_filename)
        
        file.save(filepath)
        
        # إرجاع المسار النسبي (يجب أن يبدأ بـ static/)
        return filepath
    except Exception as e:
        print(f"خطأ في معالجة ملف العقد: {e}")
        return None


def get_property_stats():
    """الحصول على إحصائيات العقارات"""
    from datetime import date, timedelta
    from core.extensions import db
    from models import RentalProperty, PropertyPayment
    from sqlalchemy import func
    
    total_properties = RentalProperty.query.filter_by(is_active=True).count()
    active_properties = RentalProperty.query.filter_by(status='active', is_active=True).count()
    
    # العقود المنتهية
    expired_properties_count = RentalProperty.query.filter(
        RentalProperty.contract_end_date < date.today(),
        RentalProperty.is_active == True
    ).count()
    
    # العقود القريبة من الانتهاء (60 يوم)
    expiring_soon_date = date.today() + timedelta(days=60)
    expiring_soon = RentalProperty.query.filter(
        RentalProperty.contract_end_date.between(date.today(), expiring_soon_date),
        RentalProperty.is_active == True
    ).count()
    
    # إجمالي الإيجار السنوي
    total_annual_rent = db.session.query(
        func.sum(RentalProperty.annual_rent_amount)
    ).filter_by(is_active=True, status='active').scalar() or 0
    
    # الدفعات المعلقة
    pending_payments = PropertyPayment.query.filter_by(status='pending').count()
    
    # الدفعات المتأخرة
    overdue_payments = PropertyPayment.query.filter(
        PropertyPayment.status == 'pending',
        PropertyPayment.payment_date < date.today()
    ).count()
    
    # إجمالي المدفوعات
    total_paid = db.session.query(
        func.sum(PropertyPayment.amount)
    ).filter_by(status='paid').scalar() or 0
    
    return {
        'total_properties': total_properties,
        'active_properties': active_properties,
        'expired_properties': expired_properties_count,
        'expiring_soon': expiring_soon,
        'total_annual_rent': total_annual_rent,
        'pending_payments': pending_payments,
        'overdue_payments': overdue_payments,
        'total_paid': total_paid,
        'expiring_soon_date': expiring_soon_date
    }
