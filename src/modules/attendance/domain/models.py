"""
Attendance & GPS Tracking Domain Models
Contains: Geofence, GeofenceEvent, GeofenceSession, GeofenceAttendance
"""

from datetime import datetime, date
from math import radians, sin, cos, sqrt, atan2
from src.core.extensions import db


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

employee_geofences = db.Table(
    'employee_geofences',
    db.Column('employee_id', db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), primary_key=True),
    db.Column('geofence_id', db.Integer, db.ForeignKey('geofences.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)


# ============================================================================
# MODELS
# ============================================================================

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
        from src.modules.employees.domain.models import Employee, EmployeeLocation
        
        employees_inside = []
        
        department_employees = Employee.query.join(db.Table(
            'employee_departments',
            db.Column('employee_id', db.Integer),
            db.Column('department_id', db.Integer)
        )).filter_by(department_id=self.department_id).all()
        
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
        from src.modules.employees.domain.models import Employee, EmployeeLocation
        
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
