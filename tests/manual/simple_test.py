#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import urllib.error

IP = "192.168.8.115"
PORT = 5000

routes = [
    ("/", "Homepage"),
    ("/auth/login", "Login"),
    ("/attendance/", "Attendance List"),
    ("/attendance/dashboard", "Dashboard"),
    ("/attendance/record", "Record"),
    ("/attendance/export", "Export"),
    ("/attendance/stats", "Stats"),
    ("/attendance/api/departments/1/employees", "API"),
    ("/static/css/custom.css", "CSS custom"),
    ("/static/css/theme.css", "CSS theme"),
    ("/static/css/fonts.css", "CSS fonts"),
    ("/static/mobile/css/mobile-theme.css", "CSS mobile-theme"),
    ("/static/mobile/css/mobile-style.css", "CSS mobile-style"),
]

passed = 0
failed = 0

print("\nTesting port 5000\n")

for path, desc in routes:
    try:
        url = f"http://{IP}:{PORT}{path}"
        with urllib.request.urlopen(url, timeout=3) as r:
            if r.status == 200:
                print(f"[OK] {desc:<20} 200")
                passed += 1
            else:
                print(f"[XX] {desc:<20} {r.status}")
                failed += 1
    except Exception as e:
        print(f"[XX] {desc:<20} ERROR")
        failed += 1

print(f"\nTotal: {passed+failed} | Passed: {passed} | Failed: {failed} | Rate: {passed*100//(passed+failed)}%\n")
