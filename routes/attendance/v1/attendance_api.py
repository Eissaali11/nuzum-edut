from flask import jsonify, request
from sqlalchemy.orm import joinedload
from core.extensions import db

def get_department_employees(department_id):
    """Return active employees for a department (optimized).

    Uses joinedload to avoid N+1 when accessing related fields.
    """
    logger = __import__('logging').getLogger(__name__)
    try:
        # Domain models
        from modules.employees.domain.models import Department, Employee

        dept = db.session.query(Department).options(joinedload(Department.employees)).get(department_id)
        if not dept:
            return jsonify({'error': 'department not found'}), 404

        employees = [e for e in dept.employees if e.status == 'active']
        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'name': emp.name,
                'employee_id': emp.employee_id,
                'job_title': getattr(emp, 'job_title', 'غير محدد'),
                'status': emp.status
            })

        logger.info('get_department_employees: returned %d employees for dept %s', len(result), department_id)
        resp = jsonify(result)
        resp.headers['X-Attendance-Handler'] = 'MODULAR_v1'
        return resp

    except Exception as e:
        logger.exception('Error in get_department_employees')
        return jsonify({'error': str(e)}), 500
