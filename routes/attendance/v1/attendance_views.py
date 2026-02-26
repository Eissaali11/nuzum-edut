"""Thin adapter that exposes a `register_views_routes` compatible API
for the new `routes/attendance/v1` scaffold.

This adapter prefers local v1 implementations where provided. For routes
not yet migrated it falls back to the legacy `_attendance_main.py` but logs
when the legacy proxy is used.
"""

from datetime import date as _date, datetime as _datetime, timedelta as _timedelta
import time as _time
from flask import request, render_template, make_response
from core.extensions import db
from sqlalchemy import func, case


def dashboard():
    """Controller: delegate dashboard assembly to AttendanceService.

    Keeps the controller thin and returns a rendered response with the
    modular handler header preserved.
    """
    logger = __import__('logging').getLogger(__name__)
    project_name = request.args.get('project', None)

    try:
        from .services.attendance_service import AttendanceService
        data = AttendanceService.get_processed_dashboard_data(project_name=project_name)

        rendered = render_template('attendance/dashboard_new.html', **data)
        resp = make_response(rendered)
        resp.headers['X-Attendance-Handler'] = 'MODULAR_v1'
        return resp
    except Exception:
        logger.exception('Error rendering dashboard via AttendanceService')
        from flask import abort
        abort(500, description='Failed to render dashboard')


def department_attendance_view():
    """Modular replacement for the legacy department attendance view.

    Accepts `department_id` and optional `date` query params and renders
    a lightweight department attendance page using the new services.
    """
    logger = __import__('logging').getLogger(__name__)
    try:
        # Parse inputs
        dept_id = request.args.get('department_id') or request.args.get('id')
        date_str = request.args.get('date')
        if date_str:
            try:
                from utils.date_converter import parse_date
                att_date = parse_date(date_str)
            except Exception:
                att_date = _datetime.now().date()
        else:
            att_date = _datetime.now().date()

        # Resolve department and attendance rows via AttendanceEngine when available
        attendances = []
        department = None
        try:
            from services.attendance_engine import AttendanceEngine
            if dept_id:
                department = db.session.query(__import__('modules.employees.domain.models', fromlist=['Department']).Department).get(int(dept_id))
            attendances = AttendanceEngine.get_unified_attendance_list(att_date=att_date, department_id=int(dept_id) if dept_id else None)
        except Exception:
            # Fallback direct query using domain models
            try:
                from modules.employees.domain.models import Attendance, Department as Dept
                if dept_id:
                    department = db.session.query(Dept).get(int(dept_id))
                    attendances = db.session.query(Attendance).filter(Attendance.date == att_date, Attendance.department_id == int(dept_id)).all()
                else:
                    attendances = db.session.query(Attendance).filter(Attendance.date == att_date).all()
            except Exception:
                logger.exception('Failed fetching department attendance')

        # Render minimal v1 template (keeps backward-compatible context keys)
        rendered = render_template('attendance/v1/department_view.html',
                       attendances=attendances,
                       department=department,
                       date=att_date)
        resp = make_response(rendered)
        resp.headers['X-Attendance-Handler'] = 'MODULAR_v1'
        return resp

    except Exception:
        logger.exception('Error in department_attendance_view')
        from flask import abort
        abort(500, description='Failed to render department attendance view')


def index():
    """Thin index entry that returns the dashboard content internally.

    This keeps the URL as `/attendance/` while serving the dashboard view
    (internal call rather than redirect), matching the user's preference.
    """
    return dashboard()


def register_views_routes(attendance_bp):
    """Register a small, safe batch of view routes by wiring the legacy
    functions from `routes.legacy._attendance_main` to the new blueprint.

    This avoids duplicating logic and keeps behavior identical while we
    progressively migrate handlers into the new modular layout.
    """
    import importlib.util
    from pathlib import Path
    import sys

    logger = __import__('logging').getLogger(__name__)

    parent_dir = Path(__file__).resolve().parent.parent

    # Helper to load legacy module on demand
    def _load_legacy():
        spec = importlib.util.spec_from_file_location("_attendance_main", str(parent_dir / "legacy" / "_attendance_main.py"))
        legacy_mod = importlib.util.module_from_spec(spec)
        sys.modules['_attendance_main'] = legacy_mod
        spec.loader.exec_module(legacy_mod)
        return legacy_mod

    # Mapping of routes we want to expose: (url, endpoint, new_name, legacy_name, methods)
    routes = [
        ('/', 'index', 'index', 'index', ['GET']),
        ('/department', 'department_attendance', 'department_attendance', 'department_attendance', ['GET', 'POST']),
        ('/department/view', 'department_attendance_view', 'department_attendance_view', 'department_attendance_view', ['GET']),
        ('/api/departments/<int:department_id>/employees', 'get_department_employees', 'get_department_employees', 'get_department_employees', ['GET']),
        ('/dashboard', 'dashboard', 'dashboard', 'dashboard', ['GET']),
    ]

    for url, endpoint, new_name, legacy_name, methods in routes:
        view_func = None

        # Try new modular location first
        try:
            mod = importlib.import_module('routes.attendance.v1.' + 'attendance_list')
            if hasattr(mod, new_name):
                view_func = getattr(mod, new_name)
        except Exception:
            # ignore import failures of new modules
            pass

        # If not found, fall back to legacy implementation
        if view_func is None:
            try:
                legacy = _load_legacy()
                if hasattr(legacy, legacy_name):
                    view_func = getattr(legacy, legacy_name)
                    logger.warning('Using legacy view for %s -> %s', endpoint, legacy_name)
            except Exception as e:
                logger.exception('Failed loading legacy attendance module: %s', e)

        # Final safety: if still missing, register a proxy that raises a clear error
        if view_func is None:
            def _missing(*a, **kw):
                from flask import abort
                logger.error('Missing attendance view function for endpoint %s', endpoint)
                abort(500, description=f'Missing view: {endpoint}')

            view_func = _missing

        attendance_bp.add_url_rule(url, endpoint, view_func, methods=methods)

    return None
