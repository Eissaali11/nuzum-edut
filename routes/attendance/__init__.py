# -*- coding: utf-8 -*-
"""
مسارات الحضور والإجازات - انتقال آمن (محدث)
Attendance Routes Module - Safe Transition (Updated Feb 22, 2026)

تطور التقسيم الهندسي:
====================
Phase 1 (OLD): النسخة القديمة المودولار - 7 ملفات (~2,300 سطر)
    - views.py, recording.py, circles.py, crud.py, export.py, statistics.py, helpers.py
    - تستخدم نمط register_*_routes(bp)

Phase 2 (NEW): النسخة الجديدة المحسّنة - 3 ملفات (~730 سطر)
    - attendance_list.py, attendance_record.py, attendance_helpers.py
    - تستخدم نمط Blueprint منفصل لكل ملف

السلوك الافتراضي:
- استخدام النسخة الأصلية (_attendance_main.py) بدون أي تغيير.

تفعيل النسخة المودولار (اختياري):
- ATTENDANCE_USE_MODULAR=1 → استخدام Phase 1 (OLD)
- ATTENDANCE_USE_MODULAR=2 → استخدام Phase 2 (NEW) [تجريبي]
- في حال فشل التفعيل، يتم الرجوع تلقائيًا للنسخة الأصلية.
"""

import os
import sys
import importlib.util
from pathlib import Path
from flask import Blueprint


def _load_legacy_module(parent_dir: Path):
	spec = importlib.util.spec_from_file_location("_attendance_main", str(parent_dir / "_attendance_main.py"))
	attendance_module = importlib.util.module_from_spec(spec)
	sys.modules['_attendance_main'] = attendance_module
	spec.loader.exec_module(attendance_module)
	return attendance_module


def _load_legacy_blueprint(parent_dir: Path):
	attendance_module = _load_legacy_module(parent_dir)
	return attendance_module.attendance_bp


def _build_modular_blueprint_v1():
	"""Phase 1: Old modular structure (7 files)"""
	attendance_bp_modular = Blueprint('attendance', __name__)

	from .views import register_views_routes
	from .recording import register_recording_routes
	from .export import register_export_routes
	from .statistics import register_statistics_routes
	from .crud import register_crud_routes
	from .circles import register_circles_routes

	register_views_routes(attendance_bp_modular)
	register_recording_routes(attendance_bp_modular)
	register_export_routes(attendance_bp_modular)
	register_statistics_routes(attendance_bp_modular)
	register_crud_routes(attendance_bp_modular)
	register_circles_routes(attendance_bp_modular)

	# Backward-compatibility bridge: routes still referenced by templates.
	parent_dir = Path(__file__).parent.parent
	legacy_module = _load_legacy_module(parent_dir)
	attendance_bp_modular.add_url_rule(
		'/department/view',
		endpoint='department_attendance_view',
		view_func=legacy_module.department_attendance_view,
		methods=['GET']
	)
	attendance_bp_modular.add_url_rule(
		'/department/export-data',
		endpoint='export_department_data',
		view_func=legacy_module.export_department_data,
		methods=['GET']
	)
	attendance_bp_modular.add_url_rule(
		'/department/export-period',
		endpoint='export_department_period',
		view_func=legacy_module.export_department_period,
		methods=['GET']
	)

	return attendance_bp_modular


def _build_modular_blueprint_v2():
	"""Phase 2: New optimized structure (9 files, complete)"""
	from flask import Blueprint
	main_bp = Blueprint('attendance', __name__)
	
	# Import all view functions directly
	from .attendance_list import index, department_attendance_view
	from .attendance_record import record, department_attendance as dept_att_record, bulk_record, all_departments_attendance, department_bulk_attendance
	from .attendance_edit_delete import confirm_delete_attendance, delete_attendance, bulk_delete_attendance, edit_attendance_page, update_attendance_page
	from .attendance_export import export_excel, export_page, export_excel_dashboard, export_excel_department, export_department_data, export_department_period
	from .attendance_stats import stats, dashboard, employee_attendance, department_stats, department_details
	from .attendance_circles import departments_circles_overview, circle_accessed_details, export_circle_access_excel, mark_circle_employees_attendance
	from .attendance_api import get_department_employees
	
	# Register routes directly on main blueprint (avoid Flask nested blueprint routing issues)
	# List & View (2 routes)
	main_bp.add_url_rule('/', 'index', index, methods=['GET'])
	main_bp.add_url_rule('/department/view', 'department_attendance_view', department_attendance_view, methods=['GET'])
	
	# Recording (5 routes)
	main_bp.add_url_rule('/record', 'record', record, methods=['GET', 'POST'])
	main_bp.add_url_rule('/department', 'department_attendance', dept_att_record, methods=['GET', 'POST'])
	main_bp.add_url_rule('/bulk-record', 'bulk_record', bulk_record, methods=['GET', 'POST'])
	main_bp.add_url_rule('/all-departments', 'all_departments_attendance', all_departments_attendance, methods=['GET', 'POST'])
	main_bp.add_url_rule('/department/bulk', 'department_bulk_attendance', department_bulk_attendance, methods=['GET', 'POST'])
	
	# Edit & Delete (5 routes)
	main_bp.add_url_rule('/delete/<int:id>/confirm', 'confirm_delete_attendance', confirm_delete_attendance, methods=['GET'])
	main_bp.add_url_rule('/delete/<int:id>', 'delete_attendance', delete_attendance, methods=['POST'])
	main_bp.add_url_rule('/bulk_delete', 'bulk_delete_attendance', bulk_delete_attendance, methods=['POST'])
	main_bp.add_url_rule('/edit/<int:id>', 'edit_attendance_page', edit_attendance_page, methods=['GET'])
	main_bp.add_url_rule('/edit/<int:id>', 'update_attendance_page', update_attendance_page, methods=['POST'])
	
	# Export (6 routes)
	main_bp.add_url_rule('/export', 'export_page', export_page, methods=['GET'])
	main_bp.add_url_rule('/export/excel', 'export_excel', export_excel, methods=['GET', 'POST'])
	main_bp.add_url_rule('/export-excel-dashboard', 'export_excel_dashboard', export_excel_dashboard, methods=['GET'])
	main_bp.add_url_rule('/export-excel-department', 'export_excel_department', export_excel_department, methods=['GET'])
	main_bp.add_url_rule('/department/export-data', 'export_department_data', export_department_data, methods=['GET'])
	main_bp.add_url_rule('/department/export-period', 'export_department_period', export_department_period, methods=['GET'])
	
	# Statistics (5 routes)
	main_bp.add_url_rule('/stats', 'stats', stats, methods=['GET'])
	main_bp.add_url_rule('/dashboard', 'dashboard', dashboard, methods=['GET'])
	main_bp.add_url_rule('/employee/<int:employee_id>', 'employee_attendance', employee_attendance, methods=['GET'])
	main_bp.add_url_rule('/department-stats', 'department_stats', department_stats, methods=['GET'])
	main_bp.add_url_rule('/department-details', 'department_details', department_details, methods=['GET'])
	
	# Circles & GPS (4 routes)
	main_bp.add_url_rule('/departments-circles-overview', 'departments_circles_overview', departments_circles_overview, methods=['GET'])
	main_bp.add_url_rule('/circle-accessed-details/<int:department_id>/<circle_name>', 'circle_accessed_details', circle_accessed_details, methods=['GET'])
	main_bp.add_url_rule('/circle-accessed-details/<int:department_id>/<circle_name>/export-excel', 'export_circle_access_excel', export_circle_access_excel, methods=['GET'])
	main_bp.add_url_rule('/mark-circle-employees-attendance/<int:department_id>/<circle_name>', 'mark_circle_employees_attendance', mark_circle_employees_attendance, methods=['POST'])
	
	# API (1 route)
	main_bp.add_url_rule('/api/departments/<int:department_id>/employees', 'get_department_employees', get_department_employees, methods=['GET'])
	
	# Total: 28 routes (matching original _attendance_main.py)
	
	return main_bp


# Resolve routes directory once (without modifying sys.path)
parent_dir = Path(__file__).parent.parent

# Default behavior: legacy blueprint (safe)
attendance_bp = _load_legacy_blueprint(parent_dir)

# Optional modular activation
modular_mode = os.getenv('ATTENDANCE_USE_MODULAR', '0')

if modular_mode == '1':
	# Phase 1: Old modular structure
	try:
		attendance_bp = _build_modular_blueprint_v1()
		print("[OK] Attendance Module: Using Phase 1 (OLD modular structure)")
	except Exception as e:
		print(f"[ERR] Phase 1 failed: {e}, falling back to legacy")
		attendance_bp = _load_legacy_blueprint(parent_dir)

elif modular_mode == '2':
	# Phase 2: New optimized structure (EXPERIMENTAL)
	try:
		attendance_bp = _build_modular_blueprint_v2()
		print("[OK] Attendance Module: Using Phase 2 (NEW optimized structure) [EXPERIMENTAL]")
	except Exception as e:
		print(f"[ERR] Phase 2 failed: {e}, falling back to legacy")
		attendance_bp = _load_legacy_blueprint(parent_dir)


__all__ = ['attendance_bp']


