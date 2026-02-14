from datetime import datetime, timedelta, date
from flask_login import UserMixin
from core.extensions import db  # تجنب الاستيراد من app لتفادي الاستيراد الدائري
import enum

# نماذج الموظفين والأقسام من النطاق (Domain)
from domain.employees.models import (
    user_accessible_departments,
    employee_departments,
    employee_geofences,
    Department,
    Nationality,
    Employee,
    EmployeeLocation,
    Attendance,
    Salary,
    Document,
)

# جدول الربط بين المركبات والمستخدمين (من نطاق المركبات)
from domain.vehicles.models import (
    vehicle_user_access,
    Vehicle,
    VehicleRental,
    VehicleWorkshop,
    VehicleWorkshopImage,
    VehicleProject,
    VehicleHandover,
    VehicleHandoverImage,
)

# Department, Nationality, Employee, EmployeeLocation, Attendance, Salary, Document → domain.employees.models

# تعريف أدوار المستخدمين
class UserRole(enum.Enum):
    ADMIN = 'admin'        # مدير النظام - كل الصلاحيات
    MANAGER = 'manager'    # مدير - جميع الصلاحيات عدا إدارة المستخدمين
    HR = 'hr'              # موارد بشرية - إدارة الموظفين والمستندات
    FINANCE = 'finance'    # مالية - إدارة الرواتب والتكاليف
    FLEET = 'fleet'        # أسطول - إدارة السيارات والمركبات
    USER = 'user'          # مستخدم عادي - صلاحيات محدودة للعرض

# تعريف الصلاحيات
class Permission:
    VIEW = 0x01            # عرض البيانات فقط
    CREATE = 0x02          # إنشاء سجلات جديدة
    EDIT = 0x04            # تعديل السجلات
    DELETE = 0x08          # حذف السجلات
    MANAGE = 0x16          # إدارة القسم الخاص
    ADMIN = 0xff           # كل الصلاحيات

# صلاحيات الأقسام
class Module(enum.Enum):
    DASHBOARD = 'لوحة التحكم'
    EMPLOYEES = 'الموظفين'
    ATTENDANCE = 'الحضور والانصراف'
    DEPARTMENTS = 'الأقسام'
    SALARIES = 'الرواتب'
    DOCUMENTS = 'الوثائق'
    VEHICLES = 'السيارات'
    USERS = 'المستخدمين'
    REPORTS = 'التقارير'
    FEES = 'الرسوم'
    ACCOUNTING = 'النظام المحاسبي'
    MOBILE_DEVICES = 'الأجهزة المحمولة'
    SIM_MANAGEMENT = 'إدارة الشرائح'
    DEVICE_ASSIGNMENT = 'تخصيص الأجهزة'
    INTEGRATED_SYSTEM = 'النظام المتكامل'
    ANALYTICS = 'التحليلات المالية'
    CHART_OF_ACCOUNTS = 'دليل الحسابات'
    COST_CENTERS = 'مراكز التكلفة'
    TRANSACTIONS = 'المعاملات المالية'
    FISCAL_YEARS = 'السنوات المالية'
    VENDORS = 'الموردين'
    CUSTOMERS = 'العملاء'
    EXTERNAL_SAFETY = 'الفحص الخارجي'
    LANDING_ADMIN = 'إدارة الصفحة الرئيسية'
    EMPLOYEE_REQUESTS = 'طلبات الموظفين'
    TRACKING = 'تتبع الموظفين'
    VOICEHUB = 'VoiceHub'
    RENTAL_PROPERTIES = 'العقارات المستأجرة'

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=True)  # اسم المستخدم
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=True)  # رقم الهاتف
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # جعلها اختيارية للسماح بتسجيل الدخول المحلي
    password_hash = db.Column(db.String(256), nullable=True)  # حقل لتخزين هاش كلمة المرور
    profile_picture = db.Column(db.String(255))
    role = db.Column(db.Enum(UserRole), default=UserRole.USER)  # دور المستخدم
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    auth_type = db.Column(db.String(20), default='local')  # local أو firebase
    
    # الربط مع الموظف إذا كان المستخدم موظفًا في النظام
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee = db.relationship('Employee', foreign_keys=[employee_id], uselist=False)
    
    # القسم المخصص للمستخدم (للتحكم في الوصول)
    assigned_department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    assigned_department = db.relationship('Department', foreign_keys=[assigned_department_id], uselist=False)
    departments = db.relationship('Department', 
                                  secondary=user_accessible_departments,
                                  back_populates='accessible_users')
    
    # العلاقة مع صلاحيات المستخدم
    permissions = db.relationship('UserPermission', back_populates='user', cascade='all, delete-orphan')

    # العلاقة مع المركبات التي يمكن للمستخدم الوصول إليها
    accessible_vehicles = db.relationship('Vehicle',
                                        secondary=vehicle_user_access,
                                        back_populates='authorized_users')

    
    def set_password(self, password):
        """تعيين كلمة المرور المشفرة"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)


   
    

    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        from werkzeug.security import check_password_hash
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    
    def has_permission(self, module, permission):
        """التحقق مما إذا كان المستخدم لديه صلاحية معينة"""
        # المديرون لديهم كل الصلاحيات
        if self.role == UserRole.ADMIN:
            return True
            
        # التحقق من صلاحيات القسم المحدد
        for user_permission in self.permissions:
            if user_permission.module == module:
                return user_permission.permissions & permission
                
        return False

    def can_access_department(self, department_id):
        if self.role == UserRole.ADMIN:
            return True
        
        # تحقق مما إذا كان معرف القسم موجوداً في قائمة الأقسام المخصصة للمستخدم
        return any(dept.id == department_id for dept in self.departments)

    def get_accessible_departments(self):
        if self.role == UserRole.ADMIN:
            from app.models import Department
            return Department.query.all()
        
        # أرجع قائمة الأقسام المرتبطة مباشرة
        return self.departments
        
    def has_module_access(self, module):
        """التحقق مما إذا كان المستخدم لديه وصول إلى وحدة معينة"""
        # المديرون لديهم وصول إلى جميع الوحدات
        if self.role == UserRole.ADMIN:
            return True
            
        return any(p.module == module for p in self.permissions)
    
    def can_access_department(self, department_id):
        """التحقق مما إذا كان المستخدم يمكنه الوصول إلى قسم معين"""
        # المديرون لديهم وصول إلى جميع الأقسام
        if self.role == UserRole.ADMIN:
            return True
            
        # إذا كان لديه قسم مخصص، يمكنه الوصول إليه فقط
        if self.assigned_department_id:
            return self.assigned_department_id == department_id
            
        # إذا لم يكن لديه قسم مخصص، لا يمكنه الوصول إلى أي قسم
        return False
    
    def get_accessible_departments(self):
        """جلب الأقسام التي يمكن للمستخدم الوصول إليها"""
        from app import db
        
        # المديرون لديهم وصول إلى جميع الأقسام
        if self.role == UserRole.ADMIN:
            return Department.query.all()
            
        # إذا كان لديه قسم مخصص، يعرض هذا القسم فقط
        if self.assigned_department_id:
            return [self.assigned_department]
            
        # إذا لم يكن لديه قسم مخصص، لا يعرض أي قسم
        return []
    
    def __repr__(self):
        return f'<User {self.email}>'

class UserPermission(db.Model):
    """صلاحيات المستخدم لكل وحدة"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    module = db.Column(db.Enum(Module), nullable=False)
    permissions = db.Column(db.Integer, default=Permission.VIEW)  # بتات الصلاحيات
    
    # العلاقات
    user = db.relationship('User', back_populates='permissions')
    
    def __repr__(self):
        return f'<UserPermission {self.user_id} - {self.module}>'

class RenewalFee(db.Model):
    """تكاليف رسوم تجديد أوراق الموظفين"""
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

class SystemAudit(db.Model):
    """سجل عمليات النظام للإجراءات المهمة - Audit trail"""
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)  # نوع الإجراء (إضافة، تعديل، حذف)
    entity_type = db.Column(db.String(50), nullable=False)  # نوع الكيان (موظف، قسم، راتب، الخ)
    entity_id = db.Column(db.Integer, nullable=False)  # معرف الكيان
    entity_name = db.Column(db.String(255))  # اسم الكيان للعرض
    previous_data = db.Column(db.Text)  # البيانات قبل التعديل (JSON)
    new_data = db.Column(db.Text)  # البيانات بعد التعديل (JSON)
    details = db.Column(db.Text)  # تفاصيل إضافية
    ip_address = db.Column(db.String(50))  # عنوان IP لمصدر العملية
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # وقت العملية
    
    # إضافة مرجع للمستخدم الذي قام بالإجراء
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<SystemAudit {self.action} on {self.entity_type} #{self.entity_id}>'
        
    @classmethod
    def create_audit_record(cls, user_id, action, entity_type, entity_id, details=None, entity_name=None):
        """
        إنشاء سجل نشاط جديد
        
        :param user_id: معرف المستخدم الذي قام بالإجراء
        :param action: نوع الإجراء (إضافة، تعديل، حذف)
        :param entity_type: نوع الكيان
        :param entity_id: معرف الكيان
        :param details: تفاصيل الإجراء (اختياري)
        :param entity_name: اسم الكيان (اختياري)
        :return: كائن SystemAudit
        """
        # إنشاء سجل جديد
        from flask import request
        
        ip_address = "127.0.0.1"
        if request:
            ip_address = request.remote_addr or "127.0.0.1"
        
        audit = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        
        # حفظ السجل في قاعدة البيانات
        from app import db
        db.session.add(audit)
        db.session.commit()
        
        return audit


class VehicleChecklist(db.Model):
    """تشيك لست فحص السيارة"""
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








class VehicleMaintenance(db.Model):
    """سجل صيانة المركبات"""
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

class AuditLog(db.Model):
    """نموذج سجل المراجعة لتتبع نشاط المستخدمين"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # create, update, delete, view
    entity_type = db.Column(db.String(50), nullable=False)  # Employee, Department, etc.
    entity_id = db.Column(db.Integer)  # ID of the affected entity
    details = db.Column(db.Text)  # Description of the action
    ip_address = db.Column(db.String(45))  # IP address of the user
    user_agent = db.Column(db.Text)  # User agent string
    previous_data = db.Column(db.Text)  # Previous data (for updates/deletes)
    new_data = db.Column(db.Text)  # New data (for creates/updates)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # العلاقات
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type} by {self.user_id}>'



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



class OperationRequest(db.Model):
    """نموذج لتتبع جميع العمليات التي تحتاج موافقة إدارية"""
    __tablename__ = "operation_requests"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # نوع العملية
    operation_type = db.Column(db.String(50), nullable=False)  # handover, workshop, external_authorization, safety_inspection
    
    # معرف السجل المرتبط بالعملية
    related_record_id = db.Column(db.Integer, nullable=False)
    
    # معرف السيارة
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    
    # معلومات العملية
    title = db.Column(db.String(200), nullable=False)  # عنوان العملية
    description = db.Column(db.Text)  # وصف العملية
    
    # معلومات الطالب
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # حالة العملية
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, under_review
    
    # معلومات المراجع
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text)  # ملاحظات المراجع
    
    # أولوية العملية
    priority = db.Column(db.String(20), default="normal")  # low, normal, high, urgent
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    vehicle = db.relationship("Vehicle", backref="operation_requests")
    requester = db.relationship("User", foreign_keys=[requested_by], backref="operation_requests")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_operations")
    
    def get_related_record(self):
        """جلب السجل المرتبط بالعملية حسب نوعها"""
        if self.operation_type == "handover":
            return VehicleHandover.query.get(self.related_record_id)
        elif self.operation_type == "workshop" or self.operation_type == "workshop_record":
            return VehicleWorkshop.query.get(self.related_record_id)
        elif self.operation_type == "external_authorization":
            return ExternalAuthorization.query.get(self.related_record_id)
        elif self.operation_type == "safety_inspection":
            return SafetyInspection.query.get(self.related_record_id)
        return None
    
    def get_operation_url(self):
        """الحصول على رابط تعديل تواريخ الوثائق للسيارة الخاصة بالعملية"""
        # توجيه جميع العمليات إلى صفحة تعديل تواريخ الوثائق مباشرة
        return f"/vehicles/documents/edit/{self.vehicle_id}"
    
    def __repr__(self):
        return f"<OperationRequest {self.operation_type} for Vehicle {self.vehicle_id}>"


class OperationNotification(db.Model):
    """نموذج للإشعارات المرتبطة بالعمليات"""
    __tablename__ = "operation_notifications"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # معرف العملية
    operation_request_id = db.Column(db.Integer, db.ForeignKey("operation_requests.id", ondelete="CASCADE"), nullable=False)
    
    # معرف المستلم
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    
    # نوع الإشعار
    notification_type = db.Column(db.String(50), nullable=False)  # new_operation, status_change, reminder
    
    # محتوى الإشعار
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # حالة الإشعار
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # العلاقات
    operation_request = db.relationship("OperationRequest", backref="notifications")
    user = db.relationship("User", backref="notifications")
    
    def __repr__(self):
        return f"<OperationNotification {self.title} to {self.user_id}>"


class MobileDevice(db.Model):
    """نموذج لإدارة الأجهزة المحمولة والهواتف"""
    __tablename__ = 'mobile_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=True)  # رقم الهاتف
    imei = db.Column(db.String(20), unique=True, nullable=False)  # رقم الـ IMEI فريد
    email = db.Column(db.String(100), nullable=True)  # الإيميل المرتبط بالجهاز
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='SET NULL'), nullable=True)  # معرف الموظف
    device_model = db.Column(db.String(50), nullable=True)  # نوع الجهاز
    device_brand = db.Column(db.String(50), nullable=True)  # ماركة الجهاز
    status = db.Column(db.String(20), default='متاح', nullable=False)  # حالة الجهاز: متاح، مرتبط، معطل
    assigned_date = db.Column(db.DateTime, nullable=True)  # تاريخ الربط
    notes = db.Column(db.Text, nullable=True)  # ملاحظات إضافية
    
    # الربط المباشر بالقسم (جديد)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)  # معرف القسم
    department_assignment_date = db.Column(db.DateTime, nullable=True)  # تاريخ الربط بالقسم
    assignment_type = db.Column(db.String(20), default='employee', nullable=False)  # نوع الربط: employee/department
    
    # حقول إضافية للربط
    is_assigned = db.Column(db.Boolean, default=False, nullable=False)  # هل الجهاز مرتبط
    assigned_to = db.Column(db.Integer, nullable=True)  # معرف المستخدم أو القسم المرتبط
    assignment_date = db.Column(db.DateTime, nullable=True)  # تاريخ الربط الفعلي
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    employee = db.relationship('Employee', backref='assigned_mobile_devices', lazy=True)
    
    def __repr__(self):
        return f'<MobileDevice {self.imei} - {self.phone_number}>'
    
    @property
    def is_available(self):
        """تحقق من توفر الجهاز للتخصيص"""
        if self.status == 'معطل':
            return False
        if self.employee_id is None:
            return True
        # تحقق من حالة الموظف
        if self.employee and self.employee.status != 'نشط':
            return True
        return False
    
    @property
    def status_class(self):
        """إرجاع كلاس CSS حسب الحالة"""
        status_classes = {
            'متاح': 'success',
            'مرتبط': 'primary', 
            'معطل': 'danger'
        }
        return status_classes.get(self.status, 'secondary')


class SimCard(db.Model):
    """نموذج لإدارة بطائق SIM والأرقام"""
    __tablename__ = 'sim_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)  # رقم الهاتف
    carrier = db.Column(db.String(50), nullable=False)  # شركة الاتصالات: STC, موبايلي, زين
    status = db.Column(db.String(20), default='متاحة', nullable=False)  # متاحة، نشطة، موقوفة، مرتبطة
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='SET NULL'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('mobile_devices.id', ondelete='SET NULL'), nullable=True)
    
    # معلومات إضافية
    description = db.Column(db.String(200), nullable=True)  # وصف الرقم
    activation_date = db.Column(db.Date, nullable=True)  # تاريخ التفعيل
    monthly_cost = db.Column(db.Float, default=0.0)  # التكلفة الشهرية
    plan_type = db.Column(db.String(100), nullable=True)  # نوع الباقة
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_date = db.Column(db.DateTime, nullable=True)  # تاريخ الربط
    
    # العلاقات
    employee = db.relationship('Employee', backref='sim_cards', lazy=True)
    device = db.relationship('MobileDevice', backref='sim_cards', lazy=True)
    
    def __repr__(self):
        return f'<SimCard {self.phone_number} - {self.carrier}>'
    
    @property
    def is_available(self):
        """تحقق من توفر الرقم للتخصيص"""
        if self.status in ['موقوفة', 'معطلة']:
            return False
        if self.employee_id is None and self.device_id is None:
            return True
        # تحقق من حالة الموظف إذا كان مربوط
        if self.employee and self.employee.status != 'نشط':
            return True
        return False
    
    @property
    def status_class(self):
        """إرجاع كلاس CSS حسب الحالة"""
        status_classes = {
            'متاحة': 'success',
            'نشطة': 'primary',
            'موقوفة': 'warning',
            'مرتبطة': 'info',
            'معطلة': 'danger'
        }
        return status_classes.get(self.status, 'secondary')

class ImportedPhoneNumber(db.Model):
    """نموذج لتخزين أرقام الهواتف المستوردة من Excel"""
    __tablename__ = 'imported_phone_numbers'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=True)  # رقم الهاتف المستورد
    description = db.Column(db.String(100), nullable=True)  # وصف أو اسم صاحب الرقم
    is_used = db.Column(db.Boolean, default=False, nullable=False)  # هل تم استخدام الرقم أم لا
    imported_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)  # المستخدم الذي استورد الرقم
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='SET NULL'), nullable=True)  # معرف الموظف المرتبط
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    user = db.relationship('User', backref='imported_phone_numbers', lazy=True)
    employee = db.relationship('Employee', backref='imported_phone_numbers', lazy=True)
    
    def __repr__(self):
        return f'<ImportedPhoneNumber {self.phone_number}>'
    
    def mark_as_used(self):
        """تحديد الرقم كمستخدم"""
        self.is_used = True
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def get_available_numbers():
        """جلب الأرقام المتاحة (غير المستخدمة)"""
        return ImportedPhoneNumber.query.filter_by(is_used=False).order_by(ImportedPhoneNumber.phone_number).all()


# نموذج ربط الأجهزة والأرقام بالموظفين
class DeviceAssignment(db.Model):
    """نموذج لتسجيل عمليات ربط الأجهزة والأرقام بالموظفين"""
    __tablename__ = 'device_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=True)  # جعلناه اختياري
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='CASCADE'), nullable=True)  # جديد للربط المباشر بالقسم
    device_id = db.Column(db.Integer, db.ForeignKey('mobile_devices.id', ondelete='SET NULL'), nullable=True)
    sim_card_id = db.Column(db.Integer, db.ForeignKey('sim_cards.id', ondelete='SET NULL'), nullable=True)
    
    # معلومات الربط
    assignment_type = db.Column(db.String(50), nullable=False)  # device_only, sim_only, device_and_sim
    assignment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    unassignment_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # معلومات إضافية
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    reason = db.Column(db.String(200), nullable=True)  # سبب الربط أو فك الربط
    
    # تواريخ النظام
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    employee = db.relationship('Employee', backref='device_assignments', lazy=True)
    department = db.relationship('Department', backref='dept_device_assignments', lazy=True)
    device = db.relationship('MobileDevice', backref='assignments', lazy=True, foreign_keys=[device_id])
    sim_card = db.relationship('SimCard', backref='assignments', lazy=True, foreign_keys=[sim_card_id])
    assigned_by_user = db.relationship('User', backref='assigned_devices', lazy=True)
    
    @property
    def assignment_target_type(self):
        """تحديد نوع الهدف (موظف أو قسم)"""
        if self.employee_id:
            return 'employee'
        elif self.department_id:
            return 'department'
        else:
            return None
    
    def __repr__(self):
        target = self.employee.name if self.employee else self.department.name if self.department else "غير محدد"
        return f'<DeviceAssignment {target} - {self.assignment_type}>'
    
    def unassign(self, reason=None):
        """فك ربط الجهاز/الرقم"""
        self.is_active = False
        self.unassignment_date = datetime.utcnow()
        self.reason = reason
        self.updated_at = datetime.utcnow()
        
        # تحديث حالة الجهاز والرقم
        if self.device:
            self.device.employee_id = None
            self.device.status = 'متاح'
        if self.sim_card:
            self.sim_card.employee_id = None
            self.sim_card.status = 'متاح'


# نماذج VoiceHub للذكاء الاصطناعي الصوتي
class VoiceHubCall(db.Model):
    """نموذج لتخزين مكالمات VoiceHub"""
    __tablename__ = 'voicehub_calls'
    
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.String(100), unique=True, nullable=False)  # معرف المكالمة من VoiceHub
    
    # معلومات المكالمة
    status = db.Column(db.String(50), nullable=True)  # started, queued, completed, in-progress, failed, etc.
    phone_number = db.Column(db.String(20), nullable=True)  # رقم الهاتف
    direction = db.Column(db.String(20), nullable=True)  # inbound, outbound
    duration = db.Column(db.Integer, nullable=True)  # مدة المكالمة بالثواني
    
    # معلومات الربط بالموظف/القسم
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='SET NULL'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # التسجيلات
    has_recordings = db.Column(db.Boolean, default=False)
    recording_urls = db.Column(db.Text, nullable=True)  # JSON list of URLs
    
    # التحليل
    has_analysis = db.Column(db.Boolean, default=False)
    analysis_id = db.Column(db.String(100), nullable=True)
    
    # بيانات إضافية
    event_data = db.Column(db.Text, nullable=True)  # JSON للبيانات الكاملة من Webhook
    notes = db.Column(db.Text, nullable=True)
    
    # تواريخ
    call_started_at = db.Column(db.DateTime, nullable=True)
    call_ended_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    employee = db.relationship('Employee', backref='voicehub_calls', lazy=True)
    department = db.relationship('Department', backref='voicehub_calls', lazy=True)
    assigned_by_user = db.relationship('User', backref='assigned_voicehub_calls', lazy=True)
    analysis = db.relationship('VoiceHubAnalysis', backref='call', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<VoiceHubCall {self.call_id} - {self.status}>'


class VoiceHubAnalysis(db.Model):
    """نموذج لتخزين تحليلات مكالمات VoiceHub"""
    __tablename__ = 'voicehub_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('voicehub_calls.id', ondelete='CASCADE'), nullable=False, unique=True)
    analysis_id = db.Column(db.String(100), unique=True, nullable=False)
    
    # الملخص
    summary = db.Column(db.Text, nullable=True)
    main_topics = db.Column(db.Text, nullable=True)  # JSON array
    
    # التحليل العاطفي
    sentiment_score = db.Column(db.Float, nullable=True)
    sentiment_label = db.Column(db.String(50), nullable=True)  # positive, negative, neutral
    positive_keywords = db.Column(db.Text, nullable=True)  # JSON array
    negative_keywords = db.Column(db.Text, nullable=True)  # JSON array
    
    # المقاييس
    empathy_score = db.Column(db.Float, nullable=True)
    resolution_status = db.Column(db.String(50), nullable=True)  # solved, unsolved
    user_interruptions_count = db.Column(db.Integer, nullable=True)
    
    # ملخص المستخدم
    user_speech_duration = db.Column(db.Integer, nullable=True)
    user_silence_duration = db.Column(db.Integer, nullable=True)
    user_wps = db.Column(db.Float, nullable=True)  # words per second
    
    # ملخص المساعد
    assistant_speech_duration = db.Column(db.Integer, nullable=True)
    assistant_silence_duration = db.Column(db.Integer, nullable=True)
    assistant_wps = db.Column(db.Float, nullable=True)
    
    # البيانات الكاملة
    full_analysis = db.Column(db.Text, nullable=True)  # JSON للتحليل الكامل
    transcript = db.Column(db.Text, nullable=True)  # النص الكامل للمحادثة
    
    # مؤشرات الولاء
    loyalty_indicators = db.Column(db.Text, nullable=True)  # JSON array
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<VoiceHubAnalysis {self.analysis_id}>'


# جدول الربط بين العقارات والموظفين القاطنين
property_employees = db.Table('property_employees',
    db.Column('property_id', db.Integer, db.ForeignKey('rental_properties.id', ondelete='CASCADE'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), primary_key=True),
    db.Column('move_in_date', db.Date, nullable=True),  # تاريخ السكن
    db.Column('move_out_date', db.Date, nullable=True),  # تاريخ الخروج
    db.Column('notes', db.Text, nullable=True)  # ملاحظات
)

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


class Geofence(db.Model):
    """دائرة جغرافية مرتبطة بقسم معين"""
    __tablename__ = 'geofences'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), default='project')
    description = db.Column(db.Text)
    center_latitude = db.Column(db.Numeric(9, 6), nullable=False)
    center_longitude = db.Column(db.Numeric(9, 6), nullable=False)
    radius_meters = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(20), default='#667eea')
    is_active = db.Column(db.Boolean, default=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='CASCADE'), nullable=False)
    notify_on_entry = db.Column(db.Boolean, default=False)
    notify_on_exit = db.Column(db.Boolean, default=False)
    attendance_start_time = db.Column(db.String(5), default='08:00')  # وقت البداية HH:MM
    attendance_required_minutes = db.Column(db.Integer, default=30)  # الحد الأدنى للبقاء
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department = db.relationship('Department', backref='geofences')
    events = db.relationship('GeofenceEvent', backref='geofence', cascade='all, delete-orphan')
    assigned_employees = db.relationship('Employee', secondary=employee_geofences, back_populates='assigned_geofences')
    
    def get_attendance_status(self, session):
        """حساب حالة حضور موظف بناءً على الجلسة"""
        if not session or not session.entry_time:
            return 'absent'
        
        # التحقق من المدة
        if session.duration_minutes and session.duration_minutes < self.attendance_required_minutes:
            return 'insufficient_time'
        
        # حساب إذا كان في الوقت أو متأخر
        if self.attendance_start_time:
            start_hour, start_minute = map(int, self.attendance_start_time.split(':'))
            entry_time = session.entry_time
            scheduled_time = entry_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            
            if entry_time <= scheduled_time:
                return 'on_time'
            else:
                delay_minutes = int((entry_time - scheduled_time).total_seconds() / 60)
                return f'late_{delay_minutes}'
        
        return 'present'
    
    def get_department_employees_inside(self):
        """جلب موظفي القسم المرتبط الموجودين داخل الدائرة فقط"""
        employees_inside = []
        
        department_employees = Employee.query.join(employee_departments).filter(
            employee_departments.c.department_id == self.department_id
        ).all()
        
        for employee in department_employees:
            latest_location = EmployeeLocation.query.filter_by(
                employee_id=employee.id
            ).order_by(EmployeeLocation.recorded_at.desc()).first()
            
            if latest_location:
                distance = self.calculate_distance(
                    latest_location.latitude,
                    latest_location.longitude
                )
                
                if distance <= self.radius_meters:
                    employees_inside.append({
                        'employee': employee,
                        'location': latest_location,
                        'distance': distance
                    })
        
        return employees_inside
    
    def get_all_employees_inside(self):
        """جلب جميع الموظفين داخل الدائرة (للعرض فقط)"""
        all_employees_inside = []
        
        all_employees = Employee.query.all()
        
        for employee in all_employees:
            latest_location = EmployeeLocation.query.filter_by(
                employee_id=employee.id
            ).order_by(EmployeeLocation.recorded_at.desc()).first()
            
            if latest_location:
                distance = self.calculate_distance(
                    latest_location.latitude,
                    latest_location.longitude
                )
                
                if distance <= self.radius_meters:
                    is_from_linked_department = any(
                        dept.id == self.department_id 
                        for dept in employee.departments
                    )
                    
                    all_employees_inside.append({
                        'employee': employee,
                        'location': latest_location,
                        'distance': distance,
                        'is_eligible': is_from_linked_department
                    })
        
        return all_employees_inside
    
    def calculate_distance(self, lat, lon):
        """حساب المسافة من مركز الدائرة باستخدام Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000
        
        lat1 = radians(float(self.center_latitude))
        lon1 = radians(float(self.center_longitude))
        lat2 = radians(lat)
        lon2 = radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def __repr__(self):
        return f'<Geofence {self.name}>'


class GeofenceEvent(db.Model):
    """حدث دخول/خروج/تسجيل جماعي"""
    __tablename__ = 'geofence_events'
    
    id = db.Column(db.Integer, primary_key=True)
    geofence_id = db.Column(db.Integer, db.ForeignKey('geofences.id', ondelete='CASCADE'))
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'))
    event_type = db.Column(db.String(30), nullable=False)  # 'enter', 'exit', 'check_in'
    location_latitude = db.Column(db.Numeric(9, 6))
    location_longitude = db.Column(db.Numeric(9, 6))
    distance_from_center = db.Column(db.Integer)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processed_at = db.Column(db.DateTime)
    source = db.Column(db.String(20), default='auto')
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'))
    notes = db.Column(db.Text)
    
    employee = db.relationship('Employee', backref='geofence_events')
    
    def __repr__(self):
        return f'<GeofenceEvent {self.event_type} - {self.employee_id}>'


class GeofenceSession(db.Model):
    """جلسة كاملة لموظف في دائرة جغرافية (من الدخول إلى الخروج)"""
    __tablename__ = 'geofence_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    geofence_id = db.Column(db.Integer, db.ForeignKey('geofences.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # أحداث الدخول/الخروج
    entry_event_id = db.Column(db.Integer, db.ForeignKey('geofence_events.id'))
    exit_event_id = db.Column(db.Integer, db.ForeignKey('geofence_events.id'))
    
    # الأوقات
    entry_time = db.Column(db.DateTime, nullable=False, index=True)
    exit_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)  # المدة بالدقائق
    
    # الحالة
    is_active = db.Column(db.Boolean, default=True)  # True = لا يزال داخل الدائرة
    
    # تواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    geofence = db.relationship('Geofence', backref=db.backref('sessions', lazy='dynamic'))
    employee = db.relationship('Employee', backref=db.backref('geofence_sessions', lazy='dynamic'))
    entry_event = db.relationship('GeofenceEvent', foreign_keys=[entry_event_id])
    exit_event = db.relationship('GeofenceEvent', foreign_keys=[exit_event_id])
    
    def calculate_duration(self):
        """حساب المدة بالدقائق"""
        if self.entry_time and self.exit_time:
            delta = self.exit_time - self.entry_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        return self.duration_minutes
    
    def __repr__(self):
        return f'<GeofenceSession {self.id} - Employee {self.employee_id} - Active: {self.is_active}>'


class GeofenceAttendance(db.Model):
    """سجل الحضور الصباحي والمسائي في الدائرة الجغرافية"""
    __tablename__ = 'geofence_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    geofence_id = db.Column(db.Integer, db.ForeignKey('geofences.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    attendance_date = db.Column(db.Date, nullable=False, index=True)  # التاريخ
    
    morning_entry = db.Column(db.DateTime, nullable=True)  # وقت دخول الصباح
    morning_entry_sa = db.Column(db.DateTime, nullable=True)  # وقت دخول الصباح بتوقيت السعودية
    
    evening_entry = db.Column(db.DateTime, nullable=True)  # وقت دخول المساء
    evening_entry_sa = db.Column(db.DateTime, nullable=True)  # وقت دخول المساء بتوقيت السعودية
    
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    geofence = db.relationship('Geofence', backref=db.backref('attendance_records', lazy='dynamic'))
    employee = db.relationship('Employee', backref=db.backref('geofence_attendance', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('idx_geofence_attendance_date', 'geofence_id', 'attendance_date'),
        db.Index('idx_employee_attendance_date', 'employee_id', 'attendance_date'),
    )
    
    def __repr__(self):
        return f'<GeofenceAttendance {self.employee_id} on {self.attendance_date}>'


# ============================================================================
# نظام طلبات الموظفين (Employee Requests System)
# ============================================================================

class RequestType(enum.Enum):
    """أنواع الطلبات"""
    INVOICE = 'invoice'
    CAR_WASH = 'car_wash'
    CAR_INSPECTION = 'car_inspection'
    ADVANCE_PAYMENT = 'advance_payment'


class RequestStatus(enum.Enum):
    """حالات الطلبات"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    CLOSED = 'closed'


class MediaType(enum.Enum):
    """أنواع الصور لطلبات غسيل السيارات"""
    PLATE = 'plate'
    FRONT = 'front'
    BACK = 'back'
    RIGHT = 'right'
    LEFT = 'left'


class FileType(enum.Enum):
    """أنواع الملفات للفحص"""
    IMAGE = 'image'
    VIDEO = 'video'


class LiabilityType(enum.Enum):
    """أنواع الالتزامات المالية"""
    DAMAGE = 'damage'
    DEBT = 'debt'
    ADVANCE_REPAYMENT = 'advance_repayment'
    OTHER = 'other'


class LiabilityStatus(enum.Enum):
    """حالات الالتزامات المالية"""
    ACTIVE = 'active'
    PAID = 'paid'
    CANCELLED = 'cancelled'


class EmployeeRequest(db.Model):
    """الطلبات الرئيسية للموظفين - جدول مركزي لجميع أنواع الطلبات"""
    __tablename__ = 'employee_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    request_type = db.Column(db.Enum(RequestType), nullable=False, index=True)
    status = db.Column(db.Enum(RequestStatus), nullable=False, default=RequestStatus.PENDING, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Numeric(10, 2))
    
    google_drive_folder_id = db.Column(db.String(255))
    google_drive_folder_url = db.Column(db.Text)
    
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    reviewed_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_employee_status', 'employee_id', 'status'),
        db.Index('idx_type_status', 'request_type', 'status'),
    )
    
    employee = db.relationship('Employee', backref=db.backref('requests', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    invoice_data = db.relationship('InvoiceRequest', back_populates='request', uselist=False, cascade='all, delete-orphan')
    advance_data = db.relationship('AdvancePaymentRequest', back_populates='request', uselist=False, cascade='all, delete-orphan')
    car_wash_data = db.relationship('CarWashRequest', back_populates='request', uselist=False, cascade='all, delete-orphan')
    inspection_data = db.relationship('CarInspectionRequest', back_populates='request', uselist=False, cascade='all, delete-orphan')
    
    notifications = db.relationship('RequestNotification', back_populates='request', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EmployeeRequest #{self.id} - {self.request_type.value} - {self.status.value}>'


class InvoiceRequest(db.Model):
    """طلبات الفواتير - بيانات خاصة بالفواتير"""
    __tablename__ = 'invoice_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    vendor_name = db.Column(db.String(200), nullable=False)
    invoice_date = db.Column(db.Date)
    
    local_image_path = db.Column(db.String(512), nullable=True)
    drive_file_id = db.Column(db.String(255), unique=True)
    drive_view_url = db.Column(db.Text)
    drive_download_url = db.Column(db.Text)
    file_size = db.Column(db.BigInteger)
    
    payment_method = db.Column(db.String(20))
    payment_date = db.Column(db.Date)
    payment_reference = db.Column(db.String(100))
    
    request = db.relationship('EmployeeRequest', back_populates='invoice_data')
    
    def __repr__(self):
        return f'<InvoiceRequest #{self.id} - {self.vendor_name}>'


class AdvancePaymentRequest(db.Model):
    """طلبات السلف - بيانات خاصة بالسلف"""
    __tablename__ = 'advance_payment_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    employee_name = db.Column(db.String(100), nullable=False)
    employee_number = db.Column(db.String(20), nullable=False)
    national_id = db.Column(db.String(20), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    snapshot_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    requested_amount = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.Text)
    installments = db.Column(db.Integer)
    installment_amount = db.Column(db.Numeric(10, 2))
    
    disbursement_method = db.Column(db.String(20))
    disbursement_date = db.Column(db.Date)
    disbursement_reference = db.Column(db.String(100))
    
    repayment_status = db.Column(db.String(20), default='pending')
    repaid_amount = db.Column(db.Numeric(10, 2), default=0)
    remaining_amount = db.Column(db.Numeric(10, 2))
    
    request = db.relationship('EmployeeRequest', back_populates='advance_data')
    
    def __repr__(self):
        return f'<AdvancePaymentRequest #{self.id} - {self.employee_name} - {self.requested_amount}>'


class CarWashRequest(db.Model):
    """طلبات غسيل السيارات"""
    __tablename__ = 'car_wash_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='CASCADE'), unique=True, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='SET NULL'))
    
    service_type = db.Column(db.String(50), nullable=False)
    scheduled_date = db.Column(db.Date)
    
    request = db.relationship('EmployeeRequest', back_populates='car_wash_data')
    vehicle = db.relationship('Vehicle')
    media_files = db.relationship('CarWashMedia', back_populates='wash_request', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CarWashRequest #{self.id} - {self.service_type}>'


class CarWashMedia(db.Model):
    """ملفات الصور لطلبات غسيل السيارات - 5 صور لكل طلب"""
    __tablename__ = 'car_wash_media'
    
    id = db.Column(db.Integer, primary_key=True)
    wash_request_id = db.Column(db.Integer, db.ForeignKey('car_wash_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    media_type = db.Column(db.Enum(MediaType), nullable=False)
    drive_file_id = db.Column(db.String(255), unique=True)
    drive_view_url = db.Column(db.Text)
    drive_download_url = db.Column(db.Text)
    local_path = db.Column(db.String(512))
    file_size = db.Column(db.BigInteger)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('wash_request_id', 'media_type', name='uq_wash_media_type'),
    )
    
    wash_request = db.relationship('CarWashRequest', back_populates='media_files')
    
    def __repr__(self):
        return f'<CarWashMedia #{self.id} - {self.media_type.value}>'


class CarInspectionRequest(db.Model):
    """طلبات فحص وتوثيق السيارات"""
    __tablename__ = 'car_inspection_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='CASCADE'), unique=True, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='SET NULL'))
    
    inspection_type = db.Column(db.String(50), nullable=False)
    inspection_date = db.Column(db.Date, default=date.today)
    
    request = db.relationship('EmployeeRequest', back_populates='inspection_data')
    vehicle = db.relationship('Vehicle')
    media_files = db.relationship('CarInspectionMedia', back_populates='inspection_request', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CarInspectionRequest #{self.id} - {self.inspection_type}>'


class CarInspectionMedia(db.Model):
    """ملفات الصور والفيديوهات لطلبات الفحص - متعددة"""
    __tablename__ = 'car_inspection_media'
    
    id = db.Column(db.Integer, primary_key=True)
    inspection_request_id = db.Column(db.Integer, db.ForeignKey('car_inspection_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    file_type = db.Column(db.Enum(FileType), nullable=False)
    original_filename = db.Column(db.String(255))
    
    drive_file_id = db.Column(db.String(255), unique=True)
    drive_view_url = db.Column(db.Text)
    drive_download_url = db.Column(db.Text)
    local_path = db.Column(db.String(512))
    
    file_size = db.Column(db.BigInteger)
    video_duration = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    upload_status = db.Column(db.String(20), default='uploading')
    upload_progress = db.Column(db.Integer, default=0)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    inspection_request = db.relationship('CarInspectionRequest', back_populates='media_files')
    
    def __repr__(self):
        return f'<CarInspectionMedia #{self.id} - {self.file_type.value}>'


class EmployeeLiability(db.Model):
    """الالتزامات المالية للموظفين - تلفيات، ديون، سداد سلف"""
    __tablename__ = 'employee_liabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    
    liability_type = db.Column(db.Enum(LiabilityType), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    remaining_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    description = db.Column(db.Text, nullable=False)
    reference_type = db.Column(db.String(50))
    employee_request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='SET NULL'))
    
    status = db.Column(db.Enum(LiabilityStatus), nullable=False, default=LiabilityStatus.ACTIVE, index=True)
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    due_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    __table_args__ = (
        db.CheckConstraint('remaining_amount >= 0', name='check_remaining_positive'),
        db.CheckConstraint('paid_amount >= 0', name='check_paid_positive'),
        db.Index('idx_liability_employee_status', 'employee_id', 'status'),
    )
    
    employee = db.relationship('Employee', backref=db.backref('liabilities', lazy='dynamic'))
    request = db.relationship('EmployeeRequest', backref='liabilities')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<EmployeeLiability #{self.id} - {self.liability_type.value} - {self.remaining_amount}>'


class InstallmentStatus(enum.Enum):
    """حالات الأقساط"""
    PENDING = 'pending'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'


class LiabilityInstallment(db.Model):
    """أقساط الالتزامات المالية - جدولة الدفعات"""
    __tablename__ = 'liability_installments'
    
    id = db.Column(db.Integer, primary_key=True)
    liability_id = db.Column(db.Integer, db.ForeignKey('employee_liabilities.id', ondelete='CASCADE'), nullable=False, index=True)
    
    installment_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.Enum(InstallmentStatus), nullable=False, default=InstallmentStatus.PENDING, index=True)
    
    paid_date = db.Column(db.DateTime)
    payment_reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint('amount > 0', name='check_installment_amount_positive'),
        db.CheckConstraint('paid_amount >= 0', name='check_installment_paid_positive'),
        db.UniqueConstraint('liability_id', 'installment_number', name='unique_liability_installment'),
        db.Index('idx_liability_status', 'liability_id', 'status'),
        db.Index('idx_due_date_status', 'due_date', 'status'),
    )
    
    liability = db.relationship('EmployeeLiability', backref=db.backref('installments', lazy='dynamic', order_by='LiabilityInstallment.installment_number'))
    
    def __repr__(self):
        return f'<LiabilityInstallment #{self.id} - Installment {self.installment_number} - {self.amount}>'


class RequestNotification(db.Model):
    """إشعارات الطلبات للموظفين"""
    __tablename__ = 'request_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('employee_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    
    notification_type = db.Column(db.String(50), nullable=False, index=True)
    title_ar = db.Column(db.String(200), nullable=False)
    message_ar = db.Column(db.Text, nullable=False)
    
    is_read = db.Column(db.Boolean, default=False, index=True)
    is_sent_to_app = db.Column(db.Boolean, default=False)
    
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_request_type', 'request_id', 'notification_type'),
        db.Index('idx_employee_read', 'employee_id', 'is_read'),
    )
    
    request = db.relationship('EmployeeRequest', back_populates='notifications')
    employee = db.relationship('Employee', backref=db.backref('request_notifications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<RequestNotification #{self.id} - {self.notification_type}>'


class InspectionUploadToken(db.Model):
    """رموز الرفع الفريدة لكل سيارة - نظام رفع صور الفحص الدوري"""
    __tablename__ = 'inspection_upload_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False, index=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # معلومات الإنشاء
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # الحالة
    is_active = db.Column(db.Boolean, default=True, index=True)
    used_at = db.Column(db.DateTime)
    
    # العلاقات
    vehicle = db.relationship('Vehicle', backref=db.backref('inspection_tokens', lazy='dynamic'))
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<InspectionUploadToken #{self.id} - Vehicle {self.vehicle_id}>'


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


class Notification(db.Model):
    """نموذج الإشعارات الشامل"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # نوع الإشعار
    notification_type = db.Column(db.String(50), nullable=False)  # absence, document_expiry, operations, etc
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # معرف الكيان المرتبط (موظف، وثيقة، مركبة، إلخ)
    related_entity_type = db.Column(db.String(50))  # employee, vehicle, document, etc
    related_entity_id = db.Column(db.Integer)
    
    # معلومات إضافية
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, critical
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)
    
    # رابط للتوجيه عند النقر
    action_url = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<Notification #{self.id} - {self.notification_type} - User {self.user_id}>'

