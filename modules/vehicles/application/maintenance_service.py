"""Maintenance and accident lifecycle service.

Provides strict vehicle lifecycle enforcement for workshop, receipt, and accident flows.
Ready to be integrated from Flask blueprints by passing form data and uploaded files.
"""

from __future__ import annotations

import os
from datetime import datetime, date
from typing import Any, Dict, Iterable, Optional, Tuple

from core.extensions import db
from modules.vehicles.domain import VehicleMaintenance, VehicleMaintenanceImage
from modules.vehicles.domain.models import Vehicle, VehicleAccident, VehicleAccidentImage
from infrastructure.storage.file_service import save_uploaded_file


class MaintenanceService:
    """Service for workshop and accident lifecycle transitions."""

    STATUS_AVAILABLE = "available"
    STATUS_IN_WORKSHOP = "in_workshop"
    STATUS_ACCIDENT = "accident"

    def __init__(self, static_folder: Optional[str] = None) -> None:
        self._static_folder = static_folder

    def send_to_workshop(
        self,
        vehicle_id: int,
        form_data: Dict[str, Any],
        attachments: Optional[Iterable[Any]] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Send a vehicle to workshop, create maintenance record, and lock the vehicle."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", None

        if vehicle.status == self.STATUS_IN_WORKSHOP:
            return False, "المركبة موجودة بالفعل في الورشة", None

        if vehicle.status != self.STATUS_AVAILABLE:
            return False, "لا يمكن إرسال المركبة للورشة إلا وهي متاحة", None

        maintenance_date = self._parse_date(form_data.get("date")) or date.today()
        maintenance_type = (form_data.get("maintenance_type") or "maintenance").strip()
        description = (form_data.get("description") or "").strip()
        technician = (form_data.get("technician") or "").strip()

        if not description:
            return False, "وصف الصيانة مطلوب", None
        if not technician:
            return False, "اسم الفني مطلوب", None

        try:
            maintenance = VehicleMaintenance(
                vehicle_id=vehicle_id,
                date=maintenance_date,
                maintenance_type=maintenance_type,
                description=description,
                status="قيد التنفيذ",
                cost=float(form_data.get("cost") or 0),
                technician=technician,
                parts_replaced=form_data.get("parts_replaced"),
                actions_taken=form_data.get("actions_taken"),
                notes=form_data.get("notes"),
            )
            db.session.add(maintenance)
            db.session.flush()

            saved = self._save_maintenance_attachments(maintenance.id, attachments or [])
            if saved:
                maintenance.receipt_image_url = saved[0]

            vehicle.status = self.STATUS_IN_WORKSHOP
            vehicle.updated_at = datetime.utcnow()

            db.session.commit()
            return True, "تم إرسال المركبة إلى الورشة", maintenance.id
        except Exception as exc:
            db.session.rollback()
            return False, f"حدث خطأ أثناء إرسال المركبة للورشة: {str(exc)}", None

    def receive_from_workshop(
        self,
        vehicle_id: int,
        maintenance_id: int,
        form_data: Dict[str, Any],
        inspection_report_file: Optional[Any] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Receive a vehicle from workshop with a required inspection/receipt report."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", None

        if vehicle.status != self.STATUS_IN_WORKSHOP:
            return False, "لا يمكن استلام المركبة لأنها ليست في الورشة", None

        if not inspection_report_file:
            return False, "تقرير الاستلام/الفحص مطلوب لإعادة المركبة", None

        manual_status = (form_data.get("received_status") or "").strip().lower()
        if manual_status not in {"received_from_workshop", "received"}:
            return False, "يجب تحديث الحالة يدويا إلى 'Received from Workshop'", None

        maintenance = VehicleMaintenance.query.get(maintenance_id)
        if not maintenance:
            return False, "سجل الصيانة غير موجود", None

        try:
            saved_path = self._save_single_attachment(inspection_report_file, "maintenance")
            if not saved_path:
                return False, "فشل حفظ تقرير الاستلام", None

            maintenance.pickup_receipt_url = saved_path
            maintenance.status = "منجزة"
            maintenance.updated_at = datetime.utcnow()

            vehicle.status = self.STATUS_AVAILABLE
            vehicle.updated_at = datetime.utcnow()

            db.session.commit()
            return True, "تم استلام المركبة وإعادتها للحالة المتاحة", maintenance.id
        except Exception as exc:
            db.session.rollback()
            return False, f"حدث خطأ أثناء استلام المركبة: {str(exc)}", None

    def register_accident(
        self,
        vehicle_id: int,
        form_data: Dict[str, Any],
        attachments: Optional[Dict[str, Any]] = None,
        requires_repair: bool = False,
    ) -> Tuple[bool, str, Optional[int]]:
        """Register an accident, update vehicle status, and store accident attachments."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", None

        accident_date = self._parse_date(form_data.get("accident_date")) or date.today()
        driver_name = (form_data.get("driver_name") or "").strip()
        if not driver_name:
            return False, "اسم السائق مطلوب", None

        try:
            accident = VehicleAccident(
                vehicle_id=vehicle_id,
                accident_date=accident_date,
                driver_name=driver_name,
                driver_phone=form_data.get("driver_phone"),
                accident_status=form_data.get("accident_status") or "قيد المعالجة",
                vehicle_condition=form_data.get("vehicle_condition"),
                severity=form_data.get("severity"),
                description=form_data.get("description"),
                location=form_data.get("location"),
                notes=form_data.get("notes"),
                police_report=bool(form_data.get("police_report")),
                insurance_claim=bool(form_data.get("insurance_claim")),
                deduction_amount=float(form_data.get("deduction_amount") or 0),
                liability_percentage=int(form_data.get("liability_percentage") or 0),
            )
            db.session.add(accident)
            db.session.flush()

            attachments = attachments or {}
            accident_report_file = attachments.get("accident_report")
            driver_id_image = attachments.get("driver_id_image")
            driver_license_image = attachments.get("driver_license_image")
            extra_images = attachments.get("images") or []

            if accident_report_file:
                accident.accident_report_file = self._save_single_attachment(accident_report_file, "accidents")
            if driver_id_image:
                accident.driver_id_image = self._save_single_attachment(driver_id_image, "accidents")
            if driver_license_image:
                accident.driver_license_image = self._save_single_attachment(driver_license_image, "accidents")

            for item in extra_images:
                path = self._save_single_attachment(item, "accidents")
                if path:
                    db.session.add(
                        VehicleAccidentImage(
                            accident_id=accident.id,
                            image_path=path,
                            image_type="other",
                        )
                    )

            vehicle.status = self.STATUS_IN_WORKSHOP if requires_repair else self.STATUS_ACCIDENT
            vehicle.updated_at = datetime.utcnow()

            db.session.commit()
            return True, "تم تسجيل الحادث بنجاح", accident.id
        except Exception as exc:
            db.session.rollback()
            return False, f"حدث خطأ أثناء تسجيل الحادث: {str(exc)}", None

    def _save_maintenance_attachments(self, maintenance_id: int, files: Iterable[Any]) -> list[str]:
        saved_paths: list[str] = []
        for file in files:
            path = self._save_single_attachment(file, "maintenance")
            if path:
                saved_paths.append(path)
                db.session.add(
                    VehicleMaintenanceImage(
                        maintenance_id=maintenance_id,
                        image_path=path,
                        image_type="receipt",
                    )
                )
        return saved_paths

    def _save_single_attachment(self, file_obj: Any, subfolder: str) -> Optional[str]:
        if not file_obj or not getattr(file_obj, "filename", None):
            return None

        upload_root = None
        if self._static_folder:
            upload_root = os.path.join(self._static_folder, "uploads")

        return save_uploaded_file(file_obj, subfolder, upload_root=upload_root)

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        if hasattr(value, "year"):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
        return None
