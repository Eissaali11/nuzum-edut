#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Enhanced Excel Report via API
الاختبار باستخدام الـ API
"""
import sys
import os
import time
import urllib.request
import urllib.error
import json

print("\n" + "="*70)
print("🧪 Testing Enhanced Excel Report API")
print("="*70)

BASE_URL = "http://127.0.0.1:5000"
GENERATE_ENDPOINT = "/analytics/generate/enhanced-excel"
EXPORT_ENDPOINT = "/analytics/export/enhanced-excel"

def test_api():
    """Test the enhanced Excel report APIs"""
    
    print("\n1️⃣  Testing Report Generation Endpoint...")
    try:
        url = f"{BASE_URL}{GENERATE_ENDPOINT}"
        print(f"   📡 Calling: {url}")
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            print(f"   ✅ Response Status: {response.status}")
            print(f"   ✅ Report Status: {data.get('status', 'unknown')}")
            
            if 'message' in data:
                print(f"   ℹ️  Message: {data['message']}")
            if 'file_path' in data:
                print(f"   📁 File Path: {data['file_path']}")
            if 'download_url' in data:
                print(f"   🔗 Download: {data['download_url']}")
            
            return True
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}")
        if e.code == 403:
            print("   ⚠️  Access forbidden - may need admin login")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            if 'error' in error_data:
                print(f"   Error: {error_data['error']}")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"   ❌ Connection Error: {e.reason}")
        print("   ⚠️  Is Flask server running at http://127.0.0.1:5000?")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_server():
    """Check if Flask server is running"""
    print("\n0️⃣  Checking Flask Server Status...")
    try:
        url = f"{BASE_URL}/"
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"   ✅ Server is running at {BASE_URL}")
            return True
    except:
        print(f"   ❌ Server is NOT running at {BASE_URL}")
        print("   ➡️  Please start the server first:")
        print("        python app.py")
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("📊 Enhanced Excel Report API Test")
    print("="*70)
    
    # Check server
    if not check_server():
        print("\n❌ Cannot proceed - server is not running")
        sys.exit(1)
    
    print("\n" + "-"*70)
    
    # Test API
    success = test_api()
    
    print("\n" + "="*70)
    if success:
        print("✅ API TEST PASSED")
        print("\n🎯 Next Steps:")
        print(f"1. Download the Excel file:")
        print(f"   {BASE_URL}{EXPORT_ENDPOINT}")
        print(f"\n2. Or use curl:")
        print(f"   curl {BASE_URL}{EXPORT_ENDPOINT} -o enhanced_report.xlsx")
    else:
        print("❌ API TEST FAILED")
        print("\nTroubleshooting:")
        print("• Ensure Flask server is running")
        print("• Check that you're logged in as admin")
        print("• Check Flask server logs for errors")
    print("="*70 + "\n")
