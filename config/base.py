"""
إعدادات أساسية مشتركة بين جميع البيئات.
"""
import os
from pathlib import Path

# جذر المشروع
BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    """الإعدادات الأساسية المشتركة."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("SESSION_SECRET")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # الحد الأقصى لرفع الملفات (500 MB)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024

    # مسارات القوالب والملفات الثابتة (الهيكل الجديد)
    PRESENTATION_TEMPLATES = str(BASE_DIR / "presentation" / "web" / "templates")
    PRESENTATION_STATIC = str(BASE_DIR / "presentation" / "web" / "static")

    # Redis (للـ Caching و Session)
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/1"

    # Session: استخدام Redis في الإنتاج
    SESSION_TYPE = "redis" if os.environ.get("REDIS_URL") else "filesystem"

    # دعم RTL واللغة
    RTL = True
    DEFAULT_LOCALE = "ar"

    # Firebase (اختياري — لتسجيل الدخول بـ Google)
    FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY") or ""
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID") or ""
    FIREBASE_APP_ID = os.environ.get("FIREBASE_APP_ID") or ""

    @staticmethod
    def init_app(app):
        """تهيئة اختيارية للتطبيق."""
        pass
