"""
مسارات الورشة — مستخرجة من routes/vehicles.py.
تُسجَّل على vehicles_bp عبر register_workshop_routes(bp) للحفاظ على url_for('vehicles.xxx').
"""
import urllib.parse
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template, current_app, send_file
from flask_login import login_required
from sqlalchemy import func

from src.core.extensions import db
from src.modules.vehicles.domain.models import Vehicle, VehicleWorkshop, VehicleWorkshopImage
from src.modules.vehicles.application.workshop_services import create_workshop_record_action
from src.infrastructure.storage import save_uploaded_file
from src.utils.vehicle_drive_uploader import VehicleDriveUploader
from src.utils.audit_logger import log_activity
from src.utils.vehicle_route_helpers import (
    format_date_arabic,
    save_file,
    save_image,
    update_vehicle_state,
    check_vehicle_operation_restrictions,
)
from src.utils.vehicle_helpers import log_audit

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


def confirm_delete_workshop_image(id):
    """صفحة تأكيد حذف صورة من سجل الورشة"""
    image = VehicleWorkshopImage.query.get_or_404(id)
    workshop = VehicleWorkshop.query.get_or_404(image.workshop_record_id)
    vehicle = Vehicle.query.get_or_404(workshop.vehicle_id)
    return render_template(
        "vehicles/confirm_delete_workshop_image.html",
        image=image,
        workshop=workshop,
        vehicle=vehicle,
    )


def delete_workshop_image(id):
    """حذف صورة من سجل الورشة"""
    image = VehicleWorkshopImage.query.get_or_404(id)
    workshop_id = image.workshop_record_id
    workshop = VehicleWorkshop.query.get_or_404(workshop_id)
    confirmation = request.form.get("confirmation")
    if confirmation != "تأكيد":
        flash("يجب كتابة كلمة \"تأكيد\" للمتابعة مع عملية الحذف!", "danger")
        return redirect(url_for("vehicles.confirm_delete_workshop_image", id=id))
    db.session.delete(image)
    db.session.commit()
    log_audit("delete", "vehicle_workshop_image", id, "تم حذف صورة من سجل الورشة للسيارة: %s" % workshop.vehicle.plate_number)
    flash("تم حذف الصورة بنجاح!", "success")
    return redirect(url_for("vehicles.edit_workshop", id=workshop_id))


def confirm_delete_workshop(id):
    """تأكيد حذف سجل ورشة"""
    record = VehicleWorkshop.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(record.vehicle_id)
    record.formatted_entry_date = format_date_arabic(record.entry_date)
    record.formatted_exit_date = format_date_arabic(record.exit_date) if record.exit_date else None
    return render_template("vehicles/confirm_delete_workshop.html", record=record, vehicle=vehicle)


def delete_workshop(id):
    """حذف سجل ورشة"""
    record = VehicleWorkshop.query.get_or_404(id)
    vehicle_id = record.vehicle_id
    if request.form.get("confirmation") != "تأكيد":
        flash("كلمة التأكيد غير صحيحة. لم يتم حذف السجل.", "danger")
        return redirect(url_for("vehicles.confirm_delete_workshop", id=id))
    log_audit("delete", "VehicleWorkshop", id, "تم حذف سجل الورشة للسيارة رقم %s" % vehicle_id)
    db.session.delete(record)
    db.session.commit()
    flash("تم حذف سجل الورشة بنجاح", "success")
    return redirect(url_for("vehicles.view", id=vehicle_id))


def export_workshop_to_pdf(id):
    """تصدير سجلات الورشة للسيارة إلى PDF"""
    from src.utils.fpdf_arabic_report import generate_workshop_report_pdf_fpdf
    vehicle = Vehicle.query.get_or_404(id)
    workshop_records = VehicleWorkshop.query.filter_by(vehicle_id=id).order_by(VehicleWorkshop.entry_date.desc()).all()
    if not workshop_records:
        flash("لا توجد سجلات ورشة لهذه المركبة!", "warning")
        return redirect(url_for("vehicles.view", id=id))
    pdf_buffer = generate_workshop_report_pdf_fpdf(vehicle, workshop_records)
    log_audit("export", "vehicle_workshop", id, "تم تصدير سجلات ورشة السيارة %s إلى PDF" % vehicle.plate_number)
    return send_file(
        pdf_buffer,
        download_name="workshop_report_%s_%s.pdf" % (vehicle.plate_number, datetime.now().strftime("%Y%m%d")),
        as_attachment=True,
        mimetype="application/pdf",
    )


def export_workshop_to_excel(id):
    """تصدير سجلات الورشة للسيارة إلى Excel"""
    from src.utils.vehicles_export import export_workshop_records_excel
    vehicle = Vehicle.query.get_or_404(id)
    workshop_records = VehicleWorkshop.query.filter_by(vehicle_id=id).order_by(VehicleWorkshop.entry_date.desc()).all()
    excel_buffer = export_workshop_records_excel(vehicle, workshop_records)
    log_audit("export", "vehicle_workshop", id, "تم تصدير سجلات ورشة السيارة %s إلى Excel" % vehicle.plate_number)
    return send_file(
        excel_buffer,
        download_name="vehicle_workshop_%s_%s.xlsx" % (vehicle.plate_number, datetime.now().strftime("%Y%m%d")),
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def share_workshop_options(id):
    """خيارات مشاركة سجلات الورشة"""
    vehicle = Vehicle.query.get_or_404(id)
    app_url = request.host_url.rstrip("/")
    pdf_url = app_url + url_for("vehicles.export_workshop_to_pdf", id=id)
    excel_url = app_url + url_for("vehicles.export_workshop_to_excel", id=id)
    whatsapp_text = "سجلات ورشة السيارة: %s - %s %s" % (vehicle.plate_number, vehicle.make, vehicle.model)
    whatsapp_url = "https://wa.me/?text=%s PDF: %s" % (urllib.parse.quote(whatsapp_text), urllib.parse.quote(pdf_url))
    email_subject = "سجلات ورشة السيارة: %s" % vehicle.plate_number
    email_body = "مرفق سجلات ورشة السيارة: %s - %s %s\n\nرابط تحميل PDF: %s\n\nرابط تحميل Excel: %s" % (vehicle.plate_number, vehicle.make, vehicle.model, pdf_url, excel_url)
    email_url = "mailto:?subject=%s&body=%s" % (urllib.parse.quote(email_subject), urllib.parse.quote(email_body))
    return render_template(
        "vehicles/share_workshop.html",
        vehicle=vehicle,
        pdf_url=pdf_url,
        excel_url=excel_url,
        whatsapp_url=whatsapp_url,
        email_url=email_url,
    )


def print_workshop_records(id):
    """عرض سجلات الورشة للطباعة"""
    vehicle = Vehicle.query.get_or_404(id)
    workshop_records = VehicleWorkshop.query.filter_by(vehicle_id=id).order_by(VehicleWorkshop.entry_date.desc()).all()
    for record in workshop_records:
        record.formatted_entry_date = format_date_arabic(record.entry_date)
        record.formatted_exit_date = format_date_arabic(record.exit_date) if record.exit_date else None
    total_maintenance_cost = db.session.query(func.sum(VehicleWorkshop.cost)).filter_by(vehicle_id=id).scalar() or 0
    days_in_workshop = sum(
        (r.exit_date - r.entry_date).days if r.exit_date else (datetime.now().date() - r.entry_date).days
        for r in workshop_records
    )
    return render_template(
        "vehicles/print_workshop.html",
        vehicle=vehicle,
        workshop_records=workshop_records,
        total_maintenance_cost=total_maintenance_cost,
        days_in_workshop=days_in_workshop,
        current_date=format_date_arabic(datetime.now().date()),
    )


def view_workshop_image(image_id):
    """عرض صورة الورشة في صفحة منفصلة"""
    image = VehicleWorkshopImage.query.get_or_404(image_id)
    workshop = VehicleWorkshop.query.get_or_404(image.workshop_record_id)
    vehicle = Vehicle.query.get_or_404(workshop.vehicle_id)
    workshop.formatted_entry_date = format_date_arabic(workshop.entry_date)
    workshop.formatted_exit_date = format_date_arabic(workshop.exit_date) if workshop.exit_date else None
    image_type_arabic = "قبل الإصلاح" if image.image_type == "before" else "بعد الإصلاح"
    return render_template(
        "vehicles/workshop_image_view.html",
        image=image,
        workshop=workshop,
        vehicle=vehicle,
        image_type_arabic=image_type_arabic,
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
    bp.add_url_rule("/workshop/image/<int:id>/confirm-delete", "confirm_delete_workshop_image", view_func=login_required(confirm_delete_workshop_image), methods=["GET"])
    bp.add_url_rule("/workshop/image/<int:id>/delete", "delete_workshop_image", view_func=login_required(delete_workshop_image), methods=["POST"])
    bp.add_url_rule("/workshop/confirm-delete/<int:id>", "confirm_delete_workshop", view_func=login_required(confirm_delete_workshop), methods=["GET"])
    bp.add_url_rule("/workshop/delete/<int:id>", "delete_workshop", view_func=login_required(delete_workshop), methods=["POST"])
    bp.add_url_rule("/<int:id>/export/workshop/pdf", "export_workshop_to_pdf", view_func=login_required(export_workshop_to_pdf), methods=["GET"])
    bp.add_url_rule("/<int:id>/export/workshop/excel", "export_workshop_to_excel", view_func=login_required(export_workshop_to_excel), methods=["GET"])
    bp.add_url_rule("/<int:id>/share/workshop", "share_workshop_options", view_func=login_required(share_workshop_options), methods=["GET"])
    bp.add_url_rule("/<int:id>/print/workshop", "print_workshop_records", view_func=login_required(print_workshop_records), methods=["GET"])
    bp.add_url_rule("/workshop-image/<int:image_id>", "view_workshop_image", view_func=login_required(view_workshop_image), methods=["GET"])