"""Test users route to see exact error"""
import sys
import traceback

# Set up the app context
import sys
sys.path.insert(0, 'D:\\nuzm')
import app as app_module
from core.extensions import db
from models import User, Department
from sqlalchemy.orm import joinedload

app = app_module.app

with app.app_context():
    try:
        print("Testing users route query...")
        
        # Test 1: Get all departments
        print("\n1. Testing Department query...")
        all_departments = Department.query.order_by(Department.name).all()
        print(f"   ✅ Found {len(all_departments)} departments")
        
        # Test 2: Get users with departments relationship
        print("\n2. Testing User query with joinedload...")
        user_query = User.query.options(joinedload(User.departments))
        all_users = user_query.order_by(User.full_name).all()
        print(f"   ✅ Found {len(all_users)} users")
        
        # Test 3: Check if users have departments
        print("\n3. Checking user attributes...")
        for user in all_users[:3]:  # Check first 3
            print(f"   User: {user.email}")
            print(f"     - full_name: {getattr(user, 'full_name', 'N/A')}")  
            print(f"     - assigned_department_id: {getattr(user, 'assigned_department_id', 'N/A')}")
            print(f"     - departments count: {len(user.departments) if hasattr(user, 'departments') else 'N/A'}")
        
        print("\n✅ All tests passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error occurred:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print("\n   Full traceback:")
        traceback.print_exc()
        sys.exit(1)
