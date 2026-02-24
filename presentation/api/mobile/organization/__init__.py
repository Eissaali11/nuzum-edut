"""Mobile organization routes (employees, departments, HR)."""

from .employee_routes import register_employee_routes
from .department_routes import register_department_routes
from .hr_routes import register_hr_routes

__all__ = [
	"register_employee_routes",
	"register_department_routes",
	"register_hr_routes",
]

