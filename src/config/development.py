"""
إعدادات بيئة التطوير.
"""
import os
from .base import BaseConfig, BASE_DIR


class DevelopmentConfig(BaseConfig):
    """إعدادات التطوير."""

    DEBUG = True
    ENV = "development"

    # SQLite افتراضي في التطوير
    DATABASE_PATH = BASE_DIR / "instance" / "nuzm_dev.db"
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or f"sqlite:///{DATABASE_PATH}"

    # Redis اختياري في التطوير
    REDIS_URL = os.environ.get("REDIS_URL") or None
    if not REDIS_URL:
        SESSION_TYPE = "filesystem"
