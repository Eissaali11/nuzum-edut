"""
مصنع التطبيق (Factory Pattern) — نواة نُظم.
تهيئة SQLAlchemy, Migrate, LoginManager, CORS وربط المجلدات.
لا يتجاوز 400 سطر (قاعدة المشروع).
استخدم shared.utils.responses لردود JSON الموحدة.
"""
import os
from pathlib import Path

from flask import Flask, Blueprint
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent.parent

# مجلد الملفات الثابتة في الجذر (قوالب الجوال والويب القديم)
ROOT_STATIC_DIR = str(BASE_DIR / "static")


def create_app(config_name=None):
    """إنشاء تطبيق Flask (Factory Pattern)."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    from config import config
    cfg = config.get(config_name) or config["default"]

    # مسارات العرض الجديد (presentation/web)
    templates_dir = str(BASE_DIR / "presentation" / "web" / "templates")
    # خدمة static من الجذر لدعم القوالب القديمة والجديدة معاً
    static_dir = ROOT_STATIC_DIR

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir,
        static_url_path="/static",
    )
    # بحث القوالب في مجلدين: النواة الجديدة أولاً ثم قوالب المسارات القديمة
    root_templates = str(BASE_DIR / "templates")
    from jinja2 import ChoiceLoader, FileSystemLoader
    module_employees_templates = str(BASE_DIR / "modules" / "employees" / "templates")
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(templates_dir),
        FileSystemLoader(module_employees_templates),
        FileSystemLoader(root_templates),
    ])
    app.config.from_object(cfg)
    if hasattr(cfg, "init_app") and cfg.init_app:
        cfg.init_app(app)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # خدمة ملفات الجوال من مجلد الجذر static/ (mobile/*) لظهور التصميم بشكل سليم
    _register_legacy_static(app)

    _init_extensions(app)
    _init_redis(app)
    _init_celery(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_template_filters(app)
    _register_context_processors(app)

    return app


def _register_legacy_static(app):
    """خدمة ملفات الجوال من مجلد الجذر static/ لظهور التصميم بشكل سليم."""
    if not os.path.isdir(ROOT_STATIC_DIR):
        return
    legacy_static_bp = Blueprint(
        "legacy_static",
        __name__,
        static_folder=ROOT_STATIC_DIR,
        static_url_path="",
    )
    app.register_blueprint(legacy_static_bp, url_prefix="/legacy-static")


def _init_extensions(app):
    """تهيئة الملحقات (DB, Login, CSRF, Migrate)."""
    from core.extensions import init_extensions
    init_extensions(app)
    # تسجيل نماذج النطاقات مع SQLAlchemy (يجب استيرادها بعد تهيئة db)
    # ملاحظة: domain.* مكررة - models.py الرئيسي يستوردها من modules
    # import domain.employees.models  # noqa: F401
    # import domain.vehicles.models  # noqa: F401


def _init_redis(app):
    """ربط REDIS_URL من البيئة بطبقة التخزين المؤقت (app.redis)."""
    app.redis = None
    redis_url = app.config.get("REDIS_URL")
    if redis_url:
        try:
            import redis as redis_lib
            app.redis = redis_lib.from_url(redis_url)
        except ImportError:
            pass


def _init_celery(app):
    """ربط Celery بتطبيق Flask (سياق التطبيق متاح داخل المهام)."""
    try:
        from core.celery_app import init_celery
        init_celery(app)
    except ImportError:
        app.celery = None


def _register_blueprints(app):
    """تسجيل Blueprints: ويب، API، مصادقة، الموظفين (Vertical Slice)، ثم Legacy."""
    from presentation.web.routes import web_bp
    from presentation.web.api_routes import api_bp
    from presentation.web.auth_routes import auth_bp
    from presentation.web.employees import employees_bp as employees_web_bp
    from modules.employees.presentation.web.routes import employees_bp as employees_module_bp
    from presentation.web.vehicles import vehicles_web_bp
    from modules.vehicles.presentation.web.main_routes import get_vehicles_blueprint

    vehicles_core_bp = get_vehicles_blueprint()
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(employees_web_bp)
    app.register_blueprint(employees_module_bp)
    app.register_blueprint(vehicles_core_bp, url_prefix="/vehicles")
    app.register_blueprint(vehicles_web_bp)
    _register_legacy_blueprints(app)
    if "root" not in app.view_functions:
        app.add_url_rule("/", "root", app.view_functions.get("web.index"))


def _register_legacy_blueprints(app):
    """تسجيل Blueprints القديمة من routes/ لتفعيل المسارات والقائمة الجانبية."""
    import sys
    from core.extensions import db
    # جعل "from core.extensions import db" يعمل دون تحميل app.py (لتجنب 404 عند استيراد المسارات)
    class _AppStub:
        pass
    _stub = _AppStub()
    _stub.db = db
    sys.modules["app"] = _stub

    def _reg(bp, prefix=None):
        if prefix:
            app.register_blueprint(bp, url_prefix=prefix)
        else:
            app.register_blueprint(bp)

    try:
        from routes.dashboard import dashboard_bp
        _reg(dashboard_bp, "/dashboard")
    except ImportError:
        pass
    # employees legacy routes are intentionally not registered here to avoid
    # URL conflicts with modules.employees (/employees)
    try:
        from routes.departments import departments_bp
        _reg(departments_bp, "/departments")
    except ImportError:
        pass
    try:
        from routes.attendance import attendance_bp
        _reg(attendance_bp, "/attendance")
    except ImportError:
        pass
    try:
        from routes.attendance_admin import attendance_admin_bp
        _reg(attendance_admin_bp)
    except ImportError:
        pass
    try:
        from routes.salaries import salaries_bp
        _reg(salaries_bp, "/salaries")
    except ImportError:
        pass
    try:
        from routes.accounting import accounting_bp
        _reg(accounting_bp, "/accounting")
    except ImportError:
        pass
    try:
        from routes.analytics import analytics_bp
        _reg(analytics_bp)
    except ImportError:
        pass
    try:
        from routes.reports import reports_bp
        _reg(reports_bp, "/reports")
    except ImportError:
        pass
    try:
        from routes.documents import documents_bp
        _reg(documents_bp, "/documents")
    except ImportError:
        pass
    try:
        from api.v2.documents_api import documents_api_v2_bp
        from core.extensions import csrf
        csrf.exempt(documents_api_v2_bp)
        _reg(documents_api_v2_bp)
    except ImportError:
        try:
            import importlib.util
            from pathlib import Path

            module_path = Path(__file__).resolve().parents[1] / "api" / "v2" / "documents_api.py"
            spec = importlib.util.spec_from_file_location("nuzm_api_v2_documents_api", module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                from core.extensions import csrf
                csrf.exempt(module.documents_api_v2_bp)
                _reg(module.documents_api_v2_bp)
        except Exception:
            pass
    try:
        from routes.users import users_bp
        _reg(users_bp, "/users")
    except ImportError:
        pass
    try:
        from routes.mobile import mobile_bp
        _reg(mobile_bp, "/mobile")
    except ImportError:
        pass
    try:
        from routes.notifications import notifications_bp
        app.register_blueprint(notifications_bp)
    except ImportError:
        pass
    try:
        from routes.powerbi_dashboard import powerbi_bp
        app.register_blueprint(powerbi_bp)
    except ImportError:
        pass
    try:
        from routes.employee_requests import employee_requests
        app.register_blueprint(employee_requests)
    except ImportError:
        pass
    try:
        from routes.mobile_devices import mobile_devices_bp
        _reg(mobile_devices_bp, "/mobile-devices")
    except ImportError:
        pass
    try:
        from routes.device_management import device_management_bp
        _reg(device_management_bp, "/device-management")
    except ImportError:
        pass
    try:
        from routes.sim_management import sim_management_bp
        _reg(sim_management_bp, "/sim-management")
    except ImportError:
        pass
    try:
        from routes.device_assignment import device_assignment_bp
        _reg(device_assignment_bp, "/device-assignment")
    except ImportError:
        pass
    try:
        from routes.external_safety import external_safety_bp
        _reg(external_safety_bp, "/external-safety")
    except ImportError:
        pass
    try:
        from modules.vehicles.presentation.web.vehicle_operations import vehicle_operations_bp
        _reg(vehicle_operations_bp, "/vehicle-operations")
    except ImportError:
        pass
    try:
        from routes.drive_browser import drive_browser_bp
        _reg(drive_browser_bp, "/drive")
    except ImportError:
        pass
    try:
        from routes.database_backup import database_backup_bp
        _reg(database_backup_bp, "/backup")
    except ImportError:
        pass
    try:
        from routes.operations import operations_bp
        _reg(operations_bp, "/operations")
    except ImportError:
        pass
    try:
        from routes.properties import properties_bp
        _reg(properties_bp, "/properties")
    except ImportError:
        pass
    try:
        from routes.voicehub import voicehub_bp
        _reg(voicehub_bp, "/voicehub")
    except ImportError:
        pass
    try:
        from routes.fees_costs import fees_costs_bp
        _reg(fees_costs_bp, "/fees-costs")
    except ImportError:
        pass
    try:
        from routes.payroll_management import payroll_bp
        _reg(payroll_bp, "/payroll")
    except ImportError:
        pass
    try:
        from routes.leave_management import leave_bp
        _reg(leave_bp, "/leaves")
    except ImportError:
        pass
    try:
        from presentation.api.v1 import api_v1
        app.register_blueprint(api_v1)
    except ImportError:
        pass

    # Fallback analytics routes if the legacy blueprint is unavailable
    if "analytics.dashboard" not in app.view_functions:
        from flask import render_template
        from flask_login import login_required, current_user

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
        from flask import render_template
        from flask_login import login_required, current_user

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


def _register_error_handlers(app):
    """معالجات الأخطاء العامة."""

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("pages/error.html", code=404, message="الصفحة المطلوبة غير موجودة"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        from core.extensions import db
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template("pages/error.html", code=500, message="خطأ داخلي في الخادم"), 500


def _register_template_filters(app):
    """فلاتر القوالب المشتركة."""

    @app.template_filter("format_date")
    def format_date(value, fmt="%Y-%m-%d"):
        if value is None:
            return ""
        try:
            return value.strftime(fmt)
        except Exception:
            return str(value)

    @app.template_filter("nl2br")
    def nl2br(s):
        if s is None:
            return ""
        from markupsafe import Markup
        return Markup(s.replace("\n", "<br>"))

    @app.template_filter("display_date")
    def display_date_filter(date, format="%Y-%m-%d", default="غير محدد"):
        """عرض التاريخ بشكل منسق أو نص بديل إذا كان التاريخ فارغاً."""
        if date:
            try:
                return date.strftime(format)
            except Exception:
                return str(date)
        return default

    @app.template_filter("days_remaining")
    def days_remaining_filter(date, from_date=None):
        """حساب عدد الأيام المتبقية من التاريخ المحدد حتى اليوم."""
        from datetime import date as date_type
        if date is None:
            return None
        ref = from_date or date_type.today()
        if hasattr(date, "date"):
            date = date.date()
        if hasattr(ref, "date"):
            ref = ref.date()
        try:
            return (date - ref).days
        except Exception:
            return None

    try:
        from utils.id_encoder import register_template_filters as register_id_encoder_filters
        register_id_encoder_filters(app)
    except Exception:
        pass


def _register_context_processors(app):
    """متغيرات القوالب العامة."""

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from flask import url_for, current_app
        from flask_login import current_user
        from werkzeug.routing import BuildError

        def safe_url_for(endpoint, **values):
            try:
                return url_for(endpoint, **values)
            except BuildError:
                return "#"

        def endpoint_exists(endpoint):
            try:
                return endpoint in current_app.view_functions
            except Exception:
                return False

        out = {
            "now": datetime.utcnow(),
            "current_user": current_user,
            "url_for": safe_url_for,
            "endpoint_exists": endpoint_exists,
            "legacy_static_prefix": "/legacy-static",  # لتحميل تصميم الجوال عند استخدام create_app
        }
        try:
            from models import Module, UserRole
            from utils.user_helpers import check_module_access
            def _check_module_access(user, module, permission=None):
                if not user or not user.is_authenticated:
                    return False
                from models import Permission
                return check_module_access(user, module, permission or Permission.VIEW)
            out["Module"] = Module
            out["UserRole"] = UserRole
            out["check_module_access"] = _check_module_access
        except Exception:
            pass
        return out
