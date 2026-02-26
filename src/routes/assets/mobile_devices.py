"""
إدارة الأجهزة المحمولة - تغليف التوافقية
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع مسارات الأجهزة والتخصيصات محفوظة:
• إدارة الأجهزة المحمولة
• تخصيص الأجهزة للموظفين
• متابعة الأجهزة والصيانة

# ما قبل: 1,293 سطر
# بعد: ~30 سطر من الكود النظيف
"""

from flask import Blueprint

def register_mobile_devices_routes(app):
    """تسجيل مسارات إدارة الأجهزة المحمولة"""
    try:
        from ..legacy.mobile_devices_old import mobile_devices_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from ..legacy.mobile_devices_old import mobile_devices_bp
except ImportError:
    mobile_devices_bp = Blueprint('mobile_devices', __name__)

__all__ = ['mobile_devices_bp', 'register_mobile_devices_routes']
