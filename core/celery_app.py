"""
تهيئة Celery للعمليات الثقيلة (تقارير PDF/Excel، واتساب).
يُستدعى من worker: celery -A core.celery_app worker --loglevel=info
لا يتجاوز 400 سطر.
"""
import os
from celery import Celery

def make_celery():
    broker = os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/1"
    celery_app = Celery(
        "nuzm",
        broker=broker,
        backend=broker.replace("/1", "/2"),
        include=[],  # أضف هنا: "application.tasks.reports", "application.tasks.notifications"
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Riyadh",
        enable_utc=True,
    )
    return celery_app

celery_app = make_celery()
