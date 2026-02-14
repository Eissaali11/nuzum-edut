"""
خدمة تفاصيل المركبة — استخراج منطق بيانات صفحة view(id).
تُستخدم من: مسار vehicles.view (عرض تفاصيل سيارة).
تعمل بشكل مستقل: تحتوي على كل الاستعلامات والمنطق المطلوب لملء قالب vehicles/view.html.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from core.extensions import db
from modules.vehicles.domain.models import (
    Vehicle,
    VehicleHandover,
    VehicleProject,
    VehicleRental,
    VehicleWorkshop,
    VehicleWorkshopImage,
)
from domain.employees.models import Department, Employee
from models import (
    ExternalAuthorization,
    OperationRequest,
    VehicleAccident,
    VehicleExternalSafetyCheck,
    VehiclePeriodicInspection,
)
from utils.vehicle_route_helpers import format_date_arabic


def get_vehicle_detail_data(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """
    يجمع كل البيانات المطلوبة لصفحة تفاصيل المركبة (view).

    يشمل: المركبة، الإيجار، سجلات الورشة، المشاريع، التسليم/الاستلام، الفحوصات الدورية،
    الحوادث، التفويضات الخارجية، الفحوصات الخارجية، المرفقات، السائق الحالي والسابقين،
    وتنبيهات الفحص. يُرجع None إذا لم تُوجَد المركبة.

    Data Contract: نفس المفاتيح التي يتوقعها قالب vehicles/view.html.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    id_ = vehicle_id

    # سجلات التسليم/الاستلام (المعتمدة أو غير المرتبطة بعملية)
    approved_ids = (
        db.session.query(OperationRequest.related_record_id)
        .filter_by(operation_type="handover", status="approved", vehicle_id=id_)
        .subquery()
    )
    all_ids = (
        db.session.query(OperationRequest.related_record_id)
        .filter_by(operation_type="handover", vehicle_id=id_)
        .subquery()
    )
    handover_records = (
        VehicleHandover.query.filter(
            VehicleHandover.vehicle_id == id_,
            or_(
                VehicleHandover.id.in_(approved_ids),
                ~VehicleHandover.id.in_(all_ids),
            ),
        )
        .order_by(VehicleHandover.created_at.desc())
        .all()
    )

    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=id_)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    rental = VehicleRental.query.filter_by(vehicle_id=id_, is_active=True).first()
    project_assignments = (
        VehicleProject.query.filter_by(vehicle_id=id_)
        .order_by(VehicleProject.start_date.desc())
        .all()
    )
    periodic_inspections = (
        VehiclePeriodicInspection.query.filter_by(vehicle_id=id_)
        .order_by(VehiclePeriodicInspection.inspection_date.desc())
        .all()
    )
    accidents = (
        VehicleAccident.query.filter_by(vehicle_id=id_, review_status="approved")
        .order_by(VehicleAccident.accident_date.desc())
        .all()
    )
    external_authorizations = (
        ExternalAuthorization.query.filter_by(vehicle_id=id_)
        .order_by(ExternalAuthorization.created_at.desc())
        .all()
    )
    external_safety_checks = (
        VehicleExternalSafetyCheck.query.filter_by(vehicle_id=id_)
        .order_by(VehicleExternalSafetyCheck.inspection_date.desc())
        .all()
    )
    departments = Department.query.all()
    employees = Employee.query.all()

    total_maintenance_cost = sum((r.cost or 0) for r in workshop_records)
    days_in_workshop = sum(
        (r.exit_date - r.entry_date).days for r in workshop_records if r.exit_date
    )
    today = datetime.now().date()

    current_driver = None
    if vehicle.driver_name:
        latest_delivery = next(
            (
                r
                for r in handover_records
                if r.handover_type == "delivery" and r.person_name == vehicle.driver_name
            ),
            None,
        )
        if latest_delivery:
            current_driver = {
                "name": latest_delivery.person_name,
                "date": latest_delivery.handover_date,
                "formatted_date": format_date_arabic(latest_delivery.handover_date),
                "handover_id": latest_delivery.id,
                "mobile": latest_delivery.driver_phone_number,
                "employee_id": latest_delivery.employee_id,
                "handover_type_ar": "تسليم" if latest_delivery.handover_type == "delivery" else "استلام",
            }

    all_deliveries = [r for r in handover_records if r.handover_type == "delivery"]
    previous_drivers: List[Dict[str, Any]] = [
        {
            "name": r.person_name,
            "date": r.handover_date,
            "formatted_date": format_date_arabic(r.handover_date),
            "handover_id": r.id,
            "mobile": r.driver_phone_number,
        }
        for r in all_deliveries[1:]
    ]

    for record in (
        workshop_records
        + project_assignments
        + handover_records
        + periodic_inspections
        + accidents
        + external_safety_checks
    ):
        for attr in [
            "entry_date",
            "exit_date",
            "start_date",
            "end_date",
            "handover_date",
            "inspection_date",
            "expiry_date",
            "check_date",
            "accident_date",
        ]:
            if (
                hasattr(record, attr)
                and getattr(record, attr)
                and isinstance(getattr(record, attr), (datetime, date))
            ):
                setattr(
                    record,
                    f"formatted_{attr}",
                    format_date_arabic(getattr(record, attr)),
                )

    if rental and rental.start_date:
        rental.formatted_start_date = format_date_arabic(rental.start_date)
        if rental.end_date:
            rental.formatted_end_date = format_date_arabic(rental.end_date)

    attachments = (
        VehicleWorkshopImage.query.join(VehicleWorkshop)
        .filter(VehicleWorkshop.vehicle_id == id_)
        .all()
    )

    inspection_warnings: List[Dict[str, Any]] = []

    return {
        "vehicle": vehicle,
        "rental": rental,
        "workshop_records": workshop_records,
        "project_assignments": project_assignments,
        "handover_records": handover_records,
        "periodic_inspections": periodic_inspections,
        "accidents": accidents,
        "external_authorizations": external_authorizations,
        "external_safety_checks": external_safety_checks,
        "departments": departments,
        "employees": employees,
        "total_maintenance_cost": total_maintenance_cost,
        "days_in_workshop": days_in_workshop,
        "current_driver": current_driver,
        "previous_drivers": previous_drivers,
        "today": today,
        "handovers": handover_records,
        "attachments": attachments,
        "inspection_warnings": inspection_warnings,
    }
