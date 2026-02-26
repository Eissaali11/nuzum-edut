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
	# Try multiple likely locations for the legacy module: top-level `routes/_attendance_main.py`
	# or the `routes/legacy/_attendance_main.py` path.
	paths_to_try = [parent_dir / "_attendance_main.py", parent_dir / "legacy" / "_attendance_main.py"]

	last_err = None
	for p in paths_to_try:
		if not p.exists():
			continue
		try:
			spec = importlib.util.spec_from_file_location("_attendance_main", str(p))
			attendance_module = importlib.util.module_from_spec(spec)
			sys.modules['_attendance_main'] = attendance_module
			spec.loader.exec_module(attendance_module)
			return attendance_module
		except Exception as e:
			last_err = e

	# If we reach here no candidate path loaded successfully.
	if last_err:
		raise last_err
	raise FileNotFoundError(f"Could not locate _attendance_main.py in {paths_to_try}")


def _load_legacy_blueprint(parent_dir: Path):
	attendance_module = _load_legacy_module(parent_dir)
	return attendance_module.attendance_bp


def _resolve_legacy_func(mod, names):
	"""Try alternative names on legacy module and return the first found callable.

	Raises AttributeError if none found.
	"""
	for name in names:
		if hasattr(mod, name):
			return getattr(mod, name)

	# Fallback: try to find a view function registered on the legacy blueprint
	bp = getattr(mod, 'attendance_bp', None)
	if bp is not None:
		# blueprint.view_functions keys can be 'attendance.endpoint' or 'endpoint'
		for name in names:
			for candidate in (f"{bp.name}.{name}", name):
				vf = bp.view_functions.get(candidate)
				if vf:
					return vf

	raise AttributeError(f"Legacy module missing any of: {names}")


def _build_modular_blueprint_v1():
	"""Phase 1: Old modular structure (7 files)"""
	attendance_bp_modular = Blueprint('attendance', __name__)

	# Prefer v1 registration helpers when present to avoid registering legacy
	# view functions that would force fallback behavior.
	try:
		from src.routes.attendance.v1.attendance_views import register_views_routes as register_views_routes
	except Exception:
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

	# Backward-compatibility bridge: prefer v1 handlers when available,
	# otherwise fall back to the legacy module functions.
	parent_dir = Path(__file__).parent.parent
	department_view_func = None
	export_data_func = None
	export_period_func = None

	# Try to use `routes.attendance.v1` implementations if present
	try:
		v1_mod = importlib.import_module('routes.attendance.v1.attendance_list')
		if hasattr(v1_mod, 'department_attendance_view'):
			department_view_func = getattr(v1_mod, 'department_attendance_view')
		if hasattr(v1_mod, 'export_department_data'):
			export_data_func = getattr(v1_mod, 'export_department_data')
		if hasattr(v1_mod, 'export_department_period'):
			export_period_func = getattr(v1_mod, 'export_department_period')
	except Exception:
		# ignore import errors and try legacy fallback below
		pass

	# Legacy fallback for any missing handlers
	legacy_module = None
	if department_view_func is None or export_data_func is None or export_period_func is None:
		legacy_module = _load_legacy_module(parent_dir)
		if department_view_func is None:
			department_view_func = _resolve_legacy_func(legacy_module, ['department_attendance_view', 'department_attendance', 'department_view'])
		if export_data_func is None:
			try:
				export_data_func = _resolve_legacy_func(legacy_module, ['export_department_data', 'export_department'])
			except AttributeError:
				def _missing_export(*a, **kw):
					from flask import abort
					abort(501, description='Export handler not implemented')
					export_data_func = _missing_export
		if export_period_func is None:
			try:
				export_period_func = _resolve_legacy_func(legacy_module, ['export_department_period', 'export_department_period'])
			except AttributeError:
				def _missing_export_period(*a, **kw):
					from flask import abort
					abort(501, description='Export period handler not implemented')
				export_period_func = _missing_export_period

	attendance_bp_modular.add_url_rule(
		'/department/view',
		endpoint='department_attendance_view',
		view_func=department_view_func,
		methods=['GET']
	)
	attendance_bp_modular.add_url_rule(
		'/department/export-data',
		endpoint='export_department_data',
		view_func=export_data_func,
		methods=['GET']
	)
	attendance_bp_modular.add_url_rule(
		'/department/export-period',
		endpoint='export_department_period',
		view_func=export_period_func,
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

# Lazy-load blueprint to avoid forcing legacy dependencies on v1-only code imports
_attendance_bp_cache = None
_initialization_attempted = False


def _initialize_attendance_bp():
	"""Initialize the attendance blueprint based on environment and fallback logic."""
	global _attendance_bp_cache, _initialization_attempted
	
	if _initialization_attempted:
		return _attendance_bp_cache
	
	_initialization_attempted = True
	
	# Optional modular activation (prefer modular if set)
	modular_mode = os.getenv('ATTENDANCE_USE_MODULAR', '0')
	
	if modular_mode == '1':
		# Phase 1: Old modular structure
		try:
			_attendance_bp_cache = _build_modular_blueprint_v1()
			print("[OK] Attendance Module: Using Phase 1 (OLD modular structure)")
			return _attendance_bp_cache
		except Exception as e:
			print(f"[ERR] Phase 1 failed: {e}, attempting legacy fallback")
	
	elif modular_mode == '2':
		# Phase 2: New optimized structure (EXPERIMENTAL)
		try:
			_attendance_bp_cache = _build_modular_blueprint_v2()
			print("[OK] Attendance Module: Using Phase 2 (NEW optimized structure) [EXPERIMENTAL]")
			return _attendance_bp_cache
		except Exception as e:
			print(f"[ERR] Phase 2 failed: {e}, attempting legacy fallback")
	
	# Default fallback: legacy blueprint
	try:
		_attendance_bp_cache = _load_legacy_blueprint(parent_dir)
		return _attendance_bp_cache
	except Exception as e:
		print(f"[ERR] Legacy blueprint load failed: {e}")
		# Create empty blueprint as last resort to avoid complete failure
		_attendance_bp_cache = Blueprint('attendance', __name__)
		return _attendance_bp_cache


def __getattr__(name):
	"""Lazy-load attendance_bp on first access to avoid forcing legacy deps."""
	if name == 'attendance_bp':
		return _initialize_attendance_bp()
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ['attendance_bp']


