"""
دوال مساعدة لإدارة الرواتب
حسابات الرواتب والخصومات والإخطارات
"""

from datetime import datetime, date
from src.core.extensions import db
from models import Salary, Employee, Attendance, Department


def get_salary_for_month(employee_id, month, year):
    """الحصول على سجل راتب موظف لشهر معين"""
    return Salary.query.filter_by(
        employee_id=employee_id,
        month_year=f"{year}-{month:02d}"
    ).first()


def get_employee_salary_history(employee_id, months=12):
    """الحصول على سجل الرواتب للموظف"""
    salary_records = Salary.query.filter_by(employee_id=employee_id).order_by(
        Salary.month.desc()
    ).limit(months).all()
    
    return salary_records


def calculate_salary_totals(salary_records):
    """حساب الإجماليات من سجلات الرواتب"""
    totals = {
        'total_salary': sum(s.total_salary or 0 for s in salary_records),
        'total_deductions': sum(s.deductions or 0 for s in salary_records),
        'total_net': sum(s.net_salary or 0 for s in salary_records),
        'average_salary': 0,
        'average_net': 0,
        'max_salary': 0,
        'min_salary': 0
    }
    
    if salary_records:
        totals['average_salary'] = round(totals['total_salary'] / len(salary_records), 2)
        totals['average_net'] = round(totals['total_net'] / len(salary_records), 2)
        totals['max_salary'] = max(s.total_salary or 0 for s in salary_records)
        totals['min_salary'] = min(s.total_salary or 0 for s in salary_records)
    
    return totals


def get_attendance_for_salary(employee_id, month, year):
    """جلب سجلات الحضور لشهر معين للموظف"""
    # بناء تاريخ البداية والنهاية
    from datetime import date as date_type
    from calendar import monthrange
    
    start_date = date_type(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date_type(year, month, last_day)
    
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    return attendance_records


def get_salary_statistics(department_id=None, month=None, year=None):
    """الحصول على إحصائيات الرواتب"""
    query = Salary.query
    
    if department_id:
        # جلب موظفي القسم
        emp_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
        query = query.filter(Salary.employee_id.in_(emp_ids))
    
    if month and year:
        query = query.filter(Salary.month_year == f"{year}-{month:02d}")
    
    salaries = query.all()
    
    stats = {
        'total_salaries': len(salaries),
        'total_amount': sum(s.total_salary or 0 for s in salaries),
        'total_net': sum(s.net_salary or 0 for s in salaries),
        'total_deductions': sum(s.deductions or 0 for s in salaries),
        'average_salary': 0,
        'max_salary': 0,
        'min_salary': 0,
        'by_status': {}
    }
    
    if salaries:
        stats['average_salary'] = round(stats['total_amount'] / len(salaries), 2)
        stats['max_salary'] = max(s.total_salary or 0 for s in salaries)
        stats['min_salary'] = min(s.total_salary or 0 for s in salaries)
    
    return stats


def validate_salary_data(salary_form):
    """التحقق من صحة بيانات الراتب"""
    errors = []
    
    if not salary_form.basic_salary.data or salary_form.basic_salary.data < 0:
        errors.append('الراتب الأساسي غير صحيح')
    
    if salary_form.deductions and salary_form.deductions.data < 0:
        errors.append('الخصومات لا يمكن أن تكون سالبة')
    
    if salary_form.allowances and salary_form.allowances.data < 0:
        errors.append('العلاوات لا يمكن أن تكون سالبة')
    
    return errors


def group_salaries_by_department(salary_records):
    """تجميع سجلات الرواتب حسب القسم"""
    grouped = {}
    
    for salary in salary_records:
        emp = Employee.query.get(salary.employee_id)
        if emp:
            dept_name = emp.department.name if emp.department else 'بدون قسم'
            if dept_name not in grouped:
                grouped[dept_name] = []
            grouped[dept_name].append(salary)
    
    return grouped


def get_salary_report_data(month=None, year=None, department_id=None):
    """جلب بيانات تقرير الرواتب"""
    query = Salary.query
    
    if month and year:
        query = query.filter(Salary.month_year == f"{year}-{month:02d}")
    
    if department_id:
        emp_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
        query = query.filter(Salary.employee_id.in_(emp_ids))
    
    salaries = query.all()
    
    # إضافة بيانات الموظف لكل راتب
    report_data = []
    for salary in salaries:
        emp = Employee.query.get(salary.employee_id)
        if emp:
            report_data.append({
                'employee': emp,
                'salary': salary,
                'department': emp.department.name if emp.department else '-'
            })
    
    return report_data
