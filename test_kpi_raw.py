"""Test analytics KPI data raw"""
import urllib.request

url = 'http://127.0.0.1:5000/analytics/api/kpis'

try:
    response = urllib.request.urlopen(url, timeout=10)
    data = response.read().decode('utf-8')
    print("=" * 60)
    print("Analytics KPI Response:")
    print("=" * 60)
    print(f"Status: {response.getcode()}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response Length: {len(data)}")
    print()
    print("Response Body:")
    print(data[:500])  # First 500 chars
    print("=" * 60)
except Exception as e:
    print(f"Error: {e}")
