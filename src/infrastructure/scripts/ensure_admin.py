"""
إضافة أو تحديث مستخدم المدير دون حذف القاعدة.
Add or update admin user without deleting the database.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.app import app, db
from models import User, UserRole

EMAIL = "admin@nuzum.com"
PASSWORD = "admin123"
USERNAME = "admin"
NAME = "مدير النظام"

with app.app_context():
    user = User.query.filter_by(email=EMAIL).first()
    if user:
        user.set_password(PASSWORD)
        user.role = UserRole.ADMIN
        user.is_active = True
        db.session.commit()
        print("Admin password updated. Login with:", EMAIL, "/", PASSWORD)
    else:
        user = User(
            username=USERNAME,
            email=EMAIL,
            name=NAME,
            role=UserRole.ADMIN,
            is_active=True,
        )
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
        print("Admin created. Login with:", EMAIL, "/", PASSWORD)
