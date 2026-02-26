"""
مسارات API — استخدام shared.utils.responses لردود JSON موحدة.
لا يتجاوز 400 سطر.
"""
from flask import Blueprint
from shared.utils.responses import json_success

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health():
    """فحص صحة الخدمة."""
    return json_success(data={"status": "ok", "service": "nuzm"})
