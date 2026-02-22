#!/usr/bin/env python3
"""Test export with detailed logging"""

import logging
import sys
import importlib.util

# Setup logging to capture everything
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Load app
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

print("=" * 70)
print("Testing Export with Full Logging")
print("=" * 70)

# Test directly with Flask test client
with app.test_client() as client:
    print("\nMaking request to /attendance/export-excel-department...")
    print("URL: /attendance/export-excel-department?department=Aramex%20Courier")
    
    response = client.get('/attendance/export-excel-department?department=Aramex%20Courier')
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Content-Type: {response.content_type}")
    print(f"Response Length: {len(response.data)} bytes")
    print(f"First 100 bytes: {response.data[:100]}")
    
    if response.status_code == 200:
        if response.content_type and 'spreadsheet' in response.content_type:
            print("\n✅ SUCCESS: Got Excel file!")
        else:
            print(f"\n❌ WRONG Content-Type: {response.content_type}")
            print(f"\nResponse preview:")
            print(response.data[:500].decode('utf-8', errors='ignore'))
    else:
        print(f"\n❌ ERROR Status Code: {response.status_code}")
        print(f"Response:")
        print(response.data.decode('utf-8', errors='ignore')[:500])
