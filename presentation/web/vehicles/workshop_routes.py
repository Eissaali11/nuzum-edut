"""
مسارات الورشة — مستخرجة من routes/vehicles.py.
تُسجَّل على vehicles_bp عبر register_workshop_routes(bp) للحفاظ على url_for('vehicles.xxx').
"""
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required

from core.extensions import db
from models import Vehicle, VehicleWorkshop, VehicleWorkshopImage
from application.vehicles.workshop_services import create_workshop_record_action
from infrastructure.storage import save_uploaded_file
from utils.vehicle_drive_uploader import VehicleDriveUploader
from utils.audit_logger import log_activity
from utils.vehicle_route_helpers import (
    format_date_arabic,
    save_file,
    save_image,
    update_vehicle_state,
    check_vehicle_operation_restrictions,
)

WORKSHOP_REASON_CHOICES = ["maintenance", "breakdown", "accident"]
REPAIR_STATUS_CHOICES = ["in_progress", "completed", "pending_approval"]


def create_workshop(id):
    """إضافة سجل دخول السيارة للورشة."""
    vehicle = Vehicle.query.get_or_404(id)
    restrictions = check_vehicle_operation_restrictions(vehicle)
    if restrictions["blocked"]:
        flash(restrictions["message"], "error")
        return redirect(url_for("vehicles.view", id=id))

    if request.method == "POST":
        form_data = {
            "entry_date": request.form.get("entry_date"),
            "exit_date": request.form.get("exit_date"),
            "reason": request.form.get("reason"),
            "description": request.form.get("description"),
            "repair_status": request.form.get("repair_status"),
            "cost": request.form.get("cost", "0"),
            "workshop_name": request.form.get("workshop_name"),
            "technician_name": request.form.get("technician_name"),
            "delivery_link": request.form.get("delivery_link"),
            "reception_link": request.form.get("reception_link"),
            "notes": request.form.get("notes"),
        }
        images_data = []
        for image in request.files.getlist("before_images"):
            if image and image.filename:
                path = save_uploaded_file(image, "workshop")
                if path:
                    images_data.append({"image_type": "before", "image_path": path})
        for image in request.files.getlist("after_images"):
            if image and image.filename:
                path = save_uploaded_file(image, "workshop")
                if path:
                    images_data.append({"image_type": "after", "image_path": path})
        result = create_workshop_record_action(vehicle_id=id, form_data=form_data, images_data=images_data)
        if not result.get("success"):
            flash("❌ " + (result.get("error") or "حدث خطأ أثناء الحفظ."), "error")
            return redirect(url_for("vehicles.create_workshop", id=id))
        workshop_record = result["workshop_record"]
        try:
            uploader = VehicleDriveUploader()
            uploader.upload_workshop_record(workshop_record.id)
        except Exception as e:
            current_app.logger.error("خطأ في الرفع التلقائي إلى Google Drive: %s", str(e))
        log_activity("create", "vehicle_workshop", workshop_record.id, "تم إضافة سجل دخول الورشة للسيارة: %s" % vehicle.plate_number)
        flash("تم إضافة سجل دخول الورشة بنجاح!", "success")
        return redirect(url_for("vehicles.view", id=id))

    return render_template(
        "vehicles/workshop_create.html",
        vehicle=vehicle,
        reasons=WORKSHOP_REASON_CHOICES,
        statuses=REPAIR_STATUS_CHOICES,
    )


def edit_workshop(id):
    """تعديل سجل ورشة مع منطق ذكي لتحديث حالة السيارة."""
    workshop = VehicleWorkshop.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(workshop.vehicle_id)

    if request.method == "POST":
        try:
            exit_date_before_update = workshop.exit_date
            entry_date_str = request.form.get("entry_date")
            exit_date_str = request.form.get("exit_date")
            reason = request.form.get("reason")
            description = request.form.get("description")
            repair_status = request.form.get("repair_status")
            cost_str = request.form.get("cost", "0")
            workshop_name = request.form.get("workshop_name")
            technician_name = request.form.get("technician_name")
            delivery_link = request.form.get("delivery_link")
            reception_link = request.form.get("reception_link")
            notes = request.form.get("notes")
            new_entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date() if entry_date_str else None
            new_exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d").date() if exit_date_str else None
            new_cost = float(cost_str) if cost_str else 0.0
            workshop.entry_date = new_entry_date
            workshop.exit_date = new_exit_date
            workshop.reason = reason
            workshop.description = description
            workshop.repair_status = repair_status
            workshop.cost = new_cost
            workshop.workshop_name = workshop_name
            workshop.technician_name = technician_name
            workshop.delivery_link = delivery_link
            workshop.reception_link = reception_link
            workshop.notes = notes
            workshop.updated_at = datetime.utcnow()
            if "delivery_receipt" in request.files:
                f = request.files["delivery_receipt"]
                if f and f.filename:
                    path, _ = save_file(f, "workshop")
                    if path:
                        workshop.delivery_receipt = path
            if "pickup_receipt" in request.files:
                f = request.files["pickup_receipt"]
                if f and f.filename:
                    path, _ = save_file(f, "workshop")
                    if path:
                        workshop.pickup_receipt = path
            before_images = request.files.getlist("before_images")
            if before_images and any(img.filename for img in before_images):
                new_before_records = []
                for image in before_images:
                    if image and image.filename:
                        image_path = save_image(image, "workshop")
                        if image_path:
                            new_before_records.append(
                                VehicleWorkshopImage(workshop_record_id=workshop.id, image_type="before", image_path=image_path)
                            )
                if new_before_records:
                    for old in VehicleWorkshopImage.query.filter_by(workshop_record_id=workshop.id, image_type="before").all():
                        db.session.delete(old)
                    for record in new_before_records:
                        db.session.add(record)
            after_images = request.files.getlist("after_images")
            if after_images and any(img.filename for img in after_images):
                new_after_records = []
                for image in after_images:
                    if image and image.filename:
                        image_path = save_image(image, "workshop")
                        if image_path:
                            new_after_records.append(
                                VehicleWorkshopImage(workshop_record_id=workshop.id, image_type="after", image_path=image_path)
                            )
                if new_after_records:
                    for old in VehicleWorkshopImage.query.filter_by(workshop_record_id=workshop.id, image_type="after").all():
                        db.session.delete(old)
                    for record in new_after_records:
                        db.session.add(record)
            db.session.commit()
            if exit_date_before_update is None and new_exit_date is not None:
                update_vehicle_state(vehicle.id)
            elif exit_date_before_update is not None and new_exit_date is None:
                vehicle.status = "in_workshop"
                db.session.commit()
            log_activity("update", "vehicle_workshop", workshop.id, "تم تعديل سجل الورشة للسيارة %s" % vehicle.plate_number)
            flash("تم تعديل سجل الورشة بنجاح!", "success")
            return redirect(url_for("vehicles.view", id=vehicle.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error("خطأ في تعديل سجل الورشة: %s", str(e))
            flash("حدث خطأ أثناء حفظ التعديلات: %s" % str(e), "danger")

    before_images = VehicleWorkshopImage.query.filter_by(workshop_record_id=id, image_type="before").all()
    after_images = VehicleWorkshopImage.query.filter_by(workshop_record_id=id, image_type="after").all()
    return render_template(
        "vehicles/workshop_edit.html",
        workshop=workshop,
        vehicle=vehicle,
        before_images=before_images,
        after_images=after_images,
        reasons=WORKSHOP_REASON_CHOICES,
        statuses=REPAIR_STATUS_CHOICES,
    )


def workshop_details(workshop_id):
    """عرض تفاصيل سجل ورشة في صفحة منفصلة."""
    record = VehicleWorkshop.query.get_or_404(workshop_id)
    vehicle = Vehicle.query.get_or_404(record.vehicle_id)
    record.formatted_entry_date = format_date_arabic(record.entry_date)
    record.formatted_exit_date = format_date_arabic(record.exit_date) if record.exit_date else None
    images = VehicleWorkshopImage.query.filter_by(workshop_record_id=workshop_id).all()
    record.images = images
    current_date = format_date_arabic(datetime.now().date())
    return render_template(
        "vehicles/workshop_details.html",
        vehicle=vehicle,
        record=record,
        current_date=current_date,
    )


def register_workshop_routes(bp):
    """تسجيل مسارات الورشة على الـ Blueprint الممرّر (مثلاً vehicles_bp)."""
    bp.add_url_rule(
        "/<int:id>/workshop/create",
        "create_workshop",
        view_func=login_required(create_workshop),
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/workshop/<int:id>/edit",
        "edit_workshop",
        view_func=login_required(edit_workshop),
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/workshop-details/<int:workshop_id>",
        "workshop_details",
        view_func=login_required(workshop_details),
        methods=["GET"],
    )
