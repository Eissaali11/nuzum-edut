import importlib
import sys
from pathlib import Path

# Ensure repo root is on sys.path so top-level imports (like `app`) work when
# running this script from the `scripts/` folder or via subprocesses.
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

# The project exposes a top-level `app` Flask instance in `app.py`.
try:
    app_module = importlib.import_module('app')
    app = getattr(app_module, 'app')
except Exception as e:
    print('ERROR importing top-level app module:', repr(e))
    raise

def run():
    with app.test_client() as c:
        res1 = c.get('/attendance/')
        res2 = c.get('/attendance/dashboard')
        res3 = c.get('/attendance/api/departments/1/employees')
        print('INDEX', res1.status_code)
        print('DASHBOARD', res2.status_code)
        print('API', res3.status_code)


if __name__ == '__main__':
    run()
