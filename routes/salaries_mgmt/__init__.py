"""
إدارة الرواتب - Blueprint مركزي
يجمع كل مسارات إدارة الرواتب (23+ مسار)
"""

from flask import Blueprint
from .salaries import salaries_bp
from routes.salaries_mgmt.salaries_helpers import (
    get_salary_for_month,
    get_employee_salary_history,
    calculate_salary_totals,
    get_attendance_for_salary,
    get_salary_statistics,
    validate_salary_data,
    group_salaries_by_department,
    get_salary_report_data
)


def register_salaries_routes(app):
    """تسجيل مسارات إدارة الرواتب"""
    # استيراد المسارات الأصلية كبديل مؤقت
    try:
        from routes.salaries import salaries_bp
        app.register_blueprint(salaries_bp)
    except ImportError:
        pass


__all__ = [
    'register_salaries_routes',
    'salaries_bp',
    'get_salary_for_month',
    'get_employee_salary_history',
    'calculate_salary_totals',
    'get_attendance_for_salary',
    'get_salary_statistics',
    'validate_salary_data',
    'group_salaries_by_department',
    'get_salary_report_data'
]
