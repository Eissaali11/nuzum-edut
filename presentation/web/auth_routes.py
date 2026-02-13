"""
مسارات المصادقة للنواة الجديدة — لا تعتمد على app.py.
لا يتجاوز 400 سطر.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """تسجيل الدخول بالبريد وكلمة المرور."""
    if current_user.is_authenticated:
        return redirect(url_for("root"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        if not email or not password:
            flash("الرجاء إدخال البريد الإلكتروني وكلمة المرور", "danger")
            return redirect(url_for("auth.login"))

        try:
            from email_validator import validate_email, EmailNotValidError
            email = validate_email(email).email
        except Exception:
            flash("البريد الإلكتروني غير صالح", "danger")
            return redirect(url_for("auth.login"))

        from core.extensions import db
        from models import User

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("البريد الإلكتروني أو كلمة المرور غير صحيحة", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        flash("تم تسجيل الدخول بنجاح", "success")
        return redirect(url_for("root"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    """تسجيل الخروج."""
    logout_user()
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("web.index"))
