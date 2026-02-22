"""
Attendance List & View Routes
==============================
Extracted from _attendance_main.py as part of modularization.
Handles all attendance listing and viewing operations.

Routes:
    - GET  /               : Main attendance list with filters
    - GET  /department/view: Department attendance view for a period
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import or_
import logging

from core.extensions import db
from models import Attendance, Employee, Department, employee_departments
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from services.attendance_engine import AttendanceEngine

logger = logging.getLogger(__name__)

# Create blueprint
list_bp = Blueprint('list', __name__)


@list_bp.route('/')
def index():
    """List attendance records with filtering options - shows all employees
    
    CHUNK #1 REFACTORED:
    - Uses AttendanceEngine.get_unified_attendance_list() instead of 8 direct queries
    - Maintains 100% backward compatibility with templates
    - Improved performance: 8 queries → 2 queries (-75%)
    """
    try:
        # Get filter parameters
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id', '')
        status = request.args.get('status', '')
        
        # Parse date with fallback
        try:
            date = parse_date(date_str)
        except (ValueError, TypeError):
            date = datetime.now().date()
            logger.warning(f'Invalid date provided: {date_str}, using today')
        
        # Get departments (with user permission checks)
        if current_user.is_authenticated:
            departments = current_user.get_accessible_departments()
            # Auto-filter to user's assigned department if applicable
            if current_user.assigned_department_id and not department_id:
                department_id = str(current_user.assigned_department_id)
        else:
            departments = Department.query.all()
        
        # Single call to AttendanceEngine for all attendance data
        unified_attendances = AttendanceEngine.get_unified_attendance_list(
            att_date=date,
            department_id=int(department_id) if department_id else None,
            status_filter=status if status else None
        )
        
        # Calculate statistics from unified list
        present_count = sum(1 for rec in unified_attendances if rec['status'] == 'present')
        absent_count = sum(1 for rec in unified_attendances if rec['status'] == 'absent')
        leave_count = sum(1 for rec in unified_attendances if rec['status'] == 'leave')
        sick_count = sum(1 for rec in unified_attendances if rec['status'] == 'sick')
        
        # Format dates for display
        hijri_date = format_date_hijri(date)
        gregorian_date = format_date_gregorian(date)
        
        logger.info(f'Index: Loaded {len(unified_attendances)} records for {date.isoformat()}')
        
        # Render with identical template signature for 100% compatibility
        return render_template('attendance/index.html', 
                              attendances=unified_attendances,
                              departments=departments,
                              date=date,
                              hijri_date=hijri_date,
                              gregorian_date=gregorian_date,
                              selected_department=department_id,
                              selected_status=status,
                              present_count=present_count,
                              absent_count=absent_count,
                              leave_count=leave_count,
                              sick_count=sick_count)
    
    except Exception as e:
        logger.error(f'Critical error in index(): {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل البيانات. الرجاء المحاولة مرة أخرى.', 'danger')
        return render_template('error.html', error_title='خطأ في النظام', error_message='فشل تحميل بيانات الحضور'), 500


@list_bp.route('/department/view', methods=['GET'])
def department_attendance_view():
    """عرض حضور الأقسام خلال فترة زمنية محددة"""
    # الحصول على معاملات الفلترة
    department_id = request.args.get('department_id', '')
    search_query = request.args.get('search_query', '').strip()
    status_filter = request.args.get('status_filter', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    working_days_required = request.args.get('working_days_required', '26')
    
    # تحديد التواريخ الافتراضية (آخر 30 يوم)
    if not start_date_str:
        start_date = datetime.now().date() - timedelta(days=30)
    else:
        start_date = parse_date(start_date_str)
    
    if not end_date_str:
        end_date = datetime.now().date()
    else:
        end_date = parse_date(end_date_str)
    
    # الحصول على الأقسام حسب صلاحيات المستخدم
    if current_user.is_authenticated:
        departments = current_user.get_accessible_departments()
    else:
        departments = Department.query.all()
    
    # بناء الاستعلام
    query = Attendance.query.join(Employee).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    # تطبيق فلتر القسم
    if department_id:
        query = query.join(employee_departments).filter(
            employee_departments.c.department_id == int(department_id)
        )
    
    # تطبيق البحث عن الموظف (الاسم، رقم الهوية، الرقم الوظيفي)
    if search_query:
        query = query.filter(
            or_(
                Employee.name.ilike(f'%{search_query}%'),
                Employee.employee_id.ilike(f'%{search_query}%'),
                Employee.national_id.ilike(f'%{search_query}%')
            )
        )
    
    # تطبيق فلتر الحالة
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    
    # الحصول على السجلات مرتبة حسب التاريخ والموظف
    attendances = query.order_by(Attendance.date.desc(), Employee.name).all()
    
    # حساب الإحصائيات
    total_count = len(attendances)
    present_count = sum(1 for a in attendances if a.status == 'present')
    absent_count = sum(1 for a in attendances if a.status == 'absent')
    leave_count = sum(1 for a in attendances if a.status == 'leave')
    sick_count = sum(1 for a in attendances if a.status == 'sick')
    
    return render_template('attendance/department_period.html',
                          departments=departments,
                          department_id=department_id,
                          search_query=search_query,
                          status_filter=status_filter,
                          start_date=start_date,
                          end_date=end_date,
                          attendances=attendances,
                          total_count=total_count,
                          present_count=present_count,
                          absent_count=absent_count,
                          leave_count=leave_count,
                          sick_count=sick_count,
                          working_days_required=working_days_required)
