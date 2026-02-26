import importlib, traceback, os, sys

# Ensure project root is on sys.path
sys.path.insert(0, os.getcwd())

try:
    m = importlib.import_module('routes.attendance.v1.attendance_list')
    print('IMPORT_OK')
    print('HAS_department_attendance_view:', hasattr(m, 'department_attendance_view'))
    print('EXPORTS:', [n for n in dir(m) if 'department' in n])
except Exception as e:
    print('IMPORT_ERR', repr(e))
    traceback.print_exc()
