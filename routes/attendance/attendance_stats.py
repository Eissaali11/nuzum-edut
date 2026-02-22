"""
Attendance Statistics & Reports Routes
=======================================
Extracted from _attendance_main.py as part of modularization.
Handles all attendance statistics, dashboards, and reporting operations.

NOTE: The /dashboard route contains ~400 lines of complex analytics logic.
      For Phase 2, we import from original for stability.
      Full refactoring with service layer will be done in Phase 3.

Routes:
    - GET /stats              : Basic stats API (JSON)
    - GET /dashboard          : Main analytics dashboard (~400 lines!)
    - GET /employee/<id>      : Individual employee attendance report
    - GET /department-stats   : Department statistics API (JSON)
    - GET /department-details : Detailed department view
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from sqlalchemy import func
from datetime import datetime, timedelta, date
import calendar
import logging
import time as time_module

from core.extensions import db
from models import Attendance, Employee, Department, employee_departments
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from services.attendance_analytics import AttendanceAnalytics

logger = logging.getLogger(__name__)

# Create blueprint
stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/stats')
def stats():
    """Get attendance statistics for a date range - Simple JSON API"""
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    department_id = request.args.get('department_id', '')
    
    try:
        start_date = parse_date(start_date_str) if start_date_str else datetime.now().date().replace(day=1)
        end_date = parse_date(end_date_str) if end_date_str else datetime.now().date()
    except ValueError:
        start_date = datetime.now().date().replace(day=1)
        end_date = datetime.now().date()
    
    query = db.session.query(
        Attendance.status,
        func.count(Attendance.id).label('count')
    ).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    if department_id and department_id != '':
        query = query.join(Employee).filter(Employee.department_id == department_id)
    
    stats_results = query.group_by(Attendance.status).all()
    
    # Convert to a dict for easier consumption by charts
    result = {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0}
    for status, count in stats_results:
        result[status] = count
    
    return jsonify(result)


# ======================================================================
# COMPLEX DASHBOARD ROUTE - Stub for Phase 2
# ======================================================================
# This function is ~400 lines of complex analytics, retry logic, and charting.
# For Phase 2, we keep it in the original file to avoid migration risks.

@stats_bp.route('/dashboard')
def dashboard():
    """لوحة معلومات الحضور مع إحصائيات يومية وأسبوعية وشهرية
    
    NOTE: This function is ~400 lines with complex analytics:
          - Daily/Weekly/Monthly stats
          - Retry logic for DB connections
          - Chart data preparation
          - Project filtering
          - AttendanceAnalytics service calls
    
    For Phase 2, importing from original _attendance_main.py
    """
    # TODO Phase 3: Extract dashboard logic to DashboardService
    # Temporary: redirect to original implementation
    from routes._attendance_main import dashboard as original_func
    return original_func()


@stats_bp.route('/department-stats')
def department_stats():
    """API لجلب إحصائيات الحضور حسب الأقسام
    
    NOTE: Contains department-level aggregations with project filtering.
          For Phase 2, importing from original for stability.
    """
    # TODO Phase 3: Extract to DepartmentStatsService
    # Temporary: redirect to original implementation
    from routes._attendance_main import department_stats as original_func
    return original_func()


@stats_bp.route('/employee/<int:employee_id>')
def employee_attendance(employee_id):
    """عرض سجلات الحضور التفصيلية للموظف مرتبة حسب الشهر والسنة
    
    NOTE: Contains detailed employee dashboard with monthly/yearly views.
          ~100 lines of logic.
          For Phase 2, importing from original.
    """
    # TODO Phase 3: Extract to EmployeeReportService
    # Temporary: redirect to original implementation
    from routes._attendance_main import employee_attendance as original_func
    return original_func(employee_id)


@stats_bp.route('/department-details')
def department_details():
    """صفحة تفاصيل الحضور لقسم معين
    
    NOTE: Contains detailed department view with:
          - Daily/Weekly breakdown
          - Employee attendance matrices
          - ~150 lines of logic
          For Phase 2, importing from original.
    """
    # TODO Phase 3: Extract to DepartmentReportService
    # Temporary: redirect to original implementation
    from routes._attendance_main import department_details as original_func
    return original_func()


# ======================================================================
# PHASE 3 REFACTORING NOTES
# ======================================================================
#
# Current state: Stats routes contain ~700 lines of complex analytics logic.
#
# Recommended Phase 3 architecture:
# 1. Create services/attendance_dashboard_service.py
#    - extract_daily_stats()
#    - extract_weekly_stats()
#    - extract_monthly_stats()
#    - prepare_chart_data()
#
# 2. Create services/employee_report_service.py
#    - get_employee_attendance_summary()
#    - get_monthly_breakdown()
#
# 3. Create services/department_report_service.py
#    - get_department_stats()
#    - get_daily_breakdown()
#    - get_weekly_summary()
#
# 4. Update these route handlers to use new services
#
# Benefits:
# - Testable business logic (isolated from Flask)
# - Reusable analytics functions
# - Cleaner separation of concerns
# - Easier to optimize queries
#
# ======================================================================
