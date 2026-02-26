import calendar
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from models import Employee, UserRole
from src.modules.leave.domain.models import LeaveRequest, LeaveBalance
from src.modules.leave.application.leave_service import LeaveService


leave_bp = Blueprint('leaves', __name__)
leave_service = LeaveService()


def _get_current_employee():
    if getattr(current_user, 'employee', None):
        return current_user.employee

    if getattr(current_user, 'employee_id', None):
        return Employee.query.get(current_user.employee_id)

    return None


def _is_manager():
    role_value = getattr(current_user.role, 'value', current_user.role)
    role_value = str(role_value).lower() if role_value is not None else ''
    return getattr(current_user, 'is_admin', False) or role_value in {'admin', 'manager', 'hr'}


@leave_bp.route('/employee')
@login_required
def employee_view():
    employee = _get_current_employee()
    if not employee:
        flash('لا يوجد ملف موظف مرتبط بحسابك', 'danger')
        return redirect(url_for('dashboard.index'))

    current_year = datetime.utcnow().year
    balances = LeaveBalance.query.filter_by(employee_id=employee.id, balance_year=current_year).all()
    requests_list = LeaveRequest.query.filter_by(employee_id=employee.id).order_by(LeaveRequest.created_at.desc()).all()

    return render_template(
        'leave/employee_view.html',
        employee=employee,
        balances=balances,
        requests_list=requests_list,
        current_year=current_year,
    )


@leave_bp.route('/request', methods=['POST'])
@login_required
def submit_request():
    employee = _get_current_employee()
    if not employee:
        flash('لا يوجد ملف موظف مرتبط بحسابك', 'danger')
        return redirect(url_for('dashboard.index'))

    try:
        leave_type = request.form.get('leave_type', '').strip()
        start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%d').date()
        reason = request.form.get('reason', '').strip()

        leave_service.create_leave_request(
            employee_id=employee.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )

        flash('تم إرسال طلب الإجازة بنجاح', 'success')
    except Exception as exc:
        flash(f'تعذر إرسال الطلب: {exc}', 'danger')

    return redirect(url_for('leaves.employee_view'))


@leave_bp.route('/manager')
@login_required
def manager_dashboard():
    if not _is_manager():
        flash('ليس لديك صلاحية لإدارة طلبات الإجازة', 'danger')
        return redirect(url_for('dashboard.index'))

    year = request.args.get('year', datetime.utcnow().year, type=int)
    month = request.args.get('month', datetime.utcnow().month, type=int)

    pending_requests = LeaveRequest.query.filter_by(status='Pending').order_by(LeaveRequest.created_at.asc()).all()

    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    month_requests = LeaveRequest.query.filter(
        LeaveRequest.start_date <= month_end,
        LeaveRequest.end_date >= month_start,
    ).all()

    days_matrix = calendar.monthcalendar(year, month)
    calendar_events = {}

    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        day_events = []
        day_date = datetime(year, month, day).date()
        for req in month_requests:
            if req.start_date <= day_date <= req.end_date:
                day_events.append({
                    'employee': req.employee.name if req.employee else f'#{req.employee_id}',
                    'type': req.leave_type,
                    'status': req.status,
                })
        calendar_events[day] = day_events

    return render_template(
        'leave/manager_dashboard.html',
        pending_requests=pending_requests,
        year=year,
        month=month,
        days_matrix=days_matrix,
        calendar_events=calendar_events,
    )


@leave_bp.route('/balances')
@login_required
def leave_balances():
    if not _is_manager():
        flash('ليس لديك صلاحية لعرض أرصدة الإجازات', 'danger')
        return redirect(url_for('dashboard.index'))

    year = request.args.get('year', datetime.utcnow().year, type=int)
    balances = LeaveBalance.query.filter_by(balance_year=year).order_by(
        LeaveBalance.employee_id.asc(),
        LeaveBalance.leave_type.asc(),
    ).all()

    return render_template(
        'leave/leave_balances.html',
        balances=balances,
        year=year,
    )


@leave_bp.route('/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_leave_request(request_id):
    if not _is_manager():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        manager_notes = request.form.get('manager_notes', '').strip()
        leave_request = leave_service.approve_request(request_id, current_user.id, manager_notes)
        return jsonify({
            'success': True,
            'message': 'تمت الموافقة على الطلب',
            'status': leave_request.status,
            'payroll_synced': leave_request.payroll_synced,
        })
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@leave_bp.route('/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_leave_request(request_id):
    if not _is_manager():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        reason = request.form.get('rejection_reason', '').strip()
        if not reason:
            return jsonify({'success': False, 'message': 'سبب الرفض مطلوب'}), 400

        leave_request = leave_service.reject_request(request_id, current_user.id, reason)
        return jsonify({
            'success': True,
            'message': 'تم رفض الطلب',
            'status': leave_request.status,
        })
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
