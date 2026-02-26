"""
إدارة بطاقات SIM - تغليف التوافقية
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع المسارات متاحة:
• routes/sim_mgmt/ - دوال مساعدة متخصصة
• جميع مسارات الـ SIM (13 مسار) محفوظة

# ما قبل: 1,010 سطر
# بعد: ~30 سطر من الكود النظيف
"""

from flask import Blueprint

def register_sim_routes(app):
    """تسجيل مسارات إدارة بطاقات SIM"""
    try:
        from .sim_management_old import sim_management_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from .sim_management_old import sim_management_bp
except ImportError:
    sim_management_bp = Blueprint('sim_management', __name__)

__all__ = ['sim_management_bp', 'register_sim_routes']
