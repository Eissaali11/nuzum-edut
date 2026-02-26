"""
سكريبت لإنشاء مستخدم مدير للدخول إلى النظام
Create Admin User Script
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# تأكد من أن app متاح في sys.modules عند التشغيل كـ __main__
if __name__ == "__main__":
    sys.modules.setdefault("app", sys.modules[__name__])

from src.app import app, db
from models import User, UserRole

def create_admin_user():
    """إنشاء مستخدم مدير جديد"""
    with app.app_context():
        print("=" * 50)
        print("إنشاء مستخدم مدير جديد")
        print("Create New Admin User")
        print("=" * 50)
        
        # بيانات المدير الافتراضية
        username = input("\nاسم المستخدم (Username) [admin]: ").strip() or "admin"
        password = input("كلمة المرور (Password) [admin123]: ").strip() or "admin123"
        email = input("البريد الإلكتروني (Email) [admin@nuzum.com]: ").strip() or "admin@nuzum.com"
        name = input("الاسم الكامل (Full Name) [مدير النظام]: ").strip() or "مدير النظام"
        
        # التحقق من وجود المستخدم
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"\n⚠️  المستخدم '{username}' موجود بالفعل!")
            overwrite = input("هل تريد تحديث كلمة المرور؟ (y/n): ").strip().lower()
            if overwrite == 'y':
                existing_user.set_password(password)
                existing_user.role = UserRole.ADMIN
                existing_user.email = email
                existing_user.name = name
                db.session.commit()
                print("\n✅ تم تحديث بيانات المستخدم بنجاح!")
            else:
                print("\n❌ تم الإلغاء")
            return
        
        # إنشاء مستخدم جديد
        try:
            new_admin = User(
                username=username,
                email=email,
                name=name,
                role=UserRole.ADMIN,
                is_active=True
            )
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            
            print("\n" + "=" * 50)
            print("✅ تم إنشاء المستخدم المدير بنجاح!")
            print("=" * 50)
            print(f"\n📋 بيانات تسجيل الدخول (استخدم البريد وكلمة المرور):")
            print(f"   البريد الإلكتروني: {email}")
            print(f"   كلمة المرور: {password}")
            print(f"   الصلاحية: مدير النظام (ADMIN)")
            print("\n🌐 رابط تسجيل الدخول:")
            print("   http://127.0.0.1:5000/auth/login")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ خطأ في إنشاء المستخدم: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_admin_user()
