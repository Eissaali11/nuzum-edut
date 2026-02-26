"""Status transition validation for vehicle lifecycle operations."""

from __future__ import annotations

from typing import Optional, Tuple

from models import Vehicle


class StatusValidator:
    """Guard clause utilities for vehicle status transitions."""

    @staticmethod
    def validate_transition(vehicle_id: int, target_status: str) -> Tuple[bool, str, Optional[str]]:
        """Validate a vehicle status transition.

        Returns (is_valid, message, current_status).
        """
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", None

        current_status = vehicle.status or ""

        if target_status == "in_workshop":
            if current_status == "in_workshop":
                return False, "المركبة موجودة بالفعل في الورشة", current_status
            if current_status != "available":
                return False, "لا يمكن إرسال المركبة للورشة إلا وهي متاحة", current_status

        if target_status == "available":
            if current_status != "in_workshop":
                return False, "لا يمكن إعادة المركبة إلا إذا كانت في الورشة", current_status

        if target_status == "accident":
            if current_status == "in_workshop":
                return False, "لا يمكن تسجيل حادث لمركبة في الورشة", current_status

        if target_status == "document_update":
            if current_status in {"in_workshop", "accident"}:
                return False, "لا يمكن تحديث الوثائق والمركبة في حالة حرجة", current_status

        return True, "", current_status
