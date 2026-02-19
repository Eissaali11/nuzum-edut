"""Inspection and safety-check routes extracted from vehicle_extra_routes."""

from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from core.extensions import db
from domain.employees.models import Employee
from modules.vehicles.application.vehicle_service import (
    INSPECTION_STATUS_CHOICES,
    INSPECTION_TYPE_CHOICES,
    SAFETY_CHECK_STATUS_CHOICES,
    SAFETY_CHECK_TYPE_CHOICES,
)
from modules.vehicles.domain.models import Vehicle, VehiclePeriodicInspection, VehicleSafetyCheck
from utils.vehicle_helpers import log_audit
from utils.vehicle_route_helpers import format_date_arabic, save_image


def register_vehicle_extra_inspection_safety_routes(bp):
    @bp.route('/<int:id>/inspections', methods=['GET'])
    @login_required
    def vehicle_inspections(id):
        vehicle = Vehicle.query.get_or_404(id)
        inspections = (
            VehiclePeriodicInspection.query.filter_by(vehicle_id=id)
            .order_by(VehiclePeriodicInspection.inspection_date.desc())
            .all()
        )
        for inspection in inspections:
            inspection.formatted_inspection_date = format_date_arabic(inspection.inspection_date)
            inspection.formatted_expiry_date = format_date_arabic(inspection.expiry_date)

        return render_template(
            'vehicles/inspections.html',
            vehicle=vehicle,
            inspections=inspections,
            inspection_types=INSPECTION_TYPE_CHOICES,
            inspection_statuses=INSPECTION_STATUS_CHOICES,
        )

    @bp.route('/<int:id>/inspections/create', methods=['GET', 'POST'])
    @login_required
    def create_inspection(id):
        vehicle = Vehicle.query.get_or_404(id)

        if request.method == 'POST':
            inspection_date = datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d').date()
            expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            certificate_file = None
            if 'certificate_file' in request.files and request.files['certificate_file']:
                certificate_file = save_image(request.files['certificate_file'], 'inspections')

            inspection = VehiclePeriodicInspection(
                vehicle_id=id,
                inspection_date=inspection_date,
                expiry_date=expiry_date,
                inspection_center=request.form.get('inspection_center'),
                supervisor_name=request.form.get('supervisor_name'),
                result=request.form.get('result'),
                inspection_number=request.form.get('inspection_center'),
                inspector_name=request.form.get('supervisor_name'),
                inspection_type=request.form.get('result'),
                inspection_status='valid',
                cost=float(request.form.get('cost') or 0),
                results=request.form.get('results'),
                recommendations=request.form.get('recommendations'),
                certificate_file=certificate_file,
                notes=request.form.get('notes'),
            )
            db.session.add(inspection)
            db.session.commit()

            log_audit('create', 'vehicle_inspection', inspection.id, f'تم إضافة سجل فحص دوري للسيارة: {vehicle.plate_number}')
            flash('تم إضافة سجل الفحص الدوري بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_inspections', id=id))

        return render_template(
            'vehicles/inspection_create.html',
            vehicle=vehicle,
            inspection_types=INSPECTION_TYPE_CHOICES,
        )

    @bp.route('/inspection/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_inspection(id):
        inspection = VehiclePeriodicInspection.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(inspection.vehicle_id)

        if request.method == 'POST':
            inspection.inspection_date = datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d').date()
            inspection.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            inspection.inspection_center = request.form.get('inspection_center')
            inspection.supervisor_name = request.form.get('supervisor_name')
            inspection.result = request.form.get('result')
            inspection.inspection_number = request.form.get('inspection_center')
            inspection.inspector_name = request.form.get('supervisor_name')
            inspection.inspection_type = request.form.get('result')
            inspection.inspection_status = request.form.get('inspection_status')
            inspection.cost = float(request.form.get('cost') or 0)
            inspection.results = request.form.get('results')
            inspection.recommendations = request.form.get('recommendations')
            inspection.notes = request.form.get('notes')
            inspection.updated_at = datetime.utcnow()

            if 'certificate_file' in request.files and request.files['certificate_file']:
                inspection.certificate_file = save_image(request.files['certificate_file'], 'inspections')

            db.session.commit()
            log_audit('update', 'vehicle_inspection', inspection.id, f'تم تعديل سجل فحص دوري للسيارة: {vehicle.plate_number}')
            flash('تم تعديل سجل الفحص الدوري بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_inspections', id=vehicle.id))

        return render_template(
            'vehicles/inspection_edit.html',
            inspection=inspection,
            vehicle=vehicle,
            inspection_types=INSPECTION_TYPE_CHOICES,
            inspection_statuses=INSPECTION_STATUS_CHOICES,
        )

    @bp.route('/inspection/<int:id>/confirm-delete')
    @login_required
    def confirm_delete_inspection(id):
        inspection = VehiclePeriodicInspection.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(inspection.vehicle_id)
        inspection.formatted_inspection_date = format_date_arabic(inspection.inspection_date)
        return render_template('vehicles/confirm_delete_inspection.html', inspection=inspection, vehicle=vehicle)

    @bp.route('/inspection/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_inspection(id):
        inspection = VehiclePeriodicInspection.query.get_or_404(id)
        vehicle_id = inspection.vehicle_id
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        log_audit('delete', 'vehicle_inspection', id, f'تم حذف سجل فحص دوري للسيارة: {vehicle.plate_number}')
        db.session.delete(inspection)
        db.session.commit()
        flash('تم حذف سجل الفحص الدوري بنجاح!', 'success')
        return redirect(url_for('vehicles.vehicle_inspections', id=vehicle_id))

    @bp.route('/<int:id>/safety-checks', methods=['GET'])
    @login_required
    def vehicle_safety_checks(id):
        vehicle = Vehicle.query.get_or_404(id)
        checks = (
            VehicleSafetyCheck.query.filter_by(vehicle_id=id)
            .order_by(VehicleSafetyCheck.check_date.desc())
            .all()
        )
        for check in checks:
            check.formatted_check_date = format_date_arabic(check.check_date)

        return render_template(
            'vehicles/safety_checks.html',
            vehicle=vehicle,
            checks=checks,
            check_types=SAFETY_CHECK_TYPE_CHOICES,
            check_statuses=SAFETY_CHECK_STATUS_CHOICES,
        )

    @bp.route('/<int:id>/safety-checks/create', methods=['GET', 'POST'])
    @login_required
    def create_safety_check(id):
        vehicle = Vehicle.query.get_or_404(id)
        supervisors = Employee.query.filter(Employee.job_title.contains('مشرف')).all()

        if request.method == 'POST':
            driver_id = request.form.get('driver_id') or None
            driver_name = request.form.get('driver_name')
            if driver_id:
                driver = Employee.query.get(driver_id)
                if driver:
                    driver_name = driver.name

            supervisor_id = request.form.get('supervisor_id') or None
            supervisor_name = request.form.get('supervisor_name')
            if supervisor_id:
                supervisor = Employee.query.get(supervisor_id)
                if supervisor:
                    supervisor_name = supervisor.name

            safety_check = VehicleSafetyCheck(
                vehicle_id=id,
                check_date=datetime.strptime(request.form.get('check_date'), '%Y-%m-%d').date(),
                check_type=request.form.get('check_type'),
                driver_id=driver_id,
                driver_name=driver_name,
                supervisor_id=supervisor_id,
                supervisor_name=supervisor_name,
                status=request.form.get('status'),
                check_form_link=request.form.get('check_form_link'),
                issues_found=bool(request.form.get('issues_found')),
                issues_description=request.form.get('issues_description'),
                actions_taken=request.form.get('actions_taken'),
                notes=request.form.get('notes'),
            )

            db.session.add(safety_check)
            db.session.commit()
            log_audit('create', 'vehicle_safety_check', safety_check.id, f'تم إضافة سجل فحص سلامة للسيارة: {vehicle.plate_number}')
            flash('تم إضافة سجل فحص السلامة بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_safety_checks', id=id))

        return render_template(
            'vehicles/safety_check_create.html',
            vehicle=vehicle,
            supervisors=supervisors,
            check_types=SAFETY_CHECK_TYPE_CHOICES,
            check_statuses=SAFETY_CHECK_STATUS_CHOICES,
        )

    @bp.route('/safety-check/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_safety_check(id):
        safety_check = VehicleSafetyCheck.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(safety_check.vehicle_id)
        supervisors = Employee.query.filter(Employee.job_title.contains('مشرف')).all()

        if request.method == 'POST':
            safety_check.check_date = datetime.strptime(request.form.get('check_date'), '%Y-%m-%d').date()
            safety_check.check_type = request.form.get('check_type')

            driver_id = request.form.get('driver_id') or None
            safety_check.driver_id = driver_id
            safety_check.driver_name = request.form.get('driver_name')
            if driver_id:
                driver = Employee.query.get(driver_id)
                if driver:
                    safety_check.driver_name = driver.name

            supervisor_id = request.form.get('supervisor_id') or None
            safety_check.supervisor_id = supervisor_id
            safety_check.supervisor_name = request.form.get('supervisor_name')
            if supervisor_id:
                supervisor = Employee.query.get(supervisor_id)
                if supervisor:
                    safety_check.supervisor_name = supervisor.name

            safety_check.status = request.form.get('status')
            safety_check.check_form_link = request.form.get('check_form_link')
            safety_check.issues_found = bool(request.form.get('issues_found'))
            safety_check.issues_description = request.form.get('issues_description')
            safety_check.actions_taken = request.form.get('actions_taken')
            safety_check.notes = request.form.get('notes')
            safety_check.updated_at = datetime.utcnow()

            db.session.commit()
            log_audit('update', 'vehicle_safety_check', safety_check.id, f'تم تعديل سجل فحص سلامة للسيارة: {vehicle.plate_number}')
            flash('تم تعديل سجل فحص السلامة بنجاح!', 'success')
            return redirect(url_for('vehicles.vehicle_safety_checks', id=vehicle.id))

        return render_template(
            'vehicles/safety_check_edit.html',
            safety_check=safety_check,
            vehicle=vehicle,
            supervisors=supervisors,
            check_types=SAFETY_CHECK_TYPE_CHOICES,
            check_statuses=SAFETY_CHECK_STATUS_CHOICES,
        )

    @bp.route('/safety-check/<int:id>/confirm-delete')
    @login_required
    def confirm_delete_safety_check(id):
        safety_check = VehicleSafetyCheck.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(safety_check.vehicle_id)
        safety_check.formatted_check_date = format_date_arabic(safety_check.check_date)
        return render_template('vehicles/confirm_delete_safety_check.html', check=safety_check, vehicle=vehicle)

    @bp.route('/safety-check/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_safety_check(id):
        safety_check = VehicleSafetyCheck.query.get_or_404(id)
        vehicle_id = safety_check.vehicle_id
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        log_audit('delete', 'vehicle_safety_check', id, f'تم حذف سجل فحص سلامة للسيارة: {vehicle.plate_number}')
        db.session.delete(safety_check)
        db.session.commit()

        flash('تم حذف سجل فحص السلامة بنجاح!', 'success')
        return redirect(url_for('vehicles.vehicle_safety_checks', id=vehicle_id))
