"""
لوحة معلومات Power BI Dashboard - تغليف التوافقية للعودة للخلف
═══════════════════════════════════════════════════════════════════════════

!!! هذا الملف تم إعادة تصميمه كـ wrapper توافقي !!!

جميع المسارات تم نقلها إلى وحدات متخصصة:
• routes/powerbi_dashboard/powerbi_main_routes.py - المسارات الرئيسية
• routes/powerbi_dashboard/powerbi_analytics_routes.py - مسارات API التحليلية  
• routes/powerbi_dashboard/powerbi_helpers.py - الدوال المساعدة المشتركة
• routes/powerbi_dashboard/__init__.py - سجل المسارات

# ما قبل: 1843 سطر من الكود المتكرر
# بعد: ~30 سطر من الكود النظيف المنظم
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from src.routes.powerbi_dashboard.powerbi_main_routes import powerbi_main_bp
from src.routes.powerbi_dashboard.powerbi_analytics_routes import powerbi_analytics_bp

# إنشاء Blueprint رئيسي يجمع كل المسارات الفرعية
# هذا يحافظ على التوافقية مع التطبيق الحالي
powerbi_bp = Blueprint('powerbi', __name__, url_prefix='/powerbi')


@powerbi_bp.route('/dashboard')
@login_required
def dashboard():
	return redirect(url_for('powerbi_main.dashboard'))

# ربط المسارات الفرعية
powerbi_bp.register_blueprint(powerbi_main_bp)
powerbi_bp.register_blueprint(powerbi_analytics_bp)

__all__ = ['powerbi_bp']
