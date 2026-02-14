"""
خدمات الموارد البشرية للجوال — الحضور والرواتب ومشاركة الراتب عبر واتساب.
الحسابات (صافي الراتب، ساعات الحضور)، الـ commit، وسجلات التدقيق.
لا يتجاوز 400 سطر.
"""
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from core.extensions import db
from sqlalchemy import func, or_

# استيراد النماذج من models (تعيد التصدير من domain.employees.models)
from models import (
    Attendance,
    Salary,
    Employee,
    Department,
    SystemAudit,
)

MONTH_NAMES_AR = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
    5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
    9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def _normalize_status(status: str) -> str:
    m = {"حاضر": "present", "غائب": "absent", "إجازة": "leave", "مرضي": "sick"}
    return m.get(status, status) if status else ""


def _parse_date(value: Any) -> date:
    if hasattr(value, "year"):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return datetime.now().date()


# --- الحضور ---

def get_attendance_list_data(
    selected_date: date,
    page: int = 1,
    per_page: int = 20,
    search_query: str = "",
    status_filter: str = "",
    department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """بيانات صفحة قائمة الحضور للتاريخ المحدد."""
    q = Attendance.query.filter_by(date=selected_date)
    if search_query:
        q = q.join(Employee).filter(
            or_(
                Employee.name.ilike(f"%{search_query}%"),
                Employee.employee_id.ilike(f"%{search_query}%"),
                Employee.national_id.ilike(f"%{search_query}%"),
            )
        )
    elif department_id:
        q = q.join(Employee).filter(Employee.department_id == department_id)
    if status_filter:
        q = q.filter_by(status=status_filter)
    q = q.order_by(Attendance.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    employees = Employee.query.filter_by(status="active").order_by(Employee.name).all()
    departments = Department.query.order_by(Department.name).all()
    present_absent = or_(Attendance.status == "حاضر", Attendance.status == "present")
    absent_status = or_(Attendance.status == "غائب", Attendance.status == "absent")
    leave_status = or_(Attendance.status == "إجازة", Attendance.status == "leave")
    today_stats = {
        "present": Attendance.query.filter(Attendance.date == selected_date, present_absent).count(),
        "absent": Attendance.query.filter(Attendance.date == selected_date, absent_status).count(),
        "leave": Attendance.query.filter(Attendance.date == selected_date, leave_status).count(),
        "total": len(employees),
    }
    return {
        "attendance_records": pagination.items,
        "selected_date": selected_date,
        "today_stats": today_stats,
        "pagination": pagination,
        "employees": employees,
        "departments": departments,
    }


def get_attendance_dashboard_data(selected_date: date) -> Dict[str, Any]:
    """بيانات لوحة الحضور (إحصائيات يومية وحسب القسم)."""
    departments = Department.query.order_by(Department.name).all()
    total_employees = Employee.query.filter_by(status="active").count()
    present_cond = or_(Attendance.status == "present", Attendance.status == "حاضر")
    absent_cond = or_(Attendance.status == "absent", Attendance.status == "غائب")
    leave_cond = or_(Attendance.status == "leave", Attendance.status == "إجازة")
    total_present = (
        db.session.query(func.count(Attendance.id))
        .join(Employee, Employee.id == Attendance.employee_id)
        .filter(Employee.status == "active", Attendance.date == selected_date, present_cond)
        .scalar() or 0
    )
    total_absent = (
        db.session.query(func.count(Attendance.id))
        .join(Employee, Employee.id == Attendance.employee_id)
        .filter(Employee.status == "active", Attendance.date == selected_date, absent_cond)
        .scalar() or 0
    )
    total_leave = (
        db.session.query(func.count(Attendance.id))
        .join(Employee, Employee.id == Attendance.employee_id)
        .filter(Employee.status == "active", Attendance.date == selected_date, leave_cond)
        .scalar() or 0
    )
    total_sick = (
        db.session.query(func.count(Attendance.id))
        .join(Employee, Employee.id == Attendance.employee_id)
        .filter(Employee.status == "active", Attendance.date == selected_date, Attendance.status == "sick")
        .scalar() or 0
    )
    department_stats = []
    for dept in departments:
        active_employees = [e for e in dept.employees if e.status == "active"]
        employees_count = len(active_employees)
        employee_ids = [e.id for e in active_employees]
        if employees_count == 0:
            continue
        present_count = (
            db.session.query(func.count(Attendance.id))
            .filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.date == selected_date,
                present_cond,
            )
            .scalar() or 0
        )
        absent_count = (
            db.session.query(func.count(Attendance.id))
            .filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.date == selected_date,
                absent_cond,
            )
            .scalar() or 0
        )
        leave_count = (
            db.session.query(func.count(Attendance.id))
            .filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.date == selected_date,
                leave_cond,
            )
            .scalar() or 0
        )
        sick_count = (
            db.session.query(func.count(Attendance.id))
            .filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.date == selected_date,
                Attendance.status == "sick",
            )
            .scalar() or 0
        )
        present_percentage = (present_count / employees_count * 100) if employees_count else 0
        absent_percentage = (absent_count / employees_count * 100) if employees_count else 0
        leave_percentage = ((leave_count + sick_count) / employees_count * 100) if employees_count else 0
        department_stats.append({
            "name": dept.name,
            "employees_count": employees_count,
            "present_count": present_count,
            "absent_count": absent_count,
            "leave_count": leave_count,
            "sick_count": sick_count,
            "present_percentage": present_percentage,
            "absent_percentage": absent_percentage,
            "leave_percentage": leave_percentage,
        })
    return {
        "selected_date": selected_date,
        "total_employees": total_employees,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_leave": total_leave,
        "total_sick": total_sick,
        "department_stats": department_stats,
    }


def add_attendance_action(form_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """
    إضافة سجل/سجلات حضور. يُرجع (success, message, redirect_route).
    يدعم: تسجيل فردي، تسجيل الكل، تسجيل جماعي لأقسام.
    """
    normalize = _normalize_status
    mass = form_data.get("mass_attendance") == "true"
    all_employees = form_data.get("all_employees") == "true"
    if mass:
        if hasattr(form_data, "getlist"):
            department_ids = form_data.getlist("department_ids")
        else:
            ids = form_data.get("department_ids")
            department_ids = ids if isinstance(ids, list) else ([ids] if ids else [])
        if not department_ids:
            return False, "يرجى اختيار قسم واحد على الأقل", None
        start_date = _parse_date(form_data.get("start_date"))
        end_date = _parse_date(form_data.get("end_date"))
        if end_date < start_date:
            return False, "تاريخ النهاية يجب أن يكون بعد تاريخ البداية", None
        status = normalize(form_data.get("status", ""))
        selected_employees = []
        for dept_id in department_ids:
            dept = Department.query.get(dept_id)
            if dept:
                selected_employees.extend([e for e in dept.employees if e.status == "active"])
        selected_employees = list(set(selected_employees))
        success_count = 0
        current_date_iter = start_date
        while current_date_iter <= end_date:
            for emp in selected_employees:
                existing = Attendance.query.filter_by(employee_id=emp.id, date=current_date_iter).first()
                if not existing:
                    db.session.add(Attendance(
                        employee_id=emp.id,
                        date=current_date_iter,
                        status=status,
                        check_in="09:00" if status == "present" else None,
                        check_out="17:00" if status == "present" else None,
                        notes="تسجيل جماعي عبر النظام المحمول",
                    ))
                    success_count += 1
            current_date_iter += timedelta(days=1)
        try:
            db.session.commit()
            return True, f"تم تسجيل {success_count} سجل حضور بنجاح", "mobile.attendance"
        except Exception as e:
            db.session.rollback()
            return False, f"حدث خطأ أثناء التسجيل: {str(e)}", None
    if all_employees:
        status = normalize(form_data.get("status", ""))
        if not status:
            return False, "يرجى اختيار حالة الحضور", None
        all_emps = Employee.query.order_by(Employee.name).all()
        attendance_date = _parse_date(form_data.get("date"))
        check_in = form_data.get("check_in")
        check_out = form_data.get("check_out")
        notes = form_data.get("notes", "")
        success_count = 0
        for emp in all_emps:
            db.session.add(Attendance(
                employee_id=emp.id,
                date=attendance_date,
                status=status,
                check_in=check_in if status == "present" else None,
                check_out=check_out if status == "present" else None,
                notes=notes,
            ))
            success_count += 1
        try:
            db.session.commit()
            return True, f"تم تسجيل حضور {success_count} موظف بنجاح", "mobile.attendance"
        except Exception as e:
            db.session.rollback()
            return False, "حدث خطأ أثناء حفظ البيانات. يرجى المحاولة مرة أخرى.", None
    employee_id = form_data.get("employee_id")
    employee = Employee.query.get(employee_id) if employee_id else None
    if not employee:
        return False, "يرجى اختيار موظف صالح", None
    attendance_date = _parse_date(form_data.get("date"))
    status = normalize(form_data.get("status", ""))
    check_in = form_data.get("check_in")
    check_out = form_data.get("check_out")
    notes = form_data.get("notes", "")
    if form_data.get("quick") == "true" and form_data.get("action"):
        now_time = datetime.now().time()
        if form_data.get("action") == "check_in":
            status, check_in, check_out, notes = "present", now_time.strftime("%H:%M"), None, "تم تسجيل الحضور عبر النظام المحمول."
        else:
            status, check_in, check_out, notes = "present", None, now_time.strftime("%H:%M"), "تم تسجيل الانصراف عبر النظام المحمول."
    db.session.add(Attendance(
        employee_id=employee.id,
        date=attendance_date,
        status=status,
        check_in=check_in,
        check_out=check_out,
        notes=notes,
    ))
    try:
        db.session.commit()
        return True, "تم تسجيل الحضور بنجاح", "mobile.attendance"
    except Exception as e:
        db.session.rollback()
        return False, "حدث خطأ أثناء تسجيل الحضور. يرجى المحاولة مرة أخرى.", None


def edit_attendance_action(record_id: int, form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """تحديث سجل حضور. يُرجع (success, message)."""
    record = Attendance.query.get(record_id)
    if not record:
        return False, "السجل غير موجود"
    try:
        record.employee_id = int(form_data.get("employee_id", record.employee_id))
        record.date = _parse_date(form_data.get("date"))
        record.status = form_data.get("status", record.status)
        ci, co = form_data.get("check_in"), form_data.get("check_out")
        record.check_in = datetime.strptime(ci, "%H:%M").time() if ci else None
        record.check_out = datetime.strptime(co, "%H:%M").time() if co else None
        record.notes = form_data.get("notes", "")
        db.session.commit()
        return True, "تم تحديث سجل الحضور بنجاح"
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء التحديث: {str(e)}"


def delete_attendance_action(record_id: int) -> Tuple[bool, str]:
    """حذف سجل حضور. يُرجع (success, message)."""
    record = Attendance.query.get(record_id)
    if not record:
        return False, "السجل غير موجود"
    try:
        db.session.delete(record)
        db.session.commit()
        return True, "تم حذف سجل الحضور بنجاح"
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء الحذف: {str(e)}"


# --- الرواتب ---

def get_salaries_list_data(
    selected_year: int,
    selected_month: int,
    page: int = 1,
    per_page: int = 20,
    employee_id: Optional[int] = None,
    department_id: Optional[int] = None,
    is_paid: Optional[bool] = None,
    search_term: str = "",
) -> Dict[str, Any]:
    """بيانات قائمة الرواتب مع الإجماليات."""
    from sqlalchemy.orm import joinedload
    query = Salary.query.filter(Salary.year == selected_year, Salary.month == selected_month)
    if employee_id:
        query = query.filter(Salary.employee_id == employee_id)
    if department_id:
        dept_emp_ids = db.session.query(Employee.id).join(Employee.departments).filter(Department.id == department_id).subquery()
        query = query.filter(Salary.employee_id.in_(dept_emp_ids))
    if is_paid is not None:
        query = query.filter(Salary.is_paid == is_paid)
    if search_term:
        query = query.join(Employee).filter(Employee.name.like(f"%{search_term}%"))
    query = query.order_by(Salary.id.desc())
    paginator = query.paginate(page=page, per_page=per_page, error_out=False)
    total_salaries = query.all()
    salary_stats = {
        "total_basic": sum(s.basic_salary for s in total_salaries),
        "total_allowances": sum(s.allowances for s in total_salaries),
        "total_deductions": sum(s.deductions for s in total_salaries),
        "total_net": sum(s.net_salary for s in total_salaries),
    }
    return {
        "salaries": paginator.items,
        "salary_stats": salary_stats,
        "pagination": paginator,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "selected_month_name": MONTH_NAMES_AR.get(selected_month, ""),
        "employee_id": employee_id,
        "department_id": department_id,
    }


def get_salary_details_data(salary_id: int) -> Optional[Dict[str, Any]]:
    """بيانات تفاصيل راتب واحد مع إحصائيات الموظف."""
    from sqlalchemy.orm import joinedload
    salary = Salary.query.options(joinedload(Salary.employee)).get(salary_id)
    if not salary:
        return None
    month_name = MONTH_NAMES_AR.get(salary.month, "")
    employee_salaries = Salary.query.filter_by(employee_id=salary.employee_id).all()
    employee_stats = {
        "total_salaries": len(employee_salaries),
        "total_paid": sum(1 for s in employee_salaries if s.is_paid),
        "total_unpaid": sum(1 for s in employee_salaries if not s.is_paid),
        "avg_net_salary": sum(s.net_salary for s in employee_salaries) / len(employee_salaries) if employee_salaries else 0,
    }
    return {"salary": salary, "month_name": month_name, "employee_stats": employee_stats}


def edit_salary_action(salary_id: int, form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """تحديث راتب وحساب صافي الراتب. يُرجع (success, message)."""
    salary = Salary.query.get(salary_id)
    if not salary:
        return False, "الراتب غير موجود"
    try:
        salary.basic_salary = float(form_data.get("basic_salary", 0))
        salary.allowances = float(form_data.get("allowances", 0))
        salary.deductions = float(form_data.get("deductions", 0))
        salary.bonus = float(form_data.get("bonus", 0))
        salary.overtime_hours = float(form_data.get("overtime_hours", 0))
        salary.is_paid = "is_paid" in form_data or form_data.get("is_paid") == "on"
        salary.notes = form_data.get("notes", "")
        salary.net_salary = salary.basic_salary + salary.allowances + salary.bonus - salary.deductions
        salary.updated_at = datetime.utcnow()
        db.session.commit()
        return True, "تم تحديث بيانات الراتب بنجاح"
    except Exception as e:
        db.session.rollback()
        return False, "حدث خطأ أثناء تحديث الراتب"


def share_salary_whatsapp_data(salary_id: int, pdf_route: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    إعداد مشاركة الراتب عبر واتساب: رسالة ورابط. تسجيل تدقيق وcommit.
    pdf_route: اسم المسار الذي يُنشئ PDF إشعار الراتب (مثل salaries.salary_notification_pdf).
    يُرجع (success, whatsapp_url, error_message).
    """
    salary = Salary.query.get(salary_id)
    if not salary:
        return False, None, "الراتب غير موجود"
    employee = salary.employee
    month_name = MONTH_NAMES_AR.get(salary.month, str(salary.month))
    try:
        from flask import url_for
        pdf_url = url_for(pdf_route, id=salary.id, _external=True)
    except Exception:
        pdf_url = ""
    message_text = f"""*إشعار راتب - نُظم*

السلام عليكم ورحمة الله وبركاته،

تحية طيبة،

نود إشعاركم بإيداع راتب شهر {month_name} {salary.year}.

الموظف: {employee.name}
الشهر: {month_name} {salary.year}

صافي الراتب: *{salary.net_salary:.2f} ريال*

للاطلاع على تفاصيل الراتب، يمكنكم تحميل نسخة الإشعار من الرابط التالي:
{pdf_url}

مع تحيات إدارة الموارد البشرية
نُظم - نظام إدارة متكامل"""
    audit = SystemAudit(
        action="share_whatsapp_link_mobile",
        entity_type="salary",
        entity_id=salary.id,
        details=f"تم مشاركة إشعار راتب عبر رابط واتس اب (موبايل) للموظف: {employee.name} لشهر {salary.month}/{salary.year}",
        user_id=None,
    )
    db.session.add(audit)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return False, None, str(e)
    to_phone = getattr(employee, "mobile", None) or ""
    if to_phone:
        to_phone = to_phone.strip()
        if not to_phone.startswith("+"):
            to_phone = "+966" + to_phone[1:] if to_phone.startswith("0") else "+966" + to_phone
        whatsapp_url = f"https://wa.me/{to_phone}?text={quote(message_text)}"
    else:
        whatsapp_url = f"https://wa.me/?text={quote(message_text)}"
    return True, whatsapp_url, None
