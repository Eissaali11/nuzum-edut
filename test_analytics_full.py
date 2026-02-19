"""Test analytics dashboard with full server check"""
import urllib.request
import urllib.error
import time

def test_endpoint(url, name):
    try:
        response = urllib.request.urlopen(url, timeout=10)
        status = response.getcode()
        print(f"✅ {name}: {status}")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print(f"🔒 {name}: Redirect to login (authentication required)")
        else:
            print(f"❌ {name}: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

print("=" * 70)
print("Analytics System Test")
print("=" * 70)

# Wait for server
time.sleep(2)

# Test main dashboard (should work without auth on some configs)
test_endpoint('http://127.0.0.1:5000/dashboard', 'Main Dashboard')

# Test analytics dashboard (requires admin auth)
test_endpoint('http://192.168.8.115:5000/analytics/dashboard', 'Analytics Dashboard')

print("=" * 70)
print("\n📌 Note: Analytics dashboard requires admin login")
print("   Access it at: http://192.168.8.115:5000/analytics/dashboard")
print("=" * 70)
