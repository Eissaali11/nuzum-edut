#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network Accessibility Test - اختبار الوصول عبر IP الشبكة
يتحقق من أن النظام يعمل عبر عنوان IP الشبكة وليس فقط localhost
"""

import requests
import socket
import time
from datetime import datetime

def get_local_ip():
    """الحصول على عنوان IP المحلي"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.8.115"

BASE_IP = get_local_ip()
LOCALHOST = "127.0.0.1"
PORT = 5001

def test_url(url, description):
    """اختبار عنوان URL واحد"""
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)
        size = len(response.content) / 1024
        status = response.status_code
        
        if status == 200:
            return "✓", status, size
        else:
            return "✗", status, size
    except requests.ConnectionError:
        return "✗", "CONN", 0
    except requests.Timeout:
        return "✗", "TIMEOUT", 0
    except Exception as e:
        return "✗", "ERROR", 0

def main():
    print("\n" + "=" * 100)
    print("Network Accessibility Test - اختبار الوصول من الشبكة")
    print("=" * 100)
    print(f"Server IP:  {BASE_IP}:{PORT}")
    print(f"Localhost:  127.0.0.1:{PORT}")
    print("=" * 100 + "\n")

    # Test from localhost
    print("1. LocalHost Access (127.0.0.1)")
    print("-" * 100)
    status, code, size = test_url(f"http://127.0.0.1:{PORT}/attendance/", "Attendance Page")
    print(f"  {status} Main Page: http://127.0.0.1:{PORT}/attendance/ (Status: {code})")
    
    if code != 200:
        print("\n[ERROR] Server not responding. Run: python start_phase2_5001.py\n")
        return
    
    print()

    # Test from network IP
    print(f"2. Network IP Access ({BASE_IP})")
    print("-" * 100)
    status, code, size = test_url(f"http://{BASE_IP}:{PORT}/attendance/", "Attendance Page from Network")
    symbol = "✓" if code == 200 else "✗"
    print(f"  {symbol} Main Page: http://{BASE_IP}:{PORT}/attendance/ (Status: {code})")
    
    if code != 200:
        print(f"\n[ERROR] Cannot reach from network IP {BASE_IP}:{PORT}")
        print("[INFO] This means the server is not listening on 0.0.0.0")
        print("[FIX] Ensure start_phase2_5001.py has: app.run(host='0.0.0.0', ...)\n")
        return
    
    print()

    # Test static files
    print("3. Static Files from Network IP")
    print("-" * 100)
    
    static_files = [
        ('static/css/custom.css', 'Custom CSS'),
        ('static/css/fonts.css', 'Fonts CSS'),
        ('static/css/logo.css', 'Logo CSS'),
        ('static/css/theme.css', 'Theme CSS'),
    ]
    
    all_ok = True
    for path, desc in static_files:
        status, code, size = test_url(f"http://{BASE_IP}:{PORT}/{path}", desc)
        symbol = "✓" if code == 200 else "✗"
        print(f"  {symbol} {desc:<25} http://{BASE_IP}:{PORT}/{path:<35} (Status: {code})")
        if code != 200:
            all_ok = False
    
    print()
    print("=" * 100)
    
    if all_ok:
        print(f"✓ SUCCESS - System is fully accessible from: http://{BASE_IP}:{PORT}/attendance/")
    else:
        print(f"✗ ISSUES DETECTED - Some static files are not accessible from {BASE_IP}")
        print(f"  Try accessing: http://127.0.0.1:{PORT}/attendance/ instead")
    
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()
