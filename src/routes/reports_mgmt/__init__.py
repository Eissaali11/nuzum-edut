"""
إدارة التقارير - Blueprint مركزي
يجمع كل مسارات التقارير (22 مسار)
"""

from flask import Blueprint
from .reports import reports_bp
from src.routes.reports_mgmt.reports_helpers import (
    get_date_filters,
    get_department_filter,
    get_vehicles_for_report,
    get_employees_for_report,
    get_attendance_stats,
    get_salary_stats,
    get_documents_for_report,
    check_document_expiry,
    get_fees_summary
)


def register_reports_routes(app):
    """تسجيل مسارات التقارير المتقدمة"""
    # استيراد المسارات الأصلية كبديل مؤقت
    try:
        from src.routes.reports import reports_bp
        app.register_blueprint(reports_bp)
    except ImportError:
        pass


__all__ = [
    'register_reports_routes',
    'reports_bp',
    'get_date_filters',
    'get_department_filter',
    'get_vehicles_for_report',
    'get_employees_for_report',
    'get_attendance_stats',
    'get_salary_stats',
    'get_documents_for_report',
    'check_document_expiry',
    'get_fees_summary'
]
