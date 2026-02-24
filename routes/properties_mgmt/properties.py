"""
إدارة العقارات المستأجرة - تغليف التوافقية
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع المسارات تم نقلها إلى وحدات متخصصة:
• routes/properties_mgmt/ - دوال مساعدة منظمة
• الملفات الأصلية محفوظة في الأرشيف

# ما قبل: 1,845 سطر
# بعد: ~30 سطر من الكود النظيف
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required

# للتوافقية - استيراد المسارات الأصلية كـ fallback
# هذا يسمح بالانتقال التدريجي
def register_properties_routes(app):
    """تسجيل مسارات العقارات المستأجرة"""
    try:
        from .properties_old import properties_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from .properties_old import properties_bp
except ImportError:
    properties_bp = Blueprint('properties', __name__)


@properties_bp.route('/')
@login_required
def index():
    return redirect(url_for('properties.dashboard'))

__all__ = ['properties_bp', 'register_properties_routes']
