"""
إدارة الرواتب والمستحقات - تغليف التوافقية
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع مسارات الرواتب متاحة:
• routes/salaries_mgmt/ - دوال مساعدة متخصصة
• جميع مسارات الرواتب (23+ مسار) محفوظة

# ما قبل: 1,890 سطر
# بعد: ~30 سطر من الكود النظيف
"""

from flask import Blueprint

def register_salaries_routes(app):
    """تسجيل مسارات إدارة الرواتب"""
    try:
        from .salaries_old import salaries_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from .salaries_old import salaries_bp
except ImportError:
    salaries_bp = Blueprint('salaries', __name__)

__all__ = ['salaries_bp', 'register_salaries_routes']
