"""
مسارات واجهة الويب الجديدة (لا تتجاوز 400 سطر).
جميع الصفحات تمتد من layout/base.html.
"""
from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    """الصفحة الرئيسية للهيكل الجديد."""
    return render_template("pages/home.html")
