"""
قسم التحليلات (Analytics) - التقارير والمحتويات التحليلية
═══════════════════════════════════════════════════════════════════════════

يضم:
- التحليلات الأساسية (Analytics)
- التحليلات المباشرة (Direct Analytics)
- التحليلات الفعلية (Real Analytics)
- التحليلات المبسطة (Simple Analytics)
- التقارير المحسّنة (Enhanced Reports)
- البصائر والرؤى (Insights)
- نظام Power BI المتقدم (Power BI Dashboard - متقدم)

═══════════════════════════════════════════════════════════════════════════
"""

from importlib import import_module

analytics_blueprints = []

modules = [
    ('analytics', 'analytics_bp'),
    ('analytics_direct', 'analytics_direct_bp'),
    ('analytics_real', 'analytics_real_bp'),
    ('analytics_simple', 'analytics_simple_bp'),
    ('enhanced_reports', 'enhanced_reports_bp'),
    ('insights', 'insights_bp'),
]

for module_name, bp_name in modules:
    try:
        module = import_module(f'.{module_name}', package=__name__)
        if hasattr(module, bp_name):
            analytics_blueprints.append(getattr(module, bp_name))
    except ImportError as e:
        print(f"⚠️ تحذير: خطأ عند استيراد {module_name}: {e}")

# نظام Power BI المتقدم
try:
    from ..powerbi_dashboard import powerbi_bp
    analytics_blueprints.append(powerbi_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد powerbi_dashboard: {e}")

# نظام التقارير المتقدم
try:
    from ..reports_mgmt import reports_bp
    analytics_blueprints.append(reports_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد reports_mgmt: {e}")

# توافق رجعي: إتاحة analytics_bp مباشرة من الحزمة
try:
    from .analytics import analytics_bp
except ImportError:
    analytics_bp = None

__all__ = [
    'analytics_blueprints',
    'analytics_bp'
]
