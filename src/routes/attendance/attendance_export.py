"""
Attendance Export Routes
========================
Extracted from _attendance_main.py as part of modularization.
Handles all attendance export operations (Excel, PDF).

NOTE: Export functions contain complex Excel generation code (~1000+ lines).
      For Phase 2, we maintain compatibility by importing from the original file.
      Full refactoring can be done in Phase 3.

Routes:
    - GET/POST /export/excel           : Export attendance to Excel
    - GET      /export                  : Export page (form)
    - GET      /export-excel-dashboard : Export dashboard summary
    - GET      /export-excel-department: Export department details  
    - GET      /department/export-data  : Export with filters (P/A format)
    - GET      /department/export-period: Export department over period (professional dashboard)
"""

from flask import Blueprint, request, flash, redirect, url_for, render_template, send_file, jsonify
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import or_
import logging

from src.core.extensions import db
from models import Attendance, Employee, Department, employee_departments
from src.utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from src.utils.excel import export_attendance_by_department
from src.utils.excel_dashboard import export_attendance_by_department_with_dashboard

logger = logging.getLogger(__name__)

# Create blueprint
export_bp = Blueprint('export', __name__)


@export_bp.route('/export/excel', methods=['POST', 'GET'])
def export_excel():
    """تصدير بيانات الحضور إلى ملف Excel
    
    NOTE: This is a simplified stub. Full implementation (~100 lines)
          uses export_attendance_by_department() from src.utils.excel
    """
    try:
        # Get parameters (support both POST and GET)
        if request.method == 'POST':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            department_id = request.form.get('department_id')
        else:  # GET
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            department_id = request.args.get('department_id')
        
        # Validate inputs
        if not start_date_str:
            flash('تاريخ البداية مطلوب', 'danger')
            return redirect(url_for('attendance.export_page'))
        
        # Parse dates
        try:
            start_date = parse_date(start_date_str)
            if end_date_str:
                end_date = parse_date(end_date_str)
            else:
                end_date = datetime.now().date()
        except (ValueError, TypeError):
            flash('تاريخ غير صالح', 'danger')
            return redirect(url_for('attendance.export_page'))
        
        # Export single department or all
        if department_id and department_id != '':
            department = Department.query.get(department_id)
            if not department:
                flash('القسم غير موجود', 'danger')
                return redirect(url_for('attendance.export_page'))
            
            # Get attendance records
            attendances = Attendance.query.filter(
                Attendance.date.between(start_date, end_date)
            ).all()
            
            # Filter employees
            employee_ids_with_attendance = set([att.employee_id for att in attendances])
            department_employee_ids = [emp.id for emp in department.employees]
            employees_to_export = Employee.query.filter(
                Employee.id.in_(department_employee_ids),
                or_(
                    ~Employee.status.in_(['terminated', 'inactive']),
                    Employee.id.in_(employee_ids_with_attendance)
                )
            ).all()
            
            attendances = [att for att in attendances if att.employee_id in department_employee_ids]
            excel_file = export_attendance_by_department(employees_to_export, attendances, start_date, end_date)
            filename = f'سجل الحضور - {department.name} - {start_date_str} إلى {end_date_str}.xlsx'
        else:
            # Export all departments
            attendances = Attendance.query.filter(
                Attendance.date.between(start_date, end_date)
            ).all()
            
            employee_ids_with_attendance = set([att.employee_id for att in attendances])
            all_employees = Employee.query.filter(
                or_(
                    ~Employee.status.in_(['terminated', 'inactive']),
                    Employee.id.in_(employee_ids_with_attendance)
                )
            ).all()
            
            excel_file = export_attendance_by_department_with_dashboard(all_employees, attendances, start_date, end_date)
            filename = f'سجل الحضور - جميع الأقسام - {start_date_str} إلى {end_date_str}.xlsx'
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f'Export excel error: {str(e)}', exc_info=True)
        flash(f'حدث خطأ أثناء تصدير البيانات: {str(e)}', 'danger')
        return redirect(url_for('attendance.export_page'))


@export_bp.route('/export')
def export_page():
    """صفحة تصدير بيانات الحضور إلى ملف Excel"""
    departments = Department.query.all()
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    
    hijri_today = format_date_hijri(today)
    gregorian_today = format_date_gregorian(today)
    hijri_start = format_date_hijri(start_of_month)
    gregorian_start = format_date_gregorian(start_of_month)
    
    return render_template('attendance/export.html',
                          departments=departments,
                          today=today,
                          start_of_month=start_of_month,
                          hijri_today=hijri_today,
                          gregorian_today=gregorian_today,
                          hijri_start=hijri_start,
                          gregorian_start=gregorian_start)


@export_bp.route('/export-excel-dashboard')
def export_excel_dashboard():
    """تصدير لوحة المعلومات إلى Excel
    
    NOTE: Requires AttendanceReportService from services/attendance_reports.py
    """
    try:
        from src.services.attendance_reports import AttendanceReportService
        
        selected_department = request.args.get('department', None)
        selected_project = request.args.get('project', None)
        
        result = AttendanceReportService.export_dashboard_summary(selected_department, selected_project)
        
        return send_file(
            result['buffer'],
            mimetype=result['mimetype'],
            as_attachment=True,
            download_name=result['filename']
        )
        
    except Exception as e:
        logger.error(f"Export Excel Dashboard Error: {type(e).__name__}: {str(e)}", exc_info=True)
        flash('حدث خطأ أثناء تصدير الملف', 'error')
        return redirect(url_for('attendance.dashboard'))


@export_bp.route('/export-excel-department')
def export_excel_department():
    """تصدير تفاصيل القسم إلى Excel
    
    NOTE: Requires AttendanceReportService from services/attendance_reports.py
    """
    logger.info("[EXPORT] export_excel_department route called")
    try:
        department_name = request.args.get('department')
        logger.info(f"[EXPORT] Department requested: {department_name}")
        selected_project = request.args.get('project', None)
        
        if not department_name:
            logger.warning("[EXPORT] No department provided")
            flash('يجب تحديد القسم', 'error')
            return redirect(url_for('attendance.dashboard'))
        
        logger.info("[EXPORT] Loading AttendanceReportService")
        from src.services.attendance_reports import AttendanceReportService
        
        logger.info(f"[EXPORT] Calling export_department_details for: {department_name}")
        result = AttendanceReportService.export_department_details(department_name, selected_project)
        logger.info(f"[EXPORT] Service returned result with filename: {result.get('filename')}")
        
        logger.info("[EXPORT] Sending file...")
        return send_file(
            result['buffer'],
            mimetype=result['mimetype'],
            as_attachment=True,
            download_name=result['filename']
        )
        
    except Exception as e:
        logger.error(f"Export Excel Department Error: {type(e).__name__}: {str(e)}", exc_info=True)
        flash(f'خطأ: {str(e)}', 'error')
        return redirect(url_for('attendance.dashboard'))


# ======================================================================
# COMPLEX EXPORT ROUTES - Stubs for Phase 2
# ======================================================================
# These functions contain 300-500 lines each of openpyxl code.
# For Phase 2, we keep them as stubs pointing to the original file.
# They will be fully refactored in Phase 3.

@export_bp.route('/department/export-data', methods=['GET'])
def export_department_data():
    """تصدير بيانات الحضور حسب الفلاتر مع تصميm احترافي
    
    NOTE: This function is ~300 lines of openpyxl code.
          For Phase 2, import from original _attendance_main.py
    """
    # TODO Phase 3: Extract this function fully
    # Temporary: redirect to original implementation
    from src.routes._attendance_main import export_department_data as original_func
    return original_func()


@export_bp.route('/department/export-period', methods=['GET'])
def export_department_period():
    """تصدير حضور قسم خلال فترة زمنية إلى Excel مع dashboard احترافي
    
    NOTE: This function is ~500 lines of openpyxl code.
          For Phase 2, import from original _attendance_main.py
    """
    # TODO Phase 3: Extract this function fully
    # Temporary: redirect to original implementation
    from src.routes._attendance_main import export_department_period as original_func
    return original_func()


# Note about complex functions:
# export_department_data() and export_department_period() contain extensive
# openpyxl formatting code (~800 lines combined). For Phase 2 modularization,
# we keep them in the original file to avoid migration risks.
# 
# Phase 3 TODO:
# - Extract Excel generation logic to separate service classes
# - Create ExcelStyleService for formatting
# - Create ExcelChartService for charts
# - Refactor into clean, testable functions
