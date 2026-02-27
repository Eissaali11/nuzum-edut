# -*- coding: utf-8 -*-
"""
مسارات الحضور — المعمارية المعيارية (Phase 2)
Attendance Routes Module - Modular Architecture
"""

from flask import Blueprint


def _build_modular_blueprint():
    main_bp = Blueprint('attendance', __name__)

    from .attendance_list import index, department_attendance_view
    from .attendance_record import record, department_attendance as dept_att_record, bulk_record, all_departments_attendance, department_bulk_attendance
    from .attendance_edit_delete import confirm_delete_attendance, delete_attendance, bulk_delete_attendance, edit_attendance_page, update_attendance_page
    from .attendance_export import export_excel, export_page, export_excel_dashboard, export_excel_department, export_department_data, export_department_period
    from .attendance_stats import stats, dashboard, employee_attendance, department_stats, department_details
    from .attendance_circles import departments_circles_overview, circle_accessed_details, export_circle_access_excel, mark_circle_employees_attendance
    from .attendance_api import get_department_employees

    main_bp.add_url_rule('/', 'index', index, methods=['GET'])
    main_bp.add_url_rule('/department/view', 'department_attendance_view', department_attendance_view, methods=['GET'])

    main_bp.add_url_rule('/record', 'record', record, methods=['GET', 'POST'])
    main_bp.add_url_rule('/department', 'department_attendance', dept_att_record, methods=['GET', 'POST'])
    main_bp.add_url_rule('/bulk-record', 'bulk_record', bulk_record, methods=['GET', 'POST'])
    main_bp.add_url_rule('/all-departments', 'all_departments_attendance', all_departments_attendance, methods=['GET', 'POST'])
    main_bp.add_url_rule('/department/bulk', 'department_bulk_attendance', department_bulk_attendance, methods=['GET', 'POST'])

    main_bp.add_url_rule('/delete/<int:id>/confirm', 'confirm_delete_attendance', confirm_delete_attendance, methods=['GET'])
    main_bp.add_url_rule('/delete/<int:id>', 'delete_attendance', delete_attendance, methods=['POST'])
    main_bp.add_url_rule('/bulk_delete', 'bulk_delete_attendance', bulk_delete_attendance, methods=['POST'])
    main_bp.add_url_rule('/edit/<int:id>', 'edit_attendance_page', edit_attendance_page, methods=['GET'])
    main_bp.add_url_rule('/edit/<int:id>', 'update_attendance_page', update_attendance_page, methods=['POST'])

    main_bp.add_url_rule('/export', 'export_page', export_page, methods=['GET'])
    main_bp.add_url_rule('/export/excel', 'export_excel', export_excel, methods=['GET', 'POST'])
    main_bp.add_url_rule('/export-excel-dashboard', 'export_excel_dashboard', export_excel_dashboard, methods=['GET'])
    main_bp.add_url_rule('/export-excel-department', 'export_excel_department', export_excel_department, methods=['GET'])
    main_bp.add_url_rule('/department/export-data', 'export_department_data', export_department_data, methods=['GET'])
    main_bp.add_url_rule('/department/export-period', 'export_department_period', export_department_period, methods=['GET'])

    main_bp.add_url_rule('/stats', 'stats', stats, methods=['GET'])
    main_bp.add_url_rule('/dashboard', 'dashboard', dashboard, methods=['GET'])
    main_bp.add_url_rule('/employee/<int:employee_id>', 'employee_attendance', employee_attendance, methods=['GET'])
    main_bp.add_url_rule('/department-stats', 'department_stats', department_stats, methods=['GET'])
    main_bp.add_url_rule('/department-details', 'department_details', department_details, methods=['GET'])

    main_bp.add_url_rule('/departments-circles-overview', 'departments_circles_overview', departments_circles_overview, methods=['GET'])
    main_bp.add_url_rule('/circle-accessed-details/<int:department_id>/<circle_name>', 'circle_accessed_details', circle_accessed_details, methods=['GET'])
    main_bp.add_url_rule('/circle-accessed-details/<int:department_id>/<circle_name>/export-excel', 'export_circle_access_excel', export_circle_access_excel, methods=['GET'])
    main_bp.add_url_rule('/mark-circle-employees-attendance/<int:department_id>/<circle_name>', 'mark_circle_employees_attendance', mark_circle_employees_attendance, methods=['POST'])

    main_bp.add_url_rule('/api/departments/<int:department_id>/employees', 'get_department_employees', get_department_employees, methods=['GET'])

    return main_bp


_attendance_bp_cache = None


def _initialize_attendance_bp():
    global _attendance_bp_cache

    if _attendance_bp_cache is not None:
        return _attendance_bp_cache

    _attendance_bp_cache = _build_modular_blueprint()
    print("[OK] Attendance Module: Using modular structure")
    return _attendance_bp_cache


def __getattr__(name):
    if name == 'attendance_bp':
        return _initialize_attendance_bp()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ['attendance_bp']
