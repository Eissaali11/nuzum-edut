"""Vehicles domain models package"""
from src.modules.vehicles.domain.models import (
    Vehicle,
    VehicleRental,
    VehicleWorkshop,
    VehicleWorkshopImage,
    VehicleProject,
    VehicleHandover,
    VehicleHandoverImage,
    vehicle_user_access
)

from src.modules.vehicles.domain.vehicle_maintenance_models import (
    VehicleChecklist,
    VehicleChecklistItem,
    VehicleChecklistImage,
    VehicleDamageMarker,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehicleFuelConsumption,
    VehiclePeriodicInspection,
    VehicleSafetyCheck,
    VehicleAccident,
    VehicleAccidentImage,
    Project,
    ExternalAuthorization,
    VehicleExternalSafetyCheck,
    VehicleSafetyImage,
    SafetyInspection,
    VehicleInspectionRecord,
    VehicleInspectionImage
)

__all__ = [
    # Core vehicle models
    'Vehicle',
    'VehicleRental',
    'VehicleWorkshop',
    'VehicleWorkshopImage',
    'VehicleProject',
    'VehicleHandover',
    'VehicleHandoverImage',
    'vehicle_user_access',
    # Maintenance and inspection models
    'VehicleChecklist',
    'VehicleChecklistItem',
    'VehicleChecklistImage',
    'VehicleDamageMarker',
    'VehicleMaintenance',
    'VehicleMaintenanceImage',
    'VehicleFuelConsumption',
    'VehiclePeriodicInspection',
    'VehicleSafetyCheck',
    'VehicleAccident',
    'VehicleAccidentImage',
    'Project',
    'ExternalAuthorization',
    'VehicleExternalSafetyCheck',
    'VehicleSafetyImage',
    'SafetyInspection',
    'VehicleInspectionRecord',
    'VehicleInspectionImage'
]
