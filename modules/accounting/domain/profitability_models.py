from datetime import datetime
from core.extensions import db


class ProjectContract(db.Model):
    __tablename__ = 'project_contracts'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='CASCADE'), nullable=False, index=True)
    client_name = db.Column(db.String(200), nullable=False)
    contract_number = db.Column(db.String(100), nullable=True)
    contract_type = db.Column(db.String(50), nullable=False, default='manpower')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='active')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship('Department', backref=db.backref('contracts', lazy='dynamic'))
    resources = db.relationship('ContractResource', back_populates='contract', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def contract_type_ar(self):
        return {'manpower': 'قوى عاملة', 'outsource': 'تعهيد خارجي', 'mixed': 'مختلط'}.get(self.contract_type, self.contract_type)

    @property
    def status_ar(self):
        return {'active': 'نشط', 'expired': 'منتهي', 'suspended': 'معلّق', 'draft': 'مسودة'}.get(self.status, self.status)

    def __repr__(self):
        return f'<ProjectContract {self.client_name} - dept:{self.department_id}>'


class ContractResource(db.Model):
    __tablename__ = 'contract_resources'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('project_contracts.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    billing_rate = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    billing_type = db.Column(db.String(20), nullable=False, default='monthly')
    overhead_monthly = db.Column(db.Numeric(10, 2), default=0)
    housing_allowance = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship('ProjectContract', back_populates='resources')
    employee = db.relationship('Employee', backref=db.backref('contract_resources', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('contract_id', 'employee_id', name='uq_contract_employee'),
    )

    @property
    def billing_type_ar(self):
        return {'monthly': 'شهري', 'daily': 'يومي'}.get(self.billing_type, self.billing_type)

    def __repr__(self):
        return f'<ContractResource contract:{self.contract_id} emp:{self.employee_id} rate:{self.billing_rate}>'
