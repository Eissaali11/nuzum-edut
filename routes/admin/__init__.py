"""
قسم الإدارة (Admin) - لوحات التحكم والإدارة
═══════════════════════════════════════════════════════════════════════════

يضم:
- لوحة معلومات الإدارة (Admin Dashboard)
- إدارة الرواتب (Payroll Management)
- إدارة الرواتب الإدارية (Payroll Admin)

═══════════════════════════════════════════════════════════════════════════
"""

admin_blueprints = []

try:
    from .admin_dashboard import admin_dashboard_bp
    admin_blueprints.append(admin_dashboard_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد admin_dashboard: {e}")

try:
    from .payroll_management import payroll_bp
    admin_blueprints.append(payroll_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد payroll_management: {e}")

try:
    from .payroll_admin import payroll_bp
    admin_blueprints.append(payroll_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد payroll_admin: {e}")

__all__ = [
    'admin_blueprints'
]
