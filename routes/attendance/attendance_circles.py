"""
Attendance Circles & Geofencing Routes
=======================================
Extracted from _attendance_main.py as part of modularization.
Handles geofencing, GPS tracking, and circle-based attendance.

NOTE: Circle routes contain ~700 lines of complex GPS/geofencing logic.
      For Phase 2, we import from original for stability.
      Full refactoring requires geofencing service architecture (Phase 3).

Routes:
    - GET  /departments-circles-overview                      : Overview of all departments & circles
    - GET  /circle-accessed-details/<dept_id>/<circle_name>  : Detailed circle access view  
    - GET  /circle-accessed-details/.../export-excel         : Export circle data to Excel
    - POST /mark-circle-employees-attendance/...             : Mark employees as present based on GPS
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required
from datetime import datetime, timedelta, time
import logging

from core.extensions import db
from models import Attendance, Employee, Department, EmployeeLocation, GeofenceSession
from utils.date_converter import format_date_hijri

logger = logging.getLogger(__name__)

# Create blueprint
circles_bp = Blueprint('circles', __name__)


# ======================================================================
# COMPLEX GEOFENCING ROUTES - Stubs for Phase 2
# ======================================================================
# These functions contain ~700 lines of complex GPS tracking logic:
# - EmployeeLocation queries
# - GeofenceSession tracking  
# - GPS coordinate processing
# - Circle entry/exit detection
# - Duration calculations
#
# For Phase 2, we keep them in the original file to avoid migration risks.
#
# Phase 3 TODO:
# - Create services/geofencing_service.py
# - Extract GPS calculation logic
# - Create GeofenceAnalytics service
# - Refactor into testable components

@circles_bp.route('/departments-circles-overview')
@login_required
def departments_circles_overview():
    """لوحة تحكم شاملة تعرض الأقسام والدوائر وبيانات الحضور مع فلاتر
    
    NOTE: This function is ~300 lines with complex logic:
          - GPS tracking (EmployeeLocation)
          - Geofence sessions (GeofenceSession)
          - Circle aggregations
          - Employee location grouping
    
    For Phase 2, importing from original _attendance_main.py
    """
    # TODO Phase 3: Extract to GeofencingService
    # Temporary: redirect to original implementation
    from routes._attendance_main import departments_circles_overview as original_func
    return original_func()


@circles_bp.route('/circle-accessed-details/<int:department_id>/<circle_name>')
@login_required
def circle_accessed_details(department_id, circle_name):
    """صفحة منفصلة لعرض تفاصيل الموظفين الواصلين للدائرة
    
    NOTE: This function contains detailed geofence analytics.
          ~200 lines of GPS and session tracking logic.
          For Phase 2, importing from original.
    """
    # TODO Phase 3: Extract to GeofenceReportService
    # Temporary: redirect to original implementation
    from routes._attendance_main import circle_accessed_details as original_func
    return original_func(department_id, circle_name)


@circles_bp.route('/circle-accessed-details/<int:department_id>/<circle_name>/export-excel')
@login_required
def export_circle_access_excel(department_id, circle_name):
    """تصدير تفاصيل الدائرة إلى Excel
    
    NOTE: Contains openpyxl code for circle attendance export.
          ~150 lines of Excel formatting.
          For Phase 2, importing from original.
    """
    # TODO Phase 3: Extract to CircleExportService
    # Temporary: redirect to original implementation
    from routes._attendance_main import export_circle_access_excel as original_func
    return original_func(department_id, circle_name)


@circles_bp.route('/mark-circle-employees-attendance/<int:department_id>/<circle_name>', methods=['POST'])
@login_required
def mark_circle_employees_attendance(department_id, circle_name):
    """تسجيل الموظفين الواصلين للدائرة كحاضرين مع أوقات الدخول والخروج
    
    NOTE: Contains GPS-based attendance marking logic.
          Processes GeofenceSession data to extract check-in/check-out times.
          ~120 lines of logic.
          For Phase 2, importing from original.
    """
    # TODO Phase 3: Extract to GeofenceAttendanceService
    # Temporary: redirect to original implementation
    from routes._attendance_main import mark_circle_employees_attendance as original_func
    return original_func(department_id, circle_name)


# ======================================================================
# PHASE 3 GEOFENCING ARCHITECTURE NOTES
# ======================================================================
#
# Current state: Circle routes contain ~700 lines of GPS/geofencing logic.
#
# Recommended Phase 3 architecture:
# 1. Create services/geofencing_service.py
#    - get_geofence_sessions(employee_id, date_range)
#    - calculate_entry_exit_times(sessions)
#    - extract_check_in_out(sessions, timezone)
#    - group_employees_by_circle(department_id)
#
# 2. Create services/gps_calculator.py
#    - calculate_distance(lat1, lon1, lat2, lon2)
#    - is_within_radius(location, circle_center, radius)
#    - get_latest_location(employee_id)
#
# 3. Create services/circle_analytics.py
#    - get_circle_summary(department_id, circle_name, date_range)
#    - get_accessed_employees(circle_name, date_range)
#    - calculate_time_in_circle(employee_id, circle_name, date)
#
# 4. Update these route handlers to use new services
#
# Benefits:
# - Testable GPS logic (isolated from Flask)
# - Reusable geofencing functions
# - Easier to add new geofence features
# - Performance optimizations possible
#
# ======================================================================
