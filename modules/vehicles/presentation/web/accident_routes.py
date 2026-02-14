"""
مسارات الحوادث المرورية — مستخرجة من routes/vehicles.py.
تُسجَّل على vehicles_bp عبر register_accident_routes(bp) للحفاظ على url_for('vehicles.xxx').
"""
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required

from core.extensions import db
from models import Vehicle, VehicleAccident, VehicleAccidentImage
from forms.vehicle_forms import VehicleAccidentForm
from modules.vehicles.application.accident_services import create_accident_record_action
from infrastructure.storage import save_uploaded_file
from utils.audit_logger import log_activity
from utils.vehicle_route_helpers import update_vehicle_state


def create_accident(id):
    """إضافة سجل حادث مروري جديد."""
    vehicle = Vehicle.query.get_or_404(id)
    form = VehicleAccidentForm()
    form.vehicle_id.data = id

    if request.method == "POST":
        if not form.validate():
            for field, errors in form.errors.items():
                for error in errors:
                    flash("خطأ في %s: %s" % (getattr(form, field).label.text, error), "danger")
        if form.validate_on_submit():
            form_data = {
                "accident_date": form.accident_date.data,
                "driver_name": form.driver_name.data,
                "accident_status": form.accident_status.data,
                "vehicle_condition": form.vehicle_condition.data,
                "deduction_amount": form.deduction_amount.data,
                "deduction_status": form.deduction_status.data,
                "liability_percentage": form.liability_percentage.data,
                "accident_file_link": form.accident_file_link.data,
                "location": form.location.data,
                "police_report": form.police_report.data,
                "insurance_claim": form.insurance_claim.data,
                "description": form.description.data,
                "notes": form.notes.data,
            }
            files_data = []
            for f in request.files.getlist("accident_images") or []:
                if f and getattr(f, "filename", None):
                    path = save_uploaded_file(f, "accidents")
                    if path:
                        files_data.append({"image_path": path, "image_type": "other"})
            result = create_accident_record_action(vehicle_id=id, form_data=form_data, files_data=files_data)
            if not result.get("success"):
                flash("❌ " + (result.get("error") or "حدث خطأ أثناء الحفظ."), "danger")
                return redirect(url_for("vehicles.create_accident", id=id))
            accident = result["accident"]
            log_activity("create", "vehicle_accident", accident.id, "تم إضافة سجل حادث مروري للسيارة: %s" % vehicle.plate_number)
            flash("تم إضافة سجل الحادث المروري بنجاح!", "success")
            return redirect(url_for("vehicles.view", id=id))

    return render_template("vehicles/create_accident.html", form=form, vehicle=vehicle)


def edit_accident(id):
    """تعديل سجل حادث مروري."""
    accident = VehicleAccident.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(accident.vehicle_id)
    form = VehicleAccidentForm(obj=accident)

    if form.validate_on_submit():
        form.populate_obj(accident)
        accident.updated_at = datetime.utcnow()
        if form.vehicle_condition.data and "شديد" in (form.vehicle_condition.data or ""):
            vehicle.status = "accident"
        elif accident.accident_status == "مغلق":
            vehicle.status = "available"
        vehicle.updated_at = datetime.utcnow()
        for f in request.files.getlist("accident_images") or []:
            if f and getattr(f, "filename", None):
                path = save_uploaded_file(f, "accidents")
                if path:
                    img = VehicleAccidentImage(accident_id=accident.id, image_path=path, image_type="other")
                    db.session.add(img)
        db.session.commit()
        update_vehicle_state(vehicle.id)
        log_activity("update", "vehicle_accident", accident.id, "تم تعديل سجل حادث مروري للسيارة: %s" % vehicle.plate_number)
        flash("تم تعديل سجل الحادث المروري بنجاح!", "success")
        return redirect(url_for("vehicles.view", id=vehicle.id))

    return render_template("vehicles/edit_accident.html", form=form, accident=accident, vehicle=vehicle)


def view_accident_details(id):
    """عرض صفحة تفاصيل الحادث المروري."""
    try:
        accident = VehicleAccident.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(accident.vehicle_id)
        accident_images = VehicleAccidentImage.query.filter_by(accident_id=id).all()
        return render_template(
            "vehicles/accident_details.html",
            accident=accident,
            vehicle=vehicle,
            accident_images=accident_images,
        )
    except Exception as e:
        current_app.logger.error("خطأ في عرض تفاصيل الحادثة: %s", str(e))
        flash("حدث خطأ في عرض تفاصيل الحادثة", "danger")
        return redirect(url_for("vehicles.index"))


def confirm_delete_accident(id):
    """عرض صفحة تأكيد حذف سجل حادث مروري."""
    accident = VehicleAccident.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(accident.vehicle_id)
    return render_template("vehicles/delete_accident.html", accident=accident, vehicle=vehicle)


def delete_accident(id):
    """حذف سجل حادث مروري."""
    accident = VehicleAccident.query.get_or_404(id)
    vehicle_id = accident.vehicle_id
    vehicle = Vehicle.query.get(vehicle_id)
    log_activity("delete", "vehicle_accident", id, "تم حذف سجل حادث مروري للسيارة: %s" % (vehicle.plate_number if vehicle else vehicle_id))
    db.session.delete(accident)
    if vehicle and vehicle.status == "accident":
        other = VehicleAccident.query.filter_by(vehicle_id=vehicle_id).filter(VehicleAccident.id != id).first()
        if not other:
            vehicle.status = "available"
            vehicle.updated_at = datetime.utcnow()
    db.session.commit()
    if vehicle:
        update_vehicle_state(vehicle_id)
    flash("تم حذف سجل الحادث المروري بنجاح!", "success")
    return redirect(url_for("vehicles.view", id=vehicle_id))


def register_accident_routes(bp):
    """تسجيل مسارات الحوادث على الـ Blueprint الممرّر (مثلاً vehicles_bp)."""
    bp.add_url_rule(
        "/<int:id>/accident/create",
        "create_accident",
        view_func=login_required(create_accident),
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/accident/<int:id>/edit",
        "edit_accident",
        view_func=login_required(edit_accident),
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/accident/<int:id>",
        "view_accident_details",
        view_func=login_required(view_accident_details),
        methods=["GET"],
    )
    bp.add_url_rule(
        "/accident/<int:id>/confirm-delete",
        "confirm_delete_accident",
        view_func=login_required(confirm_delete_accident),
        methods=["GET"],
    )
    bp.add_url_rule(
        "/accident/<int:id>/delete",
        "delete_accident",
        view_func=login_required(delete_accident),
        methods=["POST"],
    )
