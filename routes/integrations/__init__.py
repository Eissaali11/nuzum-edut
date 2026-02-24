"""
قسم التكاملات الخارجية (Integrations) - الخدمات والأنظمة الخارجية
═══════════════════════════════════════════════════════════════════════════

يضم:
- تكامل VoiceHub (VoiceHub Integration)
- تكامل جوجل درايف (Google Drive Integration)
- متصفح جوجل درايف (Google Drive Browser)
- السلامة الخارجية (External Safety)
- الأسيجة الجغرافية (Geofences)

═══════════════════════════════════════════════════════════════════════════
"""

from importlib import import_module

integrations_blueprints = []

modules = [
    ('voicehub', 'voicehub_bp'),
    ('google_drive_settings', 'google_drive_settings_bp'),
    ('drive_browser', 'drive_browser_bp'),
    ('external_safety', 'external_safety_bp'),
    ('external_safety_refactored', 'external_safety_bp'),
    ('geofences', 'geofences_bp'),
]

for module_name, bp_name in modules:
    try:
        module = import_module(f'.{module_name}', package=__name__)
        if hasattr(module, bp_name):
            integrations_blueprints.append(getattr(module, bp_name))
    except ImportError as e:
        print(f"⚠️ تحذير: خطأ عند استيراد {module_name}: {e}")

__all__ = [
    'integrations_blueprints'
]
