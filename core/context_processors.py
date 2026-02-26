from datetime import datetime
from flask import current_app
from utils.user_helpers import get_role_display_name, get_module_display_name, format_permissions

def init_context_processors(app, csrf):
    @app.context_processor
    def inject_now():
        return {
            'now': datetime.now(),
            'firebase_api_key': app.config.get('FIREBASE_API_KEY'),
            'firebase_project_id': app.config.get('FIREBASE_PROJECT_ID'),
            'firebase_app_id': app.config.get('FIREBASE_APP_ID')
        }

    @app.context_processor
    def inject_csrf_token():
        """إضافة csrf_token إلى جميع القوالب"""
        def get_csrf_token():
            return csrf._get_csrf_token()
        return {'csrf_token': get_csrf_token}

    @app.context_processor
    def inject_permissions():
        """إضافة دوال التحقق من الصلاحيات إلى جميع القوالب"""
        from utils.permissions_service import get_permissions_context
        return get_permissions_context()

    @app.context_processor
    def inject_endpoint_helpers():
        """إضافة مساعدات endpoints للقوالب (متوافق مع layout الحديث)."""
        def endpoint_exists(endpoint):
            try:
                return endpoint in current_app.view_functions
            except Exception:
                return False
        return {'endpoint_exists': endpoint_exists}

    @app.context_processor
    def inject_global_template_vars():
        from models import Module, UserRole, Permission
        return {
            'get_role_display_name': get_role_display_name,
            'get_module_display_name': get_module_display_name,
            'format_permissions': format_permissions,
            'Module': Module,
            'UserRole': UserRole,
            'Permission': Permission
        }
