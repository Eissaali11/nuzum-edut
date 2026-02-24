"""
دوال مساعدة لحسابات Power BI والاستعلامات القاعدة البيانات
"""

from datetime import datetime, timedelta
from core.extensions import db
from models import Attendance, Employee, Document, Vehicle, Department
from sqlalchemy import func, case


def calculate_attendance_rate(employee_ids, date_from, date_to):
    """حساب نسبة الحضور للموظفين و الفترة المحددة"""
    if not employee_ids:
        return 0
    
    records = Attendance.query.filter(
        Attendance.date >= date_from,
        Attendance.date <= date_to,
        Attendance.employee_id.in_(employee_ids)
    ).all()
    
    if not records:
        return 0
    
    present = sum(1 for r in records if r.status == 'present')
    return round((present / len(records)) * 100, 1)


def get_department_stats(department_id, date_from, date_to):
    """الحصول على إحصائيات كاملة لقسم معين"""
    employees = Employee.query.filter_by(department_id=department_id).all()
    employee_ids = [e.id for e in employees]
    
    if not employee_ids:
        return None
    
    attendance_records = Attendance.query.filter(
        Attendance.date >= date_from,
        Attendance.date <= date_to,
        Attendance.employee_id.in_(employee_ids)
    ).all()
    
    stats = {
        'department_id': department_id,
        'employee_count': len(employees),
        'present': sum(1 for a in attendance_records if a.status == 'present'),
        'absent': sum(1 for a in attendance_records if a.status in ['absent', 'غائب']),
        'leave': sum(1 for a in attendance_records if a.status == 'leave'),
        'sick': sum(1 for a in attendance_records if a.status == 'sick'),
        'total_records': len(attendance_records),
        'attendance_rate': calculate_attendance_rate(employee_ids, date_from, date_to)
    }
    
    return stats


def get_document_expiry_info():
    """معلومات انتهاء صلاحية الوثائق"""
    today = datetime.now().date()
    thirty_days_later = today + timedelta(days=30)
    sixty_days_later = today + timedelta(days=60)
    
    documents = Document.query.all()
    
    info = {
        'total': len(documents),
        'expired': 0,
        'expiring_soon': 0,  # خلال 30 يوم
        'expiring_later': 0,  # بين 30-60 يوم
        'valid': 0
    }
    
    for doc in documents:
        if hasattr(doc, 'expiry_date') and doc.expiry_date:
            if doc.expiry_date < today:
                info['expired'] += 1
            elif doc.expiry_date <= thirty_days_later:
                info['expiring_soon'] += 1
            elif doc.expiry_date <= sixty_days_later:
                info['expiring_later'] += 1
            else:
                info['valid'] += 1
        else:
            info['valid'] += 1
    
    return info


def get_vehicle_fleet_health():
    """تقييم صحة الأسطول"""
    vehicles = Vehicle.query.all()
    
    if not vehicles:
        return 'no_data'
    
    statuses = {}
    for v in vehicles:
        status = v.status or 'unknown'
        statuses[status] = statuses.get(status, 0) + 1
    
    in_project = statuses.get('in_project', 0)
    utilization_rate = (in_project / len(vehicles)) * 100
    
    if utilization_rate >= 80:
        return 'excellent'
    elif utilization_rate >= 60:
        return 'good'
    elif utilization_rate >= 40:
        return 'average'
    else:
        return 'poor'


def filter_employees_by_department(department_id):
    """الحصول على موظفي قسم معين"""
    return Employee.query.filter_by(department_id=department_id).all()


def get_today_attendance_summary():
    """ملخص الحضور لليوم الحالي"""
    today = datetime.now().date()
    today_records = Attendance.query.filter(Attendance.date == today).all()
    
    return {
        'date': today.strftime('%Y-%m-%d'),
        'present': sum(1 for a in today_records if a.status == 'present'),
        'absent': sum(1 for a in today_records if a.status in ['absent', 'غائب']),
        'leave': sum(1 for a in today_records if a.status == 'leave'),
        'sick': sum(1 for a in today_records if a.status == 'sick'),
        'total': len(today_records)
    }


def get_trend_analysis(metric_name, date_from, date_to, date_from_prev=None, date_to_prev=None):
    """تحليل الاتجاهات للمؤشرات المختلفة"""
    if not date_from_prev:
        date_from_prev = date_from - timedelta(days=(date_to - date_from).days)
    if not date_to_prev:
        date_to_prev = date_from
    
    if metric_name == 'attendance_rate':
        current = calculate_attendance_rate(
            [e.id for e in Employee.query.all()],
            date_from, date_to
        )
        previous = calculate_attendance_rate(
            [e.id for e in Employee.query.all()],
            date_from_prev, date_to_prev
        )
    
    trend = round(current - previous, 1)
    direction = 'up' if trend > 0 else 'down' if trend < 0 else 'stable'
    
    return {
        'current': current,
        'previous': previous,
        'trend_value': abs(trend),
        'direction': direction,
        'percentage_change': round((trend / previous * 100), 1) if previous != 0 else 0
    }


def build_attendance_query(department_id=None, employee_id=None, date_from=None, date_to=None):
    """بناء استعلام مرن لسجلات الحضور"""
    query = Attendance.query
    
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    elif department_id:
        employee_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
        if employee_ids:
            query = query.filter(Attendance.employee_id.in_(employee_ids))
    
    return query
