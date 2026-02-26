"""
دوال مساعدة لتوليد التقارير
معالجات مشتركة للـ PDF و Excel والتصفية
"""

from datetime import datetime, date, timedelta
from sqlalchemy import func
from src.core.extensions import db
from models import Department, Employee, Attendance, Salary, Document, Vehicle, Fee


def get_date_filters(request):
    """استخراج فلاتر التاريخ من طلب HTTP"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    try:
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            date_from = date.today() - timedelta(days=30)
    except:
        date_from = date.today() - timedelta(days=30)
    
    try:
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            date_to = date.today()
    except:
        date_to = date.today()
    
    return date_from, date_to


def get_department_filter(request):
    """استخراج فلتر القسم من طلب HTTP"""
    department_id = request.args.get('department_id')
    if department_id:
        try:
            return int(department_id)
        except:
            return None
    return None


def get_vehicles_for_report(status=None, vehicle_type=None, search=None):
    """جلب السيارات للتقرير مع الفلاتر"""
    query = Vehicle.query
    
    if status and status != 'all':
        query = query.filter_by(status=status)
    
    if vehicle_type and vehicle_type != 'all':
        query = query.filter_by(vehicle_type=vehicle_type)
    
    if search:
        query = query.filter(
            Vehicle.license_plate.contains(search) | 
            Vehicle.car_model.contains(search)
        )
    
    return query.all()


def get_employees_for_report(department_id=None, status='active'):
    """جلب الموظفين للتقرير مع الفلاتر"""
    query = Employee.query
    
    if status:
        query = query.filter_by(status=status)
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    return query.all()


def get_attendance_stats(employees, date_from, date_to):
    """حساب إحصائيات الحضور للموظفين"""
    stats = {}
    
    for emp in employees:
        attendance_records = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= date_from,
            Attendance.date <= date_to
        ).all()
        
        present = sum(1 for a in attendance_records if a.status == 'present')
        absent = sum(1 for a in attendance_records if a.status in ['absent', 'غائب'])
        leave = sum(1 for a in attendance_records if a.status in ['leave', 'إجازة'])
        sick = sum(1 for a in attendance_records if a.status in ['sick', 'مرضي'])
        
        total = len(attendance_records)
        rate = round((present / total) * 100, 1) if total > 0 else 0
        
        stats[emp.id] = {
            'employee': emp,
            'present': present,
            'absent': absent,
            'leave': leave,
            'sick': sick,
            'total': total,
            'rate': rate
        }
    
    return stats


def get_salary_stats(employees, date_from, date_to):
    """حساب إحصائيات الرواتب للموظفين"""
    stats = {}
    
    for emp in employees:
        salary_records = Salary.query.filter(
            Salary.employee_id == emp.id,
            Salary.month >= date_from,
            Salary.month <= date_to
        ).all()
        
        total_salary = sum(s.total_salary for s in salary_records)
        total_deductions = sum(s.deductions for s in salary_records)
        total_net = sum(s.net_salary for s in salary_records)
        
        stats[emp.id] = {
            'employee': emp,
            'salary_count': len(salary_records),
            'total_salary': total_salary,
            'total_deductions': total_deductions,
            'total_net': total_net,
            'avg_salary': round(total_salary / len(salary_records), 2) if salary_records else 0
        }
    
    return stats


def get_documents_for_report(employee_id=None, document_type=None):
    """جلب الوثائق للتقرير مع الفلاتر"""
    query = Document.query
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    if document_type and document_type != 'all':
        query = query.filter_by(document_type=document_type)
    
    return query.all()


def check_document_expiry(document):
    """التحقق من انتهاء صلاحية الوثيقة"""
    if not hasattr(document, 'expiry_date') or not document.expiry_date:
        return 'valid'
    
    today = date.today()
    if document.expiry_date < today:
        return 'expired'
    elif document.expiry_date <= today + timedelta(days=30):
        return 'expiring_soon'
    else:
        return 'valid'


def get_fees_summary(date_from=None, date_to=None):
    """ملخص الرسوم والعلاوات"""
    query = Fee.query
    
    if date_from:
        query = query.filter(Fee.created_at >= date_from)
    if date_to:
        query = query.filter(Fee.created_at <= date_to)
    
    fees = query.all()
    
    summary = {
        'total_fees': len(fees),
        'total_amount': sum(f.amount for f in fees),
        'by_type': {},
        'by_status': {}
    }
    
    for fee in fees:
        # جمع حسب النوع
        fee_type = getattr(fee, 'fee_type', 'غير محدد')
        if fee_type not in summary['by_type']:
            summary['by_type'][fee_type] = 0
        summary['by_type'][fee_type] += 1
        
        # جمع حسب الحالة
        fee_status = getattr(fee, 'status', 'pending')
        if fee_status not in summary['by_status']:
            summary['by_status'][fee_status] = 0
        summary['by_status'][fee_status] += 1
    
    return summary
