#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug test to see actual error messages"""

import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000"

print("Debugging export routes...")
print("=" * 70)

# Test 1
print("\nTEST 1: /attendance/export-excel-department")
try:
    url = f"{BASE_URL}/attendance/export-excel-department?department=IT&project=2026"
    response = urllib.request.urlopen(url, timeout=15)
    content = response.read().decode('utf-8', errors='ignore')
    print(f"Status: {response.getcode()}")
    print(f"Response (first 500 chars):")
    print(content[:500])
except Exception as e:
    print(f"Error: {e}")

# Test 2
print("\n\nTEST 2: /attendance/export-excel-dashboard")
try:
    url = f"{BASE_URL}/attendance/export-excel-dashboard?department=IT&project=2026"
    response = urllib.request.urlopen(url, timeout=15)
    content = response.read().decode('utf-8', errors='ignore')
    print(f"Status: {response.getcode()}")
    print(f"Response (first 500 chars):")
    print(content[:500])
except Exception as e:
    print(f"Error: {e}")
