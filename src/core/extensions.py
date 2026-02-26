"""
ملحقات Flask المشتركة: DB, Login, Migrate, CORS.
لا يتجاوز 400 سطر.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()
cors = CORS()
csrf = CSRFProtect()


def init_extensions(app):
    """تهيئة جميع الملحقات مع التطبيق."""
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            from models import User
            return User.query.get(int(user_id))
        except Exception:
            return None

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        from flask import flash, redirect, url_for
        flash("يجب تسجيل الدخول أولاً", "warning")
        try:
            return redirect(url_for("auth.login"))
        except Exception:
            return redirect("/auth/login")
