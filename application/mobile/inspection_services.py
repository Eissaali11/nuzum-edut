"""
خدمات الفحص الدوري وفحص السلامة وقائمة فحص المركبة — للجوال.
تتعامل مع الـ commit، ربط الصور عبر infrastructure.storage، وتحديث آخر تاريخ فحص إن وُجد.
لا يتجاوز 400 سطر.
"""
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from core.extensions import db
from infrastructure.storage import save_uploaded_file


def _parse_date(value: Any) -> Optional[date]:
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


def create_periodic_inspection_action(
    vehicle_id: int,
    form_data: Dict[str, Any],
    current_user_id: int,
) -> Tuple[bool, Any, str]:
    """
    إنشاء سجل فحص دوري للسيارة.
    يُرجع (success, inspection_or_none, message).
    """
    from models import Vehicle, VehiclePeriodicInspection, SystemAudit

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, None, "المركبة غير موجودة"

    inspection_date = _parse_date(form_data.get("inspection_date"))
    expiry_date = _parse_date(form_data.get("expiry_date"))
    if not inspection_date or not expiry_date:
        return False, None, "تاريخ الفحص وتاريخ الانتهاء مطلوبان"

    inspection = VehiclePeriodicInspection(
        vehicle_id=vehicle_id,
        inspection_date=inspection_date,
        expiry_date=expiry_date,
        inspection_center=(form_data.get("inspection_center") or "").strip() or None,
        result=(form_data.get("result") or "").strip() or None,
        driver_name=(form_data.get("driver_name") or "").strip() or "",
        supervisor_name=(form_data.get("supervisor_name") or "").strip() or "",
        notes=(form_data.get("notes") or "").strip() or "",
    )
    db.session.add(inspection)
    db.session.commit()

    try:
        SystemAudit.create_audit_record(
            current_user_id,
            "إنشاء",
            "VehiclePeriodicInspection",
            inspection.id,
            f"تم إضافة سجل فحص دوري للسيارة: {vehicle.plate_number}",
            entity_name=f"سيارة: {vehicle.plate_number}",
        )
    except Exception:
        pass

    return True, inspection, "تم إضافة سجل الفحص الدوري بنجاح"


def create_safety_check_action(
    vehicle_id: int,
    form_data: Dict[str, Any],
    current_user_id: int,
) -> Tuple[bool, Any, str]:
    """
    إنشاء سجل فحص سلامة للسيارة.
    يُرجع (success, safety_check_or_none, message).
    """
    from models import Vehicle, VehicleSafetyCheck, SystemAudit

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, None, "المركبة غير موجودة"

    check_date = _parse_date(form_data.get("check_date"))
    if not check_date:
        return False, None, "تاريخ الفحص مطلوب"

    result_val = (form_data.get("result") or "").strip() or "completed"
    safety_check = VehicleSafetyCheck(
        vehicle_id=vehicle_id,
        check_date=check_date,
        check_type=(form_data.get("check_type") or "").strip() or "يومي",
        driver_name=(form_data.get("driver_name") or "").strip() or "",
        supervisor_name=(form_data.get("supervisor_name") or "").strip() or "",
        status=result_val,
        notes=(form_data.get("notes") or "").strip() or "",
    )
    db.session.add(safety_check)
    db.session.commit()

    try:
        SystemAudit.create_audit_record(
            current_user_id,
            "إنشاء",
            "VehicleSafetyCheck",
            safety_check.id,
            f"تم إضافة سجل فحص سلامة للسيارة: {vehicle.plate_number}",
            entity_name=f"سيارة: {vehicle.plate_number}",
        )
    except Exception:
        pass

    return True, safety_check, "تم إضافة سجل فحص السلامة بنجاح"


def add_vehicle_checklist_action(
    vehicle_id: int,
    inspection_date: date,
    inspector_name: str,
    inspection_type: str,
    general_notes: str,
    items_data: List[Dict[str, Any]],
    damage_markers_data: Optional[List[Dict[str, Any]]] = None,
    uploaded_files: Optional[List[Any]] = None,
    description_for_index: Optional[Dict[int, str]] = None,
) -> Tuple[bool, Optional[Any], str]:
    """
    إضافة قائمة فحص مركبة مع العناصر وعلامات التلف والصور.
    الصور تُحفظ عبر infrastructure.storage (save_uploaded_file).
    يُرجع (success, checklist_or_none, message).
    """
    from models import (
        Vehicle,
        VehicleChecklist,
        VehicleChecklistItem,
        VehicleDamageMarker,
        VehicleChecklistImage,
    )

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, None, "المركبة غير موجودة"

    new_checklist = VehicleChecklist(
        vehicle_id=vehicle_id,
        inspection_date=inspection_date,
        inspector_name=inspector_name,
        inspection_type=inspection_type,
        notes=general_notes or "",
    )
    db.session.add(new_checklist)
    db.session.flush()

    for item_data in items_data or []:
        category = item_data.get("category")
        item_name = item_data.get("item_name")
        status = item_data.get("status")
        notes = item_data.get("notes", "")
        if not all([category, item_name, status]):
            continue
        db.session.add(
            VehicleChecklistItem(
                checklist_id=new_checklist.id,
                category=category,
                item_name=item_name,
                status=status,
                notes=notes,
            )
        )

    for marker_data in damage_markers_data or []:
        marker_type = marker_data.get("type", "damage")
        x = marker_data.get("x")
        y = marker_data.get("y")
        notes = marker_data.get("notes", "")
        if x is None or y is None:
            continue
        db.session.add(
            VehicleDamageMarker(
                checklist_id=new_checklist.id,
                marker_type=marker_type,
                position_x=float(x),
                position_y=float(y),
                notes=notes,
                color="red" if marker_type == "damage" else "yellow",
            )
        )

    subfolder = "vehicles/checklists"
    for i, file in enumerate(uploaded_files or []):
        if not file or not getattr(file, "filename", None):
            continue
        path = save_uploaded_file(file, subfolder)
        if path:
            desc = (description_for_index or {}).get(i) or f"صورة فحص بتاريخ {inspection_date}"
            db.session.add(
                VehicleChecklistImage(
                    checklist_id=new_checklist.id,
                    image_path=path,
                    image_type="inspection",
                    description=desc,
                )
            )

    db.session.commit()
    return True, new_checklist, "تم إضافة الفحص بنجاح"
