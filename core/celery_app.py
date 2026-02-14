"""
تهيئة Celery للعمليات الثقيلة (تقارير PDF/Excel، واتساب).
Flask app context متاح داخل المهام عبر ContextTask.
تشغيل الـ worker: celery -A core.celery_app worker --loglevel=info
لا يتجاوز 400 سطر.
"""
import os
from celery import Celery

_celery_app = Celery(
    "nuzm",
    broker=os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/1",
    backend=(os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/1").replace("/1", "/2"),
    include=[],
)
_celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Riyadh",
    enable_utc=True,
)


def _get_flask_app():
    from core.app_factory import create_app
    return create_app()


class ContextTask(_celery_app.Task):
    """مهمة Celery تعمل داخل سياق تطبيق Flask."""
    abstract = True

    def __call__(self, *args, **kwargs):
        with _get_flask_app().app_context():
            return self.run(*args, **kwargs)


_celery_app.Task = ContextTask


def init_celery(app):
    """ربط إعدادات Flask بـ Celery وحفظ المرجع على التطبيق."""
    _celery_app.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL") or _celery_app.conf.broker_url,
        result_backend=app.config.get("CELERY_RESULT_BACKEND") or _celery_app.conf.result_backend,
    )
    app.celery = _celery_app
    return _celery_app


celery_app = _celery_app
