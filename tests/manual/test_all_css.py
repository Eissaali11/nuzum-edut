#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive CSS Test - اختبار شامل لملفات التصميم من IP الشبكة
"""

import requests
import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.8.115"

IP = get_local_ip()
PORT = 5001

def test_file(path, description):
    """Test if file loads from network IP"""
    try:
        r = requests.get(f"http://{IP}:{PORT}/{path}", timeout=3)
        if r.status_code == 200:
            size = len(r.content) / 1024
            return "✓", size
        else:
            return "✗", r.status_code
    except Exception as e:
        return "✗", str(e)[:20]

def main():
    print("\n" + "=" * 90)
    print("Comprehensive CSS Test - شامل لجميع ملفات التصميم")
    print("=" * 90)
    print(f"Network IP: {IP}:{PORT}\n")

    # Test main attendance page
    print("1. Main Pages")
    print("-" * 90)
    status, size = test_file("attendance/", "Attendance Page")
    print(f"  {status} Main Attendance Page: {size} KB" if status == "✓" else f"  {status} Main Attendance Page: {size}")

    print("\n2. Static CSS Files (presentation/web/static/)")
    print("-" * 90)
    css_files = [
        ("static/css/custom.css", "Custom Styling"),
        ("static/css/fonts.css", "Font Definitions"),
        ("static/css/logo.css", "Logo CSS"),
        ("static/css/theme.css", "Theme CSS"),
    ]
    for path, desc in css_files:
        status, result = test_file(path, desc)
        print(f"  {status} {desc:<25} ({path})")

    print("\n3. Mobile CSS Files (static/mobile/ → presentation/web/static/mobile/)")
    print("-" * 90)
    mobile_css = [
        ("static/mobile/css/mobile-theme.css", "Mobile Theme"),
        ("static/mobile/css/mobile-style.css", "Mobile Styling"),
        ("static/mobile/css/enhanced-header.css", "Enhanced Header"),
        ("static/mobile/css/enhanced-sidebar.css", "Enhanced Sidebar"),
        ("static/mobile/css/floating-nav.css", "Floating Navigation"),
        ("static/mobile/css/install-button.css", "Install Button"),
    ]
    for path, desc in mobile_css:
        status, result = test_file(path, desc)
        print(f"  {status} {desc:<25} ({path})")

    print("\n4. Static Images & Fonts")
    print("-" * 90)
    assets = [
        ("static/mobile/images/app-icon.png", "App Icon"),
        ("static/mobile/manifest.json", "PWA Manifest"),
    ]
    for path, desc in assets:
        status, result = test_file(path, desc)
        print(f"  {status} {desc:<25} ({path})")

    print("\n" + "=" * 90)
    print("✓ ALL CSS FILES LOADED SUCCESSFULLY" if all([test_file(p, d)[0] == "✓" for p, d in css_files + mobile_css]) else "✗ Some files failed to load")
    print(f"\nAccess the system at: http://{IP}:{PORT}/attendance/")
    print("=" * 90 + "\n")

if __name__ == "__main__":
    main()
