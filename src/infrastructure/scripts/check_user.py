"""
فحص المستخدمين في قاعدة البيانات
Check Users in Database
"""
import sys
import os
# تشغيل من جذر المشروع
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.app import app, db
from models import User
from werkzeug.security import check_password_hash

print("=" * 60)
print("فحص المستخدمين في قاعدة البيانات")
print("=" * 60)

with app.app_context():
    users = User.query.all()
    
    if not users:
        print("\n❌ لا يوجد مستخدمين في قاعدة البيانات!")
        print("\nقم بتشغيل: python quick_reset.py")
    else:
        print(f"\n✓ عدد المستخدمين: {len(users)}\n")
        
        for user in users:
            print("-" * 60)
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"Name: {user.name}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
            print(f"Has Password Hash: {'Yes' if user.password_hash else 'No'}")
            
            # اختبار كلمة المرور
            if user.password_hash:
                test_password = "admin123"
                is_valid = check_password_hash(user.password_hash, test_password)
                print(f"Password 'admin123' valid: {'✓ Yes' if is_valid else '✗ No'}")
            
            print("-" * 60)
        
        print("\nإذا كانت البيانات صحيحة، جرّب تسجيل الدخول على:")
        print("http://127.0.0.1:5000/auth/login")
        print(f"\nEmail: {users[0].email}")
        print("Password: admin123")

print("\n" + "=" * 60)
