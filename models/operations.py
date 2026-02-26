"""
Operations domain model exports.

This module provides a stable domain-specific entrypoint without changing
actual model declarations or database schema.
"""

from core.domain.models import Notification
from modules.attendance.domain.models import Geofence
from modules.operations.domain.models import OperationRequest

# NOTE:
# The codebase uses specialized request entities (EmployeeRequest,
# InvoiceRequest, OperationRequest, ...). Expose a generic alias for
# compatibility with high-level domain naming.
Request = OperationRequest

__all__ = [
    "Request",
    "Notification",
    "Geofence",
]
