#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار endpoint تصدير Power BI
Test Power BI Export Endpoint
"""
import urllib.request
import os

url = 'http://127.0.0.1:5000/analytics/export/powerbi'

try:
    print("Testing /analytics/export/powerbi")
    print("=" * 50)
    
    # الوصول إلى الـ endpoint
    response = urllib.request.urlopen(url, timeout=10)
    
    # الحصول على البيانات
    file_data = response.read()
    
    print(f"Status Code: {response.getcode()}")
    print(f"File Size: {len(file_data)} bytes")
    print(f"Latest expected file: Executive_Report_20260220_001437.xlsx (7077 bytes)")
    
    # حفظ الملف للتحقق
    test_file = 'test_downloaded_report.xlsx'
    with open(test_file, 'wb') as f:
        f.write(file_data)
    
    file_size = os.path.getsize(test_file)
    print(f"Saved to: {test_file} ({file_size} bytes)")
    
    print("\n✅ SUCCESS: File downloaded successfully")
    
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}")
    if e.code == 401:
        print("Login required (401 Unauthorized)")
    elif e.code == 403:
        print("Access denied (403 Forbidden)")
except Exception as e:
    print(f"Error: {e}")
