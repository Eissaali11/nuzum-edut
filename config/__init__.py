"""
إعدادات التطبيق حسب البيئة.
لا يتجاوز أي ملف في هذا المجلد 400 سطر (قاعدة المشروع).
"""
from .base import BaseConfig
from .development import DevelopmentConfig
from .production import ProductionConfig

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
