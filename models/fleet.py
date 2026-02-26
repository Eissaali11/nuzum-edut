"""
Fleet domain model exports.

This module provides a stable domain-specific entrypoint without changing
actual model declarations or database schema.
"""

from modules.vehicles.domain.models import Vehicle
from modules.vehicles.domain.handover_models import VehicleHandover
from modules.vehicles.domain.vehicle_maintenance_models import VehicleMaintenance

# NOTE:
# A concrete VehicleInsurance db.Model class is not currently defined in the
# active domain model set. Vehicle insurance data is represented via vehicle
# fields (e.g. insurance_file) and maintenance/accident entities.
VehicleInsurance = None

__all__ = [
    "Vehicle",
    "VehicleMaintenance",
    "VehicleHandover",
    "VehicleInsurance",
]
