#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '.')

# Try direct simple test
try:
    # Import models to ensure tables exist
    from models import Attendance, Employee, Department
    from services.attendance_engine import AttendanceEngine
    from datetime import datetime, date
    
    print("Testing AttendanceEngine.get_unified_attendance_list() directly...")
    
    # Call with correct parameters
    test_date = date.today()
    print(f"Calling with att_date={test_date}, department_id=None")
    
    result = AttendanceEngine.get_unified_attendance_list(
        att_date=test_date,
        department_id=None,
        status_filter=None
    )
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
    print("SUCCESS: Method works correctly!")
    
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
