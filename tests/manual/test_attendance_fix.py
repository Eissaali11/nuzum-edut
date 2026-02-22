#!/usr/bin/env python3
import urllib.request
import urllib.error

try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/attendance/', timeout=10)
    print(f'Status: {r.getcode()}')
    data = r.read(500)
    print(f'Response size: {len(data)} bytes')
except urllib.error.HTTPError as e:
    print(f'HTTP Error {e.code}')
    error_body = e.read(500).decode('utf-8', errors='ignore')
    if 'TemplateNotFound' in error_body:
        print('ERROR: TemplateNotFound')
    elif 'Error' in error_body:
        print(f'ERROR: {error_body[:200]}')
    else:
        print('OK: 500 error caught (likely in the business logic)')
except Exception as e:
    print(f'Exception: {type(e).__name__}: {str(e)}')
