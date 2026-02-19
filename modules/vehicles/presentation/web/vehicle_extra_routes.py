"""Vehicle extra routes aggregator.

This module keeps backward-compatible registration via
`register_vehicle_extra_routes(bp)` while delegating route groups
into focused files under the same package.
"""

from modules.vehicles.presentation.web.vehicle_extra_authorization_routes import (
    register_vehicle_extra_authorization_routes,
)
from modules.vehicles.presentation.web.vehicle_extra_core_routes import (
    register_vehicle_extra_core_routes,
)
from modules.vehicles.presentation.web.vehicle_extra_document_misc_routes import (
    register_vehicle_extra_document_misc_routes,
)
from modules.vehicles.presentation.web.vehicle_extra_handover_drive_routes import (
    register_vehicle_extra_handover_drive_routes,
)
from modules.vehicles.presentation.web.vehicle_extra_inspection_safety_routes import (
    register_vehicle_extra_inspection_safety_routes,
)


def register_vehicle_extra_routes(bp):
    register_vehicle_extra_core_routes(bp)
    register_vehicle_extra_inspection_safety_routes(bp)
    register_vehicle_extra_authorization_routes(bp)
    register_vehicle_extra_handover_drive_routes(bp)
    register_vehicle_extra_document_misc_routes(bp)
