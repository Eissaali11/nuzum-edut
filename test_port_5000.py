#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test all routes on port 5000 - الاختبار الشامل على المسار الصحيح
"""

import urllib.request
import urllib.error
import socket
from datetime import datetime

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.8.115"

IP = get_ip()
PORT = 5000
BASE_URL = f"http://{IP}:{PORT}"

def test_page(path, expected_status=200, description=""):
    try:
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            status = response.status
            content = response.read()
            size = len(content) / 1024
            
            if status == expected_status:
                return True, f"[✓] {description:<40} Status: {status} | Size: {size:.1f} KB"
            else:
                return False, f"[✗] {description:<40} Status: {status} (expected {expected_status})"
    except urllib.error.HTTPError as e:
        status = e.code
        if status == expected_status:
            return True, f"[✓] {description:<40} Status: {status}"
        return False, f"[✗] {description:<40} Status: {status} (expected {expected_status})"
    except Exception as e:
        return False, f"[✗] {description:<40} Error: {str(e)[:40]}"

def main():
    print("\n" + "=" * 120)
    print("PORT 5000 - الاختبار الشامل على المسار الصحيح".center(120))
    print("=" * 120)
    print(f"\nServer IP: {IP}:{PORT}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "passed": 0,
        "failed": 0
    }

    # Test all routes
    print("TESTING ALL ROUTES")
    print("-" * 120)
    
    routes = [
        ("/", 200, "Homepage - الصفحة الرئيسية"),
        ("/auth/login", 200, "Login Page - صفحة تسجيل الدخول"),
        ("/attendance/", 200, "Attendance List - قائمة الحضور"),
        ("/attendance/dashboard", 200, "Dashboard - لوحة التحكم"),
        ("/attendance/record", 200, "Record Attendance - تسجيل الحضور"),
        ("/attendance/export", 200, "Export Options - خيارات التصدير"),
        ("/attendance/stats", 200, "Statistics - الإحصائيات"),
        ("/attendance/api/departments/1/employees", 200, "API - Employees JSON"),
        ("/static/css/custom.css", 200, "CSS - custom.css"),
        ("/static/css/theme.css", 200, "CSS - theme.css"),
        ("/static/css/fonts.css", 200, "CSS - fonts.css"),
        ("/static/mobile/css/mobile-theme.css", 200, "Mobile CSS - mobile-theme.css"),
        ("/static/mobile/css/mobile-style.css", 200, "Mobile CSS - mobile-style.css"),
    ]
    
    for path, status, desc in routes:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Final Report
    print("\n" + "=" * 120)
    print("FINAL REPORT - التقرير النهائي".center(120))
    print("=" * 120)
    
    total = results["passed"] + results["failed"]
    percentage = (results["passed"] / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {results['passed']} ✓")
    print(f"Failed: {results['failed']} ✗")
    print(f"Success Rate: {percentage:.1f}%\n")
    
    if results["failed"] == 0:
        print("✓✓✓ ALL TESTS PASSED ON PORT 5000 ✓✓✓".center(120))
        print(f"\nAccess at: http://{IP}:{PORT}/")
    else:
        print(f"⚠️ Some tests failed on port 5000".center(120))
    
    print("\n" + "=" * 120 + "\n")

if __name__ == "__main__":
    main()
