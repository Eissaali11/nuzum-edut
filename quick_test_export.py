#!/usr/bin/env python3
import urllib.request, urllib.parse, urllib.error

dept = urllib.parse.quote('Aramex Courier')
url = f'http://127.0.0.1:5000/attendance/export-excel-department?department={dept}'

try:
    r = urllib.request.urlopen(url, timeout=10)
    print(f'Status: {r.getcode()}')
    print(f'Content-Type: {r.headers.get("Content-Type")}')
    data = r.read()[:500]
    print(f'First bytes: {data[:100]}')
    if data[:2] == b'PK':
        print('SUCCESS: This is a valid ZIP/XLSX file!')
    else:
        print(f'ERROR: Not an Excel file. Starts with: {data[:4]}')
except urllib.error.HTTPError as e:
    print(f'HTTP Error {e.code}: {e.read()[:200]}')
except Exception as e:
    print(f'Error: {e}')
