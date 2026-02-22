"""Test analytics route availability"""
import urllib.request
import urllib.error

def test_route(url, name):
    try:
        r = urllib.request.urlopen(url, timeout=10)
        print(f'✅ {name}: {r.getcode()} OK')
        return True
    except urllib.error.HTTPError as e:
        print(f'❌ {name}: {e.code} {e.reason}')
        return False
    except Exception as e:
        print(f'❌ {name}: {str(e)}')
        return False

print("=" * 60)
print("Testing Analytics Routes")
print("=" * 60)

base_url = 'http://127.0.0.1:5000'

test_route(f'{base_url}/dashboard', 'Main Dashboard')
test_route(f'{base_url}/analytics/dashboard', 'Analytics Dashboard')
test_route(f'{base_url}/analytics/api/kpis', 'Analytics KPIs API')

print("=" * 60)
