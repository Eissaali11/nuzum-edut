"""
Properties & Housing Domain Models
Contains: RentalProperty, PropertyImage, PropertyPayment, PropertyFurnishing
"""

from datetime import datetime, date
from src.core.extensions import db


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

property_employees = db.Table('property_employees',
    db.Column('property_id', db.Integer, db.ForeignKey('rental_properties.id', ondelete='CASCADE'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), primary_key=True),
    db.Column('move_in_date', db.Date, nullable=True),  # تاريخ السكن
    db.Column('move_out_date', db.Date, nullable=True),  # تاريخ الخروج
    db.Column('notes', db.Text, nullable=True)  # ملاحظات
)


# ============================================================================
# MODELS
# ============================================================================

class RentalProperty(db.Model):
    """نموذج العقارات المستأجرة من قبل الشركة"""
    __tablename__ = 'rental_properties'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # معلومات العقار
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    map_link = db.Column(db.String(500), nullable=True)  # رابط الموقع على الخريطة
    location_link = db.Column(db.String(500), nullable=True)  # رابط موقع السكن
    
    # بيانات عقد الإيجار
    contract_number = db.Column(db.String(100), nullable=True, unique=False)  # رقم العقد اختياري
    contract_file = db.Column(db.String(500), nullable=True)  # ملف العقد (PDF أو صورة)
    owner_name = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.String(100), nullable=False)  # رقم هوية المالك / السجل التجاري
    contract_start_date = db.Column(db.Date, nullable=False)
    contract_end_date = db.Column(db.Date, nullable=False)
    
    # تفاصيل الإيجار
    annual_rent_amount = db.Column(db.Float, nullable=False)  # مبلغ الإيجار السنوي
    includes_utilities = db.Column(db.Boolean, default=False)  # يشمل الماء والكهرباء؟
    payment_method = db.Column(db.String(20), nullable=False)  # monthly, quarterly, semi_annually, annually
    
    # حالة العقار
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(30), default='active')  # active, expired, cancelled
    
    # ملاحظات
    notes = db.Column(db.Text, nullable=True)
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # العلاقات
    images = db.relationship('PropertyImage', back_populates='rental_property', cascade='all, delete-orphan')
    payments = db.relationship('PropertyPayment', back_populates='rental_property', cascade='all, delete-orphan')
    furnishings = db.relationship('PropertyFurnishing', back_populates='rental_property', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='rental_properties')
    
    # علاقة الموظفين القاطنين
    residents = db.relationship('Employee', secondary=property_employees, backref='housing_properties')
    
    @property
    def remaining_days(self):
        """حساب الأيام المتبقية للعقد"""
        if self.contract_end_date:
            delta = self.contract_end_date - date.today()
            return delta.days if delta.days > 0 else 0
        return 0
    
    @property
    def is_expiring_soon(self):
        """هل العقد قريب من الانتهاء (خلال 60 يوم)"""
        return 0 < self.remaining_days <= 60
    
    @property
    def is_expired(self):
        """هل العقد منتهي"""
        return self.contract_end_date < date.today()
    
    @property
    def payment_amount_per_period(self):
        """حساب مبلغ الدفعة حسب طريقة السداد"""
        if self.payment_method == 'monthly':
            return self.annual_rent_amount / 12
        elif self.payment_method == 'quarterly':
            return self.annual_rent_amount / 4
        elif self.payment_method == 'semi_annually':
            return self.annual_rent_amount / 2
        else:  # annually
            return self.annual_rent_amount
    
    def __repr__(self):
        return f'<RentalProperty {self.contract_number} - {self.city}>'


class PropertyImage(db.Model):
    """صور العقارات المستأجرة"""
    __tablename__ = 'property_images'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('rental_properties.id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    image_type = db.Column(db.String(50), nullable=True)  # واجهة، غرف، مطبخ، دورة مياه، أخرى
    description = db.Column(db.String(200), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    rental_property = db.relationship('RentalProperty', back_populates='images')
    
    def __repr__(self):
        return f'<PropertyImage {self.id} - {self.image_type}>'


class PropertyPayment(db.Model):
    """جدول دفعات الإيجار"""
    __tablename__ = 'property_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('rental_properties.id', ondelete='CASCADE'), nullable=False)
    
    # معلومات الدفعة
    payment_date = db.Column(db.Date, nullable=False)  # تاريخ الدفعة المتوقع
    amount = db.Column(db.Float, nullable=False)  # مبلغ الدفعة
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    actual_payment_date = db.Column(db.Date, nullable=True)  # التاريخ الفعلي للدفع
    
    # الملاحظات
    notes = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)  # نقدي، تحويل بنكي، شيك
    reference_number = db.Column(db.String(100), nullable=True)  # رقم مرجعي للدفعة
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    rental_property = db.relationship('RentalProperty', back_populates='payments')
    
    def is_overdue(self):
        """هل الدفعة متأخرة"""
        return self.status == 'pending' and self.payment_date < date.today()
    
    @property
    def days_until_due(self):
        """عدد الأيام حتى موعد الدفع"""
        if self.payment_date:
            delta = self.payment_date - date.today()
            return delta.days
        return None
    
    def __repr__(self):
        return f'<PropertyPayment {self.id} - {self.amount} SAR - {self.status}>'


class PropertyFurnishing(db.Model):
    """تجهيزات ومحتويات العقار المستأجر"""
    __tablename__ = 'property_furnishings'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('rental_properties.id', ondelete='CASCADE'), nullable=False)
    
    # أنواع التجهيزات
    gas_cylinder = db.Column(db.Integer, default=0)  # عدد جرات الغاز
    stoves = db.Column(db.Integer, default=0)  # عدد الطباخات
    beds = db.Column(db.Integer, default=0)  # عدد الأسرة
    blankets = db.Column(db.Integer, default=0)  # عدد البطانيات
    pillows = db.Column(db.Integer, default=0)  # عدد المخدات
    
    # تجهيزات إضافية (نص حر)
    other_items = db.Column(db.Text, nullable=True)
    
    # ملاحظات
    notes = db.Column(db.Text, nullable=True)
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    rental_property = db.relationship('RentalProperty', back_populates='furnishings')
    
    def __repr__(self):
        return f'<PropertyFurnishing {self.id} - Property {self.property_id}>'
