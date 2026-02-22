#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test if departments are loaded"""

import urllib.request
import urllib.error

try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/payroll/review?month=2&year=2026&status=approved', timeout=15)
    content = r.read().decode('utf-8')
    
    # تحقق من وجود الأقسام
    if 'option value=""' in content and 'كل الأقسام' in content:
        print("✅ الصفحة تحتوي على dropdown الأقسام")
        
        # ابحث عن الأقسام
        lines = content.split('\n')
        dept_lines = [l.strip() for l in lines if 'option value=' in l and 'departmentFilter' in content[max(0, content.find(l)-500):content.find(l)+500]]
        
        if len(dept_lines) > 1:
            print(f"✅ وجدت {len(dept_lines)} أقسام في الـ dropdown")
            for line in dept_lines[:3]:
                print(f"  {line[:100]}")
        else:
            print("❌ لم أجد أقسام في الـ dropdown")
    else:
        print("❌ الصفحة لا تحتوي على dropdown الأقسام")
        
except urllib.error.URLError as e:
    print(f"❌ الخادم لا يستجيب: {e}")
except Exception as e:
    print(f"❌ خطأ: {e}")
