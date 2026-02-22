"""Test backup route after fixing registration"""
import urllib.request
import urllib.error

routes = [
    ('http://127.0.0.1:5000/dashboard', 'Dashboard'),
    ('http://127.0.0.1:5000/backup', 'Backup'),
    ('http://192.168.8.115:5000/backup', 'Backup Network'),
]

print("Testing routes after database_backup blueprint fix...\n")

for url, name in routes:
    try:
        response = urllib.request.urlopen(url, timeout=10)
        print(f"✅ {name}: {response.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"❌ {name}: {e.code} {e.reason}")
    except Exception as e:
        print(f"⚠️  {name}: {type(e).__name__} - {e}")

print("\n" + "="*60)
print("If Backup shows 200, the fix is successful!")
print("="*60)
