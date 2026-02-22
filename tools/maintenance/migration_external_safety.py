"""
Migration Script: External Safety Legacy → Refactored
======================================================
هذا السكريبت يوضح كيفية الانتقال التدريجي من النظام القديم إلى الجديد

الخطوات:
1. تسجيل Blueprints الجديدة بـ prefix مختلف
2. اختبار Endpoints الجديدة
3. تحديث URL references في Templates
4. تعطيل Legacy code
5. إزالة Prefix المؤقت
"""

# ========================================
# Step 1: Register New Blueprints in app.py
# ========================================

# أضف هذا الكود في app.py بعد السطر الذي يستورد Legacy blueprint

"""
# ===== External Safety Module (Refactored) =====

# Legacy (keep for now as backup)
from routes.external_safety import external_safety_bp as external_safety_legacy_bp
app.register_blueprint(external_safety_legacy_bp, url_prefix='/external-safety-legacy')

# New Refactored Version (Service + Controller + API)
from routes.external_safety_refactored import external_safety_bp
from routes.api_external_safety_v2 import api_external_safety_bp

app.register_blueprint(external_safety_bp, url_prefix='/external-safety')
app.register_blueprint(api_external_safety_bp)  # /api/v2 prefix already included

print("✅ External Safety Module registered (Refactored)")
"""


# ========================================
# Step 2: Update URL References in Templates
# ========================================

# ملفات Templates التي قد تحتاج تحديث:
TEMPLATES_TO_UPDATE = [
    'templates/external_safety_check.html',
    'templates/external_safety_success.html',
    'templates/admin_external_safety_checks.html',
    'templates/admin_view_safety_check.html',
    'templates/reject_safety_check.html',
    'templates/edit_safety_check.html',
    'templates/delete_safety_check_confirm.html',
    'templates/external_safety_share_links.html',
]

# قم بالبحث عن هذه الأنماط واستبدالها:
URL_REPLACEMENTS = {
    # من
    "url_for('external_safety.admin_external_safety_checks')": 
    # إلى
    "url_for('external_safety.admin_external_safety_checks')",  # نفس الاسم - لا تغيير مطلوب!
    
    # ملاحظة: لأن اسم Blueprint لم يتغير، معظم URLs ستعمل بدون تعديل
}


# ========================================
# Step 3: Test Script
# ========================================

def test_refactored_endpoints():
    """
    سكريبت اختبار بسيط للتحقق من عمل Endpoints الجديدة
    
    Usage:
        python migration_external_safety.py test
    """
    import requests
    
    BASE_URL = "http://localhost:5001"
    
    print("🧪 Testing Refactored External Safety Endpoints...")
    
    # Test 1: Health check (API)
    print("\n1. Testing API Health Check...")
    response = requests.get(f"{BASE_URL}/api/v2/health")
    if response.status_code == 200:
        print(f"   ✅ API Health: {response.json()}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 2: List vehicles (API)
    print("\n2. Testing API List Vehicles...")
    response = requests.get(f"{BASE_URL}/api/v2/vehicles?limit=5")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['data']['total']} vehicles")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 3: Verify employee (API)
    print("\n3. Testing API Verify Employee...")
    response = requests.get(f"{BASE_URL}/api/v2/employees/1234567890")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Employee exists: {data['data']['exists']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 4: Share links page (Web)
    print("\n4. Testing Web Share Links Page...")
    response = requests.get(f"{BASE_URL}/external-safety/share-links")
    if response.status_code == 200 or response.status_code == 302:
        print(f"   ✅ Share links page accessible")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 5: Statistics (API)
    print("\n5. Testing API Statistics...")
    response = requests.get(f"{BASE_URL}/api/v2/statistics/safety-checks")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Stats: {data['data']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    print("\n✅ All tests completed!")


# ========================================
# Step 4: Database Migration (if needed)
# ========================================

def check_database_compatibility():
    """
    التحقق من توافق قاعدة البيانات مع الكود الجديد
    """
    from models import VehicleExternalSafetyCheck, VehicleSafetyImage
    from core.extensions import db
    
    print("🔍 Checking database compatibility...")
    
    # Check required columns exist
    required_columns = [
        'vehicle_id',
        'vehicle_plate_number',
        'driver_name',
        'driver_national_id',
        'check_date',
        'approval_status',
        'tires_ok',
        'lights_ok',
        'mirrors_ok',
        'body_ok',
        'cleanliness_ok'
    ]
    
    # This will fail if any column is missing
    try:
        check = VehicleExternalSafetyCheck.query.first()
        for col in required_columns:
            assert hasattr(check, col), f"Missing column: {col}"
        
        print("✅ Database schema is compatible")
        return True
    
    except Exception as e:
        print(f"❌ Database compatibility issue: {str(e)}")
        return False


# ========================================
# Step 5: Performance Comparison
# ========================================

def compare_performance():
    """
    مقارنة أداء الكود القديم vs الجديد
    """
    import time
    from services.external_safety_service import ExternalSafetyService
    
    print("📊 Performance Comparison...")
    
    # Test 1: Get all current drivers
    print("\n1. Get All Current Drivers:")
    
    # Legacy method (if available)
    # start = time.time()
    # legacy_drivers = get_all_current_drivers_legacy()
    # legacy_time = time.time() - start
    
    # New method
    start = time.time()
    new_drivers = ExternalSafetyService.get_all_current_drivers()
    new_time = time.time() - start
    
    print(f"   New Service: {new_time:.4f}s ({len(new_drivers)} drivers)")
    # print(f"   Legacy: {legacy_time:.4f}s")
    # print(f"   Improvement: {((legacy_time - new_time) / legacy_time * 100):.1f}%")
    
    # Test 2: Get checks with filters
    print("\n2. Get Checks with Filters:")
    start = time.time()
    checks = ExternalSafetyService.get_safety_checks_with_filters({'status': 'pending'})
    new_time = time.time() - start
    
    print(f"   New Service: {new_time:.4f}s ({len(checks)} checks)")


# ========================================
# Step 6: Rollback Plan
# ========================================

ROLLBACK_INSTRUCTIONS = """
🔄 Rollback Instructions (if needed)
====================================

إذا واجهت مشاكل مع الكود الجديد، اتبع هذه الخطوات للعودة للنظام القديم:

1. في app.py، قم بتعطيل Blueprints الجديدة:

   # Comment out
   # from routes.external_safety_refactored import external_safety_bp
   # from routes.api_external_safety_v2 import api_external_safety_bp
   # app.register_blueprint(external_safety_bp, url_prefix='/external-safety')
   # app.register_blueprint(api_external_safety_bp)

2. تفعيل Legacy blueprint:

   from routes.external_safety import external_safety_bp
   app.register_blueprint(external_safety_bp, url_prefix='/external-safety')

3. إعادة تشغيل الخادم:

   python app.py

4. التحقق من عمل Endpoints القديمة:

   http://localhost:5001/external-safety/share-links

ملاحظة: الـ Service Layer لن يسبب أي مشاكل حتى لو بقي موجوداً،
        لأنه لا يتم استدعاؤه إلا عند استخدام Blueprints الجديدة.
"""


# ========================================
# Main Execution
# ========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python migration_external_safety.py test       # Run tests")
        print("  python migration_external_safety.py check-db   # Check database")
        print("  python migration_external_safety.py perf       # Performance comparison")
        print("  python migration_external_safety.py rollback   # Show rollback instructions")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        test_refactored_endpoints()
    
    elif command == "check-db":
        check_database_compatibility()
    
    elif command == "perf":
        compare_performance()
    
    elif command == "rollback":
        print(ROLLBACK_INSTRUCTIONS)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


# ========================================
# Deployment Checklist
# ========================================

DEPLOYMENT_CHECKLIST = """
✅ Deployment Checklist
======================

قبل النشر للـ Production:

[ ] 1. تم اختبار جميع Endpoints (Web + API)
[ ] 2. تم التحقق من database compatibility
[ ] 3. تم تحديث environment variables (إذا لزم)
[ ] 4. تم backup قاعدة البيانات
[ ] 5. تم backup الكود القديم
[ ] 6. تم تحديث الوثائق (README, API docs)
[ ] 7. تم إعلام الفريق بالتغييرات
[ ] 8. تم تحضير rollback plan
[ ] 9. تم اختبار الأداء (load testing)
[ ] 10. تم مراجعة Security considerations

بعد النشر:

[ ] 1. مراقبة logs لأي أخطاء
[ ] 2. مراقبة performance metrics
[ ] 3. تجميع feedback من المستخدمين
[ ] 4. حذف Legacy code بعد أسبوع من الاستقرار
"""

print(DEPLOYMENT_CHECKLIST)
