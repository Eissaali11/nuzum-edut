"""
مسارات الحضور والرواتب للجوال — مستخرجة من routes/mobile.py.
تُسجَّل على mobile_bp عبر register_hr_routes(mobile_bp).
نفس الاستجابات والقوالب.
"""
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template
from flask_login import login_required

from src.core.extensions import db
from models import Employee, Department, Salary
from sqlalchemy.orm import joinedload

from src.application.mobile.hr_services import (
    get_attendance_list_data,
    get_attendance_dashboard_data,
    add_attendance_action,
    edit_attendance_action,
    delete_attendance_action,
    get_salaries_list_data,
    get_salary_details_data,
    edit_salary_action,
    share_salary_whatsapp_data,
)


def register_hr_routes(mobile_bp):
    """تسجيل مسارات الحضور والرواتب على الـ blueprint المزوّد."""

    @mobile_bp.route("/attendance")
    @login_required
    def attendance():
        """صفحة الحضور والغياب للنسخة المحمولة"""
        page = request.args.get("page", 1, type=int)
        per_page = 20
        search_query = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()
        department_id = request.args.get("department_id", "").strip()
        date_str = request.args.get("date", "").strip()
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                selected_date = datetime.now().date()
        else:
            selected_date = datetime.now().date()
        dept_id = int(department_id) if department_id and department_id.isdigit() else None
        data = get_attendance_list_data(
            selected_date=selected_date,
            page=page,
            per_page=per_page,
            search_query=search_query,
            status_filter=status_filter,
            department_id=dept_id,
        )
        return render_template(
            "mobile/attendance.html",
            employees=data["employees"],
            departments=data["departments"],
            attendance_records=data["attendance_records"],
            selected_date=data["selected_date"],
            today_stats=data["today_stats"],
            pagination=data["pagination"],
        )

    @mobile_bp.route("/attendance-dashboard")
    @login_required
    def attendance_dashboard():
        """لوحة معلومات الحضور للموبايل"""
        date_str = request.args.get("date")
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        except ValueError:
            selected_date = datetime.now().date()
        data = get_attendance_dashboard_data(selected_date)
        return render_template(
            "mobile/attendance_dashboard.html",
            selected_date=data["selected_date"],
            total_employees=data["total_employees"],
            total_present=data["total_present"],
            total_absent=data["total_absent"],
            total_leave=data["total_leave"],
            total_sick=data["total_sick"],
            department_stats=data["department_stats"],
        )

    @mobile_bp.route("/attendance/export", methods=["GET", "POST"])
    @login_required
    def export_attendance():
        """صفحة تصدير بيانات الحضور إلى Excel للنسخة المحمولة"""
        departments = Department.query.order_by(Department.name).all()
        if request.method == "POST":
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            department_id = request.form.get("department_id")
            redirect_url = url_for("attendance.export_excel")
            params = []
            if start_date:
                params.append(f"start_date={start_date}")
            if end_date:
                params.append(f"end_date={end_date}")
            if department_id:
                params.append(f"department_id={department_id}")
            if params:
                redirect_url = f"{redirect_url}?{'&'.join(params)}"
            return redirect(redirect_url)
        return render_template("mobile/attendance_export.html", departments=departments)

    @mobile_bp.route("/attendance/add", methods=["GET", "POST"])
    @login_required
    def add_attendance():
        """إضافة سجل حضور جديد للنسخة المحمولة"""
        employees = Employee.query.order_by(Employee.name).all()
        departments = Department.query.order_by(Department.name).all()
        current_date = datetime.now().date()
        if request.method == "POST":
            success, message, redirect_route = add_attendance_action(request.form)
            if success:
                flash(message, "success")
                return redirect(url_for(redirect_route))
            flash(message, "danger" if not success else "warning")
            return render_template(
                "mobile/add_attendance.html",
                employees=employees,
                departments=departments,
                current_date=current_date,
            )
        return render_template(
            "mobile/add_attendance.html",
            employees=employees,
            departments=departments,
            current_date=current_date,
        )

    @mobile_bp.route("/attendance/<int:record_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_attendance(record_id):
        """تعديل سجل حضور للنسخة المحمولة"""
        from models import Attendance
        record = Attendance.query.get_or_404(record_id)
        employees = Employee.query.filter_by(status="active").order_by(Employee.name).all()
        if request.method == "POST":
            success, message = edit_attendance_action(record_id, request.form)
            if success:
                flash(message, "success")
                return redirect(url_for("mobile.attendance"))
            flash(message, "danger")
        return render_template("mobile/edit_attendance.html", record=record, employees=employees)

    @mobile_bp.route("/attendance/<int:record_id>/delete", methods=["POST"])
    @login_required
    def delete_attendance(record_id):
        """حذف سجل حضور للنسخة المحمولة"""
        success, message = delete_attendance_action(record_id)
        flash(message, "success" if success else "danger")
        return redirect(url_for("mobile.attendance"))

    @mobile_bp.route("/salaries")
    @login_required
    def salaries():
        """صفحة الرواتب للنسخة المحمولة"""
        page = request.args.get("page", 1, type=int)
        per_page = 20
        current_year = datetime.now().year
        current_month = datetime.now().month
        selected_year = request.args.get("year", current_year, type=int)
        selected_month = request.args.get("month", current_month, type=int)
        employee_id_str = request.args.get("employee_id", "")
        employee_id = int(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
        department_id_str = request.args.get("department_id", "")
        department_id = int(department_id_str) if department_id_str and department_id_str.isdigit() else None
        is_paid = request.args.get("is_paid")
        is_paid_bool = None
        if is_paid is not None:
            is_paid_bool = is_paid == "1"
        search_term = request.args.get("search", "")
        data = get_salaries_list_data(
            selected_year=selected_year,
            selected_month=selected_month,
            page=page,
            per_page=per_page,
            employee_id=employee_id,
            department_id=department_id,
            is_paid=is_paid_bool,
            search_term=search_term,
        )
        return render_template(
            "mobile/salaries.html",
            employees=Employee.query.order_by(Employee.name).all(),
            departments=Department.query.order_by(Department.name).all(),
            salaries=data["salaries"],
            current_year=current_year,
            current_month=current_month,
            selected_year=data["selected_year"],
            selected_month=data["selected_month"],
            selected_month_name=data["selected_month_name"],
            employee_id=data["employee_id"],
            department_id=data["department_id"],
            salary_stats=data["salary_stats"],
            pagination=data["pagination"],
        )

    @mobile_bp.route("/salaries/add", methods=["GET", "POST"])
    @login_required
    def add_salary():
        """إضافة راتب جديد للنسخة المحمولة"""
        return render_template("mobile/add_salary.html")

    @mobile_bp.route("/salaries/<int:salary_id>")
    @login_required
    def salary_details(salary_id):
        """تفاصيل الراتب للنسخة المحمولة"""
        data = get_salary_details_data(salary_id)
        if not data:
            from flask import abort
            abort(404)
        return render_template(
            "mobile/salary_details.html",
            salary=data["salary"],
            month_name=data["month_name"],
            employee_stats=data["employee_stats"],
        )

    @mobile_bp.route("/salaries/<int:salary_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_salary(salary_id):
        """تعديل الراتب للنسخة المحمولة"""
        salary = Salary.query.options(joinedload(Salary.employee)).get_or_404(salary_id)
        month_names = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
        }
        month_name = month_names.get(salary.month, "")
        if request.method == "POST":
            success, message = edit_salary_action(salary_id, request.form)
            if success:
                flash(message, "success")
                return redirect(url_for("mobile.salary_details", salary_id=salary.id))
            flash(message, "error")
        return render_template("mobile/edit_salary.html", salary=salary, month_name=month_name)

    @mobile_bp.route("/salary/<int:id>/share_whatsapp")
    @login_required
    def share_salary_via_whatsapp(id):
        """مشاركة إشعار راتب عبر الواتس اب في النسخة المحمولة"""
        success, whatsapp_url, error_message = share_salary_whatsapp_data(id, "salaries.salary_notification_pdf")
        if success and whatsapp_url:
            return redirect(whatsapp_url)
        flash(error_message or "حدث خطأ أثناء مشاركة إشعار الراتب عبر الواتس اب", "danger")
        return redirect(url_for("mobile.report_salaries"))
