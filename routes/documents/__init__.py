"""
قسم الوثائق (Documents) - إدارة الوثائق
═══════════════════════════════════════════════════════════════════════════

يضم:
- إدارة الوثائق الأساسية (Documents)
- واجهة التحكم بالوثائق (Documents Controller)

═══════════════════════════════════════════════════════════════════════════
"""

documents_blueprints = []

try:
    from .documents import documents_bp
    documents_blueprints.append(documents_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد documents: {e}")

try:
    from .documents_controller import documents_refactored_bp
    documents_blueprints.append(documents_refactored_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد documents_controller: {e}")

__all__ = [
    'documents_blueprints'
]
