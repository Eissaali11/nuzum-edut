"""
إعدادات بيئة الإنتاج (تحمل 10,000+ مستخدم).
"""
import os
from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """إعدادات الإنتاج."""

    DEBUG = False
    ENV = "production"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or ""

    # Connection pool لـ PostgreSQL/MySQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    SESSION_TYPE = "redis"
    CACHE_TYPE = "RedisCache"
