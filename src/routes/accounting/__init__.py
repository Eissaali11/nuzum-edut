"""
قسم المحاسبة (Accounting) - المحاسبة والفواتير
═══════════════════════════════════════════════════════════════════════════

يضم:
- المحاسبة الأساسية (Accounting)
- تحليلات المحاسبة (Accounting Analytics)
- محاسبة متقدمة (Accounting Extended)
- الفواتير الإلكترونية (E-Invoicing)
- الرسوم والتكاليف (Fees & Costs)

═══════════════════════════════════════════════════════════════════════════
"""

from importlib import import_module

accounting_blueprints = []

modules = [
    ('accounting', 'accounting_bp'),
    ('accounting_analytics', 'accounting_analytics_bp'),
    ('accounting_extended', 'accounting_extended_bp'),
    ('e_invoicing', 'e_invoicing_bp'),
    ('fees_costs', 'fees_costs_bp'),
]

for module_name, bp_name in modules:
    try:
        module = import_module(f'.{module_name}', package=__name__)
        if hasattr(module, bp_name):
            accounting_blueprints.append(getattr(module, bp_name))
    except ImportError as e:
        print(f"⚠️ تحذير: خطأ عند استيراد {module_name}: {e}")

# توافق رجعي: إتاحة accounting_bp مباشرة من الحزمة
try:
    from .accounting import accounting_bp
except ImportError:
    accounting_bp = None

__all__ = [
    'accounting_blueprints',
    'accounting_bp'
]
