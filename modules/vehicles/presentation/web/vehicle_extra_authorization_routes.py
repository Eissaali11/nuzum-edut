"""External authorization and export routes extracted from vehicle_extra_routes."""

import os
from datetime import datetime

from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from core.extensions import db
from domain.employees.models import Department, Employee
from modules.vehicles.application.vehicle_export_service import build_vehicle_report_excel
from modules.vehicles.domain.models import ExternalAuthorization, Vehicle
from utils.vehicle_helpers import allowed_file
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions


def register_vehicle_extra_authorization_routes(bp):
    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_external_authorization(vehicle_id, auth_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)

        if request.method == 'POST':
            try:
                employee_id = request.form.get('employee_id')
                auth.employee_id = int(employee_id) if employee_id and employee_id != 'None' else None
                auth.project_name = request.form.get('project_name')
                auth.authorization_type = request.form.get('authorization_type')
                auth.city = request.form.get('city')
                auth.external_link = request.form.get('form_link')
                auth.notes = request.form.get('notes')
                auth.manual_driver_name = request.form.get('manual_driver_name')
                auth.manual_driver_phone = request.form.get('manual_driver_phone')
                auth.manual_driver_position = request.form.get('manual_driver_position')
                auth.manual_driver_department = request.form.get('manual_driver_department')

                if 'file' in request.files and request.files['file'].filename:
                    file = request.files['file']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
                        file.save(os.path.join(upload_dir, filename))
                        auth.file_path = f"static/uploads/authorizations/{filename}"

                db.session.commit()
                flash('تم تحديث التفويض بنجاح', 'success')
                return redirect(url_for('vehicles.view', id=vehicle_id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث التفويض: {str(e)}', 'error')

        departments = Department.query.all()
        employees = Employee.query.all()
        return render_template(
            'vehicles/forms/edit_external_authorization.html',
            vehicle=vehicle,
            authorization=auth,
            departments=departments,
            employees=employees,
        )

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/approve')
    @login_required
    def approve_external_authorization(vehicle_id, auth_id):
        Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)
        try:
            auth.status = 'approved'
            db.session.commit()
            flash('تم الموافقة على التفويض بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الموافقة على التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/reject')
    @login_required
    def reject_external_authorization(vehicle_id, auth_id):
        Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)
        try:
            auth.status = 'rejected'
            db.session.commit()
            flash('تم رفض التفويض', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء رفض التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/delete')
    @login_required
    def delete_external_authorization(vehicle_id, auth_id):
        Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)
        try:
            db.session.delete(auth)
            db.session.commit()
            flash('تم حذف التفويض (الملف محفوظ بشكل آمن)', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف التفويض: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/external-authorization/create', methods=['GET', 'POST'])
    @login_required
    def create_external_authorization(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('vehicles.view', id=vehicle_id))

        if request.method == 'POST':
            try:
                driver_input_type = request.form.get('driver_input_type', 'from_list')

                if driver_input_type == 'from_list':
                    employee_id = request.form.get('employee_id')
                    if not employee_id:
                        flash('يرجى اختيار موظف من القائمة', 'error')
                        return redirect(request.url)

                    external_auth = ExternalAuthorization(
                        vehicle_id=vehicle_id,
                        employee_id=employee_id,
                        project_name=request.form.get('project_name'),
                        authorization_type=request.form.get('authorization_type'),
                        status='pending',
                        external_link=request.form.get('form_link'),
                        notes=request.form.get('notes'),
                        city=request.form.get('city'),
                    )
                else:
                    manual_name = request.form.get('manual_driver_name', '').strip()
                    if not manual_name:
                        flash('يرجى إدخال اسم السائق', 'error')
                        return redirect(request.url)

                    external_auth = ExternalAuthorization(
                        vehicle_id=vehicle_id,
                        employee_id=None,
                        project_name=request.form.get('project_name'),
                        authorization_type=request.form.get('authorization_type'),
                        status='pending',
                        external_link=request.form.get('form_link'),
                        notes=request.form.get('notes'),
                        city=request.form.get('city'),
                        manual_driver_name=manual_name,
                        manual_driver_phone=request.form.get('manual_driver_phone', '').strip(),
                        manual_driver_position=request.form.get('manual_driver_position', '').strip(),
                        manual_driver_department=request.form.get('manual_driver_department', '').strip(),
                    )

                if 'file' in request.files:
                    file = request.files['file']
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
                        file.save(os.path.join(upload_dir, filename))
                        external_auth.file_path = filename

                db.session.add(external_auth)
                db.session.commit()

                flash('تم إنشاء التفويض الخارجي بنجاح', 'success')
                return redirect(url_for('vehicles.view', id=vehicle_id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إنشاء التفويض: {str(e)}', 'error')

        departments = Department.query.all()
        employees = Employee.query.all()
        return render_template(
            'vehicles/forms/create_external_authorization.html',
            vehicle=vehicle,
            departments=departments,
            employees=employees,
        )

    @bp.route('/<int:vehicle_id>/external-authorization/<int:auth_id>/view')
    @login_required
    def view_external_authorization(vehicle_id, auth_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        auth = ExternalAuthorization.query.get_or_404(auth_id)
        return render_template('vehicles/views/view_external_authorization.html', vehicle=vehicle, authorization=auth)

    @bp.route('/vehicle-report/<int:id>')
    @login_required
    def generate_vehicle_report(id):
        try:
            buffer, filename, mimetype = build_vehicle_report_excel(id)
            if buffer is None:
                abort(404)
            return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء تقرير Excel: {str(e)}', 'danger')
            return redirect(url_for('vehicles.view', id=id))
