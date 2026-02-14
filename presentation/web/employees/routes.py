"""
مسارات الموظفين — Vertical Slice.
تعرض قائمة الموظفين من application/employees/services وتستخدم layout/base.html فقط.
لا يتجاوز 400 سطر.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from application.employees.services import list_employees_page_data

employees_bp = Blueprint("employees_web", __name__, url_prefix="/app/employees")


def _can_edit_employees():
    try:
        from utils.user_helpers import require_module_access
        from models import Module, Permission
        return current_user.is_authenticated and (
            getattr(current_user, "role", None) and current_user.role.name == "ADMIN"
            or hasattr(current_user, "has_permission") and current_user.has_permission(Module.EMPLOYEES, Permission.EDIT)
        )
    except Exception:
        return False


def _can_delete_employees():
    try:
        from models import Module, Permission
        return current_user.is_authenticated and (
            getattr(current_user, "role", None) and current_user.role.name == "ADMIN"
            or hasattr(current_user, "has_permission") and current_user.has_permission(Module.EMPLOYEES, Permission.DELETE)
        )
    except Exception:
        return False


@employees_bp.route("/")
@employees_bp.route("/list")
@login_required
def list_page():
    """قائمة الموظفين — مصدر البيانات: application/employees/services."""
    assigned_id = getattr(current_user, "assigned_department_id", None) or None
    data = list_employees_page_data(
        department_filter=request.args.get("department", ""),
        status_filter=request.args.get("status", ""),
        multi_department_filter=request.args.get("multi_department", ""),
        no_department_filter=request.args.get("no_department", ""),
        duplicate_names_filter=request.args.get("duplicate_names", ""),
        assigned_department_id=assigned_id,
    )
    return render_template(
        "employees/list.html",
        employees=data["employees"],
        departments=data["departments"],
        current_department=data["current_department"],
        current_status=data["current_status"],
        current_multi_department=data["current_multi_department"],
        current_no_department=data["current_no_department"],
        current_duplicate_names=data["current_duplicate_names"],
        multi_dept_count=data["multi_dept_count"],
        single_dept_count=data["single_dept_count"],
        no_dept_count=data["no_dept_count"],
        duplicate_names_count=data["duplicate_names_count"],
        duplicate_names_set=data["duplicate_names_set"],
        can_edit=_can_edit_employees(),
        can_delete=_can_delete_employees(),
    )
