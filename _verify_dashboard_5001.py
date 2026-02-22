"""
اختبار dashboard على المنفذ 5001 بعد الإصلاحات
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# استيراد app
import importlib.util
spec = importlib.util.spec_from_file_location('app_module', 'app.py')
app_module = importlib.util.module_from_spec(spec)
sys.modules['app_real'] = app_module
spec.loader.exec_module(app_module)

app = app_module.app

print("=" * 60)
print("اختبار Dashboard على المنفذ 5001")
print("=" * 60)

# اختبار 1: التحقق من قاعدة البيانات
print("\n1️⃣ فحص قاعدة البيانات...")
with app.app_context():
    try:
        from models import Employee, User
        employee_count = Employee.query.count()
        user_count = User.query.count()
        print(f"   ✓ الموظفين: {employee_count}")
        print(f"   ✓ المستخدمين: {user_count}")
    except Exception as e:
        print(f"   ✗ خطأ في قاعدة البيانات: {e}")
        sys.exit(1)

# اختبار 2: اختبار dashboard بدون مصادقة (يجب أن يعيد توجيه)
print("\n2️⃣ اختبار dashboard بدون مصادقة...")
with app.test_client() as client:
    response = client.get('/dashboard/')
    if response.status_code == 302:
        print(f"   ✓ إعادة توجيه صحيحة: {response.status_code} -> {response.location}")
    else:
        print(f"   ⚠ حالة غير متوقعة: {response.status_code}")

# اختبار 3: اختبار dashboard مع مصادقة محاكاة
print("\n3️⃣ اختبار dashboard مع مصادقة...")
with app.app_context():
    with app.test_request_context('/dashboard/'):
        from flask_login import login_user
        from models import User
        
        test_user = User.query.first()
        if test_user:
            login_user(test_user)
            
            try:
                from routes.dashboard import index
                result = index()
                
                # فحص نوع النتيجة
                if hasattr(result, 'status_code'):
                    print(f"   ✓ Dashboard أعاد Response: {result.status_code}")
                elif isinstance(result, str):
                    # تحقق من وجود رسالة خطأ fallback
                    if 'تعذر تحميل بيانات' in result:
                        print(f"   ⚠ Dashboard يعرض رسالة fallback")
                    else:
                        print(f"   ✓ Dashboard rendered HTML ({len(result)} حرف)")
                else:
                    print(f"   ✓ Dashboard أعاد: {type(result).__name__}")
                    
            except Exception as e:
                print(f"   ✗ Dashboard فشل: {e}")
        else:
            print("   ⚠ لا يوجد مستخدمين في قاعدة البيانات")

# اختبار 4: اختبار الوصول HTTP الفعلي
print("\n4️⃣ اختبار HTTP على المنفذ 5001...")
try:
    import urllib.request
    req = urllib.request.Request('http://127.0.0.1:5001/dashboard/')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"   ✓ HTTP Response: {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print(f"   ✓ إعادة توجيه صحيحة: {e.code}")
        else:
            print(f"   ✗ خطأ HTTP: {e.code}")
except Exception as e:
    print(f"   ✗ فشل الاتصال: {e}")

print("\n" + "=" * 60)
print("انتهى الاختبار")
print("=" * 60)
