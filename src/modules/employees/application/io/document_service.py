"""Employee document and image management service."""
from dataclasses import dataclass
from typing import Optional

from src.core.extensions import db
from models import Employee
from src.modules.employees.application.file_service import save_employee_image
from src.utils.audit_logger import log_activity


@dataclass
class DocumentResult:
    """Result of document operation."""
    success: bool
    message: str
    category: str
    
    
def upload_employee_image(employee_id: int, file, image_type: str) -> DocumentResult:
    """
    Upload employee image (profile, national_id, or license).
    Returns DocumentResult with success status and message.
    """
    employee = Employee.query.get(employee_id)
    if not employee:
        return DocumentResult(False, "الموظف غير موجود", "danger")
    
    if not image_type or image_type not in ['profile', 'national_id', 'license']:
        return DocumentResult(False, "نوع الصورة غير صحيح", "danger")
    
    if not file or file.filename == '':
        return DocumentResult(False, "لم يتم اختيار ملف", "danger")
    
    # Save image file
    image_path = save_employee_image(file, employee.id, image_type)
    
    if not image_path:
        return DocumentResult(
            False,
            "❌ فشل في رفع الصورة. تأكد من أن الملف من النوع المسموح",
            "danger"
        )
    
    try:
        # Update employee record with new image path
        old_path = None
        if image_type == 'profile':
            old_path = employee.profile_image
            employee.profile_image = image_path
        elif image_type == 'national_id':
            old_path = employee.national_id_image
            employee.national_id_image = image_path
        elif image_type == 'license':
            old_path = employee.license_image
            employee.license_image = image_path
        
        db.session.commit()
        print(f"OK DB: تم حفظ {image_path} في قاعدة البيانات")
        
        # Old file is kept for safety
        if old_path:
            print(f"💾 الملف القديم محفوظ للأمان: {old_path}")
        
        success_messages = {
            'profile': '✅ تم رفع الصورة الشخصية بنجاح',
            'national_id': '✅ تم رفع صورة الهوية بنجاح',
            'license': '✅ تم رفع صورة الرخصة بنجاح'
        }
        
        return DocumentResult(
            True,
            success_messages.get(image_type, '✅ تم رفع الصورة بنجاح'),
            "success"
        )
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        return DocumentResult(False, f"❌ خطأ: {str(e)}", "danger")


def delete_housing_image(employee_id: int, image_path: str) -> DocumentResult:
    """
    Delete housing image from employee's housing images list.
    File is kept on disk for safety, only reference is removed.
    """
    employee = Employee.query.get(employee_id)
    if not employee:
        return DocumentResult(False, "الموظف غير موجود", "danger")
    
    if not image_path or not image_path.strip():
        return DocumentResult(False, "لم يتم تحديد الصورة المراد حذفها", "warning")
    
    try:
        if not employee.housing_images:
            return DocumentResult(False, "لا توجد صور سكن لحذفها", "warning")
        
        # Convert comma-separated string to list
        image_list = [img.strip() for img in employee.housing_images.split(',')]
        
        # Find image in list
        clean_image_path = image_path.replace('static/', '')
        image_to_remove = None
        
        for img in image_list:
            if img.replace('static/', '') == clean_image_path:
                image_to_remove = img
                break
        
        if not image_to_remove:
            return DocumentResult(False, "لم يتم العثور على الصورة في القائمة", "warning")
        
        # Remove image from list
        image_list.remove(image_to_remove)
        
        # File is kept for safety, only remove reference from database
        employee.housing_images = ','.join(image_list) if image_list else None
        db.session.commit()
        
        # Log activity
        log_activity('delete', 'Employee', employee.id, 
                    f'تم إزالة صورة من صور السكن للموظف: {employee.name} (الملف محفوظ)')
        
        return DocumentResult(
            True,
            "تم إزالة الصورة (الملف محفوظ بشكل آمن)",
            "success"
        )
        
    except Exception as e:
        db.session.rollback()
        return DocumentResult(False, f"حدث خطأ أثناء حذف الصورة: {str(e)}", "danger")
