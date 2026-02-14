"""
خدمات طبقة التطبيق للمركبات — استعلامات قاعدة البيانات والمنطق الصرف.
مستخرج من routes/vehicles.py لاستخدامه من طبقة العرض (vehicle_routes).
يُستورد منه: get_all_vehicles (سياق القائمة)، update_vehicle_driver، calculate_maintenance_costs، إلخ.
"""
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import extract, func, or_
from sqlalchemy.orm import joinedload

from core.extensions import db
from modules.vehicles.domain.models import (
    Vehicle,
    VehicleHandover,
    VehicleProject,
    VehicleRental,
    VehicleWorkshop,
    VehicleWorkshopImage,
)
from domain.employees.models import Department, Employee, employee_departments
from models import (
    ExternalAuthorization,
    OperationRequest,
    VehicleAccident,
    VehicleExternalSafetyCheck,
    VehiclePeriodicInspection,
)
from utils.vehicle_route_helpers import format_date_arabic

# قائمة بأهم حالات السيارة للاختيار منها في النماذج
VEHICLE_STATUS_CHOICES = [
    "available",
    "rented",
    "in_project",
    "in_workshop",
    "accident",
    "out_of_service",
]

WORKSHOP_REASON_CHOICES = ["maintenance", "breakdown", "accident"]
REPAIR_STATUS_CHOICES = ["in_progress", "completed", "pending_approval"]
HANDOVER_TYPE_CHOICES = ["delivery", "return"]
INSPECTION_TYPE_CHOICES = ["technical", "periodic", "safety"]
INSPECTION_STATUS_CHOICES = ["valid", "expired", "expiring_soon"]
SAFETY_CHECK_TYPE_CHOICES = ["daily", "weekly", "monthly"]
SAFETY_CHECK_STATUS_CHOICES = ["completed", "in_progress", "needs_review"]


def update_vehicle_driver(vehicle_id: int) -> None:
    """تحديث اسم السائق في جدول السيارات بناءً على آخر سجل تسليم من نوع delivery."""
    try:
        delivery_records = (
            VehicleHandover.query.filter_by(
                vehicle_id=vehicle_id,
                handover_type="delivery",
            )
            .order_by(VehicleHandover.handover_date.desc())
            .all()
        )
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return
        if delivery_records:
            latest = delivery_records[0]
            driver_name = None
            if latest.employee_id:
                emp = Employee.query.get(latest.employee_id)
                if emp:
                    driver_name = emp.name
            if not driver_name and latest.person_name:
                driver_name = latest.person_name
            vehicle.driver_name = driver_name
        else:
            vehicle.driver_name = None
        db.session.commit()
    except Exception:
        db.session.rollback()


def update_all_vehicle_drivers() -> int:
    """تحديث أسماء جميع السائقين في جدول السيارات."""
    vehicles = Vehicle.query.all()
    for v in vehicles:
        update_vehicle_driver(v.id)
    return len(vehicles)


def get_vehicle_current_employee_id(vehicle_id: int) -> Optional[int]:
    """الحصول على معرف الموظف الحالي للسيارة."""
    latest = (
        VehicleHandover.query.filter_by(vehicle_id=vehicle_id)
        .filter(
            VehicleHandover.handover_type.in_(["delivery", "تسليم", "handover"])
        )
        .order_by(VehicleHandover.handover_date.desc())
        .first()
    )
    return latest.employee_id if (latest and latest.employee_id) else None


def calculate_rental_adjustment(vehicle_id: int, year: int, month: int) -> float:
    """حساب الخصم على إيجار السيارة بناءً على أيام وجودها في الورشة."""
    rental = VehicleRental.query.filter_by(
        vehicle_id=vehicle_id, is_active=True
    ).first()
    if not rental:
        return 0.0
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .filter(
            extract("year", VehicleWorkshop.entry_date) == year,
            extract("month", VehicleWorkshop.entry_date) == month,
        )
        .all()
    )
    total_days = 0
    for r in workshop_records:
        if r.exit_date:
            total_days += (r.exit_date - r.entry_date).days
        else:
            last_day = 30
            total_days += last_day - r.entry_date.day
    daily_rent = rental.monthly_cost / 30
    return daily_rent * total_days


def get_filtered_vehicle_documents(
    document_status: str = "expired",
    document_type: str = "all",
    plate_number: str = "",
    vehicle_make: str = "",
) -> Tuple[List[Vehicle], List[Vehicle], List[Vehicle], List[Vehicle]]:
    """جلب وثائق المركبات مع الفلاتر. يُرجع (expired_registration, expired_inspection, expired_authorization, expired_all)."""
    today = datetime.now().date()
    base = Vehicle.query
    if plate_number:
        base = base.filter(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if vehicle_make:
        base = base.filter(
            or_(
                Vehicle.make.ilike(f"%{vehicle_make}%"),
                Vehicle.model.ilike(f"%{vehicle_make}%"),
            )
        )
    expired_registration: List[Vehicle] = []
    expired_inspection: List[Vehicle] = []
    expired_authorization: List[Vehicle] = []
    future_date = today + timedelta(days=30)

    if document_status == "expired":
        if document_type in ("all", "registration"):
            expired_registration = base.filter(
                Vehicle.registration_expiry_date.isnot(None),
                Vehicle.registration_expiry_date < today,
            ).order_by(Vehicle.registration_expiry_date).all()
        if document_type in ("all", "inspection"):
            expired_inspection = base.filter(
                Vehicle.inspection_expiry_date.isnot(None),
                Vehicle.inspection_expiry_date < today,
            ).order_by(Vehicle.inspection_expiry_date).all()
        if document_type in ("all", "authorization"):
            expired_authorization = base.filter(
                Vehicle.authorization_expiry_date.isnot(None),
                Vehicle.authorization_expiry_date < today,
            ).order_by(Vehicle.authorization_expiry_date).all()
    elif document_status == "valid":
        if document_type in ("all", "registration"):
            expired_registration = base.filter(
                Vehicle.registration_expiry_date.isnot(None),
                Vehicle.registration_expiry_date >= today,
            ).order_by(Vehicle.registration_expiry_date).all()
        if document_type in ("all", "inspection"):
            expired_inspection = base.filter(
                Vehicle.inspection_expiry_date.isnot(None),
                Vehicle.inspection_expiry_date >= today,
            ).order_by(Vehicle.inspection_expiry_date).all()
        if document_type in ("all", "authorization"):
            expired_authorization = base.filter(
                Vehicle.authorization_expiry_date.isnot(None),
                Vehicle.authorization_expiry_date >= today,
            ).order_by(Vehicle.authorization_expiry_date).all()
    elif document_status == "expiring_soon":
        if document_type in ("all", "registration"):
            expired_registration = base.filter(
                Vehicle.registration_expiry_date.isnot(None),
                Vehicle.registration_expiry_date >= today,
                Vehicle.registration_expiry_date <= future_date,
            ).order_by(Vehicle.registration_expiry_date).all()
        if document_type in ("all", "inspection"):
            expired_inspection = base.filter(
                Vehicle.inspection_expiry_date.isnot(None),
                Vehicle.inspection_expiry_date >= today,
                Vehicle.inspection_expiry_date <= future_date,
            ).order_by(Vehicle.inspection_expiry_date).all()
        if document_type in ("all", "authorization"):
            expired_authorization = base.filter(
                Vehicle.authorization_expiry_date.isnot(None),
                Vehicle.authorization_expiry_date >= today,
                Vehicle.authorization_expiry_date <= future_date,
            ).order_by(Vehicle.authorization_expiry_date).all()
    else:
        if document_type in ("all", "registration"):
            expired_registration = base.filter(
                Vehicle.registration_expiry_date.isnot(None)
            ).order_by(Vehicle.registration_expiry_date).all()
        if document_type in ("all", "inspection"):
            expired_inspection = base.filter(
                Vehicle.inspection_expiry_date.isnot(None)
            ).order_by(Vehicle.inspection_expiry_date).all()
        if document_type in ("all", "authorization"):
            expired_authorization = base.filter(
                Vehicle.authorization_expiry_date.isnot(None)
            ).order_by(Vehicle.authorization_expiry_date).all()

    all_vehicles = set(expired_registration) | set(expired_inspection) | set(expired_authorization)
    expired_all = list(all_vehicles)
    return expired_registration, expired_inspection, expired_authorization, expired_all


def get_index_context(
    status_filter: str = "",
    make_filter: str = "",
    search_plate: str = "",
    project_filter: str = "",
    assigned_department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """سياق صفحة قائمة السيارات (index). نفس أسماء المتغيرات الممررة للقالب."""
    query = Vehicle.query
    if assigned_department_id:
        dept_employee_ids = (
            db.session.query(Employee.id)
            .join(employee_departments)
            .join(Department)
            .filter(Department.id == assigned_department_id)
            .all()
        )
        dept_employee_ids = [e[0] for e in dept_employee_ids]
        if dept_employee_ids:
            vehicle_ids = [
                r[0]
                for r in db.session.query(VehicleHandover.vehicle_id)
                .filter(
                    VehicleHandover.handover_type == "delivery",
                    VehicleHandover.employee_id.in_(dept_employee_ids),
                )
                .distinct()
                .all()
            ]
            query = query.filter(Vehicle.id.in_(vehicle_ids)) if vehicle_ids else query.filter(Vehicle.id == -1)
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

    vehicles = query.order_by(Vehicle.status, Vehicle.plate_number).all()
    for v in vehicles:
        try:
            v.current_employee_id = get_vehicle_current_employee_id(v.id)
        except Exception:
            v.current_employee_id = None

    makes = [m[0] for m in db.session.query(Vehicle.make).distinct().all()]
    projects = [
        p[0]
        for p in db.session.query(Vehicle.project)
        .filter(Vehicle.project.isnot(None))
        .distinct()
        .all()
    ]
    today = datetime.now().date()
    thirty_days = today + timedelta(days=30)
    expiring_documents: List[Dict[str, Any]] = []
    for v in vehicles:
        for attr, doc_type, doc_name in [
            ("authorization_expiry_date", "authorization", "تفويض المركبة"),
            ("registration_expiry_date", "registration", "استمارة السيارة"),
            ("inspection_expiry_date", "inspection", "الفحص الدوري"),
        ]:
            d = getattr(v, attr, None)
            if d and today <= d <= thirty_days:
                expiring_documents.append({
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "document_type": doc_type,
                    "document_name": doc_name,
                    "expiry_date": d,
                    "days_remaining": (d - today).days,
                })
    expiring_documents.sort(key=lambda x: x["days_remaining"])

    stats = {
        "total": Vehicle.query.count(),
        "available": Vehicle.query.filter_by(status="available").count(),
        "rented": Vehicle.query.filter_by(status="rented").count(),
        "in_project": Vehicle.query.filter_by(status="in_project").count(),
        "in_workshop": Vehicle.query.filter_by(status="in_workshop").count(),
        "accident": Vehicle.query.filter_by(status="accident").count(),
        "out_of_service": Vehicle.query.filter_by(status="out_of_service").count(),
    }
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
        "stats": stats,
        "status_filter": status_filter,
        "make_filter": make_filter,
        "search_plate": search_plate,
        "project_filter": project_filter,
        "makes": makes,
        "projects": projects,
        "statuses": VEHICLE_STATUS_CHOICES,
        "expiring_documents": expiring_documents,
        "expired_authorization_vehicles": expired_authorization_vehicles,
        "expired_inspection_vehicles": expired_inspection_vehicles,
        "now": datetime.now(),
        "timedelta": timedelta,
        "today": today,
    }


def get_vehicle_view_context(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """سياق صفحة تفاصيل سيارة (view). نفس أسماء المتغيرات الممررة للقالب."""
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    id_ = vehicle_id

    approved_ids = db.session.query(OperationRequest.related_record_id).filter_by(
        operation_type="handover", status="approved", vehicle_id=id_
    ).subquery()
    all_ids = db.session.query(OperationRequest.related_record_id).filter_by(
        operation_type="handover", vehicle_id=id_
    ).subquery()
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
            }
    all_deliveries = [r for r in handover_records if r.handover_type == "delivery"]
    previous_drivers = [
        {
            "name": r.person_name,
            "date": r.handover_date,
            "formatted_date": format_date_arabic(r.handover_date),
            "handover_id": r.id,
            "mobile": r.driver_phone_number,
        }
        for r in all_deliveries[1:]
    ]

    for record in workshop_records + project_assignments + handover_records + periodic_inspections + accidents + external_safety_checks:
        for attr in [
            "entry_date", "exit_date", "start_date", "end_date",
            "handover_date", "inspection_date", "expiry_date", "check_date", "accident_date",
        ]:
            if hasattr(record, attr) and getattr(record, attr) and isinstance(getattr(record, attr), (datetime, date)):
                setattr(record, f"formatted_{attr}", format_date_arabic(getattr(record, attr)))
    if rental and rental.start_date:
        rental.formatted_start_date = format_date_arabic(rental.start_date)
        if rental.end_date:
            rental.formatted_end_date = format_date_arabic(rental.end_date)

    attachments = (
        VehicleWorkshopImage.query.join(VehicleWorkshop)
        .filter(VehicleWorkshop.vehicle_id == id_)
        .all()
    )

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
        "inspection_warnings": [],
    }


def get_expired_documents_context() -> Dict[str, Any]:
    """سياق صفحة الوثائق المنتهية."""
    today = datetime.now().date()
    expired_registration = Vehicle.query.filter(
        Vehicle.registration_expiry_date.isnot(None),
        Vehicle.registration_expiry_date < today,
    ).order_by(Vehicle.registration_expiry_date).all()
    expired_inspection = Vehicle.query.filter(
        Vehicle.inspection_expiry_date.isnot(None),
        Vehicle.inspection_expiry_date < today,
    ).order_by(Vehicle.inspection_expiry_date).all()
    expired_authorization = Vehicle.query.filter(
        Vehicle.authorization_expiry_date.isnot(None),
        Vehicle.authorization_expiry_date < today,
    ).order_by(Vehicle.authorization_expiry_date).all()
    expired_all = Vehicle.query.filter(
        or_(
            (Vehicle.registration_expiry_date.isnot(None)) & (Vehicle.registration_expiry_date < today),
            (Vehicle.inspection_expiry_date.isnot(None)) & (Vehicle.inspection_expiry_date < today),
            (Vehicle.authorization_expiry_date.isnot(None)) & (Vehicle.authorization_expiry_date < today),
        )
    ).order_by(Vehicle.plate_number).all()
    return {
        "expired_registration": expired_registration,
        "expired_inspection": expired_inspection,
        "expired_authorization": expired_authorization,
        "expired_all": expired_all,
        "today": today,
    }


def calculate_maintenance_costs(vehicle_id: int) -> Dict[str, Any]:
    """حساب تكاليف الصيانة وعدد الأيام في الورشة لسيارة."""
    workshop_records = (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .order_by(VehicleWorkshop.entry_date.desc())
        .all()
    )
    total_cost = sum((r.cost or 0) for r in workshop_records)
    days_in_workshop = sum(
        (r.exit_date - r.entry_date).days for r in workshop_records if r.exit_date
    )
    return {"total_maintenance_cost": total_cost, "days_in_workshop": days_in_workshop}


def get_dashboard_context() -> Dict[str, Any]:
    """سياق لوحة معلومات السيارات (dashboard)."""
    total_vehicles = Vehicle.query.count()
    status_stats = db.session.query(Vehicle.status, func.count(Vehicle.id)).group_by(Vehicle.status).all()
    status_dict = {s: c for s, c in status_stats}
    total_monthly_rent = (
        db.session.query(func.sum(VehicleRental.monthly_cost))
        .filter_by(is_active=True)
        .scalar()
        or 0
    )
    workshop_records = (
        db.session.query(VehicleWorkshop)
        .join(Vehicle, VehicleWorkshop.vehicle_id == Vehicle.id)
        .filter(VehicleWorkshop.exit_date.is_(None))
        .options(joinedload(VehicleWorkshop.vehicle))
        .all()
    )
    vehicles_in_workshop = len(workshop_records)
    workshop_vehicles_list = []
    for record in workshop_records:
        v = record.vehicle
        if v:
            days_in_workshop = (
                (datetime.now().date() - record.entry_date).days
                if record.entry_date
                else 0
            )
            workshop_vehicles_list.append({
                "id": v.id,
                "plate_number": v.plate_number,
                "make": v.make,
                "model": v.model,
                "entry_date": record.entry_date,
                "reason": record.reason,
                "cost": record.cost or 0,
                "workshop_name": record.workshop_name,
                "status": v.status,
                "days_in_workshop": days_in_workshop,
            })
    current_year = datetime.now().year
    current_month = datetime.now().month
    yearly_maintenance_cost = (
        db.session.query(func.sum(VehicleWorkshop.cost))
        .filter(extract("year", VehicleWorkshop.entry_date) == current_year)
        .scalar()
        or 0
    )
    monthly_costs = []
    for i in range(6):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        month_cost = (
            db.session.query(func.sum(VehicleWorkshop.cost))
            .filter(
                extract("year", VehicleWorkshop.entry_date) == year,
                extract("month", VehicleWorkshop.entry_date) == month,
            )
            .scalar()
            or 0
        )
        month_name = [
            "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ][month - 1]
        monthly_costs.append({"month": month_name, "cost": month_cost})
    monthly_costs.reverse()

    alerts = []
    long_workshop = VehicleWorkshop.query.filter(
        VehicleWorkshop.exit_date.is_(None),
        VehicleWorkshop.entry_date <= (datetime.now().date() - timedelta(days=14)),
    ).all()
    for stay in long_workshop:
        days = (datetime.now().date() - stay.entry_date).days
        v = Vehicle.query.get(stay.vehicle_id)
        if v:
            alerts.append({
                "type": "workshop",
                "message": f"السيارة {v.plate_number} في الورشة منذ {days} يوم",
                "vehicle_id": v.id,
                "plate_number": v.plate_number,
                "make": v.make,
                "model": v.model,
            })
    ending_rentals = VehicleRental.query.filter(
        VehicleRental.is_active == True,
        VehicleRental.end_date.isnot(None),
        VehicleRental.end_date <= (datetime.now().date() + timedelta(days=7)),
        VehicleRental.end_date >= datetime.now().date(),
    ).all()
    for rental in ending_rentals:
        if rental.end_date:
            days = (rental.end_date - datetime.now().date()).days
            v = Vehicle.query.get(rental.vehicle_id)
            if v:
                alerts.append({
                    "type": "rental",
                    "message": f"إيجار السيارة {v.plate_number} سينتهي خلال {days} يوم",
                    "vehicle_id": v.id,
                    "plate_number": v.plate_number,
                    "make": v.make,
                    "model": v.model,
                })

    today = datetime.now().date()
    expired_registration_vehicles = Vehicle.query.filter(
        Vehicle.registration_expiry_date.isnot(None),
        Vehicle.registration_expiry_date < today,
    ).order_by(Vehicle.registration_expiry_date).all()
    expired_inspection_vehicles = Vehicle.query.filter(
        Vehicle.inspection_expiry_date.isnot(None),
        Vehicle.inspection_expiry_date < today,
    ).order_by(Vehicle.inspection_expiry_date).all()
    expired_authorization_vehicles = Vehicle.query.filter(
        Vehicle.authorization_expiry_date.isnot(None),
        Vehicle.authorization_expiry_date < today,
    ).order_by(Vehicle.authorization_expiry_date).all()

    status_counts = {
        "available": status_dict.get("available", 0),
        "rented": status_dict.get("rented", 0),
        "in_project": status_dict.get("in_project", 0),
        "in_workshop": status_dict.get("in_workshop", 0),
        "accident": status_dict.get("accident", 0),
    }
    stats = {
        "total_vehicles": total_vehicles,
        "status_stats": status_dict,
        "status_counts": status_counts,
        "total_monthly_rent": total_monthly_rent,
        "total_rental_cost": total_monthly_rent,
        "vehicles_in_workshop": vehicles_in_workshop,
        "yearly_maintenance_cost": yearly_maintenance_cost,
        "new_vehicles_last_month": Vehicle.query.filter(
            Vehicle.created_at >= (datetime.now() - timedelta(days=30))
        ).count(),
        "workshop_cost_current_month": db.session.query(func.sum(VehicleWorkshop.cost))
        .filter(
            extract("year", VehicleWorkshop.entry_date) == current_year,
            extract("month", VehicleWorkshop.entry_date) == current_month,
        )
        .scalar()
        or 0,
        "vehicles_in_projects": Vehicle.query.filter_by(status="in_project").count(),
        "project_assignments_count": db.session.query(
            func.count(func.distinct(VehicleProject.project_name))
        )
        .filter_by(is_active=True)
        .scalar()
        or 0,
    }
    rental_cost_data = {"labels": [], "data_values": []}
    maintenance_cost_data = {"labels": [], "data_values": []}
    for i in range(5, -1, -1):
        month_num = (current_month - i) % 12 or 12
        year = current_year - 1 if current_month - i <= 0 else current_year
        month_name = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
        }[month_num]
        label = f"{month_name} {year}"
        rental_cost_data["labels"].append(label)
        rental_cost_data["data_values"].append(0)
        maintenance_cost_data["labels"].append(label)
        maintenance_cost_data["data_values"].append(0)

    return {
        "stats": stats,
        "monthly_costs": monthly_costs,
        "alerts": alerts,
        "rental_cost_data": rental_cost_data,
        "maintenance_cost_data": maintenance_cost_data,
        "expired_registration_vehicles": expired_registration_vehicles,
        "expired_inspection_vehicles": expired_inspection_vehicles,
        "expired_authorization_vehicles": expired_authorization_vehicles,
        "workshop_vehicles_list": workshop_vehicles_list,
        "today": today,
    }
