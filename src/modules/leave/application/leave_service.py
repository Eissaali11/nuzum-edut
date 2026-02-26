from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.core.extensions import db
from models import Employee
from src.modules.leave.domain.models import LeaveRequest, LeaveBalance
from src.modules.payroll.domain.models import PayrollRecord
from src.modules.payroll.application.payroll_processor import PayrollProcessor


class LeaveService:
    PAID_LEAVE_TYPES = {'Annual', 'Sick'}

    def get_or_create_balance(self, employee_id: int, leave_type: str, year: int) -> LeaveBalance:
        balance = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            leave_type=leave_type,
            balance_year=year,
        ).first()

        if not balance:
            default_accrual = Decimal('21') if leave_type == 'Annual' else Decimal('15') if leave_type == 'Sick' else Decimal('0')
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type=leave_type,
                balance_year=year,
                total_accrued=default_accrual,
                used=Decimal('0'),
                remaining=default_accrual,
            )
            db.session.add(balance)
            db.session.flush()

        return balance

    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        if end_date < start_date:
            return 0

        days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() not in (5, 6):
                days += 1
            current += timedelta(days=1)

        return days

    def has_sufficient_balance(self, employee_id: int, leave_type: str, leave_days: int, year: int) -> tuple[bool, Decimal]:
        if leave_type not in self.PAID_LEAVE_TYPES:
            return True, Decimal('0')

        balance = self.get_or_create_balance(employee_id, leave_type, year)
        remaining = Decimal(str(balance.remaining or 0))
        requested = Decimal(str(leave_days))
        return remaining >= requested, remaining

    def create_leave_request(self, employee_id: int, leave_type: str, start_date: date, end_date: date, reason: str = '') -> LeaveRequest:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise ValueError('Employee not found')

        if end_date < start_date:
            raise ValueError('End date must be greater than or equal to start date')

        working_days = self.calculate_working_days(start_date, end_date)
        if working_days <= 0:
            raise ValueError('No working leave days in selected range')

        enough, remaining = self.has_sufficient_balance(employee_id, leave_type, working_days, start_date.year)
        if not enough:
            raise ValueError(f'Insufficient balance: remaining {remaining}, requested {working_days}')

        leave_request = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            requested_days=working_days,
            working_days=working_days,
            status='Pending',
        )

        db.session.add(leave_request)
        db.session.commit()
        return leave_request

    def approve_request(self, leave_request_id: int, manager_id: int, manager_notes: str = '') -> LeaveRequest:
        leave_request = LeaveRequest.query.get(leave_request_id)
        if not leave_request:
            raise ValueError('Leave request not found')

        if leave_request.status != 'Pending':
            raise ValueError('Request already processed')

        leave_request.status = 'Approved'
        leave_request.approved_by = manager_id
        leave_request.approved_at = datetime.utcnow()
        leave_request.manager_notes = manager_notes

        if leave_request.leave_type in self.PAID_LEAVE_TYPES:
            balance = self.get_or_create_balance(
                leave_request.employee_id,
                leave_request.leave_type,
                leave_request.start_date.year,
            )
            balance.used = Decimal(str(balance.used or 0)) + Decimal(str(leave_request.working_days or 0))
            balance.recalculate_remaining()

        db.session.commit()

        if leave_request.leave_type == 'Unpaid':
            self.sync_to_payroll(leave_request.id)

        return leave_request

    def reject_request(self, leave_request_id: int, manager_id: int, rejection_reason: str) -> LeaveRequest:
        leave_request = LeaveRequest.query.get(leave_request_id)
        if not leave_request:
            raise ValueError('Leave request not found')

        if leave_request.status != 'Pending':
            raise ValueError('Request already processed')

        leave_request.status = 'Rejected'
        leave_request.approved_by = manager_id
        leave_request.approved_at = datetime.utcnow()
        leave_request.rejection_reason = rejection_reason

        db.session.commit()
        return leave_request

    def _count_unpaid_days_by_month(self, start_date: date, end_date: date) -> dict:
        result = defaultdict(int)
        current = start_date
        while current <= end_date:
            if current.weekday() not in (5, 6):
                result[(current.year, current.month)] += 1
            current += timedelta(days=1)
        return result

    def sync_to_payroll(self, leave_request_id: int) -> dict:
        leave_request = LeaveRequest.query.get(leave_request_id)
        if not leave_request:
            raise ValueError('Leave request not found')

        if leave_request.leave_type != 'Unpaid':
            return {'synced': False, 'message': 'Leave type is not unpaid'}

        if leave_request.status != 'Approved':
            raise ValueError('Only approved requests can sync to payroll')

        if leave_request.payroll_synced:
            return {'synced': True, 'message': 'Already synced'}

        employee = Employee.query.get(leave_request.employee_id)
        if not employee:
            raise ValueError('Employee not found')

        days_by_month = self._count_unpaid_days_by_month(leave_request.start_date, leave_request.end_date)
        updated_records = 0

        for (year, month), unpaid_days in days_by_month.items():
            payroll = PayrollRecord.query.filter_by(
                employee_id=employee.id,
                pay_period_year=year,
                pay_period_month=month,
            ).first()

            if not payroll:
                processor = PayrollProcessor(year, month)
                payroll = processor.process_employee_payroll(employee.id)
                db.session.add(payroll)
                db.session.flush()

            daily_rate = Decimal(str(payroll.daily_rate or 0))
            if daily_rate <= 0:
                processor = PayrollProcessor(year, month)
                daily_rate = processor.calculate_daily_rate(Decimal(str(payroll.basic_salary or employee.basic_salary or 0)))
                payroll.daily_rate = daily_rate

            extra_deduction = (Decimal(str(unpaid_days)) * daily_rate).quantize(Decimal('0.01'))

            payroll.unpaid_leave_days = int(payroll.unpaid_leave_days or 0) + int(unpaid_days)
            payroll.total_deductions = Decimal(str(payroll.total_deductions or 0)) + extra_deduction
            payroll.net_payable = Decimal(str(payroll.net_payable or 0)) - extra_deduction
            if payroll.net_payable < 0:
                payroll.net_payable = Decimal('0')

            note_text = f'Unpaid leave synced: +{unpaid_days} day(s) for {month}/{year}'
            payroll.admin_notes = f'{payroll.admin_notes}\n{note_text}' if payroll.admin_notes else note_text

            updated_records += 1

        leave_request.payroll_synced = True
        leave_request.payroll_synced_at = datetime.utcnow()

        db.session.commit()

        return {
            'synced': True,
            'updated_payroll_records': updated_records,
            'unpaid_days': leave_request.working_days,
        }
