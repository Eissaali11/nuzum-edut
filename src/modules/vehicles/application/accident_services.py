"""
خدمات سجلات الحوادث المرورية — إنشاء سجل، مزامنة حالة المركبة.
لا يتجاوز 400 سطر.
"""
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from src.core.extensions import db
from src.modules.vehicles.domain.models import Vehicle, VehicleAccident, VehicleAccidentImage


def _parse_date(value: Any) -> Optional[date]:
    """تحويل قيمة إلى date أو None."""
    if value is None:
        return None
    if hasattr(value, "year"):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def create_accident_record_action(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files_data: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    إنشاء سجل حادث مروري وربط الصور. يحدّث حالة المركبة إلى 'accident' عند النجاح.
    يُرجع {"success": True, "accident": record} أو {"success": False, "error": str}.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return {"success": False, "error": "المركبة غير موجودة"}

    accident_date = _parse_date(form_data.get("accident_date")) or date.today()
    driver_name = (form_data.get("driver_name") or "").strip()
    if not driver_name:
        return {"success": False, "error": "اسم السائق مطلوب"}

    accident_status = form_data.get("accident_status") or "قيد المعالجة"
    vehicle_condition = (form_data.get("vehicle_condition") or "").strip() or None
    location = (form_data.get("location") or "").strip() or None
    description = (form_data.get("description") or "").strip() or None
    notes = (form_data.get("notes") or "").strip() or None
    accident_file_link = (form_data.get("accident_file_link") or "").strip() or None

    try:
        deduction_amount = float(form_data.get("deduction_amount") or 0)
    except (TypeError, ValueError):
        deduction_amount = 0.0
    deduction_status = bool(form_data.get("deduction_status"))
    try:
        liability_percentage = int(form_data.get("liability_percentage") or 0)
    except (TypeError, ValueError):
        liability_percentage = 0
    police_report = bool(form_data.get("police_report"))
    insurance_claim = bool(form_data.get("insurance_claim"))

    try:
        accident = VehicleAccident(
            vehicle_id=vehicle_id,
            accident_date=accident_date,
            driver_name=driver_name,
            accident_status=accident_status,
            vehicle_condition=vehicle_condition,
            deduction_amount=deduction_amount,
            deduction_status=deduction_status,
            liability_percentage=liability_percentage,
            accident_file_link=accident_file_link,
            location=location,
            police_report=police_report,
            insurance_claim=insurance_claim,
            description=description,
            notes=notes,
        )
        db.session.add(accident)
        db.session.flush()

        for item in (files_data or []):
            image_path = item.get("image_path")
            if image_path:
                img = VehicleAccidentImage(
                    accident_id=accident.id,
                    image_path=image_path,
                    image_type=item.get("image_type") or "other",
                    caption=item.get("caption"),
                )
                db.session.add(img)

        vehicle.status = "accident"
        vehicle.updated_at = datetime.utcnow()
        db.session.commit()
        return {"success": True, "accident": accident}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
