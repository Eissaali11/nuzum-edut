"""
خدمات سجلات الورشة — إنشاء سجل، التحقق من عدم الدخول المزدوج.
لا يتجاوز 400 سطر.
"""
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from core.extensions import db
from modules.vehicles.domain.models import Vehicle, VehicleWorkshop, VehicleWorkshopImage


def vehicle_already_in_workshop(vehicle_id: int) -> bool:
    """True إذا كانت المركبة مسجلة حالياً في الورشة (بدون تاريخ خروج)."""
    return (
        VehicleWorkshop.query.filter_by(vehicle_id=vehicle_id)
        .filter(VehicleWorkshop.exit_date.is_(None))
        .first()
        is not None
    )


def create_workshop_record_action(
    vehicle_id: int,
    form_data: Dict[str, Any],
    images_data: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    إنشاء سجل دخول ورشة وربط الصور. يحدّث حالة المركبة إلى in_workshop عند عدم وجود تاريخ خروج.
    التحقق: لا يُدخل المركبة إذا كانت بالفعل في الورشة.
    يُرجع {"success": True, "workshop_record": record} أو {"success": False, "error": str}.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return {"success": False, "error": "المركبة غير موجودة"}
    if vehicle_already_in_workshop(vehicle_id):
        return {"success": False, "error": "المركبة مسجلة بالفعل في الورشة (لا يوجد تاريخ خروج). يرجى إغلاق السجل الحالي أولاً."}
    entry_date_str = form_data.get("entry_date") or ""
    exit_date_str = form_data.get("exit_date") or ""
    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date() if entry_date_str else date.today()
    except ValueError:
        entry_date = date.today()
    exit_date = None
    if exit_date_str:
        try:
            exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    reason = form_data.get("reason") or "maintenance"
    description = form_data.get("description") or ""
    repair_status = form_data.get("repair_status") or "in_progress"
    cost = float(form_data.get("cost") or 0)
    workshop_name = form_data.get("workshop_name") or None
    technician_name = form_data.get("technician_name") or None
    delivery_link = form_data.get("delivery_link") or None
    reception_link = form_data.get("reception_link") or None
    notes = form_data.get("notes")
    images_data = images_data or []
    try:
        workshop_record = VehicleWorkshop(
            vehicle_id=vehicle_id,
            entry_date=entry_date,
            exit_date=exit_date,
            reason=reason,
            description=description,
            repair_status=repair_status,
            cost=cost,
            workshop_name=workshop_name,
            technician_name=technician_name,
            delivery_link=delivery_link,
            reception_link=reception_link,
            notes=notes,
        )
        db.session.add(workshop_record)
        db.session.flush()
        for item in images_data:
            image_type = item.get("image_type") or "before"
            image_path = item.get("image_path")
            if image_path:
                img = VehicleWorkshopImage(
                    workshop_record_id=workshop_record.id,
                    image_type=image_type,
                    image_path=image_path,
                )
                db.session.add(img)
        if not exit_date:
            vehicle.status = "in_workshop"
        vehicle.updated_at = datetime.utcnow()
        db.session.commit()
        return {"success": True, "workshop_record": workshop_record}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
