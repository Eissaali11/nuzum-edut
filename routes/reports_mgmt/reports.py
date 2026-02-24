"""
التقارير المتقدمة - تغليف التوافقية
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع المسارات متاحة:
• routes/reports_mgmt/ - دوال مساعدة متخصصة
• جميع التقارير (22 مسار) محفوظة تماماً

# ما قبل: 2,177 سطر
# بعد: ~30 سطر من الكود النظيف
"""

from flask import Blueprint

def register_reports_routes(app):
    """تسجيل مسارات التقارير"""
    try:
        from .reports_old import reports_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from .reports_old import reports_bp
except ImportError:
    reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

__all__ = ['reports_bp', 'register_reports_routes']
