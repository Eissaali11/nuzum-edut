"""
سكريبت سريع لحذف قاعدة البيانات وإنشاء حساب مدير
Quick script to reset database and create admin
"""
import os
import sys
import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# تأكد من أن app متاح في sys.modules
if __name__ == "__main__":
    sys.modules.setdefault("app", sys.modules[__name__])

print("=" * 60)
print("إعادة تهيئة قاعدة البيانات")
print("Database Reset")
print("=" * 60)

# 1. البحث عن وحذف جميع ملفات .db
print("\n1. حذف قواعد البيانات القديمة...")
db_patterns = [
    "*.db",
    "*.db-shm", 
    "*.db-wal",
    "database/*.db*",
    "instance/*.db*"
]

deleted_count = 0
for pattern in db_patterns:
    for db_file in glob.glob(pattern):
        try:
            os.remove(db_file)
            print(f"   ✓ حذف: {db_file}")
            deleted_count += 1
        except Exception as e:
            print(f"   ⚠ لم يمكن حذف {db_file}: {e}")

if deleted_count == 0:
    print("   لم يتم العثور على ملفات قديمة")

# 2. إنشاء الجداول من الموديلات
print("\n2. إنشاء جداول قاعدة البيانات...")
from src.app import app, db

with app.app_context():
    try:
        db.create_all()
        print("   ✓ تم إنشاء جميع الجداول بنجاح")
    except Exception as e:
        print(f"   ✗ خطأ في إنشاء الجداول: {e}")
        sys.exit(1)

# 3. إنشاء مستخدم مدير
print("\n3. إنشاء حساب المدير...")
print("-" * 60)

from models import User, UserRole

with app.app_context():
    # بيانات افتراضية
    default_username = "admin"
    default_password = "admin123"
    default_email = "admin@nuzum.com"
    default_name = "مدير النظام"
    
    print(f"\nاستخدام البيانات الافتراضية:")
    print(f"  Username: {default_username}")
    print(f"  Password: {default_password}")
    print(f"  Email: {default_email}")
    print(f"  Name: {default_name}")
    print()
    
    use_defaults = input("استخدام البيانات أعلاه؟ (Enter للموافقة / n للتخصيص): ").strip().lower()
    
    if use_defaults == 'n':
        username = input(f"اسم المستخدم [{default_username}]: ").strip() or default_username
        password = input(f"كلمة المرور [{default_password}]: ").strip() or default_password
        email = input(f"البريد [{default_email}]: ").strip() or default_email
        name = input(f"الاسم [{default_name}]: ").strip() or default_name
    else:
        username = default_username
        password = default_password
        email = default_email
        name = default_name
    
    # إنشاء المستخدم (يجب استخدام set_password لتعيين password_hash)
    try:
        admin_user = User(
            username=username,
            email=email,
            name=name,
            role=UserRole.ADMIN,
            is_active=True
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("✅ تم إنشاء حساب المدير بنجاح!")
        print("=" * 60)
        print(f"\n📋 بيانات تسجيل الدخول (استخدم البريد وكلمة المرور):")
        print(f"   البريد الإلكتروني (Email): {email}")
        print(f"   كلمة المرور (Password): {password}")
        print(f"\n🌐 رابط الدخول:")
        print(f"   http://127.0.0.1:5000/auth/login")
        print("\n" + "=" * 60)
        print("\nالآن شغّل المشروع بالأمر:")
        print("   python app.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ خطأ في إنشاء المستخدم: {e}")
        db.session.rollback()
        sys.exit(1)
