"""
مسارات المركبات — Vertical Slice.
قائمة المركبات من application/vehicles/services. لا يتجاوز 400 سطر.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from application.vehicles.services import list_vehicles_service

vehicles_web_bp = Blueprint("vehicles_web", __name__, url_prefix="/app/vehicles")


@vehicles_web_bp.route("/")
@vehicles_web_bp.route("/list")
@login_required
def list_page():
    """قائمة المركبات — مصدر البيانات: application/vehicles/services."""
    assigned_id = getattr(current_user, "assigned_department_id", None) or None
    data = list_vehicles_service(
        status_filter=request.args.get("status", ""),
        make_filter=request.args.get("make", ""),
        project_filter=request.args.get("project", ""),
        search_plate=request.args.get("search_plate", ""),
        assigned_department_id=assigned_id,
    )
    return render_template(
        "vehicles/list.html",
        vehicles=data["vehicles"],
        makes=data["makes"],
        projects=data["projects"],
        departments=data["departments"],
        stats=data["stats"],
        statuses=data["statuses"],
        current_status=data["current_status"],
        current_make=data["current_make"],
        current_project=data["current_project"],
        current_search_plate=data["current_search_plate"],
        expiring_documents=data["expiring_documents"],
        expired_authorization_vehicles=data["expired_authorization_vehicles"],
        expired_inspection_vehicles=data["expired_inspection_vehicles"],
        today=data["today"],
    )
