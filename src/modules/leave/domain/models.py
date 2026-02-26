from datetime import datetime
from src.core.extensions import db


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)

    leave_type = db.Column(db.String(30), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    reason = db.Column(db.Text)

    requested_days = db.Column(db.Integer, default=0, nullable=False)
    working_days = db.Column(db.Integer, default=0, nullable=False)

    status = db.Column(db.String(20), default='Pending', nullable=False, index=True)
    manager_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)

    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)

    payroll_synced = db.Column(db.Boolean, default=False, nullable=False)
    payroll_synced_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('leave_requests', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_leave_employee_status', 'employee_id', 'status'),
        db.Index('idx_leave_period', 'start_date', 'end_date'),
    )

    def __repr__(self):
        return f'<LeaveRequest emp={self.employee_id} {self.leave_type} {self.status}>'


class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)

    leave_type = db.Column(db.String(30), nullable=False, index=True)
    balance_year = db.Column(db.Integer, nullable=False, index=True)

    total_accrued = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    used = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    remaining = db.Column(db.Numeric(10, 2), default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('leave_balances', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'leave_type', 'balance_year', name='uq_leave_balance_emp_type_year'),
    )

    def recalculate_remaining(self):
        self.remaining = (self.total_accrued or 0) - (self.used or 0)

    def __repr__(self):
        return f'<LeaveBalance emp={self.employee_id} type={self.leave_type} year={self.balance_year}>'
