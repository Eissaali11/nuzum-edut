"""Test Power BI export endpoint"""
import urllib.request
import urllib.error

url = 'http://127.0.0.1:5000/analytics/export/powerbi'

try:
    print("Testing Power BI export endpoint...")
    response = urllib.request.urlopen(url, timeout=30)
    print(f"✅ Success! Status: {response.getcode()}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Length: {response.headers.get('Content-Length')} bytes")
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error {e.code}: {e.reason}")
    # Try to read error details
    try:
        error_body = e.read().decode('utf-8')
        print("\nError details:")
        print(error_body[:500])
    except:
        pass
except Exception as e:
    print(f"❌ Error: {e}")
