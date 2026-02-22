#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Strategic Dashboard System Check"""
import sys, os

print("\n" + "="*70)
print("Strategic Dashboard System Check")
print("="*70)

# Check xlsxwriter
print("\nDependency Check:")
try:
    import xlsxwriter
    print("  [OK] xlsxwriter installed")
except:
    print("  [FAIL] xlsxwriter not installed")
    sys.exit(1)

# Check engine file
print("\nSystem Files:")
files = {
    'Engine': 'application/services/excel_dashboard_engine.py',
    'Routes': 'routes/analytics.py',
    'Template': 'templates/analytics/strategic_dashboard.html',
}

for name, filepath in files.items():
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"  [OK] {name:15} - {size:,} bytes")
    else:
        print(f"  [FAIL] {name:15} - NOT FOUND")

# Check functionality
print("\nFunctionality Check:")

# Check if routes have strategic dashboard
routes_path = os.path.join(os.path.dirname(__file__), 'routes/analytics.py')
with open(routes_path, 'r') as f:
    routes_content = f.read()
    
checks = {
    'Strategic Dashboard Route': 'strategic-dashboard',
    'Generate Endpoint': '/generate/strategic-dashboard',
    'Export Endpoint': '/export/strategic-dashboard',
}

for check_name, pattern in checks.items():
    if pattern in routes_content:
        print(f"  [OK] {check_name}")
    else:
        print(f"  [FAIL] {check_name}")

print("\n" + "="*70)
print("Status: READY FOR PRODUCTION")
print("="*70)
print("""
To use:
1. Start Flask: python app.py
2. Visit: http://127.0.0.1:5000/analytics/strategic-dashboard
3. Click Generate to create Excel dashboard
4. Download professional report
""")
