"""
نقطة الدخول لـ WSGI (Gunicorn / uWSGI).
"""
import os
from core.app_factory import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))
