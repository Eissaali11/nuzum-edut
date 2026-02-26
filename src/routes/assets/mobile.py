"""
مسارات ومعالجات الواجهة المحمولة
نُظم - النسخة المحمولة

تم تفكيك الملف إلى وحدات متخصصة داخل presentation/api/mobile
بنفس أسلوب توزيع القوالب إلى partials.
"""

from flask import Blueprint

mobile_bp = Blueprint("mobile", __name__)

from src.presentation.api.mobile.identity.auth_routes import register_auth_routes
from src.presentation.api.mobile.dashboard.dashboard_routes import register_dashboard_routes
from src.presentation.api.mobile.organization.department_routes import register_department_routes
from src.presentation.api.mobile.documents.documents_ui_routes import register_documents_ui_routes
from src.presentation.api.mobile.organization.employee_routes import register_employee_routes
from src.presentation.api.mobile.identity.google_routes import register_google_routes
from src.presentation.api.mobile.organization.hr_routes import register_hr_routes
from src.presentation.api.mobile.documents.inspection_routes import register_inspection_routes
from src.presentation.api.mobile.operations.operations_routes import register_operations_routes
from src.presentation.api.mobile.reporting.reports_routes import register_reports_routes
from src.presentation.api.mobile.tracking.tracking_routes import register_tracking_routes
from src.presentation.api.mobile.vehicles.vehicle_routes import register_vehicle_routes

register_auth_routes(mobile_bp)
register_google_routes(mobile_bp)
register_inspection_routes(mobile_bp)
register_hr_routes(mobile_bp)
register_tracking_routes(mobile_bp)
register_dashboard_routes(mobile_bp)
register_vehicle_routes(mobile_bp)
register_employee_routes(mobile_bp)
register_department_routes(mobile_bp)
register_documents_ui_routes(mobile_bp)
register_reports_routes(mobile_bp)
register_operations_routes(mobile_bp)
