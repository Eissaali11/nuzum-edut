from flask import Blueprint as FlaskBlueprint
from flask_login import login_required, current_user
from flask import render_template

def register_all_blueprints(app, csrf):
    """
    Register all blueprints and apply CSRF exemptions.
    """
    # Import and register route blueprints
    from routes.dashboard import dashboard_bp
    from routes.employees import employees_bp
    from routes.departments import departments_bp
    from routes.attendance import attendance_bp
    from routes.salaries import salaries_bp
    from routes.documents import documents_bp
    from routes.reports import reports_bp
    from routes.auth import auth_bp
    from modules.vehicles.presentation.web.main_routes import get_vehicles_blueprint
    from routes.fees_costs import fees_costs_bp
    from routes.api import api_bp
    from routes.enhanced_reports import enhanced_reports_bp
    from routes.mobile import mobile_bp
    from routes.users import users_bp
    from routes.mass_attendance import mass_attendance_bp
    from routes.attendance_dashboard import attendance_dashboard_bp
    from routes.e_invoicing import e_invoicing_bp

    # Workshop reports now using ReportLab (no GTK dependency)
    from modules.vehicles.presentation.web.workshop_reports import register_workshop_reports_routes
    workshop_reports_bp = FlaskBlueprint('workshop_reports', __name__)
    register_workshop_reports_routes(workshop_reports_bp)

    from routes.employee_portal import employee_portal_bp
    from routes.insights import insights_bp
    from routes.external_safety import external_safety_bp
    from routes.mobile_devices import mobile_devices_bp
    from routes.operations import operations_bp
    from routes.sim_management import sim_management_bp
    from routes.device_management import device_management_bp
    from routes.device_assignment import device_assignment_bp
    from routes.accounting import accounting_bp
    from routes.accounting_extended import accounting_ext_bp
    from routes.accounting.profitability_routes import profitability_bp, contracts_bp
    from routes.analytics_simple import analytics_simple_bp
    from modules.vehicles.presentation.web.vehicle_operations import vehicle_operations_bp
    from routes.integrated_simple import integrated_bp
    from routes.ai_services_simple import ai_services_bp
    from routes.email_queue import email_queue_bp
    from routes.voicehub import voicehub_bp
    from routes.properties import properties_bp
    from routes.api_external import api_external_bp
    from routes.geofences import geofences_bp
    from routes.google_drive_settings import google_drive_settings_bp
    from routes.employee_requests import employee_requests
    from routes.api_external_safety import api_external_safety

    from modules.employees.presentation.api.v1.auth_routes import auth_api_v1
    from modules.employees.presentation.api.v1.notification_routes import notifications_api_v1
    from modules.employees.presentation.api.v1.vehicle_requests_routes import vehicle_api_v1
    from modules.employees.presentation.api.v1.financial_requests_routes import financial_api_v1
    from modules.employees.presentation.api.v1.core_requests_routes import core_requests_api_v1

    
    documents_api_v2_bp = None
    try:
        from api.v2.documents_api import documents_api_v2_bp as _documents_api_v2_bp
        documents_api_v2_bp = _documents_api_v2_bp
    except ImportError:
        try:
            import importlib.util
            from pathlib import Path

            module_path = Path(__file__).resolve().parent.parent / 'api' / 'v2' / 'documents_api.py'
            spec = importlib.util.spec_from_file_location('nuzm_app_documents_api_v2', module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                documents_api_v2_bp = module.documents_api_v2_bp
        except Exception:
            documents_api_v2_bp = None
            
    from routes.drive_browser import drive_browser_bp
    from routes.attendance_api import attendance_api_bp
    from routes.api_accident_reports import api_accident_reports
    from routes.leave_management import leave_bp
    from routes.payroll_management import payroll_bp
    from routes.documents_controller import documents_refactored_bp
    from routes.api_documents_v2 import api_documents_v2_bp
    from routes.core_system_routes import core_system_bp

    # تعطيل حماية CSRF لطرق معينة
    csrf.exempt(voicehub_bp)
    csrf.exempt(auth_bp)

    csrf.exempt(api_external_bp)  # API خارجي بدون CSRF

    csrf.exempt(auth_api_v1)  # API مصادقة الموظفين
    csrf.exempt(notifications_api_v1)  # API إشعارات الموظفين
    csrf.exempt(vehicle_api_v1)  # API طلبات المركبات للموظفين
    csrf.exempt(financial_api_v1)  # API الطلبات المالية للموظفين
    csrf.exempt(core_requests_api_v1)  # API الطلبات الإدارية للموظفين

    csrf.exempt(api_external_safety)  # API فحص السلامة الخارجية
    csrf.exempt(api_accident_reports)  # API تقارير الحوادث
    csrf.exempt(attendance_api_bp)  # API الحضور بدون CSRF
    if documents_api_v2_bp is not None:
        csrf.exempt(documents_api_v2_bp)  # API v2 المستندات بدون CSRF
        
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(documents_refactored_bp)
    app.register_blueprint(api_documents_v2_bp)
    app.register_blueprint(core_system_bp)
    app.register_blueprint(employees_bp, url_prefix='/employees')
    app.register_blueprint(departments_bp, url_prefix='/departments')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(salaries_bp, url_prefix='/salaries')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(get_vehicles_blueprint(), url_prefix='/vehicles')
    app.register_blueprint(fees_costs_bp, url_prefix='/fees-costs')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(enhanced_reports_bp, url_prefix='/enhanced-reports')
    app.register_blueprint(mobile_bp, url_prefix='/mobile')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(mass_attendance_bp, url_prefix='/mass-attendance')
    app.register_blueprint(attendance_dashboard_bp, url_prefix='/attendance-dashboard')
    app.register_blueprint(e_invoicing_bp, url_prefix="/e-invoicing")
    app.register_blueprint(workshop_reports_bp, url_prefix='/workshop-reports')
    app.register_blueprint(employee_portal_bp, url_prefix='/employee-portal')
    app.register_blueprint(insights_bp, url_prefix='/insights')
    app.register_blueprint(external_safety_bp, url_prefix='/external-safety')
    app.register_blueprint(mobile_devices_bp, url_prefix='/mobile-devices')
    app.register_blueprint(operations_bp, url_prefix='/operations')
    app.register_blueprint(sim_management_bp, url_prefix='/sim-management')
    app.register_blueprint(device_management_bp, url_prefix='/device-management')
    app.register_blueprint(device_assignment_bp, url_prefix='/device-assignment')
    app.register_blueprint(vehicle_operations_bp, url_prefix='/vehicle-operations')
    app.register_blueprint(accounting_bp, url_prefix="/accounting")
    # Prevent collision: register extended accounting under a separate prefix
    app.register_blueprint(accounting_ext_bp, url_prefix="/accounting-ext")
    app.register_blueprint(profitability_bp)
    app.register_blueprint(contracts_bp)
    app.register_blueprint(analytics_simple_bp)
    app.register_blueprint(integrated_bp, url_prefix='/integrated')
    app.register_blueprint(voicehub_bp, url_prefix="/voicehub")
    app.register_blueprint(ai_services_bp, url_prefix='/ai')
    app.register_blueprint(email_queue_bp)
    app.register_blueprint(api_external_bp)  # API خارجي لتتبع المواقع (محسّن للأداء)
    app.register_blueprint(properties_bp, url_prefix='/properties')
    app.register_blueprint(google_drive_settings_bp)  # إعدادات Google Drive
    app.register_blueprint(geofences_bp)  # الدوائر الجغرافية

    # Analytics & Business Intelligence Blueprint
    from routes.analytics import analytics_bp
    app.register_blueprint(analytics_bp)
    # Fallback analytics routes if blueprint endpoints are missing
    if "analytics.dashboard" not in app.view_functions:
        @login_required
        def _analytics_dashboard_fallback():
            if hasattr(current_user, "is_admin") and not current_user.is_admin:
                return render_template("pages/error.html", code=403, message="غير مصرح"), 403
            return render_template(
                "analytics/dashboard.html",
                kpis={},
                page_title="Analytics & Business Intelligence",
            )

        app.add_url_rule(
            "/analytics/dashboard",
            "analytics.dashboard",
            _analytics_dashboard_fallback,
        )

    if "analytics.dimensions_dashboard" not in app.view_functions:
        @login_required
        def _analytics_dimensions_fallback():
            if hasattr(current_user, "is_admin") and not current_user.is_admin:
                return render_template("pages/error.html", code=403, message="غير مصرح"), 403
            return render_template(
                "analytics/dimensions.html",
                page_title="Dimensions Studio",
            )

        app.add_url_rule(
            "/analytics/dimensions",
            "analytics.dimensions_dashboard",
            _analytics_dimensions_fallback,
        )
        
    app.register_blueprint(employee_requests)  # طلبات الموظفين

    app.register_blueprint(auth_api_v1)  # API مصادقة الموظفين
    app.register_blueprint(notifications_api_v1)  # API إشعارات الموظفين
    app.register_blueprint(vehicle_api_v1)  # API طلبات المركبات للموظفين
    app.register_blueprint(financial_api_v1)  # API الطلبات المالية للموظفين
    app.register_blueprint(core_requests_api_v1)  # API الطلبات الإدارية للموظفين

    if documents_api_v2_bp is not None:
        app.register_blueprint(documents_api_v2_bp)  # API v2 المستندات
    app.register_blueprint(api_external_safety)  # API فحص السلامة الخارجية
    app.register_blueprint(drive_browser_bp, url_prefix='/drive')  # مستعرض Google Drive
    app.register_blueprint(attendance_api_bp)  # API الحضور
    app.register_blueprint(api_accident_reports)  # API تقارير حوادث السيارات
    app.register_blueprint(payroll_bp, url_prefix='/payroll')
    app.register_blueprint(leave_bp, url_prefix='/leaves')

    # استيراد وتسجيل مسار صفحة الهبوط - مسار منفصل عن النظام
    from routes.landing import landing_bp
    app.register_blueprint(landing_bp)

    # استيراد وتسجيل لوحة التحكم الإدارية
    from routes.admin_dashboard import admin_dashboard_bp
    app.register_blueprint(admin_dashboard_bp, url_prefix='/admin')

    # استيراد وتسجيل إدارة صفحة الهبوط
    from routes.landing_admin import landing_admin_bp
    app.register_blueprint(landing_admin_bp, url_prefix='/landing-admin')

    # استيراد وتسجيل نظام الإشعارات
    from routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)

    # Power BI Dashboard
    from routes.powerbi_dashboard import powerbi_bp
    app.register_blueprint(powerbi_bp)

    # Auto-register any remaining blueprints from the 12-category structure
    from routes import register_routes
    register_routes(app)
