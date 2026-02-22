#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Direct test of export methods"""

import sys
import importlib.util

# Load the app.py file directly (not the app/ package)
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

with app.app_context():
    try:
        from services.attendance_reports import AttendanceReportService
        from models import Department
        
        # List available departments
        depts = Department.query.all()
        print(f"Available departments: {len(depts)}")
        for d in depts[:5]:
            print(f"  - {d.name}")
        
        # Try to export the first department
        if depts:
            dept_name = depts[0].name
            print(f"\n\nTrying to export: {dept_name}")
            result = AttendanceReportService.export_department_details(dept_name)
            if isinstance(result, dict):
                print(f"[OK] Export successful!")
                print(f"    Filename: {result['filename']}")
                print(f"    MIME type: {result['mimetype']}")
                print(f"    Buffer size: {len(result['buffer'].getvalue())} bytes")
            else:
                print(f"[ERROR] Unexpected result type: {type(result)}")
        else:
            print("[ERROR] No departments found in database")
            
    except Exception as e:
        import traceback
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        traceback.print_exc()
