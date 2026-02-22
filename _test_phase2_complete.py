"""
اختبار شامل لبنية Phase 2 المكتملة
Complete Phase 2 Structure Test

يختبر جميع الـ 28 route من _attendance_main.py
مقسمة على 9 ملفات:
- attendance_helpers.py (helper functions)
- attendance_list.py (2 routes)
- attendance_record.py (5 routes)
- attendance_edit_delete.py (5 routes)
- attendance_export.py (6 routes)
- attendance_stats.py (5 routes)
- attendance_circles.py (4 routes)
- attendance_api.py (1 route)
"""

import os
import sys

# Set environment to use Phase 2
os.environ['ATTENDANCE_USE_MODULAR'] = '2'

# Import Flask and extensions
from flask import Flask
from core.extensions import db

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/nuzum_local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test-key-for-phase2-complete'

# Initialize extensions
db.init_app(app)

# Import and register attendance blueprint
print("="*70)
print("Testing Phase 2 Complete Modular Structure")
print("="*70)

try:
    from routes.attendance import attendance_bp
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    print("✓ Successfully registered attendance blueprint (Phase 2)")
except Exception as e:
    print(f"✗ Failed to register blueprint: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Display all registered routes
print("\n" + "="*70)
print("Registered Routes by Module:")
print("="*70)

attendance_routes = []
for rule in app.url_map.iter_rules():
    if '/attendance' in rule.rule:
        attendance_routes.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
            'path': rule.rule
        })

# Sort by path
attendance_routes.sort(key=lambda x: x['path'])

# Group by module (based on blueprint name)
route_groups = {
    'list': [],
    'record': [],
    'edit_delete': [],
    'export': [],
    'stats': [],
    'circles': [],
    'api': []
}

for route in attendance_routes:
    if 'list' in route['endpoint']:
        route_groups['list'].append(route)
    elif 'record' in route['endpoint']:
        route_groups['record'].append(route)
    elif 'edit_delete' in route['endpoint'] or 'delete' in route['path'] or 'edit' in route['path']:
        route_groups['edit_delete'].append(route)
    elif 'export' in route['endpoint'] or '/export' in route['path']:
        route_groups['export'].append(route)
    elif 'stats' in route['endpoint'] or 'dashboard' in route['path'] or 'employee' in route['path']:
        route_groups['stats'].append(route)
    elif 'circles' in route['endpoint'] or 'circle' in route['path']:
        route_groups['circles'].append(route)
    elif 'api' in route['endpoint']:
        route_groups['api'].append(route)

# Display grouped routes
for group_name, routes in route_groups.items():
    if routes:
        module_names = {
            'list': '📋 attendance_list.py',
            'record': '📝 attendance_record.py',
            'edit_delete': '✏️ attendance_edit_delete.py',
            'export': '📊 attendance_export.py',
            'stats': '📈 attendance_stats.py',
            'circles': '🗺️ attendance_circles.py',
            'api': '🔌 attendance_api.py'
        }
        
        print(f"\n{module_names.get(group_name, group_name)}:")
        print("-" * 70)
        for route in routes:
            print(f"  {route['methods']:15} {route['path']:45}")

print("\n" + "="*70)
print(f"Total Attendance Routes: {len(attendance_routes)}/28 (Expected)")
print("="*70)

# Check if all essential routes exist
essential_routes = [
    # List (2)
    '/attendance/',
    '/attendance/department/view',
    
    # Record (5)
    '/attendance/record',
    '/attendance/department',
    '/attendance/bulk-record',
    '/attendance/all-departments',
    '/attendance/department/bulk',
    
    # Edit/Delete (5)
    '/attendance/edit/<int:id>',
    '/attendance/delete/<int:id>',
    '/attendance/delete/<int:id>/confirm',
    '/attendance/bulk_delete',
    
    # Export (6)
    '/attendance/export',
    '/attendance/export/excel',
    '/attendance/export-excel-dashboard',
    '/attendance/export-excel-department',
    '/attendance/department/export-data',
    '/attendance/department/export-period',
    
    # Stats (5)
    '/attendance/stats',
    '/attendance/dashboard',
    '/attendance/employee/<int:employee_id>',
    '/attendance/department-stats',
    '/attendance/department-details',
    
    # Circles (4)
    '/attendance/departments-circles-overview',
    '/attendance/circle-accessed-details/<int:department_id>/<circle_name>',
    '/attendance/circle-accessed-details/<int:department_id>/<circle_name>/export-excel',
    '/attendance/mark-circle-employees-attendance/<int:department_id>/<circle_name>',
    
    # API (1)
    '/attendance/api/departments/<int:department_id>/employees',
]

print("\nEssential Routes Check:")
print("-" * 70)

all_route_paths = [r['path'] for r in attendance_routes]
missing_count = 0
present_count = 0

for route_path in essential_routes:
    exists = route_path in all_route_paths
    status = "✓" if exists else "✗"
    
    if exists:
        present_count += 1
    else:
        missing_count += 1
    
    print(f"{status} {route_path}")

print("\n" + "="*70)
print(f"Summary: {present_count}/{len(essential_routes)} routes present")

if missing_count > 0:
    print(f"⚠️  Warning: {missing_count} routes missing!")
else:
    print("✅ All 28 routes successfully registered!")

print("="*70)

# File statistics
print("\nPhase 2 File Statistics:")
print("-" * 70)

import glob

attendance_files = glob.glob('routes/attendance/attendance_*.py')
total_lines = 0

for file_path in sorted(attendance_files):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())
        total_lines += lines
        print(f"  {os.path.basename(file_path):30} : {lines:4} lines")

print("-" * 70)
print(f"  {'Total (Phase 2 files)':30} : {total_lines:4} lines")
print(f"  {'Original (_attendance_main.py)':30} : 3370 lines")
print(f"  {'Reduction':30} : {3370 - total_lines:4} lines ({((3370-total_lines)/3370*100):.1f}%)")
print("="*70)

print("\n✨ Phase 2 Structure Test Complete! ✨\n")
