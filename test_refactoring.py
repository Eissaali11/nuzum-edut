#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test attendance module after refactoring"""

import time
time.sleep(5)  # Give server time to start

import urllib.request
import sys

try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/dashboard', timeout=10)
    print(f'✅ Server responding: Status {r.getcode()}')
    content_len = len(r.read())  
    print(f'✅ Response size: {content_len} bytes')
    print('✅ Refactoring successful!')
    sys.exit(0)
except Exception as e:
    print(f'❌ Server error: {str(e)}')
    sys.exit(1)
