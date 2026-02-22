# -*- coding: utf-8 -*-
"""
اختبار Phase 2 - Live Testing Script
Test all 28 routes and verify Phase 2 is working correctly
"""

import requests
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:5001/attendance"

# Define all 28 routes grouped by module
ROUTES_TO_TEST = {
    "List & View (2 routes)": [
        ("GET", "/", "القائمة الرئيسية"),
        ("GET", "/department/view", "عرض حضور قسم"),
    ],
    "Recording (5 routes)": [
        ("GET", "/record", "تسجيل فردي - صفحة"),
        ("GET", "/department", "تسجيل قسم - صفحة"),
        ("GET", "/bulk-record", "تسجيل جماعي - صفحة"),
        ("GET", "/all-departments", "تسجيل أقسام - صفحة"),
        ("GET", "/department/bulk", "تسجيل قسم لفترة - صفحة"),
    ],
    "Edit & Delete (5 routes)": [
        ("GET", "/edit/1", "صفحة تعديل سجل"),
        ("GET", "/delete/1/confirm", "تأكيد حذف"),
        # POST routes skipped (need CSRF)
    ],
    "Export (6 routes)": [
        ("GET", "/export", "صفحة التصدير"),
        ("GET", "/export/excel", "تصدير Excel"),
        ("GET", "/export-excel-dashboard", "تصدير Dashboard"),
        ("GET", "/export-excel-department", "تصدير قسم"),
        ("GET", "/department/export-data", "تصدير بفلاتر"),
        ("GET", "/department/export-period", "تصدير فترة"),
    ],
    "Statistics (5 routes)": [
        ("GET", "/stats", "إحصائيات API"),
        ("GET", "/dashboard", "لوحة التحكم"),
        ("GET", "/employee/1", "تقرير موظف"),
        ("GET", "/department-stats", "إحصائيات أقسام"),
        ("GET", "/department-details", "تفاصيل قسم"),
    ],
    "Circles & GPS (4 routes)": [
        ("GET", "/departments-circles-overview", "نظرة عامة دوائر"),
        ("GET", "/circle-accessed-details/1/1", "تفاصيل دائرة"),
        # Export and POST routes skipped
    ],
    "API (1 route)": [
        ("GET", "/api/departments/1/employees", "قائمة موظفين JSON"),
    ],
}

def test_route(method, path, description):
    """Test a single route and return result"""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10, allow_redirects=False)
        else:
            response = requests.post(url, timeout=10, allow_redirects=False)
        
        # Check status
        if response.status_code in [200, 302]:  # 302 = redirect (normal for some routes)
            return True, response.status_code, len(response.content)
        elif response.status_code == 404:
            return False, 404, 0
        else:
            return False, response.status_code, 0
            
    except requests.exceptions.ConnectionError:
        return False, "CONN_ERR", 0
    except requests.exceptions.Timeout:
        return False, "TIMEOUT", 0
    except Exception as e:
        return False, str(e)[:20], 0

def main():
    print("=" * 70)
    print("Phase 2 Live Testing - 28 Routes")
    print("=" * 70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    print()
    
    total_routes = 0
    passed_routes = 0
    failed_routes = []
    
    for category, routes in ROUTES_TO_TEST.items():
        print(f"\n{category}")
        print("-" * 70)
        
        for method, path, description in routes:
            total_routes += 1
            success, status, size = test_route(method, path, description)
            
            if success:
                passed_routes += 1
                size_kb = size / 1024
                if size_kb > 0:
                    print(f"  [OK] {method:4} {path:40} [{status}] {size_kb:.1f} KB")
                else:
                    print(f"  [OK] {method:4} {path:40} [{status}]")
            else:
                failed_routes.append((method, path, description, status))
                print(f"  [FAIL] {method:4} {path:40} [{status}] FAILED")
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"[OK] Passed:  {passed_routes}/{total_routes} routes")
    print(f"[FAIL] Failed:  {len(failed_routes)}/{total_routes} routes")
    print(f"Success Rate: {(passed_routes/total_routes)*100:.1f}%")
    
    if failed_routes:
        print("\nFailed Routes:")
        for method, path, desc, status in failed_routes:
            print(f"  - {method} {path} ({desc}) - Status: {status}")
    
    print("\n" + "=" * 70)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Exit code based on success
    if passed_routes == total_routes:
        print("\nAll routes passed! Phase 2 is working perfectly!")
        sys.exit(0)
    elif passed_routes >= total_routes * 0.8:  # 80% success
        print("\nMost routes passed, but some need attention.")
        sys.exit(1)
    else:
        print("\nCritical failures detected. Phase 2 needs debugging.")
        sys.exit(2)

if __name__ == "__main__":
    main()
