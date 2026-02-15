"""
Additional Vehicle Domain Models - Maintenance, Inspections, Accidents, Safety
Contains: VehicleChecklist, VehicleMaintenance, VehiclePeriodicInspection, VehicleSafetyCheck
          VehicleAccident, VehicleExternalSafetyCheck, SafetyInspection, VehicleInspectionRecord
          Project, ExternalAuthorization and related models
"""

from datetime import datetime, date
from core.extensions import db


# ============================================================================
# VEHICLE CHECKLIST MODELS
# ============================================================================

class VehicleChecklist(db.Model):
    """تشيك لست فحص السيارة"""
    __tablename__ = 'vehicle_checklist'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)  # تاريخ الفحص
    inspector_name = db.Column(db.String(100), nullable=False)  # اسم الفاحص
    inspection_type = db.Column(db.String(20), nullable=False)  # نوع الفحص: يومي، أسبوعي، شهري، ربع سنوي
    status = db.Column(db.String(20), default='completed')  # حالة الفحص: مكتمل، قيد التنفيذ، ملغي
    notes = db.Column(db.Text)  # ملاحظات عامة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('checklists', cascade='all, delete-orphan'))
    checklist_items = db.relationship('VehicleChecklistItem', back_populates='checklist', cascade='all, delete-orphan')
    images = db.relationship('VehicleChecklistImage', back_populates='checklist', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VehicleChecklist {self.id} for vehicle {self.vehicle_id} on {self.inspection_date}>'
    
    @property
    def completion_percentage(self):
        """حساب نسبة اكتمال الفحص"""
        if not self.checklist_items:
            return 0
        
        total_items = len(self.checklist_items)
        completed_items = sum(1 for item in self.checklist_items if item.status != 'not_checked')
        
        return int((completed_items / total_items) * 100)
    
    @property
    def summary(self):
        """ملخص حالة الفحص"""
        if not self.checklist_items:
            return {'good': 0, 'fair': 0, 'poor': 0, 'not_checked': 0}
        
        summary = {'good': 0, 'fair': 0, 'poor': 0, 'not_checked': 0}
        for item in self.checklist_items:
            summary[item.status] += 1
        
        return summary


class VehicleChecklistItem(db.Model):
    """عناصر تشيك لست فحص السيارة"""
    __tablename__ = 'vehicle_checklist_item'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('vehicle_checklist.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # فئة العنصر: محرك، إطارات، إضاءة، مكونات داخلية، إلخ
    item_name = db.Column(db.String(100), nullable=False)  # اسم العنصر: زيت المحرك، ضغط الإطارات، إلخ
    status = db.Column(db.String(20), nullable=False, default='not_checked')  # الحالة: جيد، متوسط، سيء، لم يتم الفحص
    notes = db.Column(db.Text)  # ملاحظات خاصة بالعنصر
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    checklist = db.relationship('VehicleChecklist', back_populates='checklist_items')
    
    def __repr__(self):
        return f'<VehicleChecklistItem {self.id} {self.item_name} status: {self.status}>'


class VehicleChecklistImage(db.Model):
    """صور فحص السيارة (تشيك لست)"""
    __tablename__ = 'vehicle_checklist_image'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('vehicle_checklist.id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)  # مسار الصورة
    image_type = db.Column(db.String(50), default='inspection')  # نوع الصورة: فحص عام، ضرر، إلخ
    description = db.Column(db.Text)  # وصف الصورة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    checklist = db.relationship('VehicleChecklist', back_populates='images')
    
    def __repr__(self):
        return f'<VehicleChecklistImage {self.id} for checklist {self.checklist_id}>'


class VehicleDamageMarker(db.Model):
    """علامات تلف السيارة المسجلة على الرسم البياني للمركبة"""
    __tablename__ = 'vehicle_damage_marker'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('vehicle_checklist.id', ondelete='CASCADE'), nullable=False)
    marker_type = db.Column(db.String(20), nullable=False, default='damage')  # نوع العلامة: تلف، خدش، كسر، إلخ
    position_x = db.Column(db.Float, nullable=False)  # الموقع س على الصورة (نسبة مئوية)
    position_y = db.Column(db.Float, nullable=False)  # الموقع ص على الصورة (نسبة مئوية)
    color = db.Column(db.String(20), default='red')  # لون العلامة
    size = db.Column(db.Float, default=10.0)  # حجم العلامة
    notes = db.Column(db.Text)  # ملاحظات حول التلف
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    checklist = db.relationship('VehicleChecklist', backref=db.backref('damage_markers', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<VehicleDamageMarker {self.id} for checklist {self.checklist_id} at ({self.position_x}, {self.position_y})>'


# ============================================================================
# VEHICLE MAINTENANCE MODELS
# ============================================================================

class VehicleMaintenance(db.Model):
    """سجل صيانة المركبات"""
    __tablename__ = 'vehicle_maintenance'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # تاريخ الصيانة
    maintenance_type = db.Column(db.String(30), nullable=False)  # نوع الصيانة: دورية، طارئة، إصلاح، فحص
    description = db.Column(db.String(200), nullable=False)  # وصف الصيانة
    status = db.Column(db.String(20), nullable=False)  # حالة الصيانة: قيد الانتظار، قيد التنفيذ، منجزة، ملغية
    cost = db.Column(db.Float, default=0.0)  # تكلفة الصيانة
    technician = db.Column(db.String(100), nullable=False)  # الفني المسؤول
    receipt_image_url = db.Column(db.String(255))  # رابط صورة الإيصال
    delivery_receipt_url = db.Column(db.String(255))  # رابط إيصال تسليم السيارة للورشة
    pickup_receipt_url = db.Column(db.String(255))  # رابط إيصال استلام السيارة من الورشة
    parts_replaced = db.Column(db.Text)  # قطع الغيار المستبدلة
    actions_taken = db.Column(db.Text)  # الإجراءات المتخذة
    notes = db.Column(db.Text)  # ملاحظات إضافية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('maintenance_records', cascade='all, delete-orphan'))
    images = db.relationship('VehicleMaintenanceImage', back_populates='maintenance_record', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VehicleMaintenance {self.id} {self.maintenance_type} for vehicle {self.vehicle_id}>'


class VehicleMaintenanceImage(db.Model):
    """صور توثيقية لصيانة السيارة"""
    __tablename__ = 'vehicle_maintenance_image'
    
    id = db.Column(db.Integer, primary_key=True)
    maintenance_id = db.Column(db.Integer, db.ForeignKey('vehicle_maintenance.id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)  # مسار الصورة
    image_type = db.Column(db.String(20), nullable=False)  # النوع: قبل الصيانة، بعد الصيانة
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    maintenance_record = db.relationship('VehicleMaintenance', back_populates='images')
    
    def __repr__(self):
        return f'<VehicleMaintenanceImage {self.id} for maintenance {self.maintenance_id}>'


class VehicleFuelConsumption(db.Model):
    """تسجيل استهلاك الوقود اليومي للسيارات"""
    __tablename__ = 'vehicle_fuel_consumption'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # تاريخ تعبئة الوقود
    liters = db.Column(db.Float, nullable=False)  # كمية اللترات
    cost = db.Column(db.Float, nullable=False)  # التكلفة الإجمالية
    kilometer_reading = db.Column(db.Integer)  # قراءة عداد المسافة
    driver_name = db.Column(db.String(100))  # اسم السائق
    fuel_type = db.Column(db.String(20), default='بنزين')  # نوع الوقود (بنزين، ديزل، إلخ)
    filling_station = db.Column(db.String(100))  # محطة الوقود
    notes = db.Column(db.Text)  # ملاحظات إضافية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('fuel_records', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<VehicleFuelConsumption {self.id} {self.liters} liters for vehicle {self.vehicle_id}>'
    
    @property
    def cost_per_liter(self):
        """حساب تكلفة اللتر الواحد"""
        if self.liters and self.liters > 0:
            return self.cost / self.liters
        return 0


class VehiclePeriodicInspection(db.Model):
    """سجل الفحص الدوري للسيارات"""
    __tablename__ = 'vehicle_periodic_inspection'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)  # تاريخ الفحص
    expiry_date = db.Column(db.Date, nullable=False)  # تاريخ انتهاء الفحص
    
    # الحقول الجديدة
    inspection_center = db.Column(db.String(100), nullable=True)  # مركز الفحص
    result = db.Column(db.String(20), nullable=True)  # نتيجة الفحص
    driver_name = db.Column(db.String(100), nullable=True)  # اسم السائق
    supervisor_name = db.Column(db.String(100), nullable=True)  # اسم المشرف
    
    # الحقول القديمة (للتوافق مع قاعدة البيانات الحالية)
    inspection_number = db.Column(db.String(100), nullable=True)  # رقم الفحص (قديم)
    inspector_name = db.Column(db.String(100), nullable=True)  # اسم الفاحص (قديم)
    inspection_type = db.Column(db.String(20), nullable=True)  # نوع الفحص (قديم)
    
    inspection_status = db.Column(db.String(20), default='valid')  # حالة الفحص: ساري، منتهي، على وشك الانتهاء
    cost = db.Column(db.Float, default=0.0)  # تكلفة الفحص
    results = db.Column(db.Text)  # نتائج الفحص
    recommendations = db.Column(db.Text)  # التوصيات
    certificate_file = db.Column(db.String(255))  # مسار ملف شهادة الفحص
    notes = db.Column(db.Text)  # ملاحظات إضافية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', back_populates='periodic_inspections')
    
    def __repr__(self):
        return f'<VehiclePeriodicInspection {self.id} for vehicle {self.vehicle_id} expires on {self.expiry_date}>'
    
    @property
    def is_expired(self):
        """التحقق مما إذا كان الفحص منتهي الصلاحية"""
        return self.expiry_date < datetime.now().date()
    
    @property
    def is_expiring_soon(self):
        """التحقق مما إذا كان الفحص على وشك الانتهاء (خلال 30 يوم)"""
        delta = self.expiry_date - datetime.now().date()
        return 0 <= delta.days <= 30


class VehicleSafetyCheck(db.Model):
    """فحص السلامة للسيارات (يومي، أسبوعي، شهري)"""
    __tablename__ = 'vehicle_safety_check'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    check_date = db.Column(db.Date, nullable=False)  # تاريخ الفحص
    check_type = db.Column(db.String(20), nullable=False)  # نوع الفحص: يومي، أسبوعي، شهري
    driver_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)  # معرف السائق
    driver_name = db.Column(db.String(100), nullable=False)  # اسم السائق
    supervisor_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)  # معرف المشرف
    supervisor_name = db.Column(db.String(100), nullable=False)  # اسم المشرف
    status = db.Column(db.String(20), default='completed')  # حالة الفحص: مكتمل، قيد التنفيذ، بحاجة للمراجعة
    check_form_link = db.Column(db.String(255))  # رابط نموذج الفحص
    issues_found = db.Column(db.Boolean, default=False)  # هل تم العثور على مشاكل؟
    issues_description = db.Column(db.Text)  # وصف المشاكل
    actions_taken = db.Column(db.Text)  # الإجراءات المتخذة
    notes = db.Column(db.Text)  # ملاحظات
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', back_populates='safety_checks')
    driver = db.relationship('Employee', foreign_keys=[driver_id])
    supervisor = db.relationship('Employee', foreign_keys=[supervisor_id])
    
    def __repr__(self):
        return f'<VehicleSafetyCheck {self.id} {self.check_type} check for vehicle {self.vehicle_id}>'


# ============================================================================
# VEHICLE ACCIDENT MODELS
# ============================================================================

class VehicleAccident(db.Model):
    """نموذج الحوادث المرورية للمركبات"""
    __tablename__ = 'vehicle_accident'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # معلومات التقرير
    accident_date = db.Column(db.Date, nullable=False, index=True)  # تاريخ الحادث
    accident_time = db.Column(db.Time)  # وقت الحادث
    driver_name = db.Column(db.String(100), nullable=False)  # اسم السائق
    driver_phone = db.Column(db.String(20))  # رقم الهاتف المربوط بأبشر
    driver_id_image = db.Column(db.String(500))  # صورة الهوية
    driver_license_image = db.Column(db.String(500))  # صورة الرخصة
    accident_report_file = db.Column(db.String(500))  # تقرير الحادث (صورة أو PDF)
    reported_by_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)  # الموظف الذي أبلغ
    reported_via = db.Column(db.String(50), default='mobile_app')  # mobile_app, web, manual
    
    # حالة التقرير والمراجعة
    review_status = db.Column(db.String(50), default='pending', index=True)  # pending, approved, rejected, under_review
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)  # ملاحظات المراجع
    
    # معلومات الحادث
    accident_status = db.Column(db.String(50), default='قيد المعالجة')  # حالة الحادث: قيد المعالجة، مغلق، معلق، إلخ
    vehicle_condition = db.Column(db.String(100))  # حالة السيارة بعد الحادث
    severity = db.Column(db.String(50))  # بسيط، متوسط، شديد
    description = db.Column(db.Text)  # وصف الحادث
    location = db.Column(db.String(255))  # موقع الحادث (نص)
    latitude = db.Column(db.Float)  # خط العرض
    longitude = db.Column(db.Float)  # خط الطول
    
    # معلومات مالية وقانونية
    deduction_amount = db.Column(db.Float, default=0.0)  # مبلغ الخصم على السائق
    deduction_status = db.Column(db.Boolean, default=False)  # هل تم الخصم
    liability_percentage = db.Column(db.Integer, default=0)  # نسبة تحمل السائق للحادث (25%، 50%، 75%، 100%)
    police_report = db.Column(db.Boolean, default=False)  # هل تم عمل محضر شرطة
    police_report_number = db.Column(db.String(100))  # رقم محضر الشرطة
    insurance_claim = db.Column(db.Boolean, default=False)  # هل تم رفع مطالبة للتأمين
    insurance_claim_number = db.Column(db.String(100))  # رقم مطالبة التأمين
    
    # ملفات ومرفقات
    accident_file_link = db.Column(db.String(255))  # رابط ملف الحادث
    google_drive_folder = db.Column(db.String(500))  # مجلد Google Drive للحادث
    
    # ملاحظات وتواريخ
    notes = db.Column(db.Text)  # ملاحظات إضافية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', back_populates='accidents')
    reported_by = db.relationship('Employee', foreign_keys=[reported_by_employee_id], backref='reported_accidents')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    images = db.relationship('VehicleAccidentImage', back_populates='accident', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<VehicleAccident {self.id} for vehicle {self.vehicle_id} on {self.accident_date}>'


class VehicleAccidentImage(db.Model):
    """صور الحوادث"""
    __tablename__ = 'vehicle_accident_images'
    
    id = db.Column(db.Integer, primary_key=True)
    accident_id = db.Column(db.Integer, db.ForeignKey('vehicle_accident.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # معلومات الصورة
    image_path = db.Column(db.String(500), nullable=False)  # المسار المحلي
    image_url = db.Column(db.String(500))  # رابط Google Drive (اختياري)
    image_type = db.Column(db.String(50))  # نوع الصورة: damage, scene, police_report, other
    caption = db.Column(db.String(255))  # وصف الصورة
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    accident = db.relationship('VehicleAccident', back_populates='images')
    
    def __repr__(self):
        return f'<VehicleAccidentImage {self.id} for accident {self.accident_id}>'


# ============================================================================
# PROJECT & AUTHORIZATION MODELS
# ============================================================================

class Project(db.Model):
    """نموذج المشاريع"""
    __tablename__ = 'project'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    external_authorizations = db.relationship('ExternalAuthorization', back_populates='project', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'


class ExternalAuthorization(db.Model):
    """نموذج التفويضات الخارجية"""
    __tablename__ = 'external_authorization'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)  # اختياري في حالة الإدخال اليدوي
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    project_name = db.Column(db.String(200), nullable=True)  # اسم المشروع/القسم
    authorization_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    city = db.Column(db.String(100), nullable=True)  # المدينة
    file_path = db.Column(db.String(255))
    external_link = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    # حقول للإدخال اليدوي للسائق
    manual_driver_name = db.Column(db.String(200), nullable=True)  # اسم السائق المدخل يدوياً
    manual_driver_phone = db.Column(db.String(20), nullable=True)  # رقم هاتف السائق
    manual_driver_position = db.Column(db.String(100), nullable=True)  # منصب السائق
    manual_driver_department = db.Column(db.String(100), nullable=True)  # قسم السائق
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref='external_authorizations')
    employee = db.relationship('Employee', backref='external_authorizations')
    project = db.relationship('Project', back_populates='external_authorizations')
    
    @property
    def driver_name(self):
        """الحصول على اسم السائق (من الموظف أو المدخل يدوياً)"""
        if self.employee:
            return self.employee.name
        return self.manual_driver_name or 'غير محدد'
    
    @property
    def driver_phone(self):
        """الحصول على رقم هاتف السائق (من الموظف أو المدخل يدوياً)"""
        if self.employee and self.employee.mobile:
            return self.employee.mobile
        return self.manual_driver_phone or 'غير محدد'
    
    @property
    def driver_position(self):
        """الحصول على منصب السائق (من الموظف أو المدخل يدوياً)"""
        if self.employee and self.employee.job_title:
            return self.employee.job_title
        return self.manual_driver_position or 'غير محدد'
    
    def __repr__(self):
        driver_name = self.driver_name
        return f'<ExternalAuthorization {self.authorization_type} for {driver_name}>'


# ============================================================================
# VEHICLE EXTERNAL SAFETY & INSPECTION MODELS
# ============================================================================

class VehicleExternalSafetyCheck(db.Model):
    """فحوصات السلامة الخارجية للسيارات"""
    __tablename__ = 'vehicle_external_safety_check'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    
    # بيانات السائق
    driver_name = db.Column(db.String(100), nullable=False)  # اسم السائق
    driver_national_id = db.Column(db.String(20), nullable=False)  # رقم الهوية
    driver_department = db.Column(db.String(100), nullable=False)  # القسم
    driver_city = db.Column(db.String(100), nullable=False)  # المدينة
    
    # بيانات السيارة (محملة تلقائياً)
    vehicle_plate_number = db.Column(db.String(20), nullable=False)  # رقم اللوحة
    vehicle_make_model = db.Column(db.String(100), nullable=False)  # النوع والموديل
    current_delegate = db.Column(db.String(100), nullable=True)  # المفوض الحالي
    
    # تاريخ ووقت الفحص
    inspection_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # حالة الاعتماد
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # المعتمد من قبل
    approved_at = db.Column(db.DateTime, nullable=True)  # تاريخ الاعتماد
    rejection_reason = db.Column(db.Text, nullable=True)  # سبب الرفض
    
    # ملاحظات عامة
    notes = db.Column(db.Text)  # ملاحظات إضافية
    
    # ملف PDF المرفق
    pdf_file_path = db.Column(db.String(500), nullable=True)  # مسار ملف PDF المرفق
    
    # معلومات النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # حقول Google Drive (اختيارية - لا تؤثر على البيانات الحالية)
    drive_folder_id = db.Column(db.String(200), nullable=True)  # ID المجلد في Google Drive
    drive_pdf_link = db.Column(db.String(500), nullable=True)  # رابط ملف PDF
    drive_images_links = db.Column(db.Text, nullable=True)  # روابط الصور (JSON)
    drive_upload_status = db.Column(db.String(20), nullable=True)  # success, failed, pending
    drive_uploaded_at = db.Column(db.DateTime, nullable=True)  # تاريخ الرفع
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('external_safety_checks', cascade='all, delete-orphan'))
    approver = db.relationship('User', foreign_keys=[approved_by])
    safety_images = db.relationship('VehicleSafetyImage', back_populates='safety_check', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VehicleExternalSafetyCheck {self.vehicle_plate_number} by {self.driver_name}>'
        
    @property
    def is_approved(self):
        return self.approval_status == 'approved'
    
    @property
    def is_pending(self):
        return self.approval_status == 'pending'
    
    @property
    def is_rejected(self):
        return self.approval_status == 'rejected'


class VehicleSafetyImage(db.Model):
    """صور فحوصات السلامة"""
    __tablename__ = 'vehicle_safety_image'
    
    id = db.Column(db.Integer, primary_key=True)
    safety_check_id = db.Column(db.Integer, db.ForeignKey('vehicle_external_safety_check.id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)  # مسار الصورة
    image_description = db.Column(db.String(200), nullable=True)  # وصف الصورة (اختياري)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    safety_check = db.relationship('VehicleExternalSafetyCheck', back_populates='safety_images')
    
    def __repr__(self):
        return f'<VehicleSafetyImage {self.safety_check_id}>'


class SafetyInspection(db.Model):
    """نموذج فحص السلامة - نسخة مبسطة للاستخدام في routes/external_safety.py"""
    __tablename__ = 'safety_inspection'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.String(20), nullable=False)  # رقم الموظف
    driver_name = db.Column(db.String(100), nullable=False)
    
    # معلومات الفحص
    inspection_date = db.Column(db.DateTime, default=datetime.utcnow)
    issues_found = db.Column(db.Text)  # المشاكل المكتشفة
    recommendations = db.Column(db.Text)  # التوصيات
    
    # الصور المرفقة
    images = db.Column(db.Text)  # قائمة بمسارات الصور (JSON)
    
    # حالة الموافقة
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text)  # ملاحظات الإدارة
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref='safety_inspections')
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<SafetyInspection {self.vehicle_id} by {self.driver_name}>'


class VehicleInspectionRecord(db.Model):
    """سجلات الفحص الدوري للسيارات"""
    __tablename__ = 'vehicle_inspection_records'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False, index=True)
    token_id = db.Column(db.Integer, db.ForeignKey('inspection_upload_tokens.id', ondelete='SET NULL'))
    
    # بيانات الفحص
    inspection_date = db.Column(db.Date, nullable=False, index=True)
    inspection_type = db.Column(db.String(50), default='دوري')
    mileage = db.Column(db.Integer)
    notes = db.Column(db.Text)
    
    # معلومات الرفع
    uploaded_by_name = db.Column(db.String(200))
    uploaded_via = db.Column(db.String(50), default='mobile_app')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # حالة المراجعة
    review_status = db.Column(db.String(50), default='pending', index=True)
    # القيم الممكنة: pending / approved / rejected / needs_review
    
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    reviewed_at = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('inspection_records', lazy='dynamic', order_by='VehicleInspectionRecord.uploaded_at.desc()'))
    token = db.relationship('InspectionUploadToken', backref=db.backref('inspections', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    images = db.relationship('VehicleInspectionImage', backref='inspection', 
                            cascade='all, delete-orphan', lazy='dynamic',
                            order_by='VehicleInspectionImage.uploaded_at')
    
    def __repr__(self):
        return f'<VehicleInspectionRecord #{self.id} - Vehicle {self.vehicle_id} - {self.review_status}>'


class VehicleInspectionImage(db.Model):
    """صور الفحص الدوري"""
    __tablename__ = 'vehicle_inspection_images'
    
    id = db.Column(db.Integer, primary_key=True)
    inspection_record_id = db.Column(db.Integer, 
                                    db.ForeignKey('vehicle_inspection_records.id', ondelete='CASCADE'), 
                                    nullable=False, index=True)
    
    image_path = db.Column(db.String(500), nullable=False)
    image_url = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    
    # Google Drive (اختياري)
    drive_file_id = db.Column(db.String(200))
    drive_upload_status = db.Column(db.String(50), default='pending')
    
    def __repr__(self):
        return f'<VehicleInspectionImage #{self.id} - Inspection {self.inspection_record_id}>'
