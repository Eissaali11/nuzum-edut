"""Mobile vehicle routes registrar (modularized)."""

from .vehicle_core_routes import register_vehicle_core_routes
from .vehicle_handover_checklist_routes import register_vehicle_handover_checklist_routes
from .vehicle_admin_misc_routes import register_vehicle_admin_misc_routes
from .vehicle_lifecycle_routes import register_vehicle_lifecycle_routes


def register_vehicle_routes(bp):
    """Register all mobile vehicle route groups."""
    register_vehicle_core_routes(bp)
    register_vehicle_handover_checklist_routes(bp)
    register_vehicle_admin_misc_routes(bp)
    register_vehicle_lifecycle_routes(bp)
