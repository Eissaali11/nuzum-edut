"""
Operations & Requests Domain Models
Contains: RequestType, RequestStatus, MediaType, FileType, LiabilityType, LiabilityStatus, InstallmentStatus
         EmployeeRequest, InvoiceRequest, AdvancePaymentRequest, CarWashRequest, CarWashMedia
         CarInspectionRequest, CarInspectionMedia, EmployeeLiability, LiabilityInstallment
         RequestNotification, InspectionUploadToken, OperationRequest, OperationNotification
"""

import enum
from datetime import datetime, date
from src.core.extensions import db


# ============================================================================
# ENUMS
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


class InstallmentStatus(enum.Enum):
    """حالات الأقساط"""
    PENDING = 'pending'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'


# ============================================================================
# MODELS
# ============================================================================

class EmployeeRequest(db.Model):
    """الطلبات الرئيسية للموظفين - جدول مركزي لجميع أنواع الطلبات"""
    __tablename__ = 'employee_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False, index=True)
    request_type = db.Column(db.Enum(RequestType), nullable=False)
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
            from src.modules.vehicles.domain.models import VehicleHandover
            return VehicleHandover.query.get(self.related_record_id)
        elif self.operation_type == "workshop" or self.operation_type == "workshop_record":
            from src.modules.vehicles.domain.models import VehicleWorkshop
            return VehicleWorkshop.query.get(self.related_record_id)
        elif self.operation_type == "external_authorization":
            from src.modules.vehicles.domain.models import ExternalAuthorization
            return ExternalAuthorization.query.get(self.related_record_id)
        elif self.operation_type == "safety_inspection":
            from src.modules.vehicles.domain.models import SafetyInspection
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
    operation_request = db.relationship("OperationRequest", backref="unique_op_notifs")
    user = db.relationship("User", backref="unique_user_op_notifs")
    
    def __repr__(self):
        return f"<OperationNotification {self.title} to {self.user_id}>"
