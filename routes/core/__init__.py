"""
قسم النواة (Core) - المسارات الأساسية
═══════════════════════════════════════════════════════════════════════════

يضم:
- المصادقة والتحقق من الهوية (Authentication)
- إدارة المستخدمين (User Management)
- لوحة القيادة الرئيسية (Main Dashboard)
- صفحات الهبوط (Landing Pages)

═══════════════════════════════════════════════════════════════════════════
"""

try:
    from .auth import auth_bp
    core_blueprints = [auth_bp]
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد auth: {e}")
    core_blueprints = []

try:
    from .users import users_bp
    core_blueprints.append(users_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد users: {e}")

try:
    from .dashboard import dashboard_bp
    core_blueprints.append(dashboard_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد dashboard: {e}")

try:
    from .landing import landing_bp
    core_blueprints.append(landing_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد landing: {e}")

try:
    from .landing_admin import landing_admin_bp
    core_blueprints.append(landing_admin_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد landing_admin: {e}")

__all__ = [
    'auth_bp',
    'users_bp', 
    'dashboard_bp',
    'landing_bp',
    'landing_admin_bp',
    'core_blueprints'
]
