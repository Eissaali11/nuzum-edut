"""Test dashboard on port 5001"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location('app_module', 'app.py')
app_module = importlib.util.module_from_spec(spec)
sys.modules['app_real'] = app_module
spec.loader.exec_module(app_module)
app = app_module.app

print("=" * 50)
print("Testing Dashboard on Port 5001")
print("=" * 50)

# Test 1: Database check
print("\n[1] Database check...")
with app.app_context():
    try:
        from models import Employee, User
        emp_count = Employee.query.count()
        user_count = User.query.count()
        print(f"    OK - Employees: {emp_count}, Users: {user_count}")
    except Exception as e:
        print(f"    ERROR - Database: {e}")
        sys.exit(1)

# Test 2: Unauthenticated access (should redirect)
print("\n[2] Testing dashboard without auth...")
with app.test_client() as client:
    resp = client.get('/dashboard/')
    if resp.status_code == 302:
        print(f"    OK - Redirect: {resp.status_code}")
    else:
        print(f"    WARN - Unexpected: {resp.status_code}")

# Test 3: Authenticated access
print("\n[3] Testing dashboard with auth...")
with app.app_context():
    with app.test_request_context('/dashboard/'):
        from flask_login import login_user
        from models import User
        
        test_user = User.query.first()
        if test_user:
            login_user(test_user)
            
            try:
                from routes.dashboard import index
                result = index()
                
                if hasattr(result, 'status_code'):
                    print(f"    OK - Response: {result.status_code}")
                elif isinstance(result, str):
                    if 'fallback' in result.lower() or 'error' in result.lower():
                        print(f"    WARN - Fallback mode")
                    else:
                        print(f"    OK - HTML: {len(result)} chars")
                else:
                    print(f"    OK - Type: {type(result).__name__}")
                    
            except Exception as e:
                print(f"    ERROR - {e}")
        else:
            print("    WARN - No users in database")

# Test 4: HTTP request
print("\n[4] Testing HTTP on 5001...")
try:
    import urllib.request
    req = urllib.request.Request('http://127.0.0.1:5001/dashboard/')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"    OK - HTTP: {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print(f"    OK - Redirect: {e.code}")
        else:
            print(f"    ERROR - HTTP: {e.code}")
except Exception as e:
    print(f"    ERROR - Connection: {e}")

print("\n" + "=" * 50)
print("Test Complete")
print("=" * 50)
