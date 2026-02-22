"""Test both localhost and network IP"""
import urllib.request
import urllib.error

def test_url(url):
    try:
        r = urllib.request.urlopen(url, timeout=10)
        print(f'✅ {url}: {r.getcode()} OK')
        return True
    except urllib.error.HTTPError as e:
        print(f'❌ {url}: {e.code} {e.reason}')
        return False
    except Exception as e:
        print(f'❌ {url}: {e.__class__.__name__} - {str(e)[:50]}')
        return False

print("=" * 80)
print("Testing Analytics Dashboard on different IPs")
print("=" * 80)

# Test localhost
test_url('http://127.0.0.1:5000/analytics/dashboard')

# Test network IP
test_url('http://192.168.8.115:5000/analytics/dashboard')

# Test main dashboard on network IP
test_url('http://192.168.8.115:5000/dashboard')

print("=" * 80)
