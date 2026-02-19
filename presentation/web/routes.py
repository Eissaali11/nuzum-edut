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


@web_bp.route("/about")
def about():
    """صفحة من نحن."""
    return render_template("about.html")


@web_bp.route("/privacy")
def privacy():
    """صفحة سياسة الخصوصية."""
    return render_template("privacy.html")


@web_bp.route("/contact")
def contact():
    """صفحة اتصل بنا."""
    return render_template("contact.html")
