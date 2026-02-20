#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test export routes with a real department"""

import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "http://127.0.0.1:5000"

# Department "Aramex Courier" should exist
print("Testing /attendance/export-excel-department")
print("=" * 70)

try:
    # Use the actual department name with proper URL encoding
    dept = urllib.parse.quote("Aramex Courier")
    url = f"{BASE_URL}/attendance/export-excel-department?department={dept}"
    print(f"URL: {url}\n")
    
    response = urllib.request.urlopen(url, timeout=15)
    content = response.read()[:1000]
    
    print(f"Status: {response.getcode()}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Disposition: {response.headers.get('Content-Disposition')}")
    print(f"\nFirst 200 bytes:")
    print(content[:200])
    
except Exception as e:
    print(f"Error: {e}")
