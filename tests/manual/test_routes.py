import urllib.request
import urllib.error

routes = ['/auth/login', '/dashboard', '/backup']

for route in routes:
    url = f'http://127.0.0.1:5000{route}'
    try:
        response = urllib.request.urlopen(url, timeout=5)
        print(f'{route}: {response.getcode()}')
    except urllib.error.HTTPError as e:
        print(f'{route}: {e.code}')
    except Exception as e:
        print(f'{route}: ERROR - {e}')
