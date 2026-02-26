"""
Attendance Controller Layer (Refactored)
=========================================
Slim Flask routes - All business logic delegated to AttendanceService

Original: _attendance_main.py (3,403 lines)
Refactored: attendance_controller.py (~500 lines)
Service Layer: services/attendance_service.py (~900 lines)

Architecture: Controller calls Service → Service returns data → Controller renders
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
from services.attendance_service import AttendanceService
from services.attendance_analytics import AttendanceAnalytics
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from utils.decorators import module_access_required
from models import Department, Attendance, Employee
import logging

logger = logging.getLogger(__name__)

# Blueprint registration
attendance_refactored_bp = Blueprint('attendance_refactored', __name__)


def _with_modular_header(resp):
    """Attach X-Attendance-Handler header to a Flask response."""
    r = make_response(resp)
    r.headers['X-Attendance-Handler'] = 'MODULAR_v1'
    return r


@attendance_refactored_bp.after_request
def _add_modular_header(response):
    """Ensure all blueprint responses include the modular handler header."""
    response.headers['X-Attendance-Handler'] = 'MODULAR_v1'
    return response


# ==================== Main Routes ====================

@attendance_refactored_bp.route('/')
@login_required
def index():
    """List attendance records with filtering options"""
    try:
        # Get filter parameters
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id', '')
        status = request.args.get('status', '')
        
        # Parse date
        try:
            date_obj = parse_date(date_str)
        except (ValueError, TypeError):
            date_obj = datetime.now().date()
            logger.warning(f'Invalid date: {date_str}')
        
        # Get accessible departments
        departments = current_user.get_accessible_departments()
        
        # Auto-filter to user's department
        if current_user.assigned_department_id and not department_id:
            department_id = str(current_user.assigned_department_id)
        
        # Get attendance data from service
        unified_attendances = AttendanceService.get_unified_attendance_list(
            att_date=date_obj,
            department_id=int(department_id) if department_id else None,
            status_filter=status if status else None,
            user_accessible_departments=departments
        )
        
        # Calculate stats
        stats = AttendanceService.calculate_stats_from_attendances(unified_attendances)
        
        # Format dates
        hijri_date = format_date_hijri(date_obj)
        gregorian_date = format_date_gregorian(date_obj)
        
        return _with_modular_header(render_template('attendance/index.html',
                      attendances=unified_attendances,
                      departments=departments,
                      date=date_obj,
                      hijri_date=hijri_date,
                      gregorian_date=gregorian_date,
                      selected_department=department_id,
                      selected_status=status,
                      present_count=stats['present'],
                      absent_count=stats['absent'],
                      leave_count=stats['leave'],
                      sick_count=stats['sick']))
    
    except Exception as e:
        logger.error(f'Error in index: {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل البيانات', 'danger')
        resp = _with_modular_header(render_template('error.html', error_title='خطأ', error_message=str(e)))
        resp.status_code = 500
        return resp


@attendance_refactored_bp.route('/record', methods=['GET', 'POST'])
@login_required
def record():
    """Record attendance for individual employees"""
    if request.method == 'POST':
        try:
            employee_id = request.form['employee_id']
            date_str = request.form['date']
            status = request.form['status']
            notes = request.form.get('notes', '')
            
            date_obj = parse_date(date_str)
            
            # Process check times
            check_in = None
            check_out = None
            if status == 'present':
                check_in_str = request.form.get('check_in', '')
                check_out_str = request.form.get('check_out', '')
                
                if check_in_str:
                    hours, minutes = map(int, check_in_str.split(':'))
                    check_in = time(hours, minutes)
                
                if check_out_str:
                    hours, minutes = map(int, check_out_str.split(':'))
                    check_out = time(hours, minutes)
            
            # Call service
            attendance, is_new, message = AttendanceService.record_attendance(
                employee_id=employee_id,
                att_date=date_obj,
                status=status,
                check_in=check_in,
                check_out=check_out,
                notes=notes
            )
            
            flash(message, 'success' if attendance else 'danger')
            return _with_modular_header(redirect(url_for('attendance_refactored.index', date=date_str)))
        
        except Exception as e:
            logger.error(f'Error in record POST: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return _with_modular_header(redirect(url_for('attendance_refactored.record')))
    
    # GET: Show form
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    employees = AttendanceService.get_active_employees(
        user_role=user_role,
        user_assigned_department_id=current_user.assigned_department_id
    )
    
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return _with_modular_header(render_template('attendance/record.html',
                          employees=employees,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date))


@attendance_refactored_bp.route('/department', methods=['GET', 'POST'])
@login_required
def department_attendance():
    """Record attendance for entire department"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            date_str = request.form['date']
            status = request.form['status']
            
            # Check permissions
            if not current_user.can_access_department(int(department_id)):
                flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                return redirect(url_for('attendance_refactored.department_attendance'))
            
            date_obj = parse_date(date_str)
            
            # Call service
            count, message = AttendanceService.bulk_record_department(
                department_id=department_id,
                att_date=date_obj,
                status=status
            )
            
            flash(message, 'success')
            return redirect(url_for('attendance_refactored.index', date=date_str))
        
        except Exception as e:
            logger.error(f'Error in department POST: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance_refactored.department_attendance'))
    
    # GET: Show form
    departments = current_user.get_accessible_departments()
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return render_template('attendance/department.html',
                          departments=departments,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@attendance_refactored_bp.route('/department/bulk', methods=['GET', 'POST'])
@login_required
def department_bulk_attendance():
    """Record attendance for department over date range"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            start_date_str = request.form['start_date']
            end_date_str = request.form['end_date']
            status = request.form['status']
            skip_weekends = 'skip_weekends' in request.form
            overwrite_existing = 'overwrite_existing' in request.form
            
            # Check permissions
            if not current_user.can_access_department(int(department_id)):
                flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                return redirect(url_for('attendance_refactored.department_bulk_attendance'))
            
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            
            # Call service
            result = AttendanceService.bulk_record_for_period(
                department_id=department_id,
                start_date=start_date,
                end_date=end_date,
                status=status,
                skip_weekends=skip_weekends,
                overwrite_existing=overwrite_existing
            )
            
            if 'error' in result:
                flash(result['error'], 'error')
            else:
                message = f"تم تسجيل الحضور: {result['created']} جديد، {result['updated']} محدث، {result['skipped']} متخطى"
                flash(message, 'success')
            
            return redirect(url_for('attendance_refactored.department_bulk_attendance'))
        
        except Exception as e:
            logger.error(f'Error in bulk attendance: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'error')
            return redirect(url_for('attendance_refactored.department_bulk_attendance'))
    
    # GET: Show form
    departments = current_user.get_accessible_departments()
    today = datetime.now().date()
    
    return render_template('attendance/department_bulk.html',
                          departments=departments,
                          today=today)


# ==================== Delete Operations ====================

@attendance_refactored_bp.route('/delete/<int:id>/confirm')
@login_required
def confirm_delete(id):
    """Confirm deletion page"""
    attendance = Attendance.query.get_or_404(id)
    return render_template('attendance/confirm_delete.html', attendance=attendance)


@attendance_refactored_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_attendance(id):
    """Delete single attendance record"""
    success, message = AttendanceService.delete_attendance(id)
    flash(message, 'success' if success else 'danger')
    
    # Get date for redirect
    attendance = Attendance.query.get(id)
    date_redirect = attendance.date if attendance else datetime.now().date()
    
    return redirect(url_for('attendance_refactored.index', date=date_redirect))


@attendance_refactored_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_attendance():
    """Delete multiple attendance records"""
    try:
        data = request.json
        attendance_ids = data.get('attendance_ids', [])
        
        result = AttendanceService.bulk_delete_attendance(attendance_ids)
        
        return jsonify({
            'success': True,
            'deleted_count': result['deleted_count'],
            'errors': result['errors']
        })
    
    except Exception as e:
        logger.error(f'Error in bulk delete: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


# ==================== Statistics & Dashboard ====================

@attendance_refactored_bp.route('/stats')
@login_required
def stats():
    """Get attendance statistics for date range"""
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    department_id = request.args.get('department_id', '')
    
    try:
        start_date = parse_date(start_date_str) if start_date_str else datetime.now().date().replace(day=1)
        end_date = parse_date(end_date_str) if end_date_str else datetime.now().date()
    except ValueError:
        start_date = datetime.now().date().replace(day=1)
        end_date = datetime.now().date()
    
    # Get stats from service
    result = AttendanceService.get_stats_for_period(
        start_date=start_date,
        end_date=end_date,
        department_id=int(department_id) if department_id else None
    )
    
    return jsonify(result)


@attendance_refactored_bp.route('/dashboard')
@login_required
def dashboard():
    """Comprehensive attendance dashboard"""
    try:
        project_name = request.args.get('project')
        
        # Get dashboard data from service
        dashboard_data = AttendanceService.get_dashboard_data(
            current_date=datetime.now().date(),
            project_name=project_name
        )
        
        # Format dates for display
        formatted_dates = {
            'today': {
                'gregorian': format_date_gregorian(dashboard_data['today']),
                'hijri': format_date_hijri(dashboard_data['today'])
            },
            'start_of_week': {
                'gregorian': format_date_gregorian(dashboard_data['start_of_week']),
                'hijri': format_date_hijri(dashboard_data['start_of_week'])
            },
            'end_of_week': {
                'gregorian': format_date_gregorian(dashboard_data['end_of_week']),
                'hijri': format_date_hijri(dashboard_data['end_of_week'])
            },
            'start_of_month': {
                'gregorian': format_date_gregorian(dashboard_data['start_of_month']),
                'hijri': format_date_hijri(dashboard_data['start_of_month'])
            },
            'end_of_month': {
                'gregorian': format_date_gregorian(dashboard_data['end_of_month']),
                'hijri': format_date_hijri(dashboard_data['end_of_month'])
            }
        }
        
        # Month name
        month_names = [
            'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        current_month_name = month_names[dashboard_data['today'].month - 1]
        
        return render_template('attendance/dashboard_new.html',
                              today=dashboard_data['today'],
                              current_month=dashboard_data['today'].month,
                              current_year=dashboard_data['today'].year,
                              current_month_name=current_month_name,
                              formatted_today=formatted_dates['today'],
                              formatted_start_of_week=formatted_dates['start_of_week'],
                              formatted_end_of_week=formatted_dates['end_of_week'],
                              formatted_start_of_month=formatted_dates['start_of_month'],
                              formatted_end_of_month=formatted_dates['end_of_month'],
                              daily_stats=dashboard_data['daily_stats'],
                              weekly_stats=dashboard_data['weekly_stats'],
                              monthly_stats=dashboard_data['monthly_stats'],
                              daily_attendance_rate=dashboard_data['daily_attendance_rate'],
                              weekly_attendance_rate=dashboard_data['weekly_attendance_rate'],
                              monthly_attendance_rate=dashboard_data['monthly_attendance_rate'],
                              daily_attendance_data=dashboard_data['daily_attendance_data'],
                              daily_summary=dashboard_data['daily_summary'],
                              monthly_summary=dashboard_data['monthly_summary'],
                              active_employees_count=dashboard_data['active_employees_count'])
    
    except Exception as e:
        logger.error(f'Error in dashboard: {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل لوحة المعلومات', 'danger')
        return render_template('error.html', error_title='خطأ', error_message=str(e)), 500


# ==================== Export Operations ====================

@attendance_refactored_bp.route('/export/excel', methods=['POST', 'GET'])
@login_required
def export_excel():
    """Export attendance to Excel"""
    try:
        # Get parameters
        if request.method == 'POST':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            department_id = request.form.get('department_id')
            status_filter = request.form.get('status')
            search_query = request.form.get('search_query')
        else:
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            department_id = request.args.get('department_id')
            status_filter = request.args.get('status')
            search_query = request.args.get('search_query')
        
        if not start_date_str:
            flash('تاريخ البداية مطلوب', 'danger')
            return redirect(url_for('attendance_refactored.index'))
        
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str) if end_date_str else datetime.now().date()
        
        # Call service to generate Excel
        output = AttendanceService.export_to_excel(
            start_date=start_date,
            end_date=end_date,
            department_id=int(department_id) if department_id else None,
            status_filter=status_filter,
            search_query=search_query
        )
        
        filename = f"حضور_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error exporting Excel: {str(e)}", exc_info=True)
        flash(f'خطأ في التصدير: {str(e)}', 'error')
        return redirect(url_for('attendance_refactored.index'))


# ==================== Employee Routes ====================

@attendance_refactored_bp.route('/employee/<int:employee_id>')
@login_required
def employee_attendance(employee_id):
    """View attendance for specific employee"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Get date range from query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
        else:
            # Default to current month
            today = datetime.now().date()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        # Get attendance records
        attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date.desc()).all()
        
        # Calculate stats
        stats = {
            'total': len(attendances),
            'present': sum(1 for a in attendances if a.status == 'present'),
            'absent': sum(1 for a in attendances if a.status == 'absent'),
            'leave': sum(1 for a in attendances if a.status == 'leave'),
            'sick': sum(1 for a in attendances if a.status == 'sick')
        }
        
        return render_template('attendance/employee.html',
                              employee=employee,
                              attendances=attendances,
                              stats=stats,
                              start_date=start_date,
                              end_date=end_date)
    
    except Exception as e:
        logger.error(f'Error in employee_attendance: {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل بيانات الموظف', 'danger')
        return redirect(url_for('attendance_refactored.index'))


# ==================== API Routes (for AJAX) ====================

@attendance_refactored_bp.route('/api/departments/<int:department_id>/employees')
@login_required
def api_department_employees(department_id):
    """Get employees for a department (AJAX endpoint)"""
    try:
        employees_data = AttendanceService.get_employees_by_department(department_id)
        return jsonify(employees_data)
    
    except Exception as e:
        logger.error(f'Error getting department employees: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ==================== Geo Circle Routes ====================

@attendance_refactored_bp.route('/circle-accessed-details/<int:department_id>/<circle_name>')
@login_required
def circle_accessed_details(department_id, circle_name):
    """Show employees who accessed a geo circle"""
    try:
        date_str = request.args.get('date')
        
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = datetime.now().date()
        
        dept = Department.query.get_or_404(department_id)
        
        # Get employees from service
        employees_accessed = AttendanceService.get_circle_accessed_employees(
            department_id=department_id,
            circle_name=circle_name,
            selected_date=selected_date
        )
        
        return render_template(
            'attendance/circle_accessed_details.html',
            circle_name=circle_name,
            department_name=dept.name,
            department_id=department_id,
            employees_accessed=employees_accessed,
            selected_date=selected_date,
            selected_date_formatted=format_date_hijri(selected_date)
        )
    
    except Exception as e:
        logger.error(f'Error in circle_accessed_details: {str(e)}', exc_info=True)
        flash('حدث خطأ في تحميل البيانات', 'danger')
        return redirect(url_for('attendance_refactored.index'))


@attendance_refactored_bp.route('/mark-circle-employees-attendance/<int:department_id>/<circle_name>', methods=['POST'])
@login_required
def mark_circle_employees_attendance(department_id, circle_name):
    """Mark employees in circle as present"""
    try:
        date_str = request.args.get('date')
        
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = datetime.now().date()
        
        # Call service
        marked_count, message = AttendanceService.mark_circle_employees_attendance(
            department_id=department_id,
            circle_name=circle_name,
            selected_date=selected_date
        )
        
        return jsonify({
            'success': True,
            'message': message,
            'count': marked_count
        }), 200
    
    except Exception as e:
        logger.error(f"Error marking circle attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500
