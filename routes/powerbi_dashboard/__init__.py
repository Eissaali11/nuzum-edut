"""
سجل مسارات Power BI Dashboard
يجمع كل المسارات الفرعية في مجموعة blueprint واحدة
"""

from flask import Blueprint
from .powerbi_main_routes import powerbi_main_bp
from .powerbi_analytics_routes import powerbi_analytics_bp
from .powerbi_dashboard import powerbi_bp


def register_powerbi_routes(app):
    """تسجيل جميع مسارات Power BI Dashboard"""
    app.register_blueprint(powerbi_main_bp)
    app.register_blueprint(powerbi_analytics_bp)


# للعودة للخلف متوافق - تصدير التعاريف
__all__ = ['register_powerbi_routes', 'powerbi_bp', 'powerbi_main_bp', 'powerbi_analytics_bp']
