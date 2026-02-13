"""
الوحدات الأساسية للنظام
"""
from .extensions import db, login_manager

# استيراد create_app عند الطلب لتجنب تحميل config عند استيراد db فقط
def __getattr__(name):
    if name == 'create_app':
        from .app_factory import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['create_app', 'db', 'login_manager']