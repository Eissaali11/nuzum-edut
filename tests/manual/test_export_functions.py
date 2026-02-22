#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for new export functions
Tests the refactored AttendanceReportService integration
"""

import urllib.request
import urllib.error
import json
import sys
from datetime import datetime

print("=" * 70)
print("🧪 Testing New Export Functions")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

BASE_URL = "http://127.0.0.1:5000"

# Test 1: Export Excel Department
print("TEST 1: /attendance/export-excel-department")
print("-" * 70)
try:
    url = f"{BASE_URL}/attendance/export-excel-department?department=IT&project=2026"
    print(f"URL: {url}")
    
    response = urllib.request.urlopen(url, timeout=15)
    status = response.getcode()
    content_type = response.headers.get('Content-Type', 'Unknown')
    content_length = response.headers.get('Content-Length', 'Unknown')
    
    # Read content
    content = response.read()
    actual_size = len(content)
    
    print(f"✅ Status: {status}")
    print(f"   Content-Type: {content_type}")
    print(f"   Content-Length (header): {content_length}")
    print(f"   Actual size: {actual_size} bytes")
    
    # Verify it's a valid Excel file (starts with PK - zip format)
    is_valid_excel = content[:2] == b'PK'
    print(f"   Valid Excel file: {'✅ YES' if is_valid_excel else '❌ NO'}")
    
    if is_valid_excel:
        print(f"   File size: {actual_size / 1024:.2f} KB")
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error {e.code}")
    try:
        error_content = e.read().decode('utf-8', errors='ignore')
        print(f"   Response: {error_content[:200]}")
    except:
        pass
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")

print()

# Test 2: Export Excel Dashboard
print("TEST 2: /attendance/export-excel-dashboard")
print("-" * 70)
try:
    url = f"{BASE_URL}/attendance/export-excel-dashboard?department=IT&project=2026"
    print(f"URL: {url}")
    
    response = urllib.request.urlopen(url, timeout=15)
    status = response.getcode()
    content_type = response.headers.get('Content-Type', 'Unknown')
    content_length = response.headers.get('Content-Length', 'Unknown')
    
    # Read content
    content = response.read()
    actual_size = len(content)
    
    print(f"✅ Status: {status}")
    print(f"   Content-Type: {content_type}")
    print(f"   Content-Length (header): {content_length}")
    print(f"   Actual size: {actual_size} bytes")
    
    # Verify it's a valid Excel file (starts with PK - zip format)
    is_valid_excel = content[:2] == b'PK'
    print(f"   Valid Excel file: {'✅ YES' if is_valid_excel else '❌ NO'}")
    
    if is_valid_excel:
        print(f"   File size: {actual_size / 1024:.2f} KB")
    
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error {e.code}")
    try:
        error_content = e.read().decode('utf-8', errors='ignore')
        print(f"   Response: {error_content[:200]}")
    except:
        pass
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")

print()

# Test 3: Verify import of AttendanceReportService
print("TEST 3: Import AttendanceReportService")
print("-" * 70)
try:
    from services.attendance_reports import AttendanceReportService
    print("✅ Successfully imported AttendanceReportService")
    print(f"   Methods available:")
    methods = [m for m in dir(AttendanceReportService) if not m.startswith('_')]
    for method in methods:
        print(f"     - {method}")
except Exception as e:
    print(f"❌ Import failed: {type(e).__name__}: {str(e)}")

print()
print("=" * 70)
print("✅ Test suite complete!")
print("=" * 70)
