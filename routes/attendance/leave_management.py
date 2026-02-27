import calendar
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from core.extensions import db
from models import Employee, UserRole
from modules.leave.domain.models import LeaveRequest, LeaveBalance
from modules.leave.application.leave_service import LeaveService


leave_bp = Blueprint('leaves', __name__)
leave_service = LeaveService()

MONTH_NAMES_AR = {
    1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
    5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
    9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
}

DAY_NAMES_AR = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']

LEAVE_TYPE_AR = {
    'annual': 'سنوية',
    'sick': 'مرضية',
    'emergency': 'طارئة',
    'unpaid': 'بدون راتب',
    'maternity': 'أمومة',
    'paternity': 'أبوة',
    'compassionate': 'وفاة',
    'hajj': 'حج',
    'marriage': 'زواج',
    'other': 'أخرى',
}


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


def _leave_type_label(leave_type):
    if not leave_type:
        return 'غير محدد'
    return LEAVE_TYPE_AR.get(leave_type.lower(), leave_type)


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
    approved_requests = LeaveRequest.query.filter_by(status='Approved').count()
    rejected_requests = LeaveRequest.query.filter_by(status='Rejected').count()
    total_requests = LeaveRequest.query.count()

    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    month_requests = LeaveRequest.query.filter(
        LeaveRequest.start_date <= month_end,
        LeaveRequest.end_date >= month_start,
    ).all()

    month_pending = sum(1 for r in month_requests if r.status == 'Pending')
    month_approved = sum(1 for r in month_requests if r.status == 'Approved')

    days_matrix = calendar.monthcalendar(year, month)
    calendar_events = {}

    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        day_events = []
        day_date = datetime(year, month, day).date()
        for req in month_requests:
            if req.start_date <= day_date <= req.end_date:
                day_events.append({
                    'employee': req.employee.name if req.employee else f'#{req.employee_id}',
                    'type': _leave_type_label(req.leave_type),
                    'status': req.status,
                })
        calendar_events[day] = day_events

    months_list = [(m, MONTH_NAMES_AR[m]) for m in range(1, 13)]

    return render_template(
        'leave/manager_dashboard.html',
        pending_requests=pending_requests,
        year=year,
        month=month,
        month_name=MONTH_NAMES_AR.get(month, ''),
        days_matrix=days_matrix,
        calendar_events=calendar_events,
        day_names=DAY_NAMES_AR,
        months_list=months_list,
        current_year=datetime.utcnow().year,
        stats={
            'total': total_requests,
            'pending': len(pending_requests),
            'approved': approved_requests,
            'rejected': rejected_requests,
            'month_requests': len(month_requests),
            'month_pending': month_pending,
            'month_approved': month_approved,
        },
        leave_type_label=_leave_type_label,
    )


@leave_bp.route('/balances')
@login_required
def leave_balances():
    if not _is_manager():
        flash('ليس لديك صلاحية لعرض أرصدة الإجازات', 'danger')
        return redirect(url_for('dashboard.index'))

    year = request.args.get('year', datetime.utcnow().year, type=int)
    search = request.args.get('search', '').strip()
    leave_type_filter = request.args.get('leave_type', '').strip()

    query = LeaveBalance.query.filter_by(balance_year=year)

    if search:
        query = query.join(Employee, LeaveBalance.employee_id == Employee.id).filter(
            Employee.name.ilike(f'%{search}%')
        )

    if leave_type_filter:
        query = query.filter(LeaveBalance.leave_type == leave_type_filter)

    balances = query.order_by(
        LeaveBalance.employee_id.asc(),
        LeaveBalance.leave_type.asc(),
    ).all()

    total_accrued = sum(float(b.total_accrued or 0) for b in balances)
    total_used = sum(float(b.used or 0) for b in balances)
    total_remaining = sum(float(b.remaining or 0) for b in balances)
    unique_employees = len(set(b.employee_id for b in balances))

    leave_types = (
        db.session.query(LeaveBalance.leave_type)
        .filter_by(balance_year=year)
        .distinct()
        .all()
    )
    available_leave_types = [t[0] for t in leave_types]

    type_summary = {}
    for b in balances:
        lt = b.leave_type
        if lt not in type_summary:
            type_summary[lt] = {'accrued': 0, 'used': 0, 'remaining': 0, 'count': 0}
        type_summary[lt]['accrued'] += float(b.total_accrued or 0)
        type_summary[lt]['used'] += float(b.used or 0)
        type_summary[lt]['remaining'] += float(b.remaining or 0)
        type_summary[lt]['count'] += 1

    type_summary_list = [
        {'type': k, 'label': _leave_type_label(k), **v}
        for k, v in type_summary.items()
    ]

    low_balance_employees = [
        b for b in balances
        if float(b.remaining or 0) <= 3 and float(b.total_accrued or 0) > 0
    ]

    return render_template(
        'leave/leave_balances.html',
        balances=balances,
        year=year,
        current_year=datetime.utcnow().year,
        search=search,
        leave_type_filter=leave_type_filter,
        available_leave_types=available_leave_types,
        stats={
            'total_accrued': total_accrued,
            'total_used': total_used,
            'total_remaining': total_remaining,
            'unique_employees': unique_employees,
            'total_records': len(balances),
            'utilization_rate': (total_used / total_accrued * 100) if total_accrued > 0 else 0,
        },
        type_summary=type_summary_list,
        low_balance_employees=low_balance_employees,
        leave_type_label=_leave_type_label,
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
