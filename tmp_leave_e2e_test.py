from datetime import date, timedelta
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path

APP_FILE = Path(__file__).resolve().parent / 'app.py'
spec = importlib.util.spec_from_file_location('nuzm_app_entry', APP_FILE)
module = importlib.util.module_from_spec(spec)
sys.modules['app'] = module
spec.loader.exec_module(module)
app = module.app
from core.extensions import db
from models import Employee, User, UserRole
from modules.leave.application.leave_service import LeaveService
from modules.leave.domain.models import LeaveRequest
from modules.payroll.domain.models import PayrollRecord
from modules.payroll.application.payroll_processor import PayrollProcessor


def pick_two_weekdays_in_feb_2026():
    d = date(2026, 2, 1)
    end = date(2026, 2, 28)
    while d <= end:
        d2 = d + timedelta(days=1)
        if d2 <= end and d.weekday() not in (5, 6) and d2.weekday() not in (5, 6):
            return d, d2
        d += timedelta(days=1)
    raise RuntimeError('Could not find 2 weekdays in Feb 2026')


with app.app_context():
    svc = LeaveService()

    employee = Employee.query.filter(Employee.employee_id.in_(['172', 172])).first()
    if not employee:
        employee = Employee.query.filter(Employee.project.ilike('%Aramex%')).first()

    if not employee:
        raise RuntimeError('Employee 172 / Aramex not found')

    manager = User.query.filter(User.role.in_([UserRole.MANAGER, UserRole.ADMIN])).order_by(User.id.asc()).first()
    if not manager:
        raise RuntimeError('No manager/admin user found for approval step')

    start_date, end_date = pick_two_weekdays_in_feb_2026()

    payroll = PayrollRecord.query.filter_by(
        employee_id=employee.id,
        pay_period_year=2026,
        pay_period_month=2,
    ).first()

    if not payroll:
        processor = PayrollProcessor(2026, 2)
        payroll = processor.process_employee_payroll(employee.id)
        db.session.add(payroll)
        db.session.commit()

    net_before = Decimal(str(payroll.net_payable or 0))
    daily_rate_before = Decimal(str(payroll.daily_rate or 0))

    existing_pending = LeaveRequest.query.filter_by(
        employee_id=employee.id,
        leave_type='Unpaid',
        start_date=start_date,
        end_date=end_date,
        status='Pending'
    ).first()
    if existing_pending:
        db.session.delete(existing_pending)
        db.session.commit()

    req = svc.create_leave_request(
        employee_id=employee.id,
        leave_type='Unpaid',
        start_date=start_date,
        end_date=end_date,
        reason='Operational scenario test',
    )

    svc.approve_request(req.id, manager.id, 'Approved in real operation scenario test')

    db.session.refresh(req)
    payroll_after = PayrollRecord.query.filter_by(
        employee_id=employee.id,
        pay_period_year=2026,
        pay_period_month=2,
    ).first()

    net_after = Decimal(str(payroll_after.net_payable or 0))
    daily_rate_after = Decimal(str(payroll_after.daily_rate or 0))
    deduction = net_before - net_after

    print('=== REAL OPERATION SCENARIO RESULT ===')
    print(f'Employee DB ID: {employee.id}')
    print(f'Employee Code: {employee.employee_id}')
    print(f'Project: {employee.project}')
    print(f'Leave Request ID: {req.id}')
    print(f'Leave Type: {req.leave_type}')
    print(f'Leave Dates: {req.start_date} -> {req.end_date}')
    print(f'Working Days: {req.working_days}')
    print(f'Status: {req.status}')
    print(f'Payroll Synced: {req.payroll_synced}')
    print(f'Payroll Daily Rate (before): {daily_rate_before}')
    print(f'Payroll Daily Rate (after):  {daily_rate_after}')
    print(f'Net Before: {net_before}')
    print(f'Net After:  {net_after}')
    expected_deduction = (daily_rate_after * Decimal(2)).quantize(Decimal('0.01'))
    print(f'Actual Deduction: {deduction}')
    print(f'Expected Deduction (2 days): {expected_deduction}')

    if req.status == 'Approved' and req.payroll_synced and deduction == expected_deduction:
        print('SCENARIO_STATUS=PASS')
    else:
        print('SCENARIO_STATUS=CHECK_REQUIRED')
