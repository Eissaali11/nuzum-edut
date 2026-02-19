"""
Core Domain Models - Central system models for authentication, authorization, and auditing
Contains: User, UserRole, Permission, Module, SystemAudit, AuditLog, Notification
"""

import enum
from datetime import datetime
from flask_login import UserMixin
from core.extensions import db


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class UserRole(enum.Enum):
    """أدوار المستخدمين في النظام"""
    ADMIN = 'admin'
    MANAGER = 'manager'
    SUPERVISOR = 'supervisor'
    EMPLOYEE = 'employee'
    HR = 'hr'
    ACCOUNTANT = 'accountant'
    VIEWER = 'viewer'


class Module(enum.Enum):
    """الوحدات المتاحة في النظام"""
    DASHBOARD = 'dashboard'
    EMPLOYEES = 'employees'
    DEPARTMENTS = 'departments'
    VEHICLES = 'vehicles'
    VEHICLE_RENTAL = 'vehicle_rental'
    VEHICLE_MAINTENANCE = 'vehicle_maintenance'
    VEHICLE_INSPECTIONS = 'vehicle_inspections'
    VEHICLE_ACCIDENTS = 'vehicle_accidents'
    GPS_TRACKING = 'gps_tracking'
    GEOFENCING = 'geofencing'
    ATTENDANCE = 'attendance'
    SALARY = 'salary'
    SALARIES = 'salary'  # Alias for SALARY
    DOCUMENTS = 'documents'
    MOBILE_DEVICES = 'mobile_devices'
    SIM_CARDS = 'sim_cards'
    OPERATIONS = 'operations'
    REQUESTS = 'requests'
    INVOICES = 'invoices'
    CAR_WASH = 'car_wash'
    CAR_INSPECTION = 'car_inspection'
    PROPERTIES = 'properties'
    UTILITIES = 'utilities'
    REPORTS = 'reports'
    SETTINGS = 'settings'
    SYSTEM_AUDIT = 'system_audit'
    FEES = 'fees'  # Fee management
    USERS = 'users'  # User management


class Permission(object):
    """Bit-flag based permissions"""
    VIEW = 1        # 0001
    CREATE = 2      # 0010
    EDIT = 4        # 0100
    DELETE = 8      # 1000
    EXPORT = 16     # 10000
    APPROVE = 32    # 100000
    ALL = 63        # 111111
    
    # Aliases for compatibility
    ADMIN = 63      # Same as ALL
    MANAGE = 31     # VIEW + CREATE + EDIT + DELETE + EXPORT


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

user_accessible_departments = db.Table(
    'user_accessible_departments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('department.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)

vehicle_user_access = db.Table(
    'vehicle_user_access',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('vehicle_id', db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)


# ============================================================================
# CORE MODELS
# ============================================================================

class User(UserMixin, db.Model):
    """نموذج المستخدم - مركز نظام التحقق والصلاحيات"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # الدور والحالة
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # معرفات خارجية
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

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
        # المديرون لديهم وصول إلى جميع الأقسام
        if self.role == UserRole.ADMIN:
            from modules.employees.domain.models import Department
            return Department.query.all()
            
        # إذا كان لديه قسم مخصص، يعرض هذا القسم فقط
        if self.assigned_department_id:
            return [self.assigned_department]
            
        # إذا لم يكن لديه قسم مخصص، لا يعرض أي قسم
        return []
    
    def has_module_access(self, module):
        """التحقق مما إذا كان المستخدم لديه وصول إلى وحدة معينة"""
        # المديرون لديهم وصول إلى جميع الوحدات
        if self.role == UserRole.ADMIN:
            return True
            
        return any(p.module == module for p in self.permissions)
    
    def __repr__(self):
        return f'<User {self.email}>'


class UserPermission(db.Model):
    """صلاحيات المستخدم لكل وحدة"""
    __tablename__ = 'user_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    module = db.Column(db.Enum(Module), nullable=False)
    permissions = db.Column(db.Integer, default=Permission.VIEW)  # بتات الصلاحيات
    
    # العلاقات
    user = db.relationship('User', back_populates='permissions')
    
    def __repr__(self):
        return f'<UserPermission {self.user_id} - {self.module}>'


class SystemAudit(db.Model):
    """سجل عمليات النظام للإجراءات المهمة - Audit trail"""
    __tablename__ = 'system_audit'
    
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
        from core.extensions import db as app_db
        app_db.session.add(audit)
        app_db.session.commit()
        
        return audit


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
    
    # العلاقات
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Notification #{self.id} - {self.notification_type} - User {self.user_id}>'
