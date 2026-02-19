"""
مسارات المركبات (ويب) — طبقة التحكم فقط.
جميع المسارات تستدعي application.vehicles.vehicle_service و application.services.
يُسجّل على الـ blueprint عبر register_vehicle_routes(vehicles_bp).
"""
from werkzeug.datastructures import CombinedMultiDict

from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from modules.vehicles.application.vehicle_export_service import (
    build_expired_documents_excel,
    build_valid_documents_excel,
    build_vehicle_excel,
    build_vehicle_pdf,
    build_vehicles_excel,
    build_vehicles_pdf_english,
)
from modules.vehicles.application.vehicle_management_service import (
    create_vehicle_record,
    delete_vehicle_record,
    update_vehicle_record,
)
from modules.vehicles.application.vehicle_service import (
    VEHICLE_STATUS_CHOICES,
    get_dashboard_context,
    get_expired_documents_context,
)
from modules.vehicles.application.vehicle_list_service import get_vehicle_list_payload
from modules.vehicles.application.vehicle_service import get_vehicle_detail_data
from forms.vehicle_forms import VehicleCreateForm, VehicleEditForm
from core.extensions import db
from domain.employees.models import Department
from core.domain.models import User
from modules.vehicles.domain.models import Vehicle


def register_vehicle_routes(bp):
    """
    تسجيل جميع مسارات المركبات على الـ blueprint المزوّد.
    استدعاء: register_vehicle_routes(vehicles_bp) من routes/vehicles.py أو app setup.
    """
    # ---- إنشاء سيارة ----
    @bp.route("/create", methods=["GET", "POST"])
    @login_required
    def create():
        """إضافة سيارة جديدة — التفويض بالكامل لـ create_vehicle_record."""
        if request.method == "POST":
            form = VehicleCreateForm(CombinedMultiDict((request.form, request.files)))
            if form.validate_on_submit():
                fd = {k: v for k, v in form.data.items() if not hasattr(v, "filename")}
                fd["authorized_users"] = request.form.getlist("authorized_users")
                ok, msg, vid = create_vehicle_record(fd, request.files, current_app.static_folder)
                flash(msg, "success" if ok else "danger")
                if ok:
                    return redirect(url_for("vehicles.view", id=vid))
                return redirect(url_for("vehicles.create"))
            flash("يرجى تصحيح البيانات في النموذج.", "danger")
            return redirect(url_for("vehicles.create"))
        return render_template(
            "vehicles/create.html",
            form=VehicleCreateForm(),
            statuses=VEHICLE_STATUS_CHOICES,
            all_users=User.query.filter_by(is_active=True).all(),
            projects=[p[0] for p in db.session.query(Vehicle.project).filter(Vehicle.project.isnot(None)).distinct().all() if p[0]],
            departments=Department.query.all(),
        )

    # ---- قائمة السيارات ----
    @bp.route("/")
    @login_required
    def index():
        """عرض قائمة السيارات مع خيارات التصفية (البيانات من vehicle_list_service)."""
        assigned_department_id = getattr(current_user, "assigned_department_id", None)
        payload = get_vehicle_list_payload(request.args, assigned_department_id=assigned_department_id)
        return render_template("vehicles/views/index.html", **payload)

    # ---- الوثائق المنتهية ----
    @bp.route("/expired-documents")
    @login_required
    def expired_documents():
        """عرض قائمة المستندات المنتهية للمركبات بشكل تفصيلي"""
        context = get_expired_documents_context()
        return render_template(
            "vehicles/expired_documents.html",
            expired_registration=context["expired_registration"],
            expired_inspection=context["expired_inspection"],
            expired_authorization=context["expired_authorization"],
            expired_all=context["expired_all"],
            today=context["today"],
        )

    # ---- تصدير الوثائق المنتهية Excel ----
    @bp.route("/expired-documents/export/excel")
    @login_required
    def export_expired_documents_excel():
        buffer, filename, mimetype = build_expired_documents_excel()
        return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)

    # ---- عرض تفاصيل سيارة ----
    @bp.route("/<int:id>")
    @login_required
    def view(id):
        """عرض تفاصيل سيارة معينة (البيانات من vehicle_service.get_vehicle_detail_data)."""
        data = get_vehicle_detail_data(id)
        if data is None:
            abort(404)
        return render_template("vehicles/views/view.html", **data)

    # ---- تعديل سيارة ----
    @bp.route("/<int:id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(id):
        """تعديل بيانات سيارة — التحقق عبر النموذج، والمنطق في vehicle_management_service."""
        vehicle = Vehicle.query.get_or_404(id)
        if request.method == "POST":
            form = VehicleEditForm(CombinedMultiDict((request.form, request.files)))
            if form.validate_on_submit():
                form_data = {k: v for k, v in form.data.items() if not hasattr(v, "filename")}
                success, message, vehicle_id = update_vehicle_record(
                    id,
                    form_data,
                    request.files,
                    upload_base_path=current_app.static_folder,
                )
                flash(message, "success" if success else "danger")
                if success:
                    return redirect(url_for("vehicles.view", id=vehicle_id))
                return redirect(url_for("vehicles.edit", id=id))
            flash("يرجى تصحيح البيانات في النموذج.", "danger")
            return redirect(url_for("vehicles.edit", id=id))
        form = VehicleEditForm(
            plate_number=vehicle.plate_number,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            color=vehicle.color,
            status=vehicle.status,
            type_of_car=vehicle.type_of_car or "",
            driver_name=vehicle.driver_name or "",
            project=vehicle.project or "",
            owned_by=vehicle.owned_by or "",
            region=vehicle.region or "",
            notes=vehicle.notes or "",
        )
        departments = Department.query.all()
        all_users = User.query.filter_by(is_active=True).all()
        return render_template(
            "vehicles/edit.html",
            vehicle=vehicle,
            form=form,
            statuses=VEHICLE_STATUS_CHOICES,
            departments=departments,
            all_users=all_users,
        )

    # ---- لوحة المعلومات ----
    @bp.route("/dashboard")
    @login_required
    def dashboard():
        """لوحة المعلومات والإحصائيات للسيارات"""
        context = get_dashboard_context()
        return render_template(
            "vehicles/dashboard.html",
            stats=context["stats"],
            monthly_costs=context["monthly_costs"],
            alerts=context["alerts"],
            rental_cost_data=context["rental_cost_data"],
            maintenance_cost_data=context["maintenance_cost_data"],
            expired_registration_vehicles=context["expired_registration_vehicles"],
            expired_inspection_vehicles=context["expired_inspection_vehicles"],
            expired_authorization_vehicles=context["expired_authorization_vehicles"],
            workshop_vehicles_list=context["workshop_vehicles_list"],
            today=context["today"],
        )

    # ---- تأكيد حذف سيارة ----
    @bp.route("/<int:id>/confirm-delete")
    @login_required
    def confirm_delete(id):
        vehicle = Vehicle.query.get_or_404(id)
        return render_template("vehicles/modals/confirm_delete.html", vehicle=vehicle)

    # ---- حذف سيارة ----
    @bp.route("/<int:id>/delete", methods=["POST"])
    @login_required
    def delete(id):
        confirmation = request.form.get("confirmation")
        if confirmation != "تأكيد":
            flash('يجب كتابة كلمة "تأكيد" للمتابعة مع عملية الحذف!', "danger")
            return redirect(url_for("vehicles.confirm_delete", id=id))
        success, message = delete_vehicle_record(id, upload_base_path=current_app.static_folder)
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("vehicles.index"))
        return redirect(url_for("vehicles.confirm_delete", id=id))

    # ---- تصدير قائمة المركبات Excel ----
    @bp.route("/report/export/excel")
    @login_required
    def export_vehicles_excel():
        status_filter = request.args.get("status", "")
        make_filter = request.args.get("make", "")
        buffer, filename, mimetype = build_vehicles_excel(status_filter=status_filter, make_filter=make_filter)
        return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)

    # ---- تصدير مركبة واحدة PDF ----
    @bp.route("/<int:id>/export/pdf")
    @login_required
    def export_vehicle_to_pdf(id):
        buffer, filename, mimetype = build_vehicle_pdf(id)
        if buffer is None:
            abort(404)
        return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)

    # ---- تصدير مركبة واحدة Excel ----
    @bp.route("/<int:id>/export/excel")
    @login_required
    def export_vehicle_to_excel(id):
        buffer, filename, mimetype = build_vehicle_excel(id)
        if buffer is None:
            abort(404)
        return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)

    # ---- تصدير الوثائق السارية Excel ----
    @bp.route("/valid-documents/export/excel")
    @login_required
    def export_valid_documents_excel():
        plate_number = request.args.get("plate_number", "").strip()
        vehicle_make = request.args.get("vehicle_make", "").strip()
        buffer, filename, mimetype = build_valid_documents_excel(
            plate_number=plate_number,
            vehicle_make=vehicle_make,
        )
        return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)

    # ---- تصدير قائمة المركبات PDF إنجليزي ----
    @bp.route("/export/pdf/english")
    @login_required
    def export_vehicles_pdf_english():
        try:
            buffer, filename, mimetype = build_vehicles_pdf_english(static_folder=current_app.static_folder)
            return send_file(buffer, download_name=filename, as_attachment=True, mimetype=mimetype)
        except Exception as e:
            current_app.logger.exception("خطأ في إنشاء تقرير PDF")
            flash(f"حدث خطأ في إنشاء التقرير: {str(e)}", "danger")
            return redirect(url_for("vehicles.index"))
