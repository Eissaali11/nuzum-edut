"""Mobile reports routes extracted from routes/mobile.py."""

from datetime import datetime, timedelta

from flask import redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from core.extensions import db
from models import Attendance, Department, Document, Employee, FeesCost as Fee, Salary, Vehicle


def register_reports_routes(mobile_bp):
    @mobile_bp.route('/reports')
    @login_required
    def reports():
        """صفحة التقارير للنسخة المحمولة"""
        recent_reports = []
        return render_template('mobile/reports.html', recent_reports=recent_reports)

    @mobile_bp.route('/reports/employees')
    @login_required
    def report_employees():
        departments = Department.query.order_by(Department.name).all()

        department_id = request.args.get('department_id')
        status = request.args.get('status')
        search = request.args.get('search')
        export_format = request.args.get('export')

        query = Employee.query

        if department_id:
            query = query.filter_by(department_id=department_id)

        if status:
            query = query.filter_by(status=status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Employee.name.like(search_term))
                | (Employee.employee_id.like(search_term))
                | (Employee.national_id.like(search_term))
                | (Employee.job_title.like(search_term))
            )

        employees = query.order_by(Employee.name).all()

        if export_format:
            try:
                if export_format == 'pdf':
                    return redirect(
                        url_for(
                            'reports.export_employees_report',
                            export_type='pdf',
                            department_id=department_id,
                            status=status,
                            search=search,
                        )
                    )
                if export_format == 'excel':
                    return redirect(
                        url_for(
                            'reports.export_employees_report',
                            export_type='excel',
                            department_id=department_id,
                            status=status,
                            search=search,
                        )
                    )
            except Exception as e:
                print(f"خطأ في تصدير تقرير الموظفين: {str(e)}")

        return render_template('mobile/report_employees.html', departments=departments, employees=employees)

    @mobile_bp.route('/reports/attendance')
    @login_required
    def report_attendance():
        departments = Department.query.order_by(Department.name).all()

        department_id = request.args.get('department_id')
        employee_id = request.args.get('employee_id')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        export_format = request.args.get('export')

        employees_query = Employee.query
        if department_id:
            employees_query = employees_query.filter_by(department_id=department_id)
        employees = employees_query.order_by(Employee.name).all()

        attendance_query = Attendance.query

        if employee_id:
            attendance_query = attendance_query.filter_by(employee_id=employee_id)
        elif department_id:
            attendance_query = attendance_query.join(Employee).filter(Employee.department_id == department_id)

        if status:
            attendance_query = attendance_query.filter_by(status=status)

        if start_date:
            attendance_query = attendance_query.filter(Attendance.date >= start_date)

        if end_date:
            attendance_query = attendance_query.filter(Attendance.date <= end_date)

        attendance_records = attendance_query.order_by(Attendance.date.desc()).all()

        if export_format:
            try:
                if export_format == 'pdf':
                    return redirect(
                        url_for(
                            'reports.attendance_pdf',
                            department_id=department_id,
                            employee_id=employee_id,
                            status=status,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )
                if export_format == 'excel':
                    return redirect(
                        url_for(
                            'reports.attendance_excel',
                            department_id=department_id,
                            employee_id=employee_id,
                            status=status,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )
            except Exception as e:
                print(f"خطأ في تصدير تقرير الحضور: {str(e)}")

        return render_template(
            'mobile/report_attendance.html',
            departments=departments,
            employees=employees,
            attendance_records=attendance_records,
        )

    @mobile_bp.route('/reports/salaries')
    @login_required
    def report_salaries():
        departments = Department.query.order_by(Department.name).all()

        department_id = request.args.get('department_id')
        employee_id = request.args.get('employee_id')
        is_paid = request.args.get('is_paid')
        year = request.args.get('year')
        month = request.args.get('month')
        export_format = request.args.get('export')

        employees_query = Employee.query
        if department_id:
            employees_query = employees_query.filter_by(department_id=department_id)
        employees = employees_query.order_by(Employee.name).all()

        query = Salary.query

        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        elif department_id:
            query = query.join(Employee).filter(Employee.department_id == department_id)

        if is_paid:
            is_paid_bool = is_paid.lower() == 'true' or is_paid == '1'
            query = query.filter(Salary.is_paid == is_paid_bool)

        if year:
            query = query.filter(Salary.year == year)

        if month:
            query = query.filter(Salary.month == month)

        salaries = query.order_by(Salary.year.desc(), Salary.month.desc()).all()

        if export_format:
            try:
                if export_format == 'pdf':
                    return redirect(
                        url_for(
                            'reports.salaries_pdf',
                            department_id=department_id,
                            employee_id=employee_id,
                            is_paid=is_paid,
                            year=year,
                            month=month,
                        )
                    )
                if export_format == 'excel':
                    return redirect(
                        url_for(
                            'reports.salaries_excel',
                            department_id=department_id,
                            employee_id=employee_id,
                            is_paid=is_paid,
                            year=year,
                            month=month,
                        )
                    )
            except Exception as e:
                print(f"خطأ في تصدير تقرير الرواتب: {str(e)}")

        years_months = (
            db.session.query(Salary.year, Salary.month)
            .order_by(Salary.year.desc(), Salary.month.desc())
            .distinct()
            .all()
        )

        available_years = sorted(list(set([ym[0] for ym in years_months])), reverse=True)
        available_months = sorted(list(set([ym[1] for ym in years_months])))

        return render_template(
            'mobile/report_salaries.html',
            departments=departments,
            employees=employees,
            salaries=salaries,
            available_years=available_years,
            available_months=available_months,
        )

    @mobile_bp.route('/reports/documents')
    @login_required
    def report_documents():
        departments = Department.query.order_by(Department.name).all()
        current_date = datetime.now().date()

        department_id = request.args.get('department_id')
        employee_id = request.args.get('employee_id')
        document_type = request.args.get('document_type')
        status = request.args.get('status')
        export_format = request.args.get('export')

        employees_query = Employee.query
        if department_id:
            employees_query = employees_query.filter_by(department_id=department_id)
        employees = employees_query.order_by(Employee.name).all()

        query = Document.query

        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        elif department_id:
            query = query.join(Employee).filter(Employee.department_id == department_id)

        if document_type:
            query = query.filter_by(document_type=document_type)

        if status:
            if status == 'valid':
                valid_date = current_date + timedelta(days=60)
                query = query.filter(Document.expiry_date >= valid_date)
            elif status == 'expiring':
                expiring_min_date = current_date
                expiring_max_date = current_date + timedelta(days=60)
                query = query.filter(Document.expiry_date >= expiring_min_date, Document.expiry_date <= expiring_max_date)
            elif status == 'expired':
                query = query.filter(Document.expiry_date < current_date)

        documents = query.order_by(Document.expiry_date).all()

        if export_format:
            if export_format == 'pdf':
                return redirect(
                    url_for(
                        'reports.documents_pdf',
                        department_id=department_id,
                        employee_id=employee_id,
                        document_type=document_type,
                        status=status,
                    )
                )
            if export_format == 'excel':
                return redirect(
                    url_for(
                        'reports.documents_excel',
                        department_id=department_id,
                        employee_id=employee_id,
                        document_type=document_type,
                        status=status,
                    )
                )

        document_types = db.session.query(Document.document_type).distinct().order_by(Document.document_type).all()
        document_types = [d[0] for d in document_types if d[0]]

        for doc in documents:
            if doc.expiry_date:
                doc.days_remaining = (doc.expiry_date - current_date).days
            else:
                doc.days_remaining = None

        return render_template(
            'mobile/report_documents.html',
            departments=departments,
            employees=employees,
            documents=documents,
            document_types=document_types,
            current_date=current_date,
        )

    @mobile_bp.route('/reports/vehicles')
    @login_required
    def report_vehicles():
        vehicle_type = request.args.get('vehicle_type')
        status = request.args.get('status')
        search = request.args.get('search')
        export_format = request.args.get('export')

        query = Vehicle.query

        if vehicle_type:
            query = query.filter_by(make=vehicle_type)

        if status:
            query = query.filter_by(status=status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Vehicle.plate_number.like(search_term))
                | (Vehicle.make.like(search_term))
                | (Vehicle.model.like(search_term))
                | (Vehicle.color.like(search_term))
            )

        vehicles = query.order_by(Vehicle.plate_number).all()

        if export_format:
            try:
                if export_format == 'pdf':
                    return redirect(
                        url_for(
                            'reports.export_vehicles_report',
                            export_type='pdf',
                            vehicle_type=vehicle_type,
                            status=status,
                            search=search,
                        )
                    )
                if export_format == 'excel':
                    return redirect(
                        url_for(
                            'reports.export_vehicles_report',
                            export_type='excel',
                            vehicle_type=vehicle_type,
                            status=status,
                            search=search,
                        )
                    )
            except Exception as e:
                print(f"خطأ في تصدير تقرير المركبات: {str(e)}")

        vehicle_types = db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
        vehicle_types = [vt[0] for vt in vehicle_types if vt[0]]

        vehicle_statuses = db.session.query(Vehicle.status).distinct().order_by(Vehicle.status).all()
        vehicle_statuses = [vs[0] for vs in vehicle_statuses if vs[0]]

        make_stats = (
            db.session.query(Vehicle.make, func.count(Vehicle.id))
            .filter(Vehicle.make.isnot(None))
            .group_by(Vehicle.make)
            .order_by(func.count(Vehicle.id).desc())
            .all()
        )

        color_stats = (
            db.session.query(Vehicle.color, func.count(Vehicle.id))
            .filter(Vehicle.color.isnot(None))
            .group_by(Vehicle.color)
            .order_by(func.count(Vehicle.id).desc())
            .all()
        )

        total_vehicles = len(vehicles)
        active_vehicles = len([v for v in vehicles if v.status in ['نشط', 'متاح', 'available']])
        maintenance_vehicles = len([
            v
            for v in vehicles
            if 'صيانة' in (v.status or '') or 'maintenance' in (v.status or '')
        ])

        return render_template(
            'mobile/report_vehicles.html',
            vehicles=vehicles,
            vehicle_types=vehicle_types,
            vehicle_statuses=vehicle_statuses,
            make_stats=make_stats,
            color_stats=color_stats,
            total_vehicles=total_vehicles,
            active_vehicles=active_vehicles,
            maintenance_vehicles=maintenance_vehicles,
        )

    @mobile_bp.route('/reports/fees')
    @login_required
    def report_fees():
        fee_type = request.args.get('fee_type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        status = request.args.get('status')
        export_format = request.args.get('export')

        query = Fee.query

        if fee_type:
            query = query.filter_by(fee_type=fee_type)

        if date_from:
            query = query.filter(Fee.due_date >= date_from)

        if date_to:
            query = query.filter(Fee.due_date <= date_to)

        if status:
            is_paid_bool = status.lower() == 'paid'
            query = query.filter(Fee.is_paid == is_paid_bool)

        fees = query.order_by(Fee.due_date).all()

        if export_format:
            try:
                if export_format == 'pdf':
                    return redirect(
                        url_for(
                            'reports.export_fees_report',
                            export_type='pdf',
                            fee_type=fee_type,
                            date_from=date_from,
                            date_to=date_to,
                            status=status,
                        )
                    )
                if export_format == 'excel':
                    return redirect(
                        url_for(
                            'reports.export_fees_report',
                            export_type='excel',
                            fee_type=fee_type,
                            date_from=date_from,
                            date_to=date_to,
                            status=status,
                        )
                    )
            except Exception as e:
                print(f"خطأ في تصدير تقرير الرسوم: {str(e)}")

        fee_types = db.session.query(Fee.fee_type).distinct().order_by(Fee.fee_type).all()
        fee_types = [f[0] for f in fee_types if f[0]]

        total_fees = sum(fee.amount for fee in fees if fee.amount)
        total_paid = sum(fee.amount for fee in fees if fee.amount and fee.is_paid)
        total_unpaid = sum(fee.amount for fee in fees if fee.amount and not fee.is_paid)

        current_date = datetime.now().date()

        return render_template(
            'mobile/report_fees.html',
            fees=fees,
            fee_types=fee_types,
            total_fees=total_fees,
            total_paid=total_paid,
            total_unpaid=total_unpaid,
            current_date=current_date,
        )
