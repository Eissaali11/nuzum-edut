"""
خدمة وثائق المركبات — سياق وعمليات عرض/تعديل الوثائق.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from core.extensions import db
from modules.vehicles.domain.models import Vehicle
from utils.vehicle_route_helpers import format_date_arabic
from utils.vehicle_helpers import log_audit


def get_view_documents_context(vehicle_id: int) -> Optional[Dict[str, Any]]:
    """سياق صفحة عرض وثائق المركبة. يُرجع None إذا لم تُوجد المركبة."""
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None
    today = datetime.now().date()
    documents_info = []
    for attr, name in [
        ("authorization_expiry_date", "تفويض المركبة"),
        ("registration_expiry_date", "استمارة السيارة"),
        ("inspection_expiry_date", "الفحص الدوري"),
    ]:
        expiry = getattr(vehicle, attr, None)
        if not expiry:
            continue
        days_remaining = (expiry - today).days
        status = "صالح" if days_remaining >= 0 else "منتهي"
        if 0 < days_remaining <= 30:
            status = "على وشك الانتهاء"
        status_class = "success" if days_remaining > 30 else ("warning" if days_remaining > 0 else "danger")
        documents_info.append({
            "name": name,
            "expiry_date": expiry,
            "formatted_date": format_date_arabic(expiry),
            "days_remaining": days_remaining,
            "status": status,
            "status_class": status_class,
        })
    return {"vehicle": vehicle, "documents_info": documents_info}


def get_valid_documents_context(
    plate_number: str = "",
    vehicle_make: str = "",
) -> Dict[str, Any]:
    """سياق صفحة الوثائق السارية (الفحص الدوري)."""
    from sqlalchemy import case, or_

    today = datetime.now().date()
    query = Vehicle.query
    if plate_number:
        query = query.filter(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if vehicle_make:
        query = query.filter(
            or_(
                Vehicle.make.ilike(f"%{vehicle_make}%"),
                Vehicle.model.ilike(f"%{vehicle_make}%"),
            )
        )
    all_vehicles = query.order_by(
        case(
            (Vehicle.inspection_expiry_date.is_(None), 3),
            (Vehicle.inspection_expiry_date >= today, 1),
            else_=2,
        ),
        Vehicle.inspection_expiry_date,
    ).all()
    valid_inspection = [v for v in all_vehicles if v.inspection_expiry_date and v.inspection_expiry_date >= today]
    expired_inspection = [v for v in all_vehicles if v.inspection_expiry_date and v.inspection_expiry_date < today]
    undefined_inspection = [v for v in all_vehicles if not v.inspection_expiry_date]
    return {
        "all_vehicles": all_vehicles,
        "valid_inspection": valid_inspection,
        "expired_inspection": expired_inspection,
        "undefined_inspection": undefined_inspection,
        "total_vehicles": len(all_vehicles),
        "valid_count": len(valid_inspection),
        "expired_count": len(expired_inspection),
        "undefined_count": len(undefined_inspection),
        "today": today,
        "plate_number": plate_number,
        "vehicle_make": vehicle_make,
    }
