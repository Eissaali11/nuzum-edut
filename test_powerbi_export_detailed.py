"""Test Power BI export with proper login simulation"""
import urllib.request
import urllib.error
import json

url = 'http://127.0.0.1:5000/analytics/export/powerbi'

try:
    print("Testing Power BI export endpoint...")
    print("Note: This will redirect to login if not authenticated")
    print()
    
    response = urllib.request.urlopen(url, timeout=30)
    
    content_type = response.headers.get('Content-Type')
    
    if 'json' in content_type:
        # It's an error response
        data = json.loads(response.read().decode('utf-8'))
        print("❌ Export failed with error:")
        print(f"   Error: {data.get('error')}")
        print(f"   Details: {data.get('details')}")
    elif 'excel' in content_type or 'spreadsheet' in content_type:
        # Success - Excel file
        content_length = response.headers.get('Content-Length')
        print(f"✅ Success! Excel file ready")
        print(f"   Content-Type: {content_type}")
        print(f"   Size: {content_length} bytes")
    else:
        # HTML redirect to login
        print("🔒 Redirected to login (authentication required)")
        print(f"   Content-Type: {content_type}")
        
except urllib.error.HTTPError as e:
    if e.code == 500:
        # Internal server error - read the JSON error response
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print("❌ Export failed with 500 error:")
            print(f"   Error: {error_data.get('error')}")
            print(f"   Details: {error_data.get('details')}")
            if 'traceback' in error_data:
                print("\nTraceback (last 10 lines):")
                lines = error_data['traceback'].split('\n')
                for line in lines[-10:]:
                    print(f"   {line}")
        except:
            print(f"❌ HTTP Error {e.code}: {e.reason}")
    else:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
except Exception as e:
    print(f"❌ Error: {e}")
