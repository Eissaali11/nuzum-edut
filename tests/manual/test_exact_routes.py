#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test port 5000 routes - اختبار المسارات الدقيقة
"""

import urllib.request
import urllib.error
from datetime import datetime

IP = "192.168.8.115"
PORT = 5000
BASE_URL = f"http://{IP}:{PORT}"

def test_url(url, description=""):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            status = response.status
            size = len(response.read()) / 1024
            return f"[✓] {description:<40} {status} | {size:.1f} KB | {url}"
    except urllib.error.HTTPError as e:
        return f"[✗] {description:<40} {e.code} | {url}"
    except Exception as e:
        return f"[✗] {description:<40} ERR: {str(e)[:30]} | {url}"

print("\n" + "="*130)
print("Route Testing - اختبار المسارات".center(130))
print("="*130 + "\n")

test_routes = [
    ("/", "Root"),
    ("/auth/login", "Login Page"),
    ("/attendance", "Attendance (no slash)"),
    ("/attendance/", "Attendance (with slash)"),
    ("/attendance/dashboard", "Attendance Dashboard"),
    ("/attendance/record", "Attendance Record"),
    ("/static/css/custom.css", "CSS custom.css"),
    ("/static/css/theme.css", "CSS theme.css"),
    ("/static/css/fonts.css", "CSS fonts.css"),
]

for path, desc in test_routes:
    url = f"{BASE_URL}{path}"
    print(test_url(url, desc))

print("\n" + "="*130 + "\n")
