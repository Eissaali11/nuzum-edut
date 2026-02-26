import time
import importlib
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
app_module = importlib.import_module('app')
app = getattr(app_module, 'app')

endpoints = [('/attendance/', 'INDEX'), ('/attendance/dashboard', 'DASHBOARD'), ('/attendance/api/departments/1/employees', 'API')]

with app.test_client() as c:
    for path, name in endpoints:
        t0 = time.perf_counter()
        res = c.get(path)
        t1 = time.perf_counter()
        ms = (t1 - t0) * 1000.0
        handler = res.headers.get('X-Attendance-Handler', 'UNKNOWN')
        print(f"{name}\t{res.status_code}\t{handler}\t{ms:.2f} ms")
