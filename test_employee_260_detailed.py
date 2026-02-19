"""Test employee 260 existence and upload functionality."""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Employee

def test_employee_260():
    """Test if employee 260 exists and has correct attributes."""
    # App is already initialized in app.py
    from app import app
    
    with app.app_context():
        print("=" * 60)
        print("Testing Employee 260")
        print("=" * 60)
        
        # Check if employee exists
        emp = Employee.query.get(260)
        
        if not emp:
            print("❌ Employee 260 NOT FOUND in database")
            print("\nSearching for employees near ID 260...")
            nearby = Employee.query.filter(Employee.id >= 250, Employee.id <= 270).all()
            if nearby:
                print(f"Found {len(nearby)} employees in range 250-270:")
                for e in nearby:
                    print(f"  - ID {e.id}: {e.name}")
            else:
                print("No employees found in range 250-270")
            return
        
        print(f"✅ Employee 260 EXISTS: {emp.name}")
        print(f"\nEmployee Details:")
        print(f"  - ID: {emp.id}")
        print(f"  - Name: {emp.name}")
        print(f"  - Status: {emp.status if hasattr(emp, 'status') else 'N/A'}")
        
        print(f"\nImage Attributes:")
        print(f"  - Has profile_image attr: {hasattr(emp, 'profile_image')}")
        print(f"  - Has national_id_image attr: {hasattr(emp, 'national_id_image')}")
        print(f"  - Has license_image attr: {hasattr(emp, 'license_image')}")
        
        if hasattr(emp, 'profile_image'):
            print(f"\nCurrent Image Values:")
            print(f"  - profile_image: {emp.profile_image}")
            print(f"  - national_id_image: {emp.national_id_image}")
            print(f"  - license_image: {emp.license_image}")
        
        # Check column definitions
        print(f"\nColumn Info:")
        for col in ['profile_image', 'national_id_image', 'license_image']:
            if hasattr(Employee, col):
                col_obj = getattr(Employee.__table__.columns, col, None)
                if col_obj is not None:
                    print(f"  - {col}: type={col_obj.type}, nullable={col_obj.nullable}")
        
        # Test upload directory
        upload_dir = "static/uploads/employees"
        print(f"\nUpload Directory Check:")
        print(f"  - Path: {upload_dir}")
        print(f"  - Exists: {os.path.exists(upload_dir)}")
        print(f"  - Is Directory: {os.path.isdir(upload_dir) if os.path.exists(upload_dir) else 'N/A'}")
        print(f"  - Writable: {os.access(upload_dir, os.W_OK) if os.path.exists(upload_dir) else 'N/A'}")
        
        print("\n" + "=" * 60)
        print("Test completed successfully")
        print("=" * 60)

if __name__ == "__main__":
    test_employee_260()
