"""
Attendance RESTful API (v2)
============================
Modern REST API for attendance operations
Uses same AttendanceService as web controller

Author: Auto-Refactored from _attendance_main.py
Date: 2026-02-20
Version: 2.0

Endpoints:
- GET /api/v2/attendance/list - List attendance records
- POST /api/v2/attendance/record - Record single attendance
- POST /api/v2/attendance/bulk - Bulk record for department
- DELETE /api/v2/attendance/<id> - Delete attendance
- GET /api/v2/attendance/stats - Get statistics
- GET /api/v2/attendance/dashboard - Dashboard data (JSON)
- GET /api/v2/attendance/employees/<employee_id> - Employee attendance history
- GET /api/v2/attendance/departments/<dept_id>/employees - List department employees
- POST /api/v2/attendance/export - Export to Excel (returns file)
"""

from flask import Blueprint, request, jsonify, send_file
from flask_login import current_user
from datetime import datetime, date, time
from src.services.attendance_service import AttendanceService
from src.utils.date_converter import parse_date
from models import Department, Employee, Attendance
from src.core.api_v2_security import v2_jwt_required, get_api_v2_actor
import logging

logger = logging.getLogger(__name__)

# Blueprint registration
api_attendance_v2_bp = Blueprint('api_attendance_v2', __name__, url_prefix='/api/v2/attendance')


def login_required(func):
    return v2_jwt_required(
        required_scopes=['api:v2:read', 'api:v2:write', 'attendance:read', 'attendance:write']
    )(func)


# ==================== Helper Functions ====================

def validate_date(date_str):
    """Validate and parse date string"""
    try:
        return parse_date(date_str) if date_str else None
    except (ValueError, TypeError):
        return None


def api_response(success=True, data=None, message='', status_code=200):
    """Standardized API response"""
    response = {
        'success': success,
        'message': message,
        'data': data or {}
    }
    return jsonify(response), status_code


# ==================== List & Retrieve ====================

@api_attendance_v2_bp.route('/list', methods=['GET'])
@login_required
def list_attendance():
    """
    GET /api/v2/attendance/list
    Query params: date, department_id, status
    """
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id')
        status_filter = request.args.get('status')
        
        date_obj = validate_date(date_str) or datetime.now().date()
        
        # Get accessible departments
        actor = get_api_v2_actor() or current_user
        departments = actor.get_accessible_departments()
        
        # Get attendance data
        attendances = AttendanceService.get_unified_attendance_list(
            att_date=date_obj,
            department_id=int(department_id) if department_id else None,
            status_filter=status_filter,
            user_accessible_departments=departments
        )
        
        # Calculate stats
        stats = AttendanceService.calculate_stats_from_attendances(attendances)
        
        return api_response(success=True, data={
            'attendances': attendances,
            'stats': stats,
            'date': date_obj.isoformat(),
            'total': len(attendances)
        })
    
    except Exception as e:
        logger.error(f'API list error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/employees/<int:employee_id>', methods=['GET'])
@login_required
def employee_attendance(employee_id):
    """
    GET /api/v2/attendance/employees/<id>
    Query params: start_date, end_date
    """
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return api_response(success=False, message='الموظف غير موجود', status_code=404)
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = validate_date(start_date_str)
            end_date = validate_date(end_date_str)
        else:
            # Default to current month
            today = datetime.now().date()
            start_date = today.replace(day=1)
            end_date = today
        
        # Get attendance records
        attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date.desc()).all()
        
        # Format for JSON
        attendance_list = [
            {
                'id': att.id,
                'date': att.date.isoformat(),
                'status': att.status,
                'check_in': att.check_in.isoformat() if att.check_in else None,
                'check_out': att.check_out.isoformat() if att.check_out else None,
                'notes': att.notes
            }
            for att in attendances
        ]
        
        # Calculate stats
        stats = {
            'total': len(attendances),
            'present': sum(1 for a in attendances if a.status == 'present'),
            'absent': sum(1 for a in attendances if a.status == 'absent'),
            'leave': sum(1 for a in attendances if a.status == 'leave'),
            'sick': sum(1 for a in attendances if a.status == 'sick')
        }
        
        return api_response(success=True, data={
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'employee_id': employee.employee_id,
                'national_id': employee.national_id
            },
            'attendances': attendance_list,
            'stats': stats,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
    
    except Exception as e:
        logger.error(f'API employee attendance error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/departments/<int:department_id>/employees', methods=['GET'])
@login_required
def department_employees(department_id):
    """
    GET /api/v2/attendance/departments/<id>/employees
    Returns list of employees in department
    """
    try:
        employees_data = AttendanceService.get_employees_by_department(department_id)
        
        return api_response(success=True, data={
            'department_id': department_id,
            'employees': employees_data,
            'count': len(employees_data)
        })
    
    except Exception as e:
        logger.error(f'API department employees error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


# ==================== Create & Update ====================

@api_attendance_v2_bp.route('/record', methods=['POST'])
@login_required
def record_attendance():
    """
    POST /api/v2/attendance/record
    Body (JSON): {
        "employee_id": 123,
        "date": "2026-02-20",
        "status": "present",
        "check_in": "08:30" (optional),
        "check_out": "16:00" (optional),
        "notes": "..." (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return api_response(success=False, message='لا توجد بيانات', status_code=400)
        
        employee_id = data.get('employee_id')
        date_str = data.get('date')
        status = data.get('status')
        notes = data.get('notes', '')
        
        if not all([employee_id, date_str, status]):
            return api_response(success=False, message='بيانات ناقصة', status_code=400)
        
        date_obj = validate_date(date_str)
        if not date_obj:
            return api_response(success=False, message='تاريخ غير صحيح', status_code=400)
        
        # Process check times
        check_in = None
        check_out = None
        if status == 'present':
            check_in_str = data.get('check_in')
            check_out_str = data.get('check_out')
            
            if check_in_str:
                try:
                    hours, minutes = map(int, check_in_str.split(':'))
                    check_in = time(hours, minutes)
                except (ValueError, AttributeError):
                    pass
            
            if check_out_str:
                try:
                    hours, minutes = map(int, check_out_str.split(':'))
                    check_out = time(hours, minutes)
                except (ValueError, AttributeError):
                    pass
        
        # Call service
        attendance, is_new, message = AttendanceService.record_attendance(
            employee_id=employee_id,
            att_date=date_obj,
            status=status,
            check_in=check_in,
            check_out=check_out,
            notes=notes
        )
        
        if attendance:
            return api_response(success=True, message=message, data={
                'attendance_id': attendance.id,
                'is_new': is_new
            })
        else:
            return api_response(success=False, message=message, status_code=400)
    
    except Exception as e:
        logger.error(f'API record error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/bulk', methods=['POST'])
@login_required
def bulk_record():
    """
    POST /api/v2/attendance/bulk
    Body (JSON): {
        "department_id": 5,
        "date": "2026-02-20",
        "status": "present"
    }
    """
    try:
        data = request.json
        
        if not data:
            return api_response(success=False, message='لا توجد بيانات', status_code=400)
        
        department_id = data.get('department_id')
        date_str = data.get('date')
        status = data.get('status')
        
        if not all([department_id, date_str, status]):
            return api_response(success=False, message='بيانات ناقصة', status_code=400)
        
        # Check permissions
        actor = get_api_v2_actor() or current_user
        if not actor.can_access_department(int(department_id)):
            return api_response(success=False, message='ليس لديك صلاحية', status_code=403)
        
        date_obj = validate_date(date_str)
        if not date_obj:
            return api_response(success=False, message='تاريخ غير صحيح', status_code=400)
        
        # Call service
        count, message = AttendanceService.bulk_record_department(
            department_id=department_id,
            att_date=date_obj,
            status=status
        )
        
        return api_response(success=True, message=message, data={
            'count': count
        })
    
    except Exception as e:
        logger.error(f'API bulk record error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/bulk-period', methods=['POST'])
@login_required
def bulk_record_period():
    """
    POST /api/v2/attendance/bulk-period
    Body (JSON): {
        "department_id": 5,
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "status": "present",
        "skip_weekends": true (optional),
        "overwrite_existing": false (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return api_response(success=False, message='لا توجد بيانات', status_code=400)
        
        department_id = data.get('department_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        status = data.get('status')
        skip_weekends = data.get('skip_weekends', False)
        overwrite_existing = data.get('overwrite_existing', False)
        
        if not all([department_id, start_date_str, end_date_str, status]):
            return api_response(success=False, message='بيانات ناقصة', status_code=400)
        
        # Check permissions
        actor = get_api_v2_actor() or current_user
        if not actor.can_access_department(int(department_id)):
            return api_response(success=False, message='ليس لديك صلاحية', status_code=403)
        
        start_date = validate_date(start_date_str)
        end_date = validate_date(end_date_str)
        
        if not start_date or not end_date:
            return api_response(success=False, message='تاريخ غير صحيح', status_code=400)
        
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
            return api_response(success=False, message=result['error'], status_code=400)
        
        return api_response(success=True, message='تم التسجيل بنجاح', data=result)
    
    except Exception as e:
        logger.error(f'API bulk period error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


# ==================== Delete ====================

@api_attendance_v2_bp.route('/<int:id>', methods=['DELETE'])
@login_required
def delete_attendance(id):
    """
    DELETE /api/v2/attendance/<id>
    """
    try:
        success, message = AttendanceService.delete_attendance(id)
        
        if success:
            return api_response(success=True, message=message)
        else:
            return api_response(success=False, message=message, status_code=404)
    
    except Exception as e:
        logger.error(f'API delete error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    """
    POST /api/v2/attendance/bulk-delete
    Body (JSON): {
        "attendance_ids": [1, 2, 3, ...]
    }
    """
    try:
        data = request.json
        attendance_ids = data.get('attendance_ids', [])
        
        result = AttendanceService.bulk_delete_attendance(attendance_ids)
        
        return api_response(success=True, message=f'تم حذف {result["deleted_count"]} سجل', data=result)
    
    except Exception as e:
        logger.error(f'API bulk delete error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


# ==================== Statistics ====================

@api_attendance_v2_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    """
    GET /api/v2/attendance/stats
    Query params: start_date, end_date, department_id
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        department_id = request.args.get('department_id')
        
        start_date = validate_date(start_date_str) or datetime.now().date().replace(day=1)
        end_date = validate_date(end_date_str) or datetime.now().date()
        
        # Get stats
        result = AttendanceService.get_stats_for_period(
            start_date=start_date,
            end_date=end_date,
            department_id=int(department_id) if department_id else None
        )
        
        return api_response(success=True, data={
            'stats': result,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
    
    except Exception as e:
        logger.error(f'API stats error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """
    GET /api/v2/attendance/dashboard
    Query params: project (optional)
    Returns comprehensive dashboard data in JSON
    """
    try:
        project_name = request.args.get('project')
        
        # Get dashboard data
        dashboard_data = AttendanceService.get_dashboard_data(
            current_date=datetime.now().date(),
            project_name=project_name
        )
        
        # Convert dates to ISO format for JSON
        json_data = {
            'today': dashboard_data['today'].isoformat(),
            'start_of_week': dashboard_data['start_of_week'].isoformat(),
            'end_of_week': dashboard_data['end_of_week'].isoformat(),
            'start_of_month': dashboard_data['start_of_month'].isoformat(),
            'end_of_month': dashboard_data['end_of_month'].isoformat(),
            'daily_stats': dashboard_data['daily_stats'],
            'weekly_stats': dashboard_data['weekly_stats'],
            'monthly_stats': dashboard_data['monthly_stats'],
            'daily_attendance_rate': dashboard_data['daily_attendance_rate'],
            'weekly_attendance_rate': dashboard_data['weekly_attendance_rate'],
            'monthly_attendance_rate': dashboard_data['monthly_attendance_rate'],
            'daily_attendance_data': dashboard_data['daily_attendance_data'],
            'active_employees_count': dashboard_data['active_employees_count']
        }
        
        return api_response(success=True, data=json_data)
    
    except Exception as e:
        logger.error(f'API dashboard error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


# ==================== Export ====================

@api_attendance_v2_bp.route('/export', methods=['POST'])
@login_required
def export():
    """
    POST /api/v2/attendance/export
    Body (JSON): {
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "department_id": 5 (optional),
        "status": "present" (optional),
        "search_query": "..." (optional)
    }
    Returns: Excel file download
    """
    try:
        data = request.json
        
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        department_id = data.get('department_id')
        status_filter = data.get('status')
        search_query = data.get('search_query')
        
        if not start_date_str:
            return api_response(success=False, message='تاريخ البداية مطلوب', status_code=400)
        
        start_date = validate_date(start_date_str)
        end_date = validate_date(end_date_str) or datetime.now().date()
        
        if not start_date:
            return api_response(success=False, message='تاريخ غير صحيح', status_code=400)
        
        # Generate Excel
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
        logger.error(f"API export error: {str(e)}", exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


# ==================== Geo Circle ====================

@api_attendance_v2_bp.route('/circles/<int:department_id>/<circle_name>/employees', methods=['GET'])
@login_required
def circle_employees(department_id, circle_name):
    """
    GET /api/v2/attendance/circles/<dept_id>/<circle_name>/employees
    Query params: date
    """
    try:
        date_str = request.args.get('date')
        selected_date = validate_date(date_str) or datetime.now().date()
        
        employees_data = AttendanceService.get_circle_accessed_employees(
            department_id=department_id,
            circle_name=circle_name,
            selected_date=selected_date
        )
        
        return api_response(success=True, data={
            'circle_name': circle_name,
            'department_id': department_id,
            'date': selected_date.isoformat(),
            'employees': employees_data,
            'count': len(employees_data)
        })
    
    except Exception as e:
        logger.error(f'API circle employees error: {str(e)}', exc_info=True)
        return api_response(success=False, message=f'خطأ: {str(e)}', status_code=500)


@api_attendance_v2_bp.route('/circles/<int:department_id>/<circle_name>/mark-present', methods=['POST'])
@login_required
def mark_circle_present(department_id, circle_name):
    """
    POST /api/v2/attendance/circles/<dept_id>/<circle_name>/mark-present
    Body (JSON): {
        "date": "2026-02-20"
    }
    """
    try:
        data = request.json
        date_str = data.get('date')
        selected_date = validate_date(date_str) or datetime.now().date()
        
        marked_count, message = AttendanceService.mark_circle_employees_attendance(
            department_id=department_id,
            circle_name=circle_name,
            selected_date=selected_date
        )
        
        return api_response(success=True, message=message, data={
            'marked_count': marked_count
        })
    
    except Exception as e:
        logger.error(f"API mark circle error: {str(e)}")
        return api_response(success=False, message=f'حدث خطأ: {str(e)}', status_code=500)


# ==================== Health Check ====================

@api_attendance_v2_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return api_response(success=True, data={
        'status': 'healthy',
        'version': '2.0',
        'service': 'attendance_api'
    })
