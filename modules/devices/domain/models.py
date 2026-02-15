"""
Mobile Devices & Communications Domain Models
Contains: MobileDevice, SimCard, ImportedPhoneNumber, DeviceAssignment, VoiceHubCall, VoiceHubAnalysis
"""

from datetime import datetime
from core.extensions import db


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
