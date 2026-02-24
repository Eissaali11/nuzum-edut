"""Employees web routes (module)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from models import Module, Permission, Department, Nationality, Employee
from core.extensions import db
from utils.permissions_service import can_edit, can_delete
from utils.user_helpers import require_module_access
from modules.employees.application.core import (
    list_employees_page_data,
    create_employee,
    update_employee,
    delete_employee,
)

employees_bp = Blueprint("employees", __name__, url_prefix="/employees")


DEFAULT_NATIONALITIES = [
    ("سعودي", "Saudi Arabian", "SAU"),
    ("مصري", "Egyptian", "EGY"),
    ("يمني", "Yemeni", "YEM"),
    ("سوداني", "Sudanese", "SDN"),
    ("سوري", "Syrian", "SYR"),
    ("أردني", "Jordanian", "JOR"),
    ("فلبيني", "Philippine", "PHL"),
    ("باكستاني", "Pakistani", "PAK"),
    ("هندي", "Indian", "IND"),
    ("بنغلاديشي", "Bangladeshi", "BGD"),
    ("نيبالي", "Nepalese", "NPL"),
]


def _get_nationalities_with_fallback():
    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
    if nationalities:
        return nationalities

    for name_ar, name_en, country_code in DEFAULT_NATIONALITIES:
        db.session.add(
            Nationality(name_ar=name_ar, name_en=name_en, country_code=country_code)
        )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

    return Nationality.query.order_by(Nationality.name_ar).all()


def _service_message(result):
    message = result.message
    data = result.data or {}
    if message == "employee.created":
        return "تم إنشاء الموظف بنجاح"
    if message == "employee.updated":
        return "تم تحديث بيانات الموظف وأقسامه بنجاح."
    if message == "employee.deleted":
        return "تم حذف الموظف بنجاح"
    if message == "employee.duplicate_employee_id":
        employee_id = data.get("employee_id")
        if employee_id:
            return f"رقم الموظف '{employee_id}' مستخدم بالفعل."
        return "هذه المعلومات مسجلة مسبقاً: رقم الموظف موجود بالفعل في النظام"
    if message == "employee.duplicate_national_id":
        national_id = data.get("national_id")
        if national_id:
            return f"الرقم الوطني '{national_id}' مستخدم بالفعل."
        return "هذه المعلومات مسجلة مسبقاً: رقم الهوية موجود بالفعل في النظام"
    if message == "employee.duplicate":
        return "هذه المعلومات مسجلة مسبقاً، لا يمكن تكرار بيانات الموظفين"
    if message == "employee.pending_requests":
        count = data.get("pending_count", 0)
        return f"لا يمكن حذف الموظف لديه {count} طلب(ات) معلقة. يرجى حذف الطلبات أولاً"
    if message == "employee.create_failed":
        detail = data.get("detail", "")
        return f"حدث خطأ: {detail}"
    if message == "employee.update_failed":
        detail = data.get("detail", "")
        return (
            "حدث خطأ غير متوقع أثناء عملية التحديث. يرجى المحاولة مرة أخرى. "
            f"Error updating employee (ID: {data.get('employee_id', '')}): {detail}"
        )
    if message == "employee.delete_failed":
        detail = data.get("detail", "")
        return f"حدث خطأ أثناء حذف الموظف: {detail}"
    if message == "employee.not_found":
        return "الموظف غير موجود"
    return message


def _load_create_form_data():
    departments = Department.query.all()
    nationalities = _get_nationalities_with_fallback()
    from models import ImportedPhoneNumber
    available_phone_numbers = ImportedPhoneNumber.query.filter(
        ImportedPhoneNumber.employee_id.is_(None)
    ).order_by(ImportedPhoneNumber.phone_number).all()
    from models import MobileDevice
    available_imei_numbers = MobileDevice.query.filter(
        MobileDevice.status == "متاح",
        MobileDevice.employee_id.is_(None),
    ).order_by(MobileDevice.imei).all()

    return {
        "departments": departments,
        "nationalities": nationalities,
        "available_phone_numbers": available_phone_numbers,
        "available_imei_numbers": available_imei_numbers,
    }


def _load_edit_form_data(employee):
    all_departments = Department.query.order_by(Department.name).all()
    all_nationalities = _get_nationalities_with_fallback()

    from models import ImportedPhoneNumber
    available_phone_numbers = ImportedPhoneNumber.query.filter(
        ImportedPhoneNumber.employee_id.is_(None)
    ).order_by(ImportedPhoneNumber.phone_number).all()

    from models import MobileDevice
    available_imei_numbers = MobileDevice.query.filter(
        MobileDevice.status == "متاح",
        MobileDevice.employee_id.is_(None),
    ).order_by(MobileDevice.imei).all()

    from models import DeviceAssignment, SimCard
    active_assignment = DeviceAssignment.query.filter_by(
        employee_id=employee.id,
        is_active=True,
    ).first()

    assigned_device = None
    assigned_sim = None

    if active_assignment:
        if active_assignment.device_id:
            assigned_device = MobileDevice.query.get(active_assignment.device_id)
        if active_assignment.sim_card_id:
            assigned_sim = SimCard.query.get(active_assignment.sim_card_id)

    return {
        "departments": all_departments,
        "nationalities": all_nationalities,
        "available_phone_numbers": available_phone_numbers,
        "available_imei_numbers": available_imei_numbers,
        "assigned_device": assigned_device,
        "assigned_sim": assigned_sim,
    }


@employees_bp.route("/")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def index():
    """Employee list view (module)."""
    assigned_id = getattr(current_user, "assigned_department_id", None) or None
    data = list_employees_page_data(
        department_filter=request.args.get("department", ""),
        status_filter=request.args.get("status", ""),
        multi_department_filter=request.args.get("multi_department", ""),
        no_department_filter=request.args.get("no_department", ""),
        duplicate_names_filter=request.args.get("duplicate_names", ""),
        location_filter=request.args.get("location", ""),
        assigned_department_id=assigned_id,
    )
    return render_template(
        "employees/index.html",
        employees=data["employees"],
        departments=data["departments"],
        current_department=data["current_department"],
        current_status=data["current_status"],
        current_location=data.get("current_location", ""),
        current_multi_department=data["current_multi_department"],
        current_no_department=data["current_no_department"],
        current_duplicate_names=data["current_duplicate_names"],
        multi_dept_count=data["multi_dept_count"],
        single_dept_count=data["single_dept_count"],
        no_dept_count=data["no_dept_count"],
        duplicate_names_count=data["duplicate_names_count"],
        duplicate_names_set=data["duplicate_names_set"],
        can_edit=can_edit,
        can_delete=can_delete,
        Module=Module,
    )


@employees_bp.route("/tracking")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def tracking():
    return redirect(url_for("employees.index"))


@employees_bp.route("/create", methods=["GET", "POST"])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.CREATE)
def create():
    if request.method == "POST":
        result = create_employee(request.form, request.files)
        if result.success:
            flash(_service_message(result), result.category)
            return redirect(url_for("employees.index"))

        flash(_service_message(result), result.category)
        context = _load_create_form_data()
        return render_template(
            "employees/create.html",
            form_data=request.form,
            **context,
        )

    context = _load_create_form_data()
    return render_template("employees/create.html", **context)


@employees_bp.route("/import", methods=["GET", "POST"])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.CREATE)
def import_excel():
    from routes.employees import import_excel as legacy_import
    return legacy_import()


@employees_bp.route("/export")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def export_excel():
    from routes.employees import export_excel as legacy_export
    return legacy_export()


@employees_bp.route("/export_comprehensive")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def export_comprehensive():
    from routes.employees import export_comprehensive as legacy_export
    return legacy_export()


@employees_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.EDIT)
def edit(id):
    employee = Employee.query.get_or_404(id)

    if request.method == "POST":
        result = update_employee(id, request.form, request.files)
        if result.success:
            unlink_info = (result.data or {}).get("unlink") or {}
            if unlink_info:
                sim_count = unlink_info.get("sim_count", 0)
                assignment_count = unlink_info.get("assignment_count", 0)
                if sim_count or assignment_count:
                    message_parts = []
                    if sim_count:
                        message_parts.append(f"{sim_count} رقم SIM مرتبط مباشرة")
                    if assignment_count:
                        message_parts.append(f"{assignment_count} تخصيص جهاز/رقم")
                    flash(f"تم فك ربط {' و '.join(message_parts)} بالموظف تلقائياً", "info")
                if unlink_info.get("warning"):
                    flash(
                        "تحذير: حدث خطأ في فك ربط أرقام SIM. يرجى فحص الأرقام يدوياً",
                        "warning",
                    )

            flash(_service_message(result), result.category)

            return_url = request.form.get("return_url") or request.referrer
            if return_url and "/departments/" in return_url:
                try:
                    department_id = return_url.split("/departments/")[1].split("/")[0]
                    return redirect(url_for("departments.view", id=department_id))
                except Exception:
                    pass

            return redirect(url_for("employees.index"))

        flash(_service_message(result), result.category)

    context = _load_edit_form_data(employee)
    return render_template("employees/edit.html", employee=employee, **context)


@employees_bp.route("/<int:id>")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.VIEW)
def view(id):
    from routes.employees import view as legacy_view
    return legacy_view(id)


@employees_bp.route("/<int:id>/confirm_delete")
@login_required
@require_module_access(Module.EMPLOYEES, Permission.DELETE)
def confirm_delete(id):
    from routes.employees import confirm_delete as legacy_confirm
    return legacy_confirm(id)


@employees_bp.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
@require_module_access(Module.EMPLOYEES, Permission.DELETE)
def delete(id):
    employee = Employee.query.get_or_404(id)

    if request.method == "GET":
        return redirect(url_for("employees.confirm_delete", id=id))

    confirmed = request.form.get("confirmed", "no")
    if confirmed != "yes":
        flash("لم يتم تأكيد عملية الحذف", "warning")
        return redirect(url_for("employees.view", id=id))

    result = delete_employee(id)
    if not result.success:
        flash(_service_message(result), result.category)
        return redirect(url_for("employees.view", id=id))

    flash(_service_message(result), result.category)

    referrer = request.form.get("return_url")
    if referrer and "/departments/" in referrer:
        try:
            department_id = referrer.split("/departments/")[1].split("/")[0]
            return redirect(url_for("departments.view", id=department_id))
        except Exception:
            pass

    return redirect(url_for("employees.index"))
