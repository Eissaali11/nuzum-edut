"""Mobile vehicle lifecycle registrar (modularized)."""

from .vehicle_handover_lifecycle_routes import register_vehicle_handover_lifecycle_routes
from .vehicle_workshop_routes import register_vehicle_workshop_routes
from .vehicle_external_authorization_routes import register_vehicle_external_authorization_routes


def register_vehicle_lifecycle_routes(bp):
    """Register vehicle lifecycle route groups."""
    register_vehicle_handover_lifecycle_routes(bp)
    register_vehicle_workshop_routes(bp)
    register_vehicle_external_authorization_routes(bp)
