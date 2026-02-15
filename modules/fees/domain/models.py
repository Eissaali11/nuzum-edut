"""
Fees & Charges Domain Models
Contains: RenewalFee, Fee, FeesCost
"""

from datetime import datetime
from core.extensions import db


class RenewalFee(db.Model):
    """تكاليف رسوم تجديد أوراق الموظفين"""
    __tablename__ = 'renewal_fees'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    fee_date = db.Column(db.Date, nullable=False)
    fee_type = db.Column(db.String(50), nullable=False)  # passport, labor_office, insurance, social_insurance, transfer_sponsorship, other
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    payment_date = db.Column(db.Date, nullable=True)
    receipt_number = db.Column(db.String(50), nullable=True)
    transfer_number = db.Column(db.String(50), nullable=True)  # رقم نقل الكفالة
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = db.relationship('Document', backref=db.backref('renewal_fees', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<RenewalFee {self.fee_type} for document #{self.document_id}>'


class Fee(db.Model):
    """نموذج الرسوم العامة - للاستخدام في تقارير الرسوم والمدفوعات"""
    __tablename__ = 'fees'
    
    id = db.Column(db.Integer, primary_key=True)
    fee_type = db.Column(db.String(50), nullable=False)  # نوع الرسم
    description = db.Column(db.String(255))  # وصف الرسم
    amount = db.Column(db.Float, nullable=False)  # مبلغ الرسم
    due_date = db.Column(db.Date)  # تاريخ استحقاق الرسم
    is_paid = db.Column(db.Boolean, default=False)  # هل تم دفع الرسم
    paid_date = db.Column(db.Date)  # تاريخ الدفع
    recipient = db.Column(db.String(100))  # الجهة المستلمة
    reference_number = db.Column(db.String(50))  # رقم المرجع
    notes = db.Column(db.Text)  # ملاحظات
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات (اختياري - يمكن ربط الرسم بموظف أو مركبة أو مستند)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='SET NULL'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id', ondelete='SET NULL'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='SET NULL'), nullable=True)
    
    # العلاقات
    employee = db.relationship('Employee', backref=db.backref('fees', lazy='dynamic'))
    document = db.relationship('Document', backref=db.backref('fees', lazy='dynamic'))
    vehicle = db.relationship('Vehicle', backref=db.backref('fees', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Fee {self.fee_type} - {self.amount} SAR>'


class FeesCost(db.Model):
    """تكاليف الرسوم للوثائق والمستندات"""
    __tablename__ = 'fees_costs'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # نوع الوثيقة: national_id, residence, passport, etc.
    
    # تكاليف مختلف الرسوم
    passport_fee = db.Column(db.Float, default=0.0)  # رسوم الجوازات
    labor_office_fee = db.Column(db.Float, default=0.0)  # رسوم مكتب العمل
    insurance_fee = db.Column(db.Float, default=0.0)  # رسوم التأمين
    social_insurance_fee = db.Column(db.Float, default=0.0)  # رسوم التأمينات الاجتماعية
    transfer_sponsorship = db.Column(db.Boolean, default=False)  # هل يتطلب نقل كفالة
    
    # معلومات التواريخ والدفع
    due_date = db.Column(db.Date, nullable=False)  # تاريخ استحقاق الرسوم
    payment_status = db.Column(db.String(20), default='pending')  # حالة السداد: pending, paid, overdue
    payment_date = db.Column(db.Date, nullable=True)  # تاريخ السداد
    
    # معلومات إضافية
    notes = db.Column(db.Text)  # ملاحظات
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    document = db.relationship('Document', backref=db.backref('fees_costs', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<FeesCost for document #{self.document_id}, type: {self.document_type}>'
    
    @property
    def total_fees(self):
        """إجمالي تكاليف جميع الرسوم"""
        return self.passport_fee + self.labor_office_fee + self.insurance_fee + self.social_insurance_fee
