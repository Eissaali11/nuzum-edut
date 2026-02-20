"""
Strategic Payroll Engine - Domain Models
نموذج جداول الرواتب والمزايا والخصومات
يتوافق مع نظام العمل السعودي
"""
from datetime import datetime, date
from decimal import Decimal
from core.extensions import db


class PayrollRecord(db.Model):
    """سجل الراتب الشامل للموظف"""
    __tablename__ = 'payroll_records'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # فترة الراتب
    pay_period_year = db.Column(db.Integer, nullable=False)
    pay_period_month = db.Column(db.Integer, nullable=False)  # 1-12
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    
    # ═══════════════════════════════════════════════════════════════════
    # المرتب الأساسي والمزايا
    # ═══════════════════════════════════════════════════════════════════
    
    basic_salary = db.Column(db.Numeric(12, 2), nullable=False)
    daily_rate = db.Column(db.Numeric(10, 4), default=0)  # الراتب اليومي
    hourly_rate = db.Column(db.Numeric(10, 4), default=0)  # الراتب بالساعة
    
    # المزايا الإضافية
    housing_allowance = db.Column(db.Numeric(10, 2), default=0)  # بدل السكن
    transportation = db.Column(db.Numeric(10, 2), default=0)  # بدل المواصلات
    meal_allowance = db.Column(db.Numeric(10, 2), default=0)  # بدل الطعام
    performance_bonus = db.Column(db.Numeric(10, 2), default=0)  # حافز الأداء
    attendance_bonus = db.Column(db.Numeric(10, 2), default=0)  # بدل الحضور
    other_allowances = db.Column(db.Numeric(10, 2), default=0)  # مزايا أخرى
    
    # ═══════════════════════════════════════════════════════════════════
    # حسابات الحضور والغياب
    # ═══════════════════════════════════════════════════════════════════
    
    working_days_required = db.Column(db.Integer, default=22)  # أيام العمل المطلوبة
    actual_working_days = db.Column(db.Integer, default=0)  # الأيام الفعلية
    present_days = db.Column(db.Integer, default=0)  # أيام الحضور
    absent_days = db.Column(db.Integer, default=0)  # أيام الغياب
    leave_days = db.Column(db.Integer, default=0)  # أيام الإجازة (مدفوعة)
    unpaid_leave_days = db.Column(db.Integer, default=0)  # إجازة بدون راتب
    sick_leave_days = db.Column(db.Integer, default=0)  # إجازة مرضية
    public_holiday_days = db.Column(db.Integer, default=0)  # أيام العطل والأعياد
    
    # ساعات العمل
    total_working_hours = db.Column(db.Numeric(10, 2), default=0)  # إجمالي ساعات العمل
    overtime_hours = db.Column(db.Numeric(10, 2), default=0)  # ساعات إضافية
    
    # ═══════════════════════════════════════════════════════════════════
    # الحسابات والخصومات
    # ═══════════════════════════════════════════════════════════════════
    
    # الراتب الإجمالي قبل الخصومات
    gross_salary = db.Column(db.Numeric(12, 2), default=0)
    
    # غياب والتأخيرات
    absence_deduction = db.Column(db.Numeric(10, 2), default=0)  # خصم الغياب
    late_deduction = db.Column(db.Numeric(10, 2), default=0)  # خصم التأخير
    early_leave_deduction = db.Column(db.Numeric(10, 2), default=0)  # خصم الانصراف المبكر
    
    # الخصومات القانونية
    gosi_employee = db.Column(db.Numeric(10, 2), default=0)  # اشتراك الموظف (GOSI) - 10%
    gosi_company = db.Column(db.Numeric(10, 2), default=0)  # اشتراك الشركة (GOSI)
    income_tax = db.Column(db.Numeric(10, 2), default=0)  # ضريبة الدخل (إن وجدت)
    
    # خصومات أخرى
    loan_deduction = db.Column(db.Numeric(10, 2), default=0)  # خصم قرض
    advance_salary = db.Column(db.Numeric(10, 2), default=0)  # راتب مقدم
    insurance_deduction = db.Column(db.Numeric(10, 2), default=0)  # خصم التأمين
    other_deductions = db.Column(db.Numeric(10, 2), default=0)  # خصومات أخرى
    
    # إجمالي الخصومات
    total_deductions = db.Column(db.Numeric(12, 2), default=0)
    
    # ═══════════════════════════════════════════════════════════════════
    # الراتب النهائي
    # ═══════════════════════════════════════════════════════════════════
    
    net_payable = db.Column(db.Numeric(12, 2), default=0)  # الراتب الصافي المستحق
    
    # ═══════════════════════════════════════════════════════════════════
    # معلومات الدفع
    # ═══════════════════════════════════════════════════════════════════
    
    payment_method = db.Column(db.String(50), default='bank_transfer')  # طريقة الدفع
    bank_account = db.Column(db.String(30))  # رقم الحساب البنكي
    bank_name = db.Column(db.String(100))  # اسم البنك
    payment_status = db.Column(db.String(20), default='pending')  # الحالة: pending, approved, paid, rejected
    payment_date = db.Column(db.DateTime)  # تاريخ الدفع الفعلي
    
    # ═══════════════════════════════════════════════════════════════════
    # التحقق والموافقة
    # ═══════════════════════════════════════════════════════════════════
    
    calculated_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # المستخدم الذي قام بالحساب
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # المستخدم الذي وافق على الراتب
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # المستخدم الذي قام بمراجعة الراتب
    
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    
    # الملاحظات
    notes = db.Column(db.Text)  # ملاحظات إضافية
    admin_notes = db.Column(db.Text)  # ملاحظات الإدارة
    
    # ═══════════════════════════════════════════════════════════════════
    # البيانات الوصفية
    # ═══════════════════════════════════════════════════════════════════
    
    is_locked = db.Column(db.Boolean, default=False)  # هل الراتب مقفل (لا يمكن تعديله)
    is_exported = db.Column(db.Boolean, default=False)  # هل تم تصديره
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    employee = db.relationship('Employee', backref=db.backref('payroll_records', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('idx_employee_period', 'employee_id', 'pay_period_year', 'pay_period_month', unique=True),
        db.Index('idx_payroll_status', 'payment_status'),
        db.Index('idx_payroll_period', 'pay_period_year', 'pay_period_month'),
    )
    
    def __repr__(self):
        return f'<PayrollRecord {self.employee_id} - {self.pay_period_month}/{self.pay_period_year}>'


class PayrollConfiguration(db.Model):
    """إعدادات الرواتب والنسب المئوية"""
    __tablename__ = 'payroll_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # النسب المئوية والحسابات
    gosi_employee_percentage = db.Column(db.Numeric(5, 2), default=10)  # 10% من الراتب الأساسي
    gosi_company_percentage = db.Column(db.Numeric(5, 2), default=13)  # 13% من الراتب الأساسي
    income_tax_percentage = db.Column(db.Numeric(5, 2), default=0)  # نسبة ضريبة الدخل
    
    # أيام العمل
    working_days_per_month = db.Column(db.Integer, default=22)
    working_hours_per_day = db.Column(db.Numeric(5, 2), default=8)
    
    # الحد الأدنى للراتب (Minimum Wage)
    minimum_wage = db.Column(db.Numeric(12, 2), default=2000)
    
    # سياسة التأخيرات
    late_deduction_percentage = db.Column(db.Numeric(5, 2), default=0.5)  # خصم التأخيرات %
    late_deduction_per_hour = db.Column(db.Numeric(10, 2), default=0)  # خصم بالساعة
    
    # الساعات الإضافية
    overtime_multiplier = db.Column(db.Numeric(5, 2), default=1.5)  # 1.5x للساعات الإضافية
    
    # الجنسيات (للتحقق من متطلبات GOSI)
    saudi_national_gosi_required = db.Column(db.Boolean, default=True)
    expat_gosi_required = db.Column(db.Boolean, default=True)
    
    # البنك والتحويلات
    default_bank_code = db.Column(db.String(10))  # رمز البنك الافتراضي
    bank_transfer_fee = db.Column(db.Numeric(10, 2), default=0)  # رسوم التحويل
    
    # التاريخ النشط
    effective_from = db.Column(db.Date, default=date.today)
    effective_to = db.Column(db.Date)
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PayrollConfiguration from {self.effective_from}>'


class PayrollHistory(db.Model):
    """سجل تاريخي للتغييرات على الرواتب"""
    __tablename__ = 'payroll_history'
    
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll_records.id', ondelete='CASCADE'))
    
    # البيانات المتغيرة
    field_name = db.Column(db.String(100))  # اسم الحقل المتغير
    old_value = db.Column(db.String(255))  # القيمة القديمة
    new_value = db.Column(db.String(255))  # القيمة الجديدة
    
    # معلومات التعديل
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    change_reason = db.Column(db.Text)
    
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    payroll = db.relationship('PayrollRecord', backref=db.backref('history', lazy='dynamic'))
    
    def __repr__(self):
        return f'<PayrollHistory {self.payroll_id} - {self.field_name}>'


class BankTransferFile(db.Model):
    """ملف تحويل بنكي للدفع الجماعي"""
    __tablename__ = 'bank_transfer_files'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # معلومات الملف
    file_name = db.Column(db.String(255), unique=True)
    file_path = db.Column(db.String(500))
    file_format = db.Column(db.String(20), default='txt')  # txt, csv, xml
    
    # فترة الراتب
    pay_period_year = db.Column(db.Integer)
    pay_period_month = db.Column(db.Integer)
    
    # البنك
    bank_code = db.Column(db.String(10))
    bank_name = db.Column(db.String(100))
    
    # إحصائيات
    total_records = db.Column(db.Integer, default=0)  # عدد الموظفين
    total_amount = db.Column(db.Numeric(15, 2), default=0)  # إجمالي المبلغ
    
    # الحالة
    status = db.Column(db.String(20), default='draft')  # draft, ready, sent, confirmed
    
    # معلومات الإرسال
    sent_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    sent_at = db.Column(db.DateTime)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    confirmed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BankTransferFile {self.file_name}>'
