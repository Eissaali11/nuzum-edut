"""
مسارات الفحص الدوري وفحص السلامة وقائمة فحص المركبة — مستخرجة من routes/mobile.py.
تُسجَّل على mobile_bp عبر register_inspection_routes(mobile_bp).
نفس عناوين المسارات وهيكل JSON للجوال (Flutter/Dart).
"""
import json
from datetime import datetime
from flask import (
    request,
    redirect,
    url_for,
    flash,
    render_template,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user

from core.extensions import db
from models import Vehicle, Employee
from application.mobile.inspection_services import (
    create_periodic_inspection_action,
    create_safety_check_action,
    add_vehicle_checklist_action,
)
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions


def register_inspection_routes(mobile_bp):
    """تسجيل مسارات الفحوصات وقوائم الفحص على الـ blueprint المزوّد."""

    @mobile_bp.route("/vehicles/<int:vehicle_id>/periodic-inspection/create", methods=["GET", "POST"])
    @login_required
    def create_periodic_inspection(vehicle_id):
        """إنشاء فحص دوري جديد للسيارة - النسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == "POST":
            try:
                form_data = {
                    "inspection_date": request.form.get("inspection_date"),
                    "expiry_date": request.form.get("expiry_date"),
                    "inspection_center": request.form.get("inspection_center"),
                    "result": request.form.get("result"),
                    "driver_name": request.form.get("driver_name", ""),
                    "supervisor_name": request.form.get("supervisor_name", ""),
                    "notes": request.form.get("notes", ""),
                }
                success, _, message = create_periodic_inspection_action(
                    vehicle_id, form_data, current_user.id
                )
                if success:
                    flash(message, "success")
                    return redirect(url_for("mobile.vehicle_details", vehicle_id=vehicle_id))
                flash(message, "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"حدث خطأ أثناء إضافة سجل الفحص: {str(e)}", "danger")

        return render_template(
            "mobile/create_periodic_inspection.html",
            vehicle=vehicle,
            now=datetime.now(),
        )

    @mobile_bp.route("/vehicles/<int:vehicle_id>/safety-check/create", methods=["GET", "POST"])
    @login_required
    def create_safety_check(vehicle_id):
        """إنشاء فحص سلامة جديد للسيارة - النسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == "POST":
            try:
                form_data = {
                    "check_date": request.form.get("check_date"),
                    "check_type": request.form.get("check_type"),
                    "driver_name": request.form.get("driver_name", ""),
                    "supervisor_name": request.form.get("supervisor_name", ""),
                    "result": request.form.get("result"),
                    "notes": request.form.get("notes", ""),
                }
                success, _, message = create_safety_check_action(
                    vehicle_id, form_data, current_user.id
                )
                if success:
                    flash(message, "success")
                    return redirect(url_for("mobile.vehicle_details", vehicle_id=vehicle_id))
                flash(message, "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"حدث خطأ أثناء إضافة سجل الفحص: {str(e)}", "danger")

        drivers = Employee.query.filter(Employee.job_title.like("%سائق%")).order_by(Employee.name).all()
        supervisors = Employee.query.filter(Employee.job_title.like("%مشرف%")).order_by(Employee.name).all()
        return render_template(
            "mobile/create_safety_check.html",
            vehicle=vehicle,
            drivers=drivers,
            supervisors=supervisors,
            now=datetime.now(),
        )

    @mobile_bp.route("/vehicles/checklist/add", methods=["POST"])
    @login_required
    def add_vehicle_checklist():
        """إضافة فحص جديد للسيارة للنسخة المحمولة"""
        if request.method != "POST":
            return jsonify({"status": "error", "message": "طريقة غير مسموح بها"})

        data = None
        damage_markers_data = []
        uploaded_files = []
        description_for_index = {}

        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "لم يتم استلام بيانات"})
            damage_markers_data = data.get("damage_markers", [])

        elif request.content_type and "multipart/form-data" in request.content_type:
            try:
                form_data_str = request.form.get("data")
                if not form_data_str:
                    return jsonify({"status": "error", "message": "لم يتم استلام بيانات النموذج"})
                data = json.loads(form_data_str)
                damage_markers_str = request.form.get("damage_markers")
                damage_markers_data = json.loads(damage_markers_str) if damage_markers_str else []
                images_list = request.files.getlist("images") if "images" in request.files else []
                uploaded_files = list(images_list)
                for key in request.files:
                    if key.startswith("image_") and key not in ("images",):
                        uploaded_files.append(request.files[key])
                for i in range(len(uploaded_files)):
                    desc_key = f"image_description_{i}"
                    if request.form.get(desc_key):
                        description_for_index[i] = request.form.get(desc_key)
            except Exception as e:
                current_app.logger.error("خطأ في معالجة بيانات النموذج: %s", str(e))
                return jsonify({"status": "error", "message": f"خطأ في معالجة البيانات: {str(e)}"})
        else:
            return jsonify({"status": "error", "message": "نوع المحتوى غير مدعوم"})

        vehicle_id = data.get("vehicle_id")
        inspection_date_str = data.get("inspection_date")
        inspector_name = data.get("inspector_name")
        inspection_type = data.get("inspection_type")
        general_notes = data.get("general_notes", "")
        items_data = data.get("items", [])

        if not all([vehicle_id, inspection_date_str, inspector_name, inspection_type]):
            return jsonify({"status": "error", "message": "بيانات غير مكتملة، يرجى ملء جميع الحقول المطلوبة"})

        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({"status": "error", "message": "المركبة غير موجودة"})

        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions.get("blocked"):
            return jsonify({"status": "error", "message": restrictions.get("message", "السيارة غير متاحة")})

        try:
            inspection_date = datetime.strptime(inspection_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "تاريخ الفحص غير صالح"})

        success, checklist, message = add_vehicle_checklist_action(
            vehicle_id=vehicle_id,
            inspection_date=inspection_date,
            inspector_name=inspector_name,
            inspection_type=inspection_type,
            general_notes=general_notes,
            items_data=items_data,
            damage_markers_data=damage_markers_data,
            uploaded_files=uploaded_files if uploaded_files else None,
            description_for_index=description_for_index if description_for_index else None,
        )

        if success and checklist:
            return jsonify({
                "status": "success",
                "message": "تم إضافة الفحص بنجاح",
                "checklist_id": checklist.id,
            })
        return jsonify({"status": "error", "message": message or "حدث خطأ أثناء إضافة الفحص"})
