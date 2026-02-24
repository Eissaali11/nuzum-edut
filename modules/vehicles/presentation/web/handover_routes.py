"""
مسارات التسليم والاستلام — مستخرجة من routes/vehicles.py.
تُسجَّل على vehicles_bp عبر register_handover_routes(bp) للحفاظ على url_for('vehicles.xxx').
"""
from datetime import datetime
import os
import io
import base64
from flask import request, redirect, url_for, flash, render_template, abort, current_app, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.exceptions import HTTPException
import qrcode

from core.extensions import db
from modules.vehicles.domain.models import Vehicle, VehicleHandover, VehicleHandoverImage
from domain.employees.models import Employee, Department
from modules.vehicles.application.services import get_vehicle_handover_context, create_vehicle_handover_action
from infrastructure.storage import save_base64_image, save_uploaded_file
from routes.operations import create_operation_request
from utils.vehicle_drive_uploader import VehicleDriveUploader
from utils.audit_logger import log_activity
from utils.vehicle_route_helpers import save_file, update_vehicle_state, format_date_arabic
from utils.vehicle_helpers import log_audit


def _resolve_damage_diagram_image(vehicle):
    vehicle_type = ((getattr(vehicle, "type_of_car", "") or "") + " " + (getattr(vehicle, "make", "") or "")).strip().lower()

    if any(token in vehicle_type for token in ["باص", "bus", "haice", "هاي"]):
        return "images/vehicles/haice.png"
    if any(token in vehicle_type for token in ["سيدان", "sedan"]):
        return "images/vehicles/sidan.png"
    if (("شاحنة" in vehicle_type and ("نقل خفيف" in vehicle_type or "نقل حفيف" in vehicle_type))
            or "iszo" in vehicle_type or "isuzu" in vehicle_type):
        return "images/vehicles/iszo.png"
    if any(token in vehicle_type for token in ["شاحنة صغير", "شاحنة صغيرة", "دكر", "dokr"]):
        return "images/dokr.png"

    return "images/vehicle_diagram.png"


def _image_to_base64(file_path):
    if not file_path or file_path in {"None", "null"}:
        return None

    normalized = str(file_path).replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    stripped_static = normalized.replace("static/", "", 1) if normalized.startswith("static/") else normalized

    candidates = [
        normalized,
        stripped_static,
        os.path.join(current_app.root_path, normalized),
        os.path.join(current_app.root_path, stripped_static),
        os.path.join(current_app.root_path, "static", normalized),
        os.path.join(current_app.root_path, "static", stripped_static),
        os.path.join(current_app.static_folder, normalized),
        os.path.join(current_app.static_folder, stripped_static),
    ]

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        real = os.path.normpath(candidate)
        if real in seen:
            continue
        seen.add(real)
        if os.path.exists(real) and os.path.isfile(real):
            try:
                with open(real, "rb") as image_file:
                    image_data = image_file.read()
                ext = os.path.splitext(real)[1].lower()
                mime_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".webp": "image/webp",
                }.get(ext, "image/png")
                encoded = base64.b64encode(image_data).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
            except Exception:
                continue
    return None


def _qr_data_url(link):
    if not link:
        return None
    qr_image = qrcode.make(link)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _build_handover_report_context(handover):
    handover_images_b64 = []
    if getattr(handover, "images", None):
        for image in handover.images:
            path = image.get_path() if hasattr(image, "get_path") else None
            path = path or getattr(image, "file_path", None) or getattr(image, "image_path", None)
            if not path:
                continue
            lower_path = str(path).lower()
            if lower_path.endswith(".pdf"):
                continue
            image_b64 = _image_to_base64(path)
            if image_b64:
                description = image.get_description() if hasattr(image, "get_description") else None
                description = description or getattr(image, "file_description", None) or getattr(image, "image_description", None)
                handover_images_b64.append({"file_path": image_b64, "file_description": description})

    return {
        "qr_code_url": _qr_data_url(getattr(handover, "form_link", None)),
        "qr_code_url_2": _qr_data_url(getattr(handover, "form_link_2", None)),
        "damage_diagram_b64": _image_to_base64(getattr(handover, "damage_diagram_path", None)),
        "driver_signature_b64": _image_to_base64(getattr(handover, "driver_signature_path", None)),
        "supervisor_signature_b64": _image_to_base64(getattr(handover, "supervisor_signature_path", None)),
        "movement_officer_signature_b64": _image_to_base64(getattr(handover, "movement_officer_signature_path", None)),
        "custom_logo_b64": _image_to_base64(getattr(handover, "custom_logo_path", None)),
        "handover_images_b64": handover_images_b64,
    }


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
            "vehicles/handovers/handover_create.html",
            vehicle=vehicle,
            damage_diagram_image=_resolve_damage_diagram_image(vehicle),
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
        "vehicles/handovers/handover_create.html",
        handover=handover,
        vehicle=vehicle,
        damage_diagram_image=_resolve_damage_diagram_image(vehicle),
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


def view_handover(id, vehicle_id=None):
    """عرض تفاصيل نموذج تسليم/استلام"""
    handover = VehicleHandover.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
    images = VehicleHandoverImage.query.filter_by(handover_record_id=id).all()
    handover.formatted_handover_date = format_date_arabic(handover.handover_date)
    if handover.handover_type in ["delivery", "تسليم", "handover"]:
        handover_type_name = "تسليم"
    elif handover.handover_type in ["return", "استلام"]:
        handover_type_name = "استلام"
    else:
        handover_type_name = handover.handover_type
    return render_template(
        "vehicles/handovers/handover_view.html",
        handover=handover,
        vehicle=vehicle,
        images=images,
        handover_type_name=handover_type_name,
    )


def confirm_delete_handovers(vehicle_id):
    """صفحة تأكيد حذف سجلات التسليم/الاستلام المحددة"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    record_ids = request.form.getlist("handover_ids[]")
    if not record_ids:
        flash("لم يتم تحديد أي سجل للحذف!", "warning")
        return redirect(url_for("vehicles.view", id=vehicle_id))
    record_ids = [int(x) for x in record_ids]
    records = VehicleHandover.query.filter(VehicleHandover.id.in_(record_ids)).all()
    for record in records:
        if record.vehicle_id != vehicle_id:
            flash("خطأ في البيانات المرسلة! بعض السجلات لا تنتمي لهذه السيارة.", "danger")
            return redirect(url_for("vehicles.view", id=vehicle_id))
    for record in records:
        record.formatted_handover_date = format_date_arabic(record.handover_date)
    return render_template(
        "vehicles/modals/confirm_delete_handovers.html",
        vehicle=vehicle,
        records=records,
        record_ids=record_ids,
    )


def delete_handovers(vehicle_id):
    """حذف سجلات التسليم/الاستلام المحددة"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    confirmation = request.form.get("confirmation")
    if confirmation != "تأكيد":
        flash("يجب كتابة كلمة \"تأكيد\" للمتابعة مع عملية الحذف!", "danger")
        return redirect(url_for("vehicles.view", id=vehicle_id))
    record_ids = request.form.getlist("record_ids")
    if not record_ids:
        flash("لم يتم تحديد أي سجل للحذف!", "warning")
        return redirect(url_for("vehicles.view", id=vehicle_id))
    record_ids = [int(x) for x in record_ids]
    records = VehicleHandover.query.filter(VehicleHandover.id.in_(record_ids)).all()
    for record in records:
        if record.vehicle_id != vehicle_id:
            flash("خطأ في البيانات المرسلة! بعض السجلات لا تنتمي لهذه السيارة.", "danger")
            return redirect(url_for("vehicles.view", id=vehicle_id))
    for record in records:
        log_audit(
            "delete",
            "vehicle_handover",
            record.id,
            f'تم حذف سجل {"تسليم" if record.handover_type == "delivery" else "استلام"} للسيارة {vehicle.plate_number}',
        )
        db.session.delete(record)
    db.session.commit()
    update_vehicle_state(vehicle_id)
    flash("تم حذف السجل بنجاح!" if len(records) == 1 else f"تم حذف {len(records)} سجلات بنجاح!", "success")
    return redirect(url_for("vehicles.view", id=vehicle_id))


def handover_pdf(id):
    """توجيه مسار PDF الداخلي إلى المسار العام الموحّد لمنع اختلاف القوالب."""
    return redirect(url_for("vehicles.handover_pdf_public", id=id))


def handover_view_public(id):
    """عرض صفحة PDF العامة"""
    handover = VehicleHandover.query.get_or_404(id)
    vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
    return render_template(
        "vehicles/handovers/handover_pdf_public.html",
        handover=handover,
        vehicle=vehicle,
        pdf_url=url_for("vehicles.handover_pdf_public", id=id),
    )


def handover_pdf_public(id):
    """إنشاء ملف PDF لنموذج تسليم/استلام (وصول عام)"""
    try:
        handover = VehicleHandover.query.get_or_404(id)
        vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
        try:
            from utils.fpdf_handover_pdf import generate_handover_report_pdf_weasyprint
            pdf_buffer = generate_handover_report_pdf_weasyprint(handover)
        except Exception as weasy_error:
            current_app.logger.warning("WeasyPrint غير متاح للتسليم %s: %s. سيتم عرض القالب الأصلي HTML.", id, weasy_error)
            report_context = _build_handover_report_context(handover)
            html_string = render_template(
                "vehicles/handover_report.html",
                handover=handover,
                **report_context,
            )

            html_string = html_string.replace('href="static/', 'href="/static/')
            html_string = html_string.replace('src="static/', 'src="/static/')
            html_string = html_string.replace('src="images/', 'src="/static/images/')
            html_string = html_string.replace('src="uploads/', 'src="/uploads/')

            return current_app.response_class(html_string, mimetype="text/html")

        if not pdf_buffer:
            current_app.logger.error("فشل في إنشاء PDF للتسليم %s", id)
            return "خطأ في إنشاء ملف PDF. يرجى المحاولة مرة أخرى.", 500
        pdf_buffer.seek(0, 2)
        pdf_size = pdf_buffer.tell()
        pdf_buffer.seek(0)
        if pdf_size == 0:
            current_app.logger.error("PDF فارغ للتسليم %s", id)
            return "ملف PDF فارغ. يرجى المحاولة مرة أخرى.", 500
        plate_clean = (handover.vehicle.plate_number.replace(" ", "_") if handover.vehicle and handover.vehicle.plate_number else f"record_{handover.id}")
        driver_name = handover.person_name.replace(" ", "_") if handover.person_name else "غير_محدد"
        handover_type = "تسليم" if handover.handover_type == "delivery" else "استلام"
        date_str = handover.handover_date.strftime("%Y-%m-%d") if handover.handover_date else "no_date"
        filename = f"{plate_clean}_{driver_name}_{handover_type}_{date_str}.pdf"
        return send_file(pdf_buffer, download_name=filename, as_attachment=False, mimetype="application/pdf")
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error("خطأ في إنشاء PDF للتسليم %s: %s", id, e)
        return "خطأ في إنشاء الملف. يرجى المحاولة مرة أخرى.", 500


def view_handover_form(handover_id):
    """عرض النموذج الإلكتروني لسجل التسليم/الاستلام"""
    try:
        handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
        return render_template(
            "vehicles/handovers/handover_form_view.html",
            handover=handover,
            vehicle=vehicle,
        )
    except Exception as e:
        flash("حدث خطأ أثناء عرض النموذج: %s" % str(e), "danger")
        return redirect(url_for("vehicles.handovers_list"))


def update_handover_link(handover_id):
    """تحديث الرابط الخارجي لنموذج التسليم/الاستلام"""
    handover = VehicleHandover.query.get_or_404(handover_id)
    vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
    if request.method == "POST":
        form_link = request.form.get("form_link", "").strip()
        handover.form_link = form_link if form_link else None
        try:
            db.session.commit()
            flash("تم تحديث الرابط الخارجي بنجاح", "success")
            log_audit(
                "تحديث رابط نموذج خارجي",
                "VehicleHandover",
                handover.id,
                "تحديث الرابط الخارجي لنموذج %s السيارة %s" % (handover.handover_type, vehicle.plate_number),
            )
        except Exception as e:
            db.session.rollback()
            flash("خطأ في تحديث الرابط: %s" % str(e), "error")
        return redirect(url_for("vehicles.view_handover", id=handover_id))
    return render_template("vehicles/handovers/update_handover_link.html", handover=handover, vehicle=vehicle)


def confirm_delete_single_handover(handover_id):
    """صفحة تأكيد حذف سجل تسليم/استلام واحد"""
    handover = VehicleHandover.query.get_or_404(handover_id)
    vehicle = handover.vehicle
    handover.formatted_handover_date = format_date_arabic(handover.handover_date)
    return render_template(
        "vehicles/modals/confirm_delete_single_handover.html",
        handover=handover,
        vehicle=vehicle,
    )


def delete_single_handover(handover_id):
    """حذف سجل تسليم/استلام واحد"""
    handover = VehicleHandover.query.get_or_404(handover_id)
    vehicle_id = handover.vehicle_id
    vehicle = handover.vehicle
    confirmation = request.form.get("confirmation")
    if confirmation != "تأكيد":
        flash('يجب كتابة كلمة "تأكيد" للمتابعة مع عملية الحذف!', "danger")
        return redirect(url_for("vehicles.confirm_delete_single_handover", handover_id=handover_id))
    handover_type_name = "تسليم" if handover.handover_type == "delivery" else "استلام"
    log_audit("delete", "vehicle_handover", handover.id, "تم حذف سجل %s للسيارة %s" % (handover_type_name, vehicle.plate_number))
    db.session.delete(handover)
    db.session.commit()
    update_vehicle_state(vehicle_id)
    flash("تم حذف سجل %s بنجاح!" % handover_type_name, "success")
    return redirect(url_for("vehicles.view", id=vehicle_id))


def delete_handover_image(image_id):
    """حذف صورة من سجل التسليم/الاستلام (API)"""
    try:
        image = VehicleHandoverImage.query.get_or_404(image_id)
        if getattr(image, "get_path", None):
            path = image.get_path()
            if path:
                current_app.logger.info("الصورة محفوظة للأمان: %s", path)
        db.session.delete(image)
        db.session.commit()
        log_audit("delete", "handover_image", image_id, "تم حذف صورة من سجل التسليم/الاستلام رقم %s" % image.handover_record_id)
        return jsonify({"success": True, "message": "تم حذف الصورة بنجاح"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("خطأ في حذف صورة التسليم/الاستلام: %s", str(e))
        return jsonify({"success": False, "message": str(e)}), 500


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
    bp.add_url_rule("/handover/<int:id>/view", "view_handover", view_func=login_required(view_handover), methods=["GET"])
    bp.add_url_rule("/<int:vehicle_id>/handover/<int:id>", "view_handover_by_vehicle", view_func=login_required(view_handover), methods=["GET"])
    bp.add_url_rule("/<int:vehicle_id>/handovers/confirm-delete", "confirm_delete_handovers", view_func=login_required(confirm_delete_handovers), methods=["POST"])
    bp.add_url_rule("/<int:vehicle_id>/handovers/delete", "delete_handovers", view_func=login_required(delete_handovers), methods=["POST"])
    bp.add_url_rule("/handover/<int:id>/pdf", "handover_pdf", view_func=login_required(handover_pdf), methods=["GET"])
    bp.add_url_rule("/handover/<int:id>/view/public", "handover_view_public", view_func=handover_view_public, methods=["GET"])
    bp.add_url_rule("/handover/<int:id>/pdf/public", "handover_pdf_public", view_func=handover_pdf_public, methods=["GET"])
    bp.add_url_rule("/handover/<int:handover_id>/form", "view_handover_form", view_func=login_required(view_handover_form), methods=["GET"])
    bp.add_url_rule("/handover/<int:handover_id>/update_link", "update_handover_link", view_func=login_required(update_handover_link), methods=["GET", "POST"])
    bp.add_url_rule("/handover/<int:handover_id>/confirm-delete", "confirm_delete_single_handover", view_func=login_required(confirm_delete_single_handover), methods=["GET"])
    bp.add_url_rule("/handover/<int:handover_id>/delete", "delete_single_handover", view_func=login_required(delete_single_handover), methods=["POST"])
    bp.add_url_rule("/handover/image/<int:image_id>/delete", "delete_handover_image", view_func=login_required(delete_handover_image), methods=["POST"])