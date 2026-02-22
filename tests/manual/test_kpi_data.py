"""Test analytics KPI data"""
import urllib.request
import json

url = 'http://127.0.0.1:5000/analytics/api/kpis'

response = urllib.request.urlopen(url, timeout=10)
data = json.loads(response.read().decode('utf-8'))

print("=" * 60)
print("Analytics KPI Data:")
print("=" * 60)
for key, value in data.items():
    print(f"{key}: {value}")
print("=" * 60)
