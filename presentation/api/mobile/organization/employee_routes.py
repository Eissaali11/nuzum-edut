"""Mobile employee routes extracted from routes/mobile.py."""

from datetime import datetime, timedelta, date

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

from core.extensions import db
from models import (
    Attendance,
    Department,
    Document,
    Employee,
    MobileDevice,
    Nationality,
    Salary,
    Vehicle,
    VehicleHandover,
)


def register_employee_routes(mobile_bp):
    @mobile_bp.route('/employees')
    @login_required
    def employees():
        """صفحة الموظفين للنسخة المحمولة"""
        page = request.args.get('page', 1, type=int)
        per_page = 20

        query = Employee.query

        department_id = request.args.get('department_id')
        search_query = request.args.get('search', '').strip()

        if department_id:
            dept_id = int(department_id)
            query = query.join(Employee.departments).filter(Department.id == dept_id)

        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                (Employee.name.like(search_term))
                | (Employee.employee_id.like(search_term))
                | (Employee.national_id.like(search_term))
                | (Employee.job_title.like(search_term))
            )

        query = query.order_by(Employee.name)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        employees_items = pagination.items

        departments = Department.query.order_by(Department.name).all()

        return render_template(
            'mobile/employees.html',
            employees=employees_items,
            pagination=pagination,
            departments=departments,
        )

    @mobile_bp.route('/employees/add', methods=['GET', 'POST'])
    @login_required
    def add_employee():
        """صفحة إضافة موظف جديد للنسخة المحمولة"""
        if request.method == 'POST':
            try:
                employee_id_value = request.form.get('employee_id')
                if employee_id_value:
                    existing_employee = Employee.query.filter_by(employee_id=employee_id_value).first()
                    if existing_employee:
                        flash('رقم الموظف موجود بالفعل، يرجى استخدام رقم آخر', 'danger')
                        departments = Department.query.order_by(Department.name).all()
                        nationalities = Nationality.query.order_by(Nationality.name_ar).all()
                        available_mobile_devices = MobileDevice.query.filter(
                            MobileDevice.employee_id == None
                        ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
                        return render_template(
                            'mobile/add_employee.html',
                            departments=departments,
                            nationalities=nationalities,
                            available_mobile_devices=available_mobile_devices,
                        )

                employee = Employee(
                    name=request.form.get('name'),
                    employee_id=employee_id_value,
                    national_id=request.form.get('national_id'),
                    mobile=request.form.get('mobile'),
                    email=request.form.get('email'),
                    job_title=request.form.get('job_title'),
                    nationality_id=int(request.form.get('nationality_id')) if request.form.get('nationality_id') else None,
                    department_id=int(request.form.get('department_id')) if request.form.get('department_id') else None,
                    contract_status=request.form.get('contract_status'),
                    license_status=request.form.get('license_status'),
                    employee_type=request.form.get('employee_type'),
                    status=request.form.get('status', 'active'),
                    has_mobile_custody=request.form.get('has_mobile_custody') == 'yes',
                    sponsorship_status=request.form.get('sponsorship_status'),
                    residence_details=request.form.get('residence_details'),
                    pants_size=request.form.get('pants_size'),
                    shirt_size=request.form.get('shirt_size'),
                    location=request.form.get('location'),
                    project=request.form.get('project'),
                    join_date=datetime.strptime(request.form.get('join_date'), '%Y-%m-%d').date() if request.form.get('join_date') else None,
                    birth_date=datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date() if request.form.get('birth_date') else None,
                    basic_salary=float(request.form.get('basic_salary')) if request.form.get('basic_salary') else 0,
                    attendance_bonus=float(request.form.get('attendance_bonus')) if request.form.get('attendance_bonus') else 0,
                )

                db.session.add(employee)
                db.session.flush()

                department_ids = request.form.getlist('department_ids')
                if department_ids:
                    employee.departments = Department.query.filter(Department.id.in_(department_ids)).all()

                if request.form.get('mobile_device_id'):
                    mobile_device = MobileDevice.query.get(int(request.form.get('mobile_device_id')))
                    if mobile_device:
                        mobile_device.employee_id = employee.id
                        mobile_device.assigned_date = datetime.now()
                        mobile_device.is_assigned = True

                db.session.commit()
                flash('تم إضافة الموظف بنجاح', 'success')
                return redirect(url_for('mobile.employees'))

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إضافة الموظف: {str(e)}', 'danger')

        departments = Department.query.order_by(Department.name).all()
        nationalities = Nationality.query.order_by(Nationality.name_ar).all()
        available_mobile_devices = MobileDevice.query.filter(
            MobileDevice.employee_id == None
        ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()

        return render_template(
            'mobile/add_employee.html',
            departments=departments,
            nationalities=nationalities,
            available_mobile_devices=available_mobile_devices,
        )

    @mobile_bp.route('/employees/<int:employee_id>')
    @login_required
    def employee_details(employee_id):
        """صفحة تفاصيل الموظف للنسخة المحمولة"""
        employee = Employee.query.get_or_404(employee_id)

        current_date = datetime.now().date()
        current_month_start = date(current_date.year, current_date.month, 1)
        next_month = current_date.month + 1 if current_date.month < 12 else 1
        next_year = current_date.year if current_date.month < 12 else current_date.year + 1
        current_month_end = date(next_year, next_month, 1) - timedelta(days=1)

        attendance_records = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= current_month_start.strftime('%Y-%m-%d'),
            Attendance.date <= current_month_end.strftime('%Y-%m-%d'),
        ).order_by(Attendance.date.desc()).all()

        salary = Salary.query.filter_by(employee_id=employee_id).order_by(Salary.year.desc(), Salary.month.desc()).first()
        documents = Document.query.filter_by(employee_id=employee_id).all()

        current_vehicle = VehicleHandover.query.join(Vehicle).filter(
            or_(VehicleHandover.employee_id == employee_id, VehicleHandover.supervisor_employee_id == employee_id),
            VehicleHandover.handover_type == 'delivery',
            Vehicle.status == 'in_project',
        ).order_by(VehicleHandover.handover_date.desc()).first()

        all_vehicle_handovers = VehicleHandover.query.join(Vehicle).filter(
            or_(VehicleHandover.employee_id == employee_id, VehicleHandover.supervisor_employee_id == employee_id)
        ).order_by(VehicleHandover.handover_date.desc()).all()

        return render_template(
            'mobile/employee_details.html',
            employee=employee,
            attendance_records=attendance_records,
            salary=salary,
            documents=documents,
            current_vehicle=current_vehicle,
            all_vehicle_handovers=all_vehicle_handovers,
            current_date=current_date,
        )

    @mobile_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_employee(employee_id):
        """صفحة تعديل موظف للنسخة المحمولة"""
        employee = Employee.query.get_or_404(employee_id)

        if request.method == 'POST':
            try:
                employee_id_value = request.form.get('employee_id')
                if employee_id_value and employee_id_value != employee.employee_id:
                    existing_employee = Employee.query.filter_by(employee_id=employee_id_value).first()
                    if existing_employee:
                        flash('رقم الموظف موجود بالفعل، يرجى استخدام رقم آخر', 'danger')
                        departments = Department.query.order_by(Department.name).all()
                        nationalities = Nationality.query.order_by(Nationality.name_ar).all()
                        available_mobile_devices = MobileDevice.query.filter(
                            (MobileDevice.employee_id == None) | (MobileDevice.employee_id == employee.id)
                        ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()
                        return render_template(
                            'mobile/edit_employee.html',
                            employee=employee,
                            departments=departments,
                            nationalities=nationalities,
                            available_mobile_devices=available_mobile_devices,
                        )

                employee.name = request.form.get('name')
                employee.employee_id = employee_id_value
                employee.national_id = request.form.get('national_id')
                employee.mobile = request.form.get('mobile')
                employee.email = request.form.get('email')
                employee.job_title = request.form.get('job_title')
                employee.nationality_id = int(request.form.get('nationality_id')) if request.form.get('nationality_id') else None
                employee.department_id = int(request.form.get('department_id')) if request.form.get('department_id') else None
                employee.contract_status = request.form.get('contract_status')
                employee.license_status = request.form.get('license_status')
                employee.employee_type = request.form.get('employee_type')
                employee.status = request.form.get('status', 'active')
                employee.has_mobile_custody = request.form.get('has_mobile_custody') == 'yes'
                employee.sponsorship_status = request.form.get('sponsorship_status')
                employee.residence_details = request.form.get('residence_details')
                employee.pants_size = request.form.get('pants_size')
                employee.shirt_size = request.form.get('shirt_size')
                employee.location = request.form.get('location')
                employee.project = request.form.get('project')
                employee.join_date = datetime.strptime(request.form.get('join_date'), '%Y-%m-%d').date() if request.form.get('join_date') else None
                employee.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date() if request.form.get('birth_date') else None
                employee.basic_salary = float(request.form.get('basic_salary')) if request.form.get('basic_salary') else 0
                employee.attendance_bonus = float(request.form.get('attendance_bonus')) if request.form.get('attendance_bonus') else 0
                employee.residence_location_url = request.form.get('residence_location_url')
                employee.housing_drive_links = request.form.get('housing_drive_links')
                employee.current_sponsor_name = request.form.get('current_sponsor_name')

                department_ids = request.form.getlist('department_ids')
                if department_ids:
                    employee.departments = Department.query.filter(Department.id.in_(department_ids)).all()
                else:
                    employee.departments = []

                old_device = MobileDevice.query.filter_by(employee_id=employee.id).first()
                if old_device:
                    old_device.employee_id = None
                    old_device.assigned_date = None
                    old_device.is_assigned = False

                if request.form.get('mobile_device_id'):
                    mobile_device = MobileDevice.query.get(int(request.form.get('mobile_device_id')))
                    if mobile_device:
                        mobile_device.employee_id = employee.id
                        mobile_device.assigned_date = datetime.now()
                        mobile_device.is_assigned = True

                db.session.commit()
                flash('تم تحديث بيانات الموظف بنجاح', 'success')
                return redirect(url_for('mobile.employee_details', employee_id=employee.id))

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث الموظف: {str(e)}', 'danger')

        departments = Department.query.order_by(Department.name).all()
        nationalities = Nationality.query.order_by(Nationality.name_ar).all()

        available_mobile_devices = MobileDevice.query.filter(
            (MobileDevice.employee_id == None) | (MobileDevice.employee_id == employee.id)
        ).order_by(MobileDevice.device_brand, MobileDevice.device_model).all()

        return render_template(
            'mobile/edit_employee.html',
            employee=employee,
            departments=departments,
            nationalities=nationalities,
            available_mobile_devices=available_mobile_devices,
        )
