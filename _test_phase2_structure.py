"""
اختبار سريع للبنية الجديدة المودولار Phase 2
Quick Test for New Modular Structure Phase 2

يختبر:
- تحميل الـ blueprints الجديدة
- تسجيل الـ routes
- عرض جميع الـ endpoints المتاحة
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
app.config['SECRET_KEY'] = 'test-key-for-phase2'

# Initialize extensions
db.init_app(app)

# Import and register attendance blueprint
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
print("\n" + "="*60)
print("Registered Routes (Phase 2):")
print("="*60)

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

# Display
for route in attendance_routes:
    print(f"{route['methods']:15} {route['path']:40} → {route['endpoint']}")

print("="*60)
print(f"Total Attendance Routes: {len(attendance_routes)}")
print("="*60)

# Check if essential routes exist
essential_routes = [
    '/attendance/',
    '/attendance/record',
    '/attendance/department',
    '/attendance/bulk-record',
    '/attendance/all-departments',
    '/attendance/department/bulk',
    '/attendance/department/view'
]

print("\nEssential Routes Check:")
print("-" * 60)
for route_path in essential_routes:
    exists = any(r['path'] == route_path for r in attendance_routes)
    status = "✓" if exists else "✗"
    print(f"{status} {route_path}")

print("\n" + "="*60)
print("Phase 2 Structure Test Complete!")
print("="*60)
