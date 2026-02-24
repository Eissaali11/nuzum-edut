"""
قسم الطلبات (Requests) - الطلبات والشؤون الإدارية
═══════════════════════════════════════════════════════════════════════════

يضم:
- طلبات الموظفين الأساسية (Employee Requests)
- واجهة التحكم بالطلبات (Requests Controller)
- API الطلبات (API Requests)

═══════════════════════════════════════════════════════════════════════════
"""

requests_blueprints = []

try:
    from .employee_requests import employee_requests_bp
    requests_blueprints.append(employee_requests_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد employee_requests: {e}")

try:
    from .employee_requests_controller import employee_requests_controller_bp
    requests_blueprints.append(employee_requests_controller_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد employee_requests_controller: {e}")

try:
    from .api_employee_requests import api_employee_requests_bp
    requests_blueprints.append(api_employee_requests_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد api_employee_requests: {e}")

__all__ = [
    'requests_blueprints'
]
