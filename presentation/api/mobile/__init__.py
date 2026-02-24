"""
مسارات API الجوال — مصادقة، فحوصات، قوائم فحص، حضور/رواتب، تتبع، لوحة تحكم، ومركبات.
"""
from .identity.auth_routes import register_auth_routes
from .documents.inspection_routes import register_inspection_routes
from .organization.hr_routes import register_hr_routes
from .tracking.tracking_routes import register_tracking_routes
from .dashboard.dashboard_routes import register_dashboard_routes
from .vehicles.vehicle_routes import register_vehicle_routes
from .identity.google_routes import register_google_routes
from .organization.employee_routes import register_employee_routes
from .organization.department_routes import register_department_routes
from .documents.documents_ui_routes import register_documents_ui_routes
from .reporting.reports_routes import register_reports_routes
from .operations.operations_routes import register_operations_routes
from .vehicles.vehicle_core_routes import register_vehicle_core_routes
from .vehicles.vehicle_handover_checklist_routes import register_vehicle_handover_checklist_routes
from .vehicles.vehicle_admin_misc_routes import register_vehicle_admin_misc_routes
from .vehicles.vehicle_lifecycle_routes import register_vehicle_lifecycle_routes
from .vehicles.vehicle_handover_lifecycle_routes import register_vehicle_handover_lifecycle_routes
from .vehicles.vehicle_workshop_routes import register_vehicle_workshop_routes
from .vehicles.vehicle_external_authorization_routes import register_vehicle_external_authorization_routes

__all__ = [
    "register_auth_routes",
    "register_inspection_routes",
    "register_hr_routes",
    "register_tracking_routes",
    "register_dashboard_routes",
    "register_vehicle_routes",
    "register_google_routes",
    "register_employee_routes",
    "register_department_routes",
    "register_documents_ui_routes",
    "register_reports_routes",
    "register_operations_routes",
    "register_vehicle_core_routes",
    "register_vehicle_handover_checklist_routes",
    "register_vehicle_admin_misc_routes",
    "register_vehicle_lifecycle_routes",
    "register_vehicle_handover_lifecycle_routes",
    "register_vehicle_workshop_routes",
    "register_vehicle_external_authorization_routes",
]
