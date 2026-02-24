"""Mobile department routes extracted from routes/mobile.py."""

from flask import render_template
from flask_login import login_required

from models import Department, Employee


def register_department_routes(mobile_bp):
    @mobile_bp.route('/departments')
    @login_required
    def departments():
        """صفحة الأقسام للنسخة المحمولة"""
        departments_items = Department.query.all()
        employees_count = Employee.query.count()

        return render_template(
            'mobile/departments.html',
            departments=departments_items,
            employees_count=employees_count,
        )

    @mobile_bp.route('/departments/add', methods=['GET', 'POST'])
    @login_required
    def add_department():
        """صفحة إضافة قسم جديد للنسخة المحمولة"""
        employees = Employee.query.order_by(Employee.name).all()
        return render_template('mobile/add_department.html', employees=employees)

    @mobile_bp.route('/departments/<int:department_id>')
    @login_required
    def department_details(department_id):
        """صفحة تفاصيل القسم للنسخة المحمولة"""
        department = Department.query.get_or_404(department_id)
        return render_template('mobile/department_details.html', department=department)
