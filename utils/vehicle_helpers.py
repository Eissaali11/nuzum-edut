"""
مساعدات المركبات — دوال مساعدة بدون مسارات (لا @route).
يُستورد منها: log_audit، allowed_file.
الثوابت والدوال المرتبطة بقاعدة البيانات في application.vehicles.vehicle_service.
"""
from utils.audit_logger import log_activity


def log_audit(action, entity_type, entity_id, details=None):
    """تسجيل الإجراء في سجل النظام (غلاف لـ log_activity)."""
    log_activity(action, entity_type, entity_id, details)


def allowed_file(filename, allowed_extensions=None):
    """
    التحقق من أن امتداد الملف مسموح.
    إذا لم تُمرر allowed_extensions تُستخدم القيمة الافتراضية: png, jpg, jpeg, gif, pdf, doc, docx.
    """
    if allowed_extensions is None:
        allowed_extensions = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
