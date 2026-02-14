"""
API v1 لبيانات المركبات: قائمة (GET /vehicles/data) وتفاصيل (GET /vehicles/<id>).
"""
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from modules.vehicles.application.vehicle_list_service import get_vehicle_list_payload
from modules.vehicles.application.vehicle_service import get_vehicle_detail_data

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _vehicle_to_dict(v):
    """تحويل نموذج Vehicle إلى قاموس قابل لـ JSON."""
    return {
        "id": v.id,
        "plate_number": v.plate_number,
        "make": v.make,
        "model": v.model,
        "year": v.year,
        "color": v.color,
        "status": v.status,
        "driver_name": v.driver_name,
        "project": v.project,
        "current_employee_id": getattr(v, "current_employee_id", None),
        "authorization_expiry_date": v.authorization_expiry_date.isoformat() if v.authorization_expiry_date else None,
        "registration_expiry_date": v.registration_expiry_date.isoformat() if v.registration_expiry_date else None,
        "inspection_expiry_date": v.inspection_expiry_date.isoformat() if v.inspection_expiry_date else None,
    }


def _payload_to_json_serializable(payload):
    """تحويل سياق القائمة إلى بنية قابلة لـ jsonify (بدون كائنات SQLAlchemy أو datetime غير قابلة للتسلسل)."""
    vehicles = [_vehicle_to_dict(v) for v in payload["vehicles"]]
    expired_auth = [_vehicle_to_dict(v) for v in payload["expired_authorization_vehicles"]]
    expired_insp = [_vehicle_to_dict(v) for v in payload["expired_inspection_vehicles"]]
    expiring = []
    for d in payload["expiring_documents"]:
        expiring.append({
            **d,
            "expiry_date": d["expiry_date"].isoformat() if isinstance(d.get("expiry_date"), date) else d.get("expiry_date"),
        })
    return {
        "vehicles": vehicles,
        "stats": payload["stats"],
        "status_filter": payload["status_filter"],
        "make_filter": payload["make_filter"],
        "search_plate": payload["search_plate"],
        "project_filter": payload["project_filter"],
        "makes": payload["makes"],
        "projects": payload["projects"],
        "statuses": payload["statuses"],
        "expiring_documents": expiring,
        "expired_authorization_vehicles": expired_auth,
        "expired_inspection_vehicles": expired_insp,
        "now": payload["now"].isoformat() if isinstance(payload.get("now"), datetime) else payload.get("now"),
        "today": payload["today"].isoformat() if isinstance(payload.get("today"), date) else payload.get("today"),
    }


@api_v1.route("/vehicles/data", methods=["GET"])
def vehicles_data():
    """
    GET /vehicles/data?status=...&make=...&search_plate=...&project=...&assigned_department_id=...
    يُرجع نفس بيانات سياق index كـ JSON (مركبات، إحصائيات، تصفيات، وثائق منتهية/قريبة الانتهاء).
    """
    assigned_department_id = request.args.get("assigned_department_id", type=int)
    payload = get_vehicle_list_payload(request.args, assigned_department_id=assigned_department_id)
    data = _payload_to_json_serializable(payload)
    return jsonify(data)


def _serialize_vehicle_detail(data):
    """تحويل سياق تفاصيل المركبة إلى بنية قابلة لـ JSON."""
    if data is None:
        return None
    vehicle = data.get("vehicle")
    out = {
        "vehicle": _vehicle_to_dict(vehicle) if vehicle else None,
        "rental": None,
        "workshop_records": [],
        "project_assignments": [],
        "handover_records": [],
        "periodic_inspections": [],
        "accidents": [],
        "external_authorizations": [],
        "external_safety_checks": [],
        "departments": [],
        "employees": [],
        "total_maintenance_cost": data.get("total_maintenance_cost"),
        "days_in_workshop": data.get("days_in_workshop"),
        "current_driver": data.get("current_driver"),
        "previous_drivers": data.get("previous_drivers"),
        "today": data["today"].isoformat() if isinstance(data.get("today"), date) else data.get("today"),
        "handovers": [],
        "attachments": [],
        "inspection_warnings": data.get("inspection_warnings", []),
    }
    r = data.get("rental")
    if r:
        out["rental"] = {
            "id": r.id,
            "vehicle_id": r.vehicle_id,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "monthly_cost": r.monthly_cost,
            "is_active": r.is_active,
        }
    for rec in data.get("workshop_records", []):
        out["workshop_records"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "entry_date": rec.entry_date.isoformat() if getattr(rec, "entry_date", None) else None,
            "exit_date": rec.exit_date.isoformat() if getattr(rec, "exit_date", None) else None,
            "reason": getattr(rec, "reason", None),
            "repair_status": getattr(rec, "repair_status", None),
            "cost": getattr(rec, "cost", None),
        })
    for rec in data.get("project_assignments", []):
        out["project_assignments"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "start_date": rec.start_date.isoformat() if getattr(rec, "start_date", None) else None,
            "end_date": rec.end_date.isoformat() if getattr(rec, "end_date", None) else None,
        })
    for rec in data.get("handover_records", []):
        out["handover_records"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "handover_type": getattr(rec, "handover_type", None),
            "handover_date": rec.handover_date.isoformat() if getattr(rec, "handover_date", None) else None,
            "person_name": getattr(rec, "person_name", None),
        })
    out["handovers"] = out["handover_records"]
    for rec in data.get("periodic_inspections", []):
        out["periodic_inspections"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "inspection_date": rec.inspection_date.isoformat() if getattr(rec, "inspection_date", None) else None,
        })
    for rec in data.get("accidents", []):
        out["accidents"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "accident_date": rec.accident_date.isoformat() if getattr(rec, "accident_date", None) else None,
        })
    for rec in data.get("external_authorizations", []):
        out["external_authorizations"].append({"id": rec.id, "vehicle_id": rec.vehicle_id})
    for rec in data.get("external_safety_checks", []):
        out["external_safety_checks"].append({
            "id": rec.id,
            "vehicle_id": rec.vehicle_id,
            "inspection_date": rec.inspection_date.isoformat() if getattr(rec, "inspection_date", None) else None,
        })
    for d in data.get("departments", []):
        out["departments"].append({"id": d.id, "name": d.name})
    for e in data.get("employees", []):
        out["employees"].append({"id": e.id, "name": e.name})
    for a in data.get("attachments", []):
        out["attachments"].append({"id": a.id, "workshop_record_id": getattr(a, "workshop_record_id", None)})
    if out.get("current_driver") and isinstance(out["current_driver"].get("date"), date):
        out["current_driver"] = {**out["current_driver"], "date": out["current_driver"]["date"].isoformat()}
    for i, pd in enumerate(out.get("previous_drivers") or []):
        if isinstance(pd.get("date"), date):
            out["previous_drivers"][i] = {**pd, "date": pd["date"].isoformat()}
    return out


@api_v1.route("/vehicles/<int:id>", methods=["GET"])
def vehicle_detail(id):
    """GET /api/v1/vehicles/<id> — تفاصيل سيارة واحدة (نفس بيانات صفحة view)."""
    data = get_vehicle_detail_data(id)
    if data is None:
        return jsonify({"error": "Vehicle not found"}), 404
    return jsonify(_serialize_vehicle_detail(data))


def register_vehicle_api(bp):
    """
    تسجيل مسارات مركبات API v1 على blueprint آخر (اختياري).
    المسار الرئيسي مُسجّل على api_v1 أعلاه.
    """
    bp.add_url_rule("/vehicles/data", view_func=vehicles_data, methods=["GET"])
    bp.add_url_rule("/vehicles/<int:id>", view_func=vehicle_detail, methods=["GET"])
