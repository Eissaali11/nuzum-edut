"""
مسارات API الجوال — مصادقة، فحوصات، قوائم فحص، حضور/رواتب، تتبع، لوحة تحكم، ومركبات.
"""
from .auth_routes import register_auth_routes
from .inspection_routes import register_inspection_routes
from .hr_routes import register_hr_routes
from .tracking_routes import register_tracking_routes
from .dashboard_routes import register_dashboard_routes
from .vehicle_routes import register_vehicle_routes

__all__ = [
    "register_auth_routes",
    "register_inspection_routes",
    "register_hr_routes",
    "register_tracking_routes",
    "register_dashboard_routes",
    "register_vehicle_routes",
]
