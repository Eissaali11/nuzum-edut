"""Test the upload functionality simulating the route."""
import sys
sys.path.insert(0, '.')

from app import app

with app.app_context():
    from models import Employee
    
    # Test 1: Check if Employee import works
    print("=" * 60)
    print("Test 1: Employee Model Import")
    print("=" * 60)
    
    try:
        emp = Employee.query.get(260)
        if emp:
            print(f"✅ Employee 260 found: {emp.name}")
            print(f"   Has profile_image: {hasattr(emp, 'profile_image')}")
            print(f"   Current profile_image: {emp.profile_image}")
        else:
            print(f"❌ Employee 260 not found")
    except Exception as e:
        print(f"❌ Error querying employee: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Check if upload_employee_image can be imported
    print("\n" + "=" * 60)
    print("Test 2: Import upload_employee_image")
    print("=" * 60)
    
    try:
        from modules.employees.application.io import upload_employee_image
        print("✅ upload_employee_image imported successfully")
        print(f"   Function: {upload_employee_image}")
    except Exception as e:
        print(f"❌ Error importing upload_employee_image: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check file service
    print("\n" + "=" * 60)
    print("Test 3: Import save_employee_image")
    print("=" * 60)
    
    try:
        from modules.employees.application.file_service import save_employee_image
        print("✅ save_employee_image imported successfully")
        print(f"   Function: {save_employee_image}")
    except Exception as e:
        print(f"❌ Error importing save_employee_image: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check upload directory
    print("\n" + "=" * 60)
    print("Test 4: Upload Directory")
    print("=" * 60)
    
    import os
    upload_dir = "static/uploads/employees"
    print(f"Path: {upload_dir}")
    print(f"Exists: {os.path.exists(upload_dir)}")
    print(f"Is Directory: {os.path.isdir(upload_dir) if os.path.exists(upload_dir) else 'N/A'}")
    print(f"Writable: {os.access(upload_dir, os.W_OK) if os.path.exists(upload_dir) else 'N/A'}")
    
    if os.path.exists(upload_dir):
        files = os.listdir(upload_dir)
        print(f"Files in directory: {len(files)}")
        if files:
            print(f"Sample files: {files[:5]}")
    
    print("\n" + "=" * 60)
    print("All Tests Complete")
    print("=" * 60)
