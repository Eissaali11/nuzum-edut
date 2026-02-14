"""
خدمات طبقة التطبيق للمركبات — قائمة، فلترة، تسليم/استلام (قراءة + إنشاء).
يُستدعى من طبقة العرض فقط. لا يتجاوز 400 سطر.
"""
from typing import Optional, List, Any, Dict

from datetime import datetime, timedelta, date
from sqlalchemy import or_

from core.extensions import db
from domain.vehicles.models import Vehicle, VehicleHandover
from domain.employees.models import Department, Employee, employee_departments


# حالات المركبة التي تمنع تسليم/استلام (للخدمة النقية فقط — الرسائل والتحويلات يبنيها المسار)
HANDOVER_UNSUITABLE_STATUSES = ("in_workshop", "accident", "out_of_service")

VEHICLE_STATUS_CHOICES = [
    "available",
    "rented",
    "in_project",
    "in_workshop",
    "accident",
    "out_of_service",
]


def list_vehicles_service(
    status_filter: str = "",
    make_filter: str = "",
    project_filter: str = "",
    search_plate: str = "",
    assigned_department_id: Optional[int] = None,
) -> dict:
    """
    يجلب بيانات صفحة قائمة المركبات: المركبات المفلترة، قوائم التصفية، والإحصائيات.
    assigned_department_id: إن وُجد، يُقيّد المركبات بتلك التي لها تسليم لموظف في هذا القسم.
    """
    query = Vehicle.query.options(db.joinedload(Vehicle.department))

    if assigned_department_id:
        dept_employee_ids = (
            db.session.query(Employee.id)
            .join(employee_departments)
            .join(Department)
            .filter(Department.id == assigned_department_id)
            .all()
        )
        dept_employee_ids = [r[0] for r in dept_employee_ids]
        if dept_employee_ids:
            vehicle_ids_with_handovers = (
                db.session.query(VehicleHandover.vehicle_id)
                .filter(
                    VehicleHandover.handover_type == "delivery",
                    VehicleHandover.employee_id.in_(dept_employee_ids),
                )
                .distinct()
                .all()
            )
            vehicle_ids = [r[0] for r in vehicle_ids_with_handovers]
            if vehicle_ids:
                query = query.filter(Vehicle.id.in_(vehicle_ids))
            else:
                query = query.filter(Vehicle.id == -1)
        else:
            query = query.filter(Vehicle.id == -1)

    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if make_filter:
        query = query.filter(Vehicle.make == make_filter)
    if project_filter:
        query = query.filter(Vehicle.project == project_filter)
    if search_plate:
        query = query.filter(Vehicle.plate_number.contains(search_plate))

    vehicles: List[Any] = query.order_by(Vehicle.status, Vehicle.plate_number).all()

    makes = [r[0] for r in db.session.query(Vehicle.make).distinct().all()]
    projects = [
        r[0]
        for r in db.session.query(Vehicle.project)
        .filter(Vehicle.project.isnot(None))
        .distinct()
        .all()
    ]
    departments = Department.query.all() if not assigned_department_id else Department.query.filter_by(id=assigned_department_id).all()

    stats = {
        "total": Vehicle.query.count(),
        "available": Vehicle.query.filter_by(status="available").count(),
        "rented": Vehicle.query.filter_by(status="rented").count(),
        "in_project": Vehicle.query.filter_by(status="in_project").count(),
        "in_workshop": Vehicle.query.filter_by(status="in_workshop").count(),
        "accident": Vehicle.query.filter_by(status="accident").count(),
        "out_of_service": Vehicle.query.filter_by(status="out_of_service").count(),
    }

    today = datetime.now().date()
    thirty_days_later = today + timedelta(days=30)
    expiring_documents: List[dict] = []
    for v in vehicles:
        if v.authorization_expiry_date and today <= v.authorization_expiry_date <= thirty_days_later:
            expiring_documents.append(
                {
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "document_type": "authorization",
                    "document_name": "تفويض المركبة",
                    "expiry_date": v.authorization_expiry_date,
                    "days_remaining": (v.authorization_expiry_date - today).days,
                }
            )
        if v.registration_expiry_date and today <= v.registration_expiry_date <= thirty_days_later:
            expiring_documents.append(
                {
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "document_type": "registration",
                    "document_name": "استمارة السيارة",
                    "expiry_date": v.registration_expiry_date,
                    "days_remaining": (v.registration_expiry_date - today).days,
                }
            )
        if v.inspection_expiry_date and today <= v.inspection_expiry_date <= thirty_days_later:
            expiring_documents.append(
                {
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "document_type": "inspection",
                    "document_name": "الفحص الدوري",
                    "expiry_date": v.inspection_expiry_date,
                    "days_remaining": (v.inspection_expiry_date - today).days,
                }
            )
    expiring_documents.sort(key=lambda x: x["days_remaining"])

    expired_authorization_vehicles = Vehicle.query.filter(
        Vehicle.authorization_expiry_date.isnot(None),
        Vehicle.authorization_expiry_date < today,
    ).all()
    expired_inspection_vehicles = Vehicle.query.filter(
        Vehicle.inspection_expiry_date.isnot(None),
        Vehicle.inspection_expiry_date < today,
    ).all()

    return {
        "vehicles": vehicles,
        "makes": makes,
        "projects": projects,
        "departments": departments,
        "stats": stats,
        "statuses": VEHICLE_STATUS_CHOICES,
        "current_status": status_filter,
        "current_make": make_filter,
        "current_project": project_filter,
        "current_search_plate": search_plate,
        "expiring_documents": expiring_documents,
        "expired_authorization_vehicles": expired_authorization_vehicles,
        "expired_inspection_vehicles": expired_inspection_vehicles,
        "today": today,
    }


def get_vehicle_handover_context(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """
    سياق قراءة فقط لصفحة إنشاء تسليم/استلام: أحدث حالة وأهلية المركبة.
    لا يعتمد على request أو flash. يُرجع None إذا لم تُوجَد المركبة.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    from application.operations.services import get_handover_approval_state
    state = get_handover_approval_state(vehicle_id)
    approved_ids = state["approved_ids"]
    all_request_ids = state["all_request_record_ids"]
    base_official = VehicleHandover.query.filter(VehicleHandover.vehicle_id == vehicle_id)
    if approved_ids or all_request_ids:
        base_official = base_official.filter(
            or_(
                VehicleHandover.id.in_(approved_ids),
                ~VehicleHandover.id.in_(all_request_ids),
            )
        )
    latest_delivery = (
        base_official.filter(
            VehicleHandover.handover_type.in_(["delivery", "تسليم"])
        )
        .order_by(VehicleHandover.created_at.desc())
        .first()
    )
    latest_return = (
        base_official.filter(
            VehicleHandover.handover_type.in_(["return", "استلام", "receive"])
        )
        .order_by(VehicleHandover.created_at.desc())
        .first()
    )
    is_currently_handed_out = bool(
        latest_delivery
        and (not latest_return or latest_delivery.created_at > latest_return.created_at)
    )
    if is_currently_handed_out:
        force_mode = "return"
        current_driver_info = latest_delivery
        info_message = (
            f"تنبيه: المركبة مسلمة حالياً لـِ '{latest_delivery.person_name}'. "
            "النموذج معد لعملية الاستلام فقط."
        )
    else:
        force_mode = "delivery"
        current_driver_info = None
        info_message = "المركبة متاحة حالياً. النموذج معد لعملية التسليم لسائق جديد."
    eligible = vehicle.status not in HANDOVER_UNSUITABLE_STATUSES
    eligibility_message = None
    eligibility_redirect_route = None
    eligibility_redirect_anchor = None
    if not eligible:
        if vehicle.status == "in_workshop":
            eligibility_message = (
                "لا يمكن تسليم أو استلام المركبة لأنها حالياً في الورشة. يجب إخراجها أولاً."
            )
            eligibility_redirect_route = "vehicles.view"
            eligibility_redirect_anchor = "workshop-records-section"
        elif vehicle.status == "accident":
            eligibility_message = (
                "لا يمكن تسليم أو استلام المركبة لأنه مسجل عليها حادث نشط. يجب إغلاق ملف الحادث أولاً."
            )
            eligibility_redirect_route = "vehicles.view"
            eligibility_redirect_anchor = "accidents-section"
        elif vehicle.status == "out_of_service":
            eligibility_message = (
                'لا يمكن تسليم أو استلام المركبة لأنها "خارج الخدمة". يرجى تعديل حالة المركبة أولاً.'
            )
            eligibility_redirect_route = "vehicles.edit"
            eligibility_redirect_anchor = None
    return {
        "vehicle": vehicle,
        "eligible": eligible,
        "eligibility_message": eligibility_message,
        "eligibility_redirect_route": eligibility_redirect_route,
        "eligibility_redirect_anchor": eligibility_redirect_anchor,
        "force_mode": force_mode,
        "info_message": info_message,
        "current_driver_info": current_driver_info,
        "latest_delivery": latest_delivery,
        "latest_return": latest_return,
    }


def create_vehicle_handover_action(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files_data: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    """
    إنشاء سجل تسليم/استلام واحد مع ربط مسارات التواقيع والرسوم.
    لا ينشئ OperationRequest — المسار يربطها بعد الحصول على handover.id.
    يُرجع {"success": True, "handover": handover} أو {"success": False, "error": str}.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return {"success": False, "error": "المركبة غير موجودة"}
    handover_date_str = form_data.get("handover_date") or ""
    handover_time_str = form_data.get("handover_time") or ""
    try:
        handover_date = (
            datetime.strptime(handover_date_str, "%Y-%m-%d").date()
            if handover_date_str
            else date.today()
        )
    except ValueError:
        handover_date = date.today()
    handover_time = None
    if handover_time_str:
        try:
            handover_time = datetime.strptime(handover_time_str, "%H:%M").time()
        except ValueError:
            pass
    employee_id_str = form_data.get("employee_id") or ""
    person_name_from_form = (form_data.get("person_name") or "").strip()
    driver = None
    if employee_id_str and str(employee_id_str).isdigit():
        driver = Employee.query.get(int(employee_id_str))
    if not driver and person_name_from_form:
        driver = (
            Employee.query.filter(Employee.name.ilike(f"%{person_name_from_form}%"))
            .first()
        )
    supervisor_employee_id_str = form_data.get("supervisor_employee_id") or ""
    supervisor_name_from_form = (form_data.get("supervisor_name") or "").strip()
    supervisor = None
    if supervisor_employee_id_str and str(supervisor_employee_id_str).isdigit():
        supervisor = Employee.query.get(int(supervisor_employee_id_str))
    mileage = int(form_data.get("mileage") or 0)
    fuel_level = form_data.get("fuel_level") or ""
    handover_type = form_data.get("handover_type") or "delivery"
    project_name = form_data.get("project_name") or None
    city = form_data.get("city") or None
    reason_for_change = form_data.get("reason_for_change") or None
    vehicle_status_summary = form_data.get("vehicle_status_summary") or None
    notes = form_data.get("notes")
    reason_for_authorization = form_data.get("reason_for_authorization") or None
    authorization_details = form_data.get("authorization_details") or None
    movement_officer_name = form_data.get("movement_officer_name") or None
    form_link = form_data.get("form_link") or None
    form_link_2 = form_data.get("form_link_2") or None
    custom_company_name = (form_data.get("custom_company_name") or "").strip() or None
    saved_diagram_path = files_data.get("damage_diagram_path")
    saved_supervisor_sig_path = files_data.get("supervisor_signature_path")
    saved_driver_sig_path = files_data.get("driver_signature_path")
    movement_officer_signature_path = files_data.get("movement_officer_signature_path")
    saved_custom_logo_path = files_data.get("custom_logo_path")
    try:
        handover = VehicleHandover(
            vehicle_id=vehicle_id,
            handover_type=handover_type,
            handover_date=handover_date,
            handover_time=handover_time,
            mileage=mileage,
            project_name=project_name,
            city=city,
            vehicle_car_type=f"{vehicle.make} {vehicle.model}",
            vehicle_plate_number=vehicle.plate_number,
            vehicle_model_year=str(vehicle.year),
            employee_id=driver.id if driver else None,
            person_name=driver.name if driver else person_name_from_form,
            driver_company_id=driver.employee_id if driver else None,
            driver_phone_number=getattr(driver, "mobilePersonal", None) if driver else None,
            driver_work_phone=driver.mobile if driver else None,
            driver_residency_number=driver.national_id if driver else None,
            driver_contract_status=getattr(driver, "contract_status", None) if driver else None,
            driver_license_status=getattr(driver, "license_status", None) if driver else None,
            driver_signature_path=saved_driver_sig_path,
            supervisor_employee_id=supervisor.id if supervisor else None,
            supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
            supervisor_company_id=supervisor.employee_id if supervisor else None,
            supervisor_phone_number=supervisor.mobile if supervisor else None,
            supervisor_residency_number=supervisor.national_id if supervisor else None,
            supervisor_contract_status=getattr(supervisor, "contract_status", None) if supervisor else None,
            supervisor_license_status=getattr(supervisor, "license_status", None) if supervisor else None,
            supervisor_signature_path=saved_supervisor_sig_path,
            reason_for_change=reason_for_change,
            vehicle_status_summary=vehicle_status_summary,
            notes=notes,
            reason_for_authorization=reason_for_authorization,
            authorization_details=authorization_details,
            fuel_level=fuel_level,
            has_spare_tire=form_data.get("has_spare_tire", True),
            has_fire_extinguisher=form_data.get("has_fire_extinguisher", True),
            has_first_aid_kit=form_data.get("has_first_aid_kit", True),
            has_warning_triangle=form_data.get("has_warning_triangle", True),
            has_tools=form_data.get("has_tools", True),
            has_oil_leaks=form_data.get("has_oil_leaks", False),
            has_gear_issue=form_data.get("has_gear_issue", False),
            has_clutch_issue=form_data.get("has_clutch_issue", False),
            has_engine_issue=form_data.get("has_engine_issue", False),
            has_windows_issue=form_data.get("has_windows_issue", False),
            has_tires_issue=form_data.get("has_tires_issue", False),
            has_body_issue=form_data.get("has_body_issue", False),
            has_electricity_issue=form_data.get("has_electricity_issue", False),
            has_lights_issue=form_data.get("has_lights_issue", False),
            has_ac_issue=form_data.get("has_ac_issue", False),
            movement_officer_name=movement_officer_name,
            movement_officer_signature_path=movement_officer_signature_path,
            damage_diagram_path=saved_diagram_path,
            form_link=form_link,
            form_link_2=form_link_2,
            custom_company_name=custom_company_name,
            custom_logo_path=saved_custom_logo_path,
        )
        db.session.add(handover)
        db.session.commit()
        return {"success": True, "handover": handover}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
