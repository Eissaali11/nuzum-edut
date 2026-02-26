"""
لوحة معلومات Power BI الرئيسية
مسارات لوحة التحكم والتصدير PDF
"""

from flask import Blueprint, render_template, request, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from src.core.extensions import db
from models import Employee, Attendance, Document, Vehicle, Department
from sqlalchemy import func, or_, and_, case
import logging

powerbi_main_bp = Blueprint('powerbi_main', __name__, url_prefix='/powerbi')


@powerbi_main_bp.route('/')
@login_required
def dashboard():
    """الصفحة الرئيسية للوحة معلومات Power BI الاحترافية - بيانات حقيقية"""
    from datetime import datetime, timedelta
    
    # البيانات الأساسية
    departments = Department.query.all()
    total_vehicles = Vehicle.query.count()
    total_documents = Document.query.count()
    
    # فلاتر التاريخ
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    department_id = request.args.get('department_id')
    
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        except:
            date_from = datetime.now().date() - timedelta(days=30)
    else:
        date_from = datetime.now().date() - timedelta(days=30)
    
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except:
            date_to = datetime.now().date()
    else:
        date_to = datetime.now().date()
    
    # تصحيح التواريخ إذا كانت معكوسة
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    
    # تحديد الأقسام المستهدفة حسب الفلتر
    if department_id:
        try:
            dept_id = int(department_id)
            target_departments = [d for d in departments if d.id == dept_id]
        except:
            target_departments = departments
    else:
        target_departments = departments
    
    # جلب موظفي الأقسام المستهدفة النشطين
    if department_id:
        try:
            dept_id = int(department_id)
            active_emp_query = db.session.query(Employee.id).join(
                Employee.departments
            ).filter(
                Department.id == dept_id,
                Employee.status == 'active'
            )
            active_emp_ids = [e[0] for e in active_emp_query.all()]
        except:
            active_emp_ids = [e.id for e in Employee.query.filter(Employee.status == 'active').all()]
    else:
        active_emp_ids = [e.id for e in Employee.query.filter(Employee.status == 'active').all()]
    
    # جلب الموظفين النشطين فقط الذين لهم حضور في الفترة المحددة
    active_employee_ids_with_attendance = db.session.query(Attendance.employee_id).filter(
        Attendance.date >= date_from,
        Attendance.date <= date_to,
        Attendance.employee_id.in_(active_emp_ids) if active_emp_ids else Attendance.employee_id.isnot(None)
    ).distinct().all()
    active_employee_ids_with_attendance = [e[0] for e in active_employee_ids_with_attendance]
    
    # عدد الموظفين النشطين الذين لهم حضور
    active_employees_count = Employee.query.filter(
        Employee.status == 'active',
        Employee.id.in_(active_employee_ids_with_attendance)
    ).count()
    
    total_employees = active_employees_count
    
    # سجلات الحضور للموظفين النشطين فقط
    attendance_records = Attendance.query.filter(
        Attendance.date >= date_from,
        Attendance.date <= date_to,
        Attendance.employee_id.in_(active_emp_ids) if active_emp_ids else Attendance.employee_id.isnot(None)
    ).all()
    
    attendance_stats = {
        'present': sum(1 for a in attendance_records if a.status == 'present'),
        'absent': sum(1 for a in attendance_records if a.status in ['absent', 'غائب']),
        'leave': sum(1 for a in attendance_records if a.status == 'leave'),
        'sick': sum(1 for a in attendance_records if a.status == 'sick'),
        'total': len(attendance_records)
    }
    attendance_stats['rate'] = round((attendance_stats['present'] / attendance_stats['total']) * 100, 1) if attendance_stats['total'] > 0 else 0
    
    # إحصائيات السيارات
    vehicles = Vehicle.query.all()
    vehicle_stats = {}
    for v in vehicles:
        status = v.status or 'unknown'
        vehicle_stats[status] = vehicle_stats.get(status, 0) + 1
    
    # الحضور حسب القسم - الموظفين النشطين فقط الذين لهم حضور
    dept_attendance = []
    for dept in target_departments:
        # جلب موظفي القسم النشطين فقط
        emp_ids = db.session.query(Employee.id).join(
            Employee.departments
        ).filter(
            Department.id == dept.id,
            Employee.status == 'active'
        ).all()
        emp_ids = [e[0] for e in emp_ids]
        
        if not emp_ids:
            continue
        
        # الموظفين الذين لهم حضور فعلي في الفترة
        emp_ids_with_attendance = db.session.query(Attendance.employee_id).filter(
            Attendance.date >= date_from,
            Attendance.date <= date_to,
            Attendance.employee_id.in_(emp_ids)
        ).distinct().all()
        emp_ids_with_attendance = [e[0] for e in emp_ids_with_attendance]
        
        if not emp_ids_with_attendance:
            continue
            
        # حساب الحضور
        dept_records = Attendance.query.filter(
            Attendance.date >= date_from,
            Attendance.date <= date_to,
            Attendance.employee_id.in_(emp_ids_with_attendance)
        ).all()
        
        present = sum(1 for a in dept_records if a.status == 'present')
        absent = sum(1 for a in dept_records if a.status in ['absent', 'غائب'])
        total = len(dept_records)
        rate = round((present / total) * 100, 1) if total > 0 else 0
        
        # حساب عدد أيام الحضور الفريدة
        present_days = len(set(a.date for a in dept_records if a.status == 'present'))
        
        dept_attendance.append({
            'name': dept.name,
            'employee_count': len(emp_ids_with_attendance),
            'present': present,
            'absent': absent,
            'present_days': present_days,
            'total': total,
            'rate': rate
        })
    
    # ترتيب حسب نسبة الحضور
    dept_attendance.sort(key=lambda x: x['rate'], reverse=True)
    
    # طباعة للتصحيح
    logging.info(f"[POWERBI] dept_attendance count: {len(dept_attendance)}")
    for da in dept_attendance[:3]:
        logging.info(f"[POWERBI] dept: {da['name']}, emp: {da['employee_count']}, rate: {da['rate']}")
    
    # توزيع الموظفين حسب القسم (للرسم البياني) - الموظفين النشطين الذين لهم حضور فقط
    dept_distribution = []
    for dept in departments:
        emp_count = 0
        for da in dept_attendance:
            if da['name'] == dept.name:
                emp_count = da['employee_count']
                break
        if emp_count > 0:
            dept_distribution.append({
                'name': dept.name,
                'count': emp_count
            })
    
    # ترتيب حسب العدد
    dept_distribution.sort(key=lambda x: x['count'], reverse=True)
    
    # إحصائيات الوثائق
    today = datetime.now().date()
    thirty_days = today + timedelta(days=30)
    
    docs = Document.query.all()
    doc_stats = {
        'valid': 0,
        'expiring': 0,
        'expired': 0,
        'total': len(docs)
    }
    
    for doc in docs:
        if hasattr(doc, 'expiry_date') and doc.expiry_date:
            if doc.expiry_date < today:
                doc_stats['expired'] += 1
            elif doc.expiry_date <= thirty_days:
                doc_stats['expiring'] += 1
            else:
                doc_stats['valid'] += 1
        else:
            doc_stats['valid'] += 1
    
    return render_template('powerbi/dashboard_enhanced.html',
        departments=departments,
        total_employees=total_employees,
        total_vehicles=total_vehicles,
        total_documents=total_documents,
        attendance_stats=attendance_stats,
        vehicle_stats=vehicle_stats,
        dept_attendance=dept_attendance,
        dept_distribution=dept_distribution,
        doc_stats=doc_stats,
        date_from=date_from,
        date_to=date_to
    )


@powerbi_main_bp.route('/export-pdf')
@login_required
def export_pdf():
    """تصدير لوحة المعلومات إلى PDF"""
    # سيتم استكمال هذه الدالة من الملف الأصلي
    pass
