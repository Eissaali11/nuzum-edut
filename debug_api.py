#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Enhanced Excel Report - Debug Version
"""
import sys
import os
import urllib.request
import urllib.error

print("\n" + "="*70)
print("🔍 Debug: Testing Enhanced Excel Report API")
print("="*70)

BASE_URL = "http://127.0.0.1:5000"
ENDPOINT = "/analytics/generate/enhanced-excel"

print(f"\n📡 Request URL: {BASE_URL}{ENDPOINT}")

try:
    url = f"{BASE_URL}{ENDPOINT}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'},
        method='GET'
    )
    
    print("\n📤 Sending request...")
    with urllib.request.urlopen(req, timeout=10) as response:
        status = response.status
        headers = dict(response.headers)
        body = response.read()
        
        print(f"\n✅ Response Status: {status}")
        print(f"\n📋 Response Headers:")
        for key, value in headers.items():
            print(f"   {key}: {value}")
        
        print(f"\n📄 Response Body (first 500 chars):")
        print(body[:500].decode('utf-8', errors='ignore'))
        
        if len(body) > 500:
            print(f"\n   ... (total {len(body)} bytes)")
        
except urllib.error.HTTPError as e:
    print(f"\n❌ HTTP Error {e.code}")
    
    headers = dict(e.headers)
    body = e.read()
    
    print(f"\n📋 Response Headers:")
    for key, value in headers.items():
        print(f"   {key}: {value}")
    
    print(f"\n📄 Response Body (first 500 chars):")
    print(body[:500].decode('utf-8', errors='ignore'))
    
except urllib.error.URLError as e:
    print(f"\n❌ Connection Error: {e.reason}")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*70 + "\n")
