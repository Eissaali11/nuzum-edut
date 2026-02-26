"""Document service for vehicle documents and expiry validation."""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, Optional, Tuple

from src.modules.vehicles.domain.models import Vehicle
from src.infrastructure.storage.file_service import save_uploaded_file


class DocumentService:
    """Service layer for vehicle document operations."""

    DOC_FIELD_MAP = {
        "registration_form": "registration_form_image",
        "plate": "plate_image",
        "insurance": "insurance_file",
        "inspection": "license_image",
    }

    EXPIRY_FIELD_MAP = {
        "registration_form": "registration_expiry_date",
        "inspection": "inspection_expiry_date",
        "authorization": "authorization_expiry_date",
    }

    def __init__(self, upload_root: Optional[str] = None) -> None:
        self._upload_root = upload_root

    def upload_document(
        self,
        vehicle_id: int,
        document_type: str,
        file,
        form_data: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", {}

        field_name = self.DOC_FIELD_MAP.get(document_type)
        if not field_name:
            return False, "نوع الوثيقة غير صحيح", {}

        if not file or not getattr(file, "filename", None):
            return False, "لم يتم اختيار ملف", {}

        issue_date, expiry_date, error = self._validate_dates(form_data)
        if error:
            return False, error, {}

        relative_path = save_uploaded_file(
            file,
            subfolder=f"documents/{vehicle_id}",
            upload_root=self._upload_root,
        )
        if not relative_path:
            return False, "فشل حفظ الوثيقة", {}

        setattr(vehicle, field_name, relative_path)
        expiry_field = self.EXPIRY_FIELD_MAP.get(document_type)
        if expiry_field and expiry_date:
            setattr(vehicle, expiry_field, expiry_date)

        vehicle.updated_at = datetime.utcnow()

        warning = None
        if document_type == "insurance" and expiry_date and expiry_date < date.today():
            warning = "انتهت صلاحية وثيقة التأمين"

        return True, "تم رفع الوثيقة بنجاح", {
            "vehicle_id": vehicle_id,
            "document_type": document_type,
            "file_path": relative_path,
            "warning": warning,
        }

    def delete_document(self, vehicle_id: int, document_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", {}

        field_name = self.DOC_FIELD_MAP.get(document_type)
        if not field_name:
            return False, "نوع الوثيقة غير صحيح", {}

        if not getattr(vehicle, field_name):
            return False, "لا توجد وثيقة لحذفها", {}

        setattr(vehicle, field_name, None)
        vehicle.updated_at = datetime.utcnow()

        return True, "تم حذف الوثيقة بنجاح", {
            "vehicle_id": vehicle_id,
            "document_type": document_type,
        }

    def list_documents(self) -> Dict[str, Any]:
        vehicles = Vehicle.query.all()
        today = date.today()

        documents = []
        warnings = []

        for vehicle in vehicles:
            if vehicle.registration_expiry_date:
                documents.append(self._build_doc_entry(vehicle, "registration", "رخصة سير", "fa-id-card", vehicle.registration_expiry_date, today))

            if vehicle.authorization_expiry_date:
                documents.append(self._build_doc_entry(vehicle, "authorization", "تفويض", "fa-shield-alt", vehicle.authorization_expiry_date, today))

            if vehicle.inspection_expiry_date:
                documents.append(self._build_doc_entry(vehicle, "inspection", "فحص دوري", "fa-clipboard-check", vehicle.inspection_expiry_date, today))

            if vehicle.insurance_file and vehicle.authorization_expiry_date and vehicle.authorization_expiry_date < today:
                warnings.append({
                    "vehicle_id": vehicle.id,
                    "plate_number": vehicle.plate_number,
                    "message": "انتهت صلاحية وثيقة التأمين",
                })

        documents.sort(key=lambda x: x["expiry_date"])

        valid_docs = len([d for d in documents if d["status"] == "valid"])
        warning_docs = len([d for d in documents if d["status"] == "warning"])
        expired_docs = len([d for d in documents if d["status"] == "expired"])

        return {
            "documents": documents,
            "valid_docs": valid_docs,
            "warning_docs": warning_docs,
            "expired_docs": expired_docs,
            "total_docs": len(documents),
            "warnings": warnings,
        }

    @staticmethod
    def _build_doc_entry(vehicle, doc_type: str, type_name: str, icon: str, expiry_date: date, today: date) -> Dict[str, Any]:
        days_remaining = (expiry_date - today).days
        status = "valid" if days_remaining > 30 else "warning" if days_remaining > 0 else "expired"
        return {
            "vehicle_id": vehicle.id,
            "vehicle_plate": vehicle.plate_number,
            "type": doc_type,
            "type_name": type_name,
            "icon": icon,
            "expiry_date": expiry_date,
            "days_remaining": days_remaining,
            "status": status,
        }

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

    def _validate_dates(self, form_data: Dict[str, Any]) -> Tuple[Optional[date], Optional[date], Optional[str]]:
        issue_date = self._parse_date(form_data.get("issue_date"))
        expiry_date = self._parse_date(form_data.get("expiry_date"))
        if issue_date and expiry_date and expiry_date <= issue_date:
            return issue_date, expiry_date, "تاريخ الانتهاء يجب أن يكون بعد تاريخ الإصدار"
        return issue_date, expiry_date, None
