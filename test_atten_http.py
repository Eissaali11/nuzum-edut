#!/usr/bin/env python
import urllib.request
import urllib.error

try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/attendance/', timeout=10)
    print('Status:', r.getcode())
except urllib.error.HTTPError as e:
    print('Status:', e.code)
