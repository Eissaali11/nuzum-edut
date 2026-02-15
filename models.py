"""
Central Models Registry Shim
This file re-exports all domain models from their respective modules to maintain
backward compatibility and ensure flask db migrate recognizes all tables.

All models are organized into domain-specific modules:
- core/domain/models.py: User, UserRole, Permission, Module, SystemAudit, AuditLog, Notification
- modules/employees/domain/models.py: Employee, Department, Attendance, Salary, Document, Nationality, EmployeeLocation
- modules/vehicles/domain/: Vehicle, VehicleRental, VehicleWorkshop, and maintenance/inspection/accident models
- modules/attendance/domain/models.py: Geofence, GeofenceEvent, GeofenceSession, GeofenceAttendance
- modules/operations/domain/models.py: EmployeeRequest, InvoiceRequest, AdvancePaymentRequest, CarWashRequest, etc.
- modules/devices/domain/models.py: MobileDevice, SimCard, ImportedPhoneNumber, DeviceAssignment, VoiceHubCall, VoiceHubAnalysis
- modules/properties/domain/models.py: RentalProperty, PropertyImage, PropertyPayment, PropertyFurnishing
- modules/fees/domain/models.py: RenewalFee, Fee, FeesCost
"""

# ============================================================================
# Core Domain Models
# ============================================================================
from core.domain.models import (
    User,
    UserRole,
    UserPermission,
    Module,
    Permission,
    SystemAudit,
    AuditLog,
    Notification,
    user_accessible_departments,
    vehicle_user_access
)

# ============================================================================
# Employee Domain Models
# ============================================================================
from modules.employees.domain.models import (
    Department,
    Nationality,
    Employee,
    EmployeeLocation,
    Attendance,
    Salary,
    Document,
    employee_departments,
    employee_geofences
)

# ============================================================================
# Vehicle Domain Models
# ============================================================================
from modules.vehicles.domain.models import (
    Vehicle,
    VehicleRental,
    VehicleWorkshop,
    VehicleWorkshopImage,
    VehicleProject,
    VehicleHandover,
    VehicleHandoverImage
)

from modules.vehicles.domain.vehicle_maintenance_models import (
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

# ============================================================================
# Attendance Domain Models
# ============================================================================
from modules.attendance.domain.models import (
    Geofence,
    GeofenceEvent,
    GeofenceSession,
    GeofenceAttendance
)

# ============================================================================
# Operations Domain Models
# ============================================================================
from modules.operations.domain.models import (
    RequestType,
    RequestStatus,
    MediaType,
    FileType,
    LiabilityType,
    LiabilityStatus,
    InstallmentStatus,
    EmployeeRequest,
    InvoiceRequest,
    AdvancePaymentRequest,
    CarWashRequest,
    CarWashMedia,
    CarInspectionRequest,
    CarInspectionMedia,
    EmployeeLiability,
    LiabilityInstallment,
    RequestNotification,
    InspectionUploadToken,
    OperationRequest,
    OperationNotification
)

# ============================================================================
# Mobile Devices Domain Models
# ============================================================================
from modules.devices.domain.models import (
    MobileDevice,
    SimCard,
    ImportedPhoneNumber,
    DeviceAssignment,
    VoiceHubCall,
    VoiceHubAnalysis
)

# ============================================================================
# Properties Domain Models
# ============================================================================
from modules.properties.domain.models import (
    RentalProperty,
    PropertyImage,
    PropertyPayment,
    PropertyFurnishing,
    property_employees
)

# ============================================================================
# Fees Domain Models
# ============================================================================
from modules.fees.domain.models import (
    RenewalFee,
    Fee,
    FeesCost
)

# ============================================================================
# EXPORT ALL MODELS
# ============================================================================

__all__ = [
    # Core
    'User', 'UserRole', 'UserPermission', 'Module', 'Permission', 'SystemAudit', 'AuditLog', 'Notification',
    'user_accessible_departments', 'vehicle_user_access',
    
    # Employees
    'Department', 'Nationality', 'Employee', 'EmployeeLocation', 'Attendance', 'Salary', 'Document',
    'employee_departments', 'employee_geofences',
    
    # Vehicles
    'Vehicle', 'VehicleRental', 'VehicleWorkshop', 'VehicleWorkshopImage', 'VehicleProject',
    'VehicleHandover', 'VehicleHandoverImage',
    'VehicleChecklist', 'VehicleChecklistItem', 'VehicleChecklistImage', 'VehicleDamageMarker',
    'VehicleMaintenance', 'VehicleMaintenanceImage', 'VehicleFuelConsumption',
    'VehiclePeriodicInspection', 'VehicleSafetyCheck',
    'VehicleAccident', 'VehicleAccidentImage',
    'Project', 'ExternalAuthorization',
    'VehicleExternalSafetyCheck', 'VehicleSafetyImage',
    'SafetyInspection',
    'VehicleInspectionRecord', 'VehicleInspectionImage',
    
    # Attendance/Geofencing
    'Geofence', 'GeofenceEvent', 'GeofenceSession', 'GeofenceAttendance',
    
    # Operations/Requests
    'RequestType', 'RequestStatus', 'MediaType', 'FileType', 'LiabilityType', 'LiabilityStatus', 'InstallmentStatus',
    'EmployeeRequest', 'InvoiceRequest', 'AdvancePaymentRequest',
    'CarWashRequest', 'CarWashMedia',
    'CarInspectionRequest', 'CarInspectionMedia',
    'EmployeeLiability', 'LiabilityInstallment',
    'RequestNotification',
    'InspectionUploadToken',
    'OperationRequest', 'OperationNotification',
    
    # Mobile Devices
    'MobileDevice', 'SimCard', 'ImportedPhoneNumber', 'DeviceAssignment',
    'VoiceHubCall', 'VoiceHubAnalysis',
    
    # Properties
    'RentalProperty', 'PropertyImage', 'PropertyPayment', 'PropertyFurnishing', 'property_employees',
    
    # Fees
    'RenewalFee', 'Fee', 'FeesCost',
]

