# -*- coding: utf-8 -*-
"""
مسارات عرض الحضور
View routes for attendance dashboard and main pages

الدوال:
- index: الصفحة الرئيسية لسجلات الحضور
- department_attendance: تسجيل حضور القسم كاملاً
- employee_attendance: تسجيل الموظف الفردي
- get_department_employees: API لجلب موظفي القسم
- dashboard: لوحة معلومات الحضور الشاملة
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from datetime import datetime, date, timedelta, calendar, time
from core.extensions import db
from models import Attendance, Employee, Department, SystemAudit, employee_departments
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from utils.decorators import module_access_required
from services.attendance_analytics import AttendanceAnalytics
from services.attendance_engine import AttendanceEngine
import logging
import time as time_module
from .helpers import format_time_12h_ar, format_time_12h_ar_short

logger = logging.getLogger(__name__)

# These will be registered as routes in __init__.py
def index():
    """List attendance records with filtering options - shows all employees"""
    try:
        # Get filter parameters
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id', '')
        status = request.args.get('status', '')
        
        # Parse date with fallback
        try:
            date_obj = parse_date(date_str)
        except (ValueError, TypeError):
            date_obj = datetime.now().date()
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
            att_date=date_obj,
            department_id=int(department_id) if department_id else None,
            status_filter=status if status else None
        )
        
        # Calculate statistics from unified list
        present_count = sum(1 for rec in unified_attendances if rec['status'] == 'present')
        absent_count = sum(1 for rec in unified_attendances if rec['status'] == 'absent')
        leave_count = sum(1 for rec in unified_attendances if rec['status'] == 'leave')
        sick_count = sum(1 for rec in unified_attendances if rec['status'] == 'sick')
        
        # Format dates for display
        hijri_date = format_date_hijri(date_obj)
        gregorian_date = format_date_gregorian(date_obj)
        
        logger.info(f'Index: Loaded {len(unified_attendances)} records for {date_obj.isoformat()}')
        
        # Render with identical template signature for 100% compatibility
        return render_template('attendance/index.html', 
                              attendances=unified_attendances,
                              departments=departments,
                              date=date_obj,
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


@attendance_bp.route('/department', methods=['GET', 'POST'])
@login_required
@module_access_required('attendance_management')
def department_attendance():
    """Record attendance for an entire department at once"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            date_str = request.form['date']
            status = request.form['status']
            
            # Check user permissions for accessing this department
            if current_user.is_authenticated and not current_user.can_access_department(int(department_id)):
                flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                return redirect(url_for('attendance.department_attendance'))
            
            # Parse date
            date_obj = parse_date(date_str)
            
            # Use AttendanceEngine to bulk record attendance
            count, message = AttendanceEngine.bulk_record_department(
                department_id=department_id,
                att_date=date_obj,
                status=status
            )
            
            if count > 0:
                flash(f'تم تسجيل الحضور لـ {count} موظف بنجاح', 'success')
            else:
                flash(message, 'danger')
            
            return redirect(url_for('attendance.index', date=date_str))
        
        except Exception as e:
            logger.error(f'Error in department_attendance() POST: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.department_attendance'))
    
    # Get departments based on user permissions
    if current_user.is_authenticated:
        departments = current_user.get_accessible_departments()
    else:
        departments = Department.query.all()
    
    # Default to today's date
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return render_template('attendance/department.html', 
                          departments=departments,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@attendance_bp.route('/api/departments/<int:department_id>/employees')
@login_required
def get_department_employees(department_id):
    """API endpoint to get all employees in a department"""
    try:
        # Get the department first
        department = Department.query.get_or_404(department_id)
        
        # Get all active employees in this department using many-to-many relationship
        employees = [emp for emp in department.employees if emp.status == 'active']
        
        employee_data = []
        for employee in employees:
            employee_data.append({
                'id': employee.id,
                'name': employee.name,
                'employee_id': employee.employee_id,
                'job_title': employee.job_title or 'غير محدد',
                'status': employee.status
            })
        
        logger.info(f"تم جلب {len(employee_data)} موظف نشط من القسم {department_id} ({department.name})")
        return jsonify(employee_data)
    
    except Exception as e:
        logger.error(f"خطأ في جلب موظفي القسم {department_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/dashboard')
@login_required
def dashboard():
    """Attendance dashboard with daily, weekly, and monthly statistics"""
    
    # Add retry mechanism for handling temporary connection errors
    max_retries = 3
    retry_count = 0
    retry_delay = 1
    
    while retry_count < max_retries:
        try:
            # Reload all data from database to ensure data is up-to-date
            db.session.expire_all()
            
            # Get selected project (if any)
            project_name = request.args.get('project', None)
            
            # Get current date
            today = datetime.now().date()
            current_month = today.month
            current_year = today.year
            
            # Calculate week start and end
            start_of_month = today.replace(day=1)
            days_since_month_start = (today - start_of_month).days
            weeks_since_month_start = days_since_month_start // 7
            start_of_week = start_of_month + timedelta(days=weeks_since_month_start * 7)
            end_of_week = start_of_week + timedelta(days=6)
            
            # Adjust end of week if it exceeds month end
            last_day = calendar.monthrange(current_year, current_month)[1]
            end_of_month = today.replace(day=last_day)
            if end_of_week > end_of_month:
                end_of_week = end_of_month
            
            # Ensure start and end of month are correct
            start_of_month = today.replace(day=1)
            
            # Build base query
            query_base = db.session.query(
                Attendance.status,
                func.count(Attendance.id).label('count')
            )
            
            # Define employee IDs list (will be None for all employees)
            employee_ids = None
            
            if project_name:
                # Query for employees in the specified project
                project_employees = db.session.query(Employee.id).filter(
                    Employee.project == project_name,
                    ~Employee.status.in_(['terminated', 'inactive'])
                ).all()
                
                employee_ids = [emp[0] for emp in project_employees]
            
            # Initialize statistics variables
            daily_stats = []
            weekly_stats = []
            monthly_stats = []
            
            # If project is specified and no employees found, leave statistics empty
            if project_name and not employee_ids:
                pass
            else:
                # Build statistics queries
                if employee_ids:
                    # Statistics for employees in specified project
                    daily_stats = query_base.filter(
                        Attendance.date == today,
                        Attendance.employee_id.in_(employee_ids)
                    ).group_by(Attendance.status).all()
                    
                    weekly_stats = query_base.filter(
                        Attendance.date >= start_of_week,
                        Attendance.date <= end_of_week,
                        Attendance.employee_id.in_(employee_ids)
                    ).group_by(Attendance.status).all()
                    
                    monthly_stats = query_base.filter(
                        Attendance.date >= start_of_month,
                        Attendance.date <= end_of_month,
                        Attendance.employee_id.in_(employee_ids)
                    ).group_by(Attendance.status).all()
                else:
                    # General statistics for all employees
                    daily_stats = query_base.filter(
                        Attendance.date == today
                    ).group_by(Attendance.status).all()
                    
                    weekly_stats = query_base.filter(
                        Attendance.date >= start_of_week,
                        Attendance.date <= end_of_week
                    ).group_by(Attendance.status).all()
                    
                    monthly_stats = query_base.filter(
                        Attendance.date >= start_of_month,
                        Attendance.date <= end_of_month
                    ).group_by(Attendance.status).all()
            
            # Daily attendance data for charts
            daily_attendance_data = []
            
            for day in range(1, last_day + 1):
                current_date = date(current_year, current_month, day)
                
                if current_date > today:
                    break
                    
                if employee_ids:
                    present_count = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.date == current_date,
                        Attendance.status == 'present',
                        Attendance.employee_id.in_(employee_ids)
                    ).scalar() or 0
                    
                    absent_count = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.date == current_date,
                        Attendance.status == 'absent',
                        Attendance.employee_id.in_(employee_ids)
                    ).scalar() or 0
                else:
                    present_count = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.date == current_date,
                        Attendance.status == 'present'
                    ).scalar() or 0
                    
                    absent_count = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.date == current_date,
                        Attendance.status == 'absent'
                    ).scalar() or 0
                    
                daily_attendance_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day': str(day),
                    'present': present_count,
                    'absent': absent_count
                })
            
            # Get list of active projects for filter
            active_projects = db.session.query(Employee.project).filter(
                ~Employee.status.in_(['terminated', 'inactive']),
                Employee.project.isnot(None)
            ).distinct().all()
            
            active_projects = [project[0] for project in active_projects if project[0]]
            
            # Convert statistics to dictionaries
            def stats_to_dict(stats_data):
                result = {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0}
                for item in stats_data:
                    result[item[0]] = item[1]
                return result
            
            daily_stats_dict = stats_to_dict(daily_stats)
            weekly_stats_dict = stats_to_dict(weekly_stats)
            monthly_stats_dict = stats_to_dict(monthly_stats)
            
            # Prepare chart data
            daily_chart_data = {
                'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                'datasets': [{
                    'data': [
                        daily_stats_dict['present'],
                        daily_stats_dict['absent'],
                        daily_stats_dict['leave'],
                        daily_stats_dict['sick']
                    ],
                    'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                }]
            }
            
            weekly_chart_data = {
                'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                'datasets': [{
                    'data': [
                        weekly_stats_dict['present'],
                        weekly_stats_dict['absent'],
                        weekly_stats_dict['leave'],
                        weekly_stats_dict['sick']
                    ],
                    'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                }]
            }
            
            monthly_chart_data = {
                'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                'datasets': [{
                    'data': [
                        monthly_stats_dict['present'],
                        monthly_stats_dict['absent'],
                        monthly_stats_dict['leave'],
                        monthly_stats_dict['sick']
                    ],
                    'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                }]
            }
            
            daily_trend_chart_data = {
                'labels': [item['day'] for item in daily_attendance_data],
                'datasets': [
                    {
                        'label': 'الحضور',
                        'data': [item['present'] for item in daily_attendance_data],
                        'backgroundColor': 'rgba(40, 167, 69, 0.2)',
                        'borderColor': 'rgba(40, 167, 69, 1)',
                        'borderWidth': 1,
                        'tension': 0.4
                    },
                    {
                        'label': 'الغياب',
                        'data': [item['absent'] for item in daily_attendance_data],
                        'backgroundColor': 'rgba(220, 53, 69, 0.2)',
                        'borderColor': 'rgba(220, 53, 69, 1)',
                        'borderWidth': 1,
                        'tension': 0.4
                    }
                ]
            }
            
            # Calculate attendance rates
            total_days = (
                daily_stats_dict['present'] + 
                daily_stats_dict['absent'] + 
                daily_stats_dict['leave'] + 
                daily_stats_dict['sick']
            )
            
            daily_attendance_rate = 0
            if total_days > 0:
                daily_attendance_rate = round((daily_stats_dict['present'] / total_days) * 100)
            
            # Count active employees
            if employee_ids:
                active_employees_count = len(employee_ids)
            else:
                active_employees_count = db.session.query(func.count(func.distinct(Employee.id))).join(
                    employee_departments, Employee.id == employee_departments.c.employee_id
                ).filter(
                    ~Employee.status.in_(['terminated', 'inactive'])
                ).scalar() or 0
            
            # Calculate weekly rates
            days_in_week = (end_of_week - start_of_week).days + 1
            total_days_week = (
                weekly_stats_dict['present'] + 
                weekly_stats_dict['absent'] + 
                weekly_stats_dict['leave'] + 
                weekly_stats_dict['sick']
            )
            
            weekly_attendance_rate = 0
            if total_days_week > 0:
                weekly_attendance_rate = round((weekly_stats_dict['present'] / total_days_week) * 100)
            
            # Calculate monthly rates
            total_days_month = (
                monthly_stats_dict['present'] + 
                monthly_stats_dict['absent'] + 
                monthly_stats_dict['leave'] + 
                monthly_stats_dict['sick']
            )
            
            days_in_month = (today - start_of_month).days + 1
            monthly_attendance_rate = 0
            if total_days_month > 0:
                monthly_attendance_rate = round((monthly_stats_dict['present'] / total_days_month) * 100)
            
            # Format dates for display
            formatted_today = {
                'gregorian': format_date_gregorian(today),
                'hijri': format_date_hijri(today)
            }
            
            formatted_start_of_week = {
                'gregorian': format_date_gregorian(start_of_week),
                'hijri': format_date_hijri(start_of_week)
            }
            
            formatted_end_of_week = {
                'gregorian': format_date_gregorian(end_of_week),
                'hijri': format_date_hijri(end_of_week)
            }
            
            formatted_start_of_month = {
                'gregorian': format_date_gregorian(start_of_month),
                'hijri': format_date_hijri(start_of_month)
            }
            
            formatted_end_of_month = {
                'gregorian': format_date_gregorian(end_of_month),
                'hijri': format_date_hijri(end_of_month)
            }
            
            # Current month name
            month_names = [
                'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
                'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
            ]
            current_month_name = month_names[current_month - 1]
            
            # Get detailed absence summaries
            daily_summary = AttendanceAnalytics.get_department_summary(
                start_date=today,
                end_date=today,
                project_name=project_name
            )
            
            monthly_summary = AttendanceAnalytics.get_department_summary(
                start_date=start_of_month,
                end_date=end_of_month,
                project_name=project_name
            )
            
            # Render template
            return render_template('attendance/dashboard_new.html',
                                today=today,
                                current_month=current_month,
                                current_year=current_year,
                                current_month_name=current_month_name,
                                formatted_today=formatted_today,
                                formatted_start_of_week=formatted_start_of_week,
                                formatted_end_of_week=formatted_end_of_week,
                                formatted_start_of_month=formatted_start_of_month,
                                formatted_end_of_month=formatted_end_of_month,
                                start_of_week=start_of_week,
                                end_of_week=end_of_week,
                                start_of_month=start_of_month,
                                end_of_month=end_of_month,
                                daily_stats=daily_stats_dict,
                                weekly_stats=weekly_stats_dict,
                                monthly_stats=monthly_stats_dict,
                                daily_chart_data=daily_chart_data,
                                weekly_chart_data=weekly_chart_data,
                                monthly_chart_data=monthly_chart_data,
                                daily_trend_chart_data=daily_trend_chart_data,
                                daily_attendance_rate=daily_attendance_rate,
                                weekly_attendance_rate=weekly_attendance_rate,
                                monthly_attendance_rate=monthly_attendance_rate,
                                active_employees_count=active_employees_count,
                                active_projects=active_projects,
                                selected_project=project_name,
                                daily_summary=daily_summary,
                                monthly_summary=monthly_summary)
            
            # Exit retry loop if successful
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Error loading dashboard (attempt {retry_count}): {str(e)}")
            
            if retry_count < max_retries:
                time_module.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.critical(f"Error loading dashboard after {max_retries} attempts: {str(e)}")
                return render_template('error.html', 
                                      error_title="خطأ في الاتصال",
                                      error_message="حدث خطأ أثناء الاتصال بقاعدة البيانات. الرجاء المحاولة مرة أخرى.",
                                      error_details=str(e))


@attendance_bp.route('/employee/<int:employee_id>')
@login_required
def employee_attendance(employee_id):
    """View detailed attendance records for an employee organized by month and year"""
    # Get the employee
    employee = Employee.query.get_or_404(employee_id)
    
    # Get current date
    today = datetime.now().date()
    
    # Get year and month from URL or use current
    selected_year = request.args.get('year', today.year, type=int)
    selected_month = request.args.get('month', today.month, type=int)
    
    # Define query period (selected month)
    year = selected_year
    month = selected_month
    start_of_month = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)
    
    # Get attendance records for selected month
    attendances = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_of_month,
        Attendance.date <= end_of_month
    ).order_by(Attendance.date).all()
    
    # Organize records by day for calendar
    attendance_by_day = {}
    for record in attendances:
        attendance_by_day[record.date.day] = record
    
    # Calculate overall statistics
    present_count = sum(1 for a in attendances if a.status == 'present')
    absent_count = sum(1 for a in attendances if a.status == 'absent')
    leave_count = sum(1 for a in attendances if a.status == 'leave')
    sick_count = sum(1 for a in attendances if a.status == 'sick')
    total_records = len(attendances)
    
    # Calculate percentages
    present_percentage = (present_count / total_records * 100) if total_records > 0 else 0
    absent_percentage = (absent_count / total_records * 100) if total_records > 0 else 0
    leave_percentage = (leave_count / total_records * 100) if total_records > 0 else 0
    sick_percentage = (sick_count / total_records * 100) if total_records > 0 else 0
    
    attendance_rate = round(present_percentage, 1) if total_records > 0 else 0
    
    # Get all available periods (years and months with records)
    all_records = Attendance.query.filter(Attendance.employee_id == employee_id).all()
    attendance_periods = {}
    for record in all_records:
        if record.date.year not in attendance_periods:
            attendance_periods[record.date.year] = set()
        attendance_periods[record.date.year].add(record.date.month)
    
    # Calendar information
    first_day_weekday = calendar.monthrange(year, month)[0]
    days_in_month = last_day
    
    # Format dates for display
    hijri_today = format_date_hijri(today)
    gregorian_today = format_date_gregorian(today)
    
    return render_template('attendance/employee_attendance.html',
                          employee=employee,
                          attendances=attendances,
                          attendance_by_day=attendance_by_day,
                          year=year,
                          month=month,
                          selected_year=selected_year,
                          selected_month=selected_month,
                          first_day_weekday=first_day_weekday,
                          days_in_month=days_in_month,
                          attendance_periods=attendance_periods,
                          present_count=present_count,
                          absent_count=absent_count,
                          leave_count=leave_count,
                          sick_count=sick_count,
                          total_records=total_records,
                          present_percentage=present_percentage,
                          absent_percentage=absent_percentage,
                          leave_percentage=leave_percentage,
                          sick_percentage=sick_percentage,
                          attendance_rate=attendance_rate,
                          today=today,
                          hijri_today=hijri_today,
                          gregorian_today=gregorian_today)
