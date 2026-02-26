"""Mobile vehicle domain routes."""

from .vehicle_routes import register_vehicle_routes
from .vehicle_core_routes import register_vehicle_core_routes
from .vehicle_handover_checklist_routes import register_vehicle_handover_checklist_routes
from .vehicle_admin_misc_routes import register_vehicle_admin_misc_routes
from .vehicle_lifecycle_routes import register_vehicle_lifecycle_routes
from .vehicle_handover_lifecycle_routes import register_vehicle_handover_lifecycle_routes
from .vehicle_workshop_routes import register_vehicle_workshop_routes
from .vehicle_external_authorization_routes import register_vehicle_external_authorization_routes

__all__ = [
	"register_vehicle_routes",
	"register_vehicle_core_routes",
	"register_vehicle_handover_checklist_routes",
	"register_vehicle_admin_misc_routes",
	"register_vehicle_lifecycle_routes",
	"register_vehicle_handover_lifecycle_routes",
	"register_vehicle_workshop_routes",
	"register_vehicle_external_authorization_routes",
]

