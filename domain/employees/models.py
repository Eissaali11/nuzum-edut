"""Shim to preserve legacy imports for employees domain models."""
from modules.employees.domain.models import (
    user_accessible_departments,
    employee_departments,
    employee_geofences,
    Department,
    Nationality,
    Employee,
    EmployeeLocation,
    Attendance,
    Salary,
    Document,
)

__all__ = [
    "user_accessible_departments",
    "employee_departments",
    "employee_geofences",
    "Department",
    "Nationality",
    "Employee",
    "EmployeeLocation",
    "Attendance",
    "Salary",
    "Document",
]
