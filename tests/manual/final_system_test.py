#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final System Test - الاختبار النهائي الشامل للنظام
بدون استخدام requests
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
PORT = 5001
BASE_URL = f"http://{IP}:{PORT}"

def test_page(path, expected_status=200, description=""):
    try:
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            status = response.status
            size = len(response.read()) / 1024
            
            if status == expected_status:
                return True, f"[✓] {description:<35} Status: {status} | Size: {size:.1f} KB"
            else:
                return False, f"[✗] {description:<35} Status: {status} (expected {expected_status})"
    except urllib.error.HTTPError as e:
        status = e.code
        if status == expected_status:
            return True, f"[✓] {description:<35} Status: {status} (redirect)"
        return False, f"[✗] {description:<35} Status: {status} (expected {expected_status})"
    except Exception as e:
        return False, f"[✗] {description:<35} Error: {str(e)[:35]}"

def main():
    print("\n" + "=" * 100)
    print("Final System Test - الاختبار النهائي الشامل")
    print("=" * 100)
    print(f"Server IP: {IP}:{PORT}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "passed": 0,
        "failed": 0
    }

    # Group 1: Landing Pages
    print("1. LANDING PAGES")
    print("-" * 100)
    pages = [
        ("/", 200, "Homepage"),
        ("/auth/login", 200, "Login Page (Beautiful Design)"),
    ]
    for path, status, desc in pages:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Group 2: Authentication
    print("\n2. AUTHENTICATION")
    print("-" * 100)
    auth_pages = [
        ("/auth/login", 200, "Login Form"),
    ]
    for path, status, desc in auth_pages:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Group 3: Attendance System
    print("\n3. ATTENDANCE SYSTEM")
    print("-" * 100)
    attendance_pages = [
        ("/attendance/", 200, "Main Attendance List"),
        ("/attendance/record", 200, "Record Attendance Form"),
        ("/attendance/export", 200, "Export Options"),
        ("/attendance/dashboard", 200, "Dashboard"),
        ("/attendance/stats", 200, "Statistics"),
    ]
    for path, status, desc in attendance_pages:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Group 4: Static Files
    print("\n4. STATIC FILES")
    print("-" * 100)
    static_files = [
        ("/static/css/custom.css", 200, "Custom CSS"),
        ("/static/css/fonts.css", 200, "Fonts CSS"),
        ("/static/css/theme.css", 200, "Theme CSS"),
        ("/static/mobile/css/mobile-theme.css", 200, "Mobile Theme"),
        ("/static/mobile/css/mobile-style.css", 200, "Mobile Style"),
    ]
    for path, status, desc in static_files:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Group 5: API Endpoints
    print("\n5. API ENDPOINTS")
    print("-" * 100)
    api_pages = [
        ("/attendance/api/departments/1/employees", 200, "Get Employees (JSON API)"),
    ]
    for path, status, desc in api_pages:
        ok, msg = test_page(path, status, desc)
        print(f"  {msg}")
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Final Report
    print("\n" + "=" * 100)
    print("FINAL REPORT")
    print("=" * 100)
    
    total = results["passed"] + results["failed"]
    percentage = (results["passed"] / total * 100) if total > 0 else 0
    
    print(f"\nResults:")
    print(f"  Total Tests: {total}")
    print(f"  Passed: {results['passed']} ✓")
    print(f"  Failed: {results['failed']} ✗")
    print(f"  Success Rate: {percentage:.1f}%\n")
    
    if results["failed"] == 0:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe system is fully operational!")
        print(f"Access at: http://{IP}:{PORT}/auth/login")
    else:
        print(f"⚠️ {results['failed']} test(s) failed")
    
    print("\n" + "=" * 100 + "\n")

if __name__ == "__main__":
    main()
