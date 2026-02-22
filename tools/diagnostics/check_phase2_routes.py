# Check all attendance routes in Phase 2
import os
os.environ['ATTENDANCE_USE_MODULAR'] = '2'
os.environ['DATABASE_URL'] = 'sqlite:///D:/nuzm/instance/nuzum_local.db'

from core.app_factory import create_app

app = create_app()

with app.app_context():
    rules = [r for r in app.url_map.iter_rules() if 'attendance' in r.rule]
    
    print("="*100)
    print("All Attendance Routes:")
    print("="*100)
    
    for r in sorted(rules, key=lambda x: x.rule):
        methods = ', '.join([m for m in r.methods if m not in ['HEAD', 'OPTIONS']])
        print(f"{r.endpoint:60} {methods:15} {r.rule}")
    
    print("\n" + "="*100)
    print("Edit/Delete/Employee Routes (checking 404s):")
    print("="*100)
    
    edit_rules = [r for r in rules if 'edit' in r.rule or 'delete' in r.rule or 'employee' in r.rule]
    for r in sorted(edit_rules, key=lambda x: x.rule):
        methods = ', '.join([m for m in r.methods if m not in ['HEAD', 'OPTIONS']])
        print(f"{r.endpoint:60} {methods:15} {r.rule}")
