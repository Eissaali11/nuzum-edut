"""Check if employee 260 exists."""
from core.extensions import db
from models import Employee
from app import create_app

app = create_app()
with app.app_context():
    emp = Employee.query.get(260)
    if emp:
        print(f"Employee 260 FOUND: {emp.name}")
        print(f"Profile image: {emp.profile_image}")
        print(f"National ID: {emp.national_id_image}")
        print(f"License: {emp.license_image}")
    else:
        print("Employee 260 NOT FOUND")
