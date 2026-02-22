"""
Attendance API Endpoints
========================
Extracted from _attendance_main.py as part of modularization.
Handles JSON API endpoints for attendance data.

Routes:
    - GET /api/departments/<id>/employees : Get all employees in a department (JSON)
"""

from flask import Blueprint, jsonify
import logging

from models import Department

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/api/departments/<int:department_id>/employees')
def get_department_employees(department_id):
    """API endpoint to get all employees in a department
    
    Returns JSON with employee list:
    [
        {
            "id": 1,
            "name": "أحمد محمد",
            "employee_id": "EMP001",
            "job_title": "مهندس",
            "status": "active"
        },
        ...
    ]
    """
    try:
        # Get department first
        department = Department.query.get_or_404(department_id)
        
        # Get all active employees in this department (many-to-many relationship)
        employees = [emp for emp in department.employees if emp.status == 'active']
        
        employee_data = []
        for employee in employees:
            employee_data.append({
                'id': employee.id,
                'name': employee.name,
                'employee_id': employee.employee_id,
                'job_title': employee.job_title or 'غير محدد',
                'status': employee.status
            })
        
        logger.info(f"Retrieved {len(employee_data)} active employees from department {department_id} ({department.name})")
        return jsonify(employee_data)
    
    except Exception as e:
        logger.error(f"Error retrieving employees for department {department_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
