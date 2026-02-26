"""Mobile maintenance and accident routes.

Extracted from vehicle_routes.py to slim the monolith and enforce strict lifecycle rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, render_template, request, url_for, redirect, flash
from flask_login import login_required

from utils.status_validator import StatusValidator
from core.extensions import db
from models import Vehicle, VehicleMaintenance, VehicleMaintenanceImage
from modules.vehicles.application.maintenance_service import MaintenanceService
from modules.vehicles.application.vehicle_mobile_service import get_maintenance_details_context


maintenance_bp = Blueprint("maintenance", __name__)


def _json_response(success: bool, message: str, data: Dict[str, Any] | None = None, status_code: int = 200):
    return jsonify({
        "status": "success" if success else "error",
        "message": message,
        "data": data or {},
    }), status_code


@maintenance_bp.route('/vehicles/<int:vehicle_id>/maintenance/send-to-workshop', methods=['POST'])
@login_required
def send_to_workshop(vehicle_id: int):
    """Send vehicle to workshop with strict status validation."""
    valid, message, _ = StatusValidator.validate_transition(vehicle_id, "in_workshop")
    if not valid:
        return _json_response(False, message, status_code=400)

    form_data = {
        "date": request.form.get("date"),
        "maintenance_type": request.form.get("maintenance_type"),
        "description": request.form.get("description"),
        "cost": request.form.get("cost"),
        "technician": request.form.get("technician"),
        "parts_replaced": request.form.get("parts_replaced"),
        "actions_taken": request.form.get("actions_taken"),
        "notes": request.form.get("notes"),
    }
    attachments = request.files.getlist("attachments") or request.files.getlist("files")

    service = MaintenanceService(static_folder=current_app.static_folder)
    success, svc_message, maintenance_id = service.send_to_workshop(vehicle_id, form_data, attachments)

    data = {"vehicle_id": vehicle_id, "maintenance_id": maintenance_id}
    return _json_response(success, svc_message, data=data, status_code=200 if success else 400)


@maintenance_bp.route('/vehicles/<int:vehicle_id>/maintenance/<int:maintenance_id>/receive', methods=['POST'])
@login_required
def receive_from_workshop(vehicle_id: int, maintenance_id: int):
    """Receive vehicle from workshop with required inspection report."""
    valid, message, _ = StatusValidator.validate_transition(vehicle_id, "available")
    if not valid:
        return _json_response(False, message, status_code=400)

    form_data = {
        "received_status": request.form.get("received_status"),
    }
    inspection_report_file = request.files.get("inspection_report") or request.files.get("receipt_file")

    service = MaintenanceService(static_folder=current_app.static_folder)
    success, svc_message, record_id = service.receive_from_workshop(
        vehicle_id,
        maintenance_id,
        form_data,
        inspection_report_file,
    )

    data = {"vehicle_id": vehicle_id, "maintenance_id": record_id}
    return _json_response(success, svc_message, data=data, status_code=200 if success else 400)


@maintenance_bp.route('/vehicles/<int:vehicle_id>/accidents/register', methods=['POST'])
@login_required
def register_accident(vehicle_id: int):
    """Register accident with strict status validation."""
    valid, message, _ = StatusValidator.validate_transition(vehicle_id, "accident")
    if not valid:
        return _json_response(False, message, status_code=400)

    form_data = {
        "accident_date": request.form.get("accident_date"),
        "driver_name": request.form.get("driver_name"),
        "driver_phone": request.form.get("driver_phone"),
        "accident_status": request.form.get("accident_status"),
        "vehicle_condition": request.form.get("vehicle_condition"),
        "severity": request.form.get("severity"),
        "description": request.form.get("description"),
        "location": request.form.get("location"),
        "notes": request.form.get("notes"),
        "police_report": request.form.get("police_report"),
        "insurance_claim": request.form.get("insurance_claim"),
        "deduction_amount": request.form.get("deduction_amount"),
        "liability_percentage": request.form.get("liability_percentage"),
    }

    requires_repair_raw = request.form.get("requires_repair")
    requires_repair = str(requires_repair_raw).lower() in {"1", "true", "yes", "on"}

    attachments = {
        "accident_report": request.files.get("accident_report"),
        "driver_id_image": request.files.get("driver_id_image"),
        "driver_license_image": request.files.get("driver_license_image"),
        "images": request.files.getlist("images") or request.files.getlist("accident_images"),
    }

    service = MaintenanceService(static_folder=current_app.static_folder)
    success, svc_message, accident_id = service.register_accident(
        vehicle_id,
        form_data,
        attachments,
        requires_repair=requires_repair,
    )

    data = {"vehicle_id": vehicle_id, "accident_id": accident_id}
    return _json_response(success, svc_message, data=data, status_code=200 if success else 400)


@maintenance_bp.route('/vehicles/maintenance/<int:maintenance_id>')
@login_required
def maintenance_details(maintenance_id: int):
    """Maintenance details page (mobile)."""
    context = get_maintenance_details_context(maintenance_id)
    if not context:
        flash('سجل الصيانة غير موجود', 'error')
        return redirect(url_for('mobile.vehicles'))

    return render_template('mobile/maintenance_details.html', **context)


@maintenance_bp.route('/vehicles/maintenance/edit/<int:maintenance_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance(maintenance_id: int):
    """Edit maintenance record (mobile)."""
    maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    vehicles = Vehicle.query.all()

    if request.method == 'POST':
        try:
            vehicle_id = request.form.get('vehicle_id')
            maintenance_type = request.form.get('maintenance_type')
            description = request.form.get('description')
            cost = request.form.get('cost', 0.0, type=float)
            date_str = request.form.get('date')
            status = request.form.get('status')
            technician = request.form.get('technician')
            notes = request.form.get('notes', '')
            parts_replaced = request.form.get('parts_replaced', '')
            actions_taken = request.form.get('actions_taken', '')

            if not vehicle_id or not maintenance_type or not description or not date_str or not status or not technician:
                flash('يرجى ملء جميع الحقول المطلوبة', 'warning')
                return render_template(
                    'mobile/edit_maintenance.html',
                    maintenance=maintenance,
                    vehicles=vehicles,
                    now=datetime.now(),
                )

            maintenance_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            receipt_image_url = request.form.get('receipt_image_url', '')
            delivery_receipt_url = request.form.get('delivery_receipt_url', '')
            pickup_receipt_url = request.form.get('pickup_receipt_url', '')

            maintenance.vehicle_id = vehicle_id
            maintenance.date = maintenance_date
            maintenance.maintenance_type = maintenance_type
            maintenance.description = description
            maintenance.status = status
            maintenance.cost = cost
            maintenance.technician = technician
            maintenance.receipt_image_url = receipt_image_url
            maintenance.delivery_receipt_url = delivery_receipt_url
            maintenance.pickup_receipt_url = pickup_receipt_url
            maintenance.parts_replaced = parts_replaced
            maintenance.actions_taken = actions_taken
            maintenance.notes = notes

            db.session.commit()

            flash('تم تحديث سجل الصيانة بنجاح', 'success')
            return redirect(url_for('maintenance.maintenance_details', maintenance_id=maintenance.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث سجل الصيانة: {str(e)}', 'danger')

    return render_template(
        'mobile/edit_maintenance.html',
        maintenance=maintenance,
        vehicles=vehicles,
        now=datetime.now(),
    )


@maintenance_bp.route('/vehicles/maintenance/delete/<int:maintenance_id>')
@login_required
def delete_maintenance(maintenance_id: int):
    """Delete maintenance record (mobile)."""
    try:
        maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)

        images = VehicleMaintenanceImage.query.filter_by(maintenance_id=maintenance_id).all()
        for image in images:
            db.session.delete(image)

        db.session.delete(maintenance)
        db.session.commit()

        flash('تم حذف سجل الصيانة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء محاولة حذف سجل الصيانة: {str(e)}', 'danger')

    return redirect(url_for('mobile.vehicles'))


def register_maintenance_routes(bp):
    """Register maintenance blueprint on the provided parent blueprint."""
    bp.register_blueprint(maintenance_bp)
