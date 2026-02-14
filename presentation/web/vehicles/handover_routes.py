"""
مسارات التسليم والاستلام — مستخرجة من routes/vehicles.py.
تُسجَّل على vehicles_bp عبر register_handover_routes(bp) للحفاظ على url_for('vehicles.xxx').
"""
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template, abort, current_app
from flask_login import login_required, current_user

from core.extensions import db
from models import (
    Vehicle,
    VehicleHandover,
    VehicleHandoverImage,
    Employee,
    Department,
)
from application.vehicles.services import get_vehicle_handover_context, create_vehicle_handover_action
from infrastructure.storage import save_base64_image, save_uploaded_file
from routes.operations import create_operation_request
from utils.vehicle_drive_uploader import VehicleDriveUploader
from utils.audit_logger import log_activity
from utils.vehicle_route_helpers import save_file, update_vehicle_state


def create_handover(id):
    """إنشاء نموذج تسليم/استلام للسيارة."""
    ctx = get_vehicle_handover_context(id)
    if ctx is None:
        abort(404)
    vehicle = ctx["vehicle"]
    if not ctx["eligible"]:
        flash("❌ " + (ctx["eligibility_message"] or ""), "danger")
        if ctx["eligibility_redirect_route"] == "vehicles.edit":
            return redirect(url_for("vehicles.edit", id=id))
        return redirect(url_for("vehicles.view", id=id, _anchor=ctx["eligibility_redirect_anchor"] or ""))

    if request.method == "GET":
        if ctx.get("info_message"):
            flash(ctx["info_message"], "info")
        employees = Employee.query.options(db.joinedload(Employee.departments)).order_by(Employee.name).all()
        departments = Department.query.order_by(Department.name).all()
        return render_template(
            "vehicles/handover_create.html",
            vehicle=vehicle,
            handover_types=["delivery", "return"],
            employees=employees,
            departments=departments,
            force_mode=ctx["force_mode"],
            info_message=ctx["info_message"],
            current_driver_info=ctx["current_driver_info"],
        )

    if request.method == "POST":
        try:
            form_data = {
                "handover_type": request.form.get("handover_type"),
                "handover_date": request.form.get("handover_date"),
                "handover_time": request.form.get("handover_time"),
                "employee_id": request.form.get("employee_id"),
                "supervisor_employee_id": request.form.get("supervisor_employee_id"),
                "person_name": request.form.get("person_name", "").strip(),
                "supervisor_name": request.form.get("supervisor_name", "").strip(),
                "mileage": int(request.form.get("mileage", 0)),
                "fuel_level": request.form.get("fuel_level"),
                "project_name": request.form.get("project_name"),
                "city": request.form.get("city"),
                "reason_for_change": request.form.get("reason_for_change"),
                "vehicle_status_summary": request.form.get("vehicle_status_summary"),
                "notes": request.form.get("notes"),
                "reason_for_authorization": request.form.get("reason_for_authorization"),
                "authorization_details": request.form.get("authorization_details"),
                "movement_officer_name": request.form.get("movement_officer_name"),
                "form_link": request.form.get("form_link"),
                "form_link_2": request.form.get("form_link_2"),
                "custom_company_name": (request.form.get("custom_company_name") or "").strip() or None,
                "has_spare_tire": "has_spare_tire" in request.form,
                "has_fire_extinguisher": "has_fire_extinguisher" in request.form,
                "has_first_aid_kit": "has_first_aid_kit" in request.form,
                "has_warning_triangle": "has_warning_triangle" in request.form,
                "has_tools": "has_tools" in request.form,
                "has_oil_leaks": "has_oil_leaks" in request.form,
                "has_gear_issue": "has_gear_issue" in request.form,
                "has_clutch_issue": "has_clutch_issue" in request.form,
                "has_engine_issue": "has_engine_issue" in request.form,
                "has_windows_issue": "has_windows_issue" in request.form,
                "has_tires_issue": "has_tires_issue" in request.form,
                "has_body_issue": "has_body_issue" in request.form,
                "has_electricity_issue": "has_electricity_issue" in request.form,
                "has_lights_issue": "has_lights_issue" in request.form,
                "has_ac_issue": "has_ac_issue" in request.form,
            }
            saved_diagram_path = save_base64_image(request.form.get("damage_diagram_data"), "diagrams")
            saved_supervisor_sig_path = save_base64_image(request.form.get("supervisor_signature_data"), "signatures")
            saved_driver_sig_path = save_base64_image(request.form.get("driver_signature_data"), "signatures")
            movement_officer_sig_path = save_base64_image(request.form.get("movement_officer_signature"), "signatures")
            custom_logo_file = request.files.get("custom_logo_file")
            saved_custom_logo_path = save_uploaded_file(custom_logo_file, "logos")
            files_data = {
                "damage_diagram_path": saved_diagram_path,
                "supervisor_signature_path": saved_supervisor_sig_path,
                "driver_signature_path": saved_driver_sig_path,
                "movement_officer_signature_path": movement_officer_sig_path,
                "custom_logo_path": saved_custom_logo_path,
            }
            result = create_vehicle_handover_action(vehicle_id=id, form_data=form_data, files_data=files_data)
            if not result.get("success"):
                flash("❌ " + (result.get("error") or "حدث خطأ أثناء الحفظ."), "danger")
                return redirect(url_for("vehicles.create_handover", id=id))
            handover = result["handover"]
            handover_type = form_data["handover_type"]
            action_type = "تسليم" if handover_type == "delivery" else "استلام"
            try:
                operation_title = f"طلب موافقة على {action_type} مركبة {vehicle.plate_number}"
                operation_description = f"تم إنشاء {action_type} للمركبة {vehicle.plate_number} من قبل {current_user.username} ويحتاج للموافقة الإدارية"
                create_operation_request(
                    operation_type="handover",
                    related_record_id=handover.id,
                    vehicle_id=vehicle.id,
                    title=operation_title,
                    description=operation_description,
                    requested_by=current_user.id,
                    priority="normal",
                )
                db.session.commit()
            except Exception as e:
                current_app.logger.error("خطأ في إنشاء طلب العملية للتسليم والاستلام: %s", str(e))
            for file in request.files.getlist("files"):
                if file and file.filename:
                    file_path, file_type = save_file(file, "handover")
                    if file_path:
                        file_description = request.form.get(f"description_{file.filename}", "")
                        file_record = VehicleHandoverImage(
                            handover_record_id=handover.id,
                            image_path=file_path,
                            image_description=file_description,
                            file_path=file_path,
                            file_type=file_type,
                            file_description=file_description,
                        )
                        db.session.add(file_record)
                        db.session.commit()
            try:
                uploader = VehicleDriveUploader()
                uploader.upload_handover_operation(handover.id)
            except Exception as e:
                current_app.logger.error("خطأ في الرفع التلقائي إلى Google Drive: %s", str(e))
            return redirect(url_for("vehicles.view", id=id))
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash("حدث خطأ غير متوقع أثناء الحفظ: %s" % str(e), "danger")
            return redirect(url_for("vehicles.create_handover", id=id))
    return redirect(url_for("vehicles.view", id=id))


def edit_handover(id):
    """تعديل بيانات نموذج تسليم/استلام."""
    handover = VehicleHandover.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
    images = VehicleHandoverImage.query.filter_by(handover_record_id=id).all()
    handover_date_str = handover.handover_date.strftime("%Y-%m-%d") if handover.handover_date else None
    handover_type_name = "تسليم" if handover.handover_type == "delivery" else "استلام"

    if request.method == "POST":
        try:
            handover_date_str = request.form.get("handover_date")
            person_name = request.form.get("person_name")
            mileage_str = request.form.get("mileage")
            fuel_level = request.form.get("fuel_level")
            vehicle_condition = request.form.get("vehicle_condition")
            form_link = request.form.get("form_link")
            form_link_2 = request.form.get("form_link_2")
            notes = request.form.get("notes")
            has_spare_tire = "has_spare_tire" in request.form
            has_fire_extinguisher = "has_fire_extinguisher" in request.form
            has_first_aid_kit = "has_first_aid_kit" in request.form
            has_warning_triangle = "has_warning_triangle" in request.form
            has_tools = "has_tools" in request.form
            handover_date = datetime.strptime(handover_date_str, "%Y-%m-%d").date() if handover_date_str else None
            try:
                mileage = int(mileage_str.replace(",", "")) if mileage_str else 0
            except (ValueError, TypeError):
                flash("خطأ في تنسيق قراءة العداد.", "danger")
                return redirect(url_for("vehicles.edit_handover", id=id))
            handover.handover_date = handover_date
            handover.person_name = person_name
            handover.mileage = mileage
            handover.fuel_level = fuel_level
            handover.vehicle_condition = vehicle_condition
            handover.form_link = form_link
            handover.form_link_2 = form_link_2
            handover.notes = notes
            handover.has_spare_tire = has_spare_tire
            handover.has_fire_extinguisher = has_fire_extinguisher
            handover.has_first_aid_kit = has_first_aid_kit
            handover.has_warning_triangle = has_warning_triangle
            handover.has_tools = has_tools
            handover.updated_at = datetime.utcnow()
            damage_diagram_data = request.form.get("damage_diagram_data")
            if damage_diagram_data and damage_diagram_data.startswith("data:image/"):
                saved_diagram_path = save_base64_image(damage_diagram_data, "diagrams")
                if saved_diagram_path:
                    handover.damage_diagram_path = saved_diagram_path
            supervisor_signature_data = request.form.get("supervisor_signature_data")
            if supervisor_signature_data and supervisor_signature_data.startswith("data:image/"):
                saved_sig = save_base64_image(supervisor_signature_data, "signatures")
                if saved_sig:
                    handover.supervisor_signature_path = saved_sig
            driver_signature_data = request.form.get("driver_signature_data")
            if driver_signature_data and driver_signature_data.startswith("data:image/"):
                saved_sig = save_base64_image(driver_signature_data, "signatures")
                if saved_sig:
                    handover.driver_signature_path = saved_sig
            for file in request.files.getlist("files"):
                if file and file.filename:
                    file_path, file_type = save_file(file, "handover")
                    if file_path:
                        file_description = request.form.get(f"description_{file.filename}", "")
                        file_record = VehicleHandoverImage(
                            handover_record_id=handover.id,
                            image_path=file_path,
                            image_description=file_description,
                            file_path=file_path,
                            file_type=file_type,
                            file_description=file_description,
                        )
                        db.session.add(file_record)
            db.session.commit()
            update_vehicle_state(vehicle.id)
            log_activity("update", "vehicle_handover", handover.id, "تم تعديل نموذج %s للسيارة: %s" % (handover_type_name, vehicle.plate_number))
            flash("تم تعديل بيانات نموذج %s بنجاح!" % handover_type_name, "success")
            return redirect(url_for("vehicles.view_handover", id=id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Error updating handover form: %s", str(e))
            flash("حدث خطأ أثناء تعديل نموذج التسليم/الاستلام: %s" % str(e), "danger")
    employees = Employee.query.order_by(Employee.name).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template(
        "vehicles/handover_create.html",
        handover=handover,
        vehicle=vehicle,
        images=images,
        handover_date=handover_date_str,
        handover_type_name=handover_type_name,
        employees=employees,
        departments=departments,
        edit_mode=True,
        handover_types=[handover.handover_type],
        force_mode=None,
        info_message=None,
        current_driver_info=None,
    )


def register_handover_routes(bp):
    """تسجيل مسارات التسليم/الاستلام على الـ Blueprint الممرّر (مثلاً vehicles_bp)."""
    bp.add_url_rule(
        "/<int:id>/handover/create",
        "create_handover",
        view_func=login_required(create_handover),
        methods=["GET", "POST"],
    )
    bp.add_url_rule(
        "/handover/<int:id>/edit",
        "edit_handover",
        view_func=login_required(edit_handover),
        methods=["GET", "POST"],
    )
