"""
قسم الاتصالات (Communications) - الإخطارات والبريد الإلكتروني
═══════════════════════════════════════════════════════════════════════════

يضم:
- نظام الإخطارات (Notifications)
- نظام طابور البريد الإلكتروني (Email Queue)

═══════════════════════════════════════════════════════════════════════════
"""

communications_blueprints = []

try:
    from .notifications import notifications_bp
    communications_blueprints.append(notifications_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد notifications: {e}")

try:
    from .email_queue import email_queue_bp
    communications_blueprints.append(email_queue_bp)
except ImportError as e:
    print(f"⚠️ تحذير: خطأ عند استيراد email_queue: {e}")

__all__ = [
    'communications_blueprints'
]
