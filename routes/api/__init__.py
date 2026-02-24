"""
قسم واجهات API (API) - نقاط نهاية API الخارجية
═══════════════════════════════════════════════════════════════════════════

يضم:
- API الأساسية (API Core)
- API تقارير الحوادث (Accident Reports API)
- API الحضور v2 (Attendance API v2)
- API الوثائق v2 (Documents API v2)
- API الخارجية (External API)
- API السلامة الخارجية (External Safety API)
- API طلبات الموظفين (Employee Requests API)

═══════════════════════════════════════════════════════════════════════════
"""

from importlib import import_module

api_blueprints = []

modules = [
    ('api', 'api_bp'),
    ('api_accident_reports', 'api_accident_reports_bp'),
    ('api_attendance_v2', 'api_attendance_v2_bp'),
    ('api_documents_v2', 'api_documents_v2_bp'),
    ('api_external', 'api_external_bp'),
    ('api_external_safety', 'api_external_safety_bp'),
    ('api_external_safety_v2', 'api_external_safety_v2_bp'),
]

for module_name, bp_name in modules:
    try:
        module = import_module(f'.{module_name}', package=__name__)
        if hasattr(module, bp_name):
            api_blueprints.append(getattr(module, bp_name))
    except ImportError as e:
        print(f"⚠️ تحذير: خطأ عند استيراد {module_name}: {e}")

# توافق رجعي: إتاحة api_bp مباشرة من الحزمة
try:
    from .api import api_bp
except ImportError:
    api_bp = None

__all__ = [
    'api_blueprints',
    'api_bp'
]
