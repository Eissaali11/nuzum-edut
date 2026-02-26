"""
مسارات مصادقة الجوال — مستخرجة من routes/mobile.py.
تُسجَّل على mobile_bp عبر register_auth_routes(mobile_bp) للحفاظ على /mobile/*.
لا تغيير في عناوين المسارات أو هيكل الاستجابة (الخط beIN-Normal عند الحاجة).
"""
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

from src.application.auth.services import verify_credentials, record_login


class LoginForm(FlaskForm):
    """نموذج تسجيل الدخول للجوال (اسم المستخدم أو البريد + كلمة المرور)."""
    username = StringField("اسم المستخدم", validators=[DataRequired("اسم المستخدم مطلوب")])
    password = PasswordField("كلمة المرور", validators=[DataRequired("كلمة المرور مطلوبة")])
    remember = BooleanField("تذكرني")
    submit = SubmitField("تسجيل الدخول")


def register_auth_routes(mobile_bp):
    """تسجيل مسارات المصادقة على الـ blueprint المزوّد (نفس نمط vehicles)."""
    # تسجيل الدخول
    @mobile_bp.route("/login", methods=["GET", "POST"])
    def login():
        """صفحة تسجيل الدخول للنسخة المحمولة"""
        if current_user.is_authenticated:
            return redirect(url_for("mobile.index"))

        form = LoginForm()

        if form.validate_on_submit():
            user, error = verify_credentials(form.username.data, form.password.data)
            if user:
                login_user(user, remember=form.remember.data)
                record_login(user)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("mobile.index"))
            flash(error or "اسم المستخدم أو كلمة المرور غير صحيحة", "danger")

        return render_template("mobile/login.html", form=form)

    # تسجيل الخروج
    @mobile_bp.route("/logout")
    @login_required
    def logout():
        """تسجيل الخروج من النسخة المحمولة"""
        logout_user()
        return redirect(url_for("mobile.login"))

    # نسيت كلمة المرور
    @mobile_bp.route("/forgot-password")
    def forgot_password():
        """صفحة نسيت كلمة المرور للنسخة المحمولة"""
        return render_template("mobile/forgot_password.html")

    # الملف الشخصي
    @mobile_bp.route("/profile")
    @login_required
    def profile():
        """صفحة الملف الشخصي للنسخة المحمولة"""
        return render_template("mobile/profile.html")

    # تغيير كلمة المرور
    @mobile_bp.route("/change-password", methods=["GET", "POST"])
    @login_required
    def change_password():
        """صفحة تغيير كلمة المرور للنسخة المحمولة"""
        return render_template("mobile/change_password.html")
