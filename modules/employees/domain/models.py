"""
نماذج نطاق الموظفين — Employee, Department, Nationality والجداول المرتبطة.
مستخرج من models.py مع الحفاظ على العلاقات والقيود.
لا يتجاوز 400 سطر.
"""
from datetime import datetime, date
from core.extensions import db

# ─── جداول الربط (يُستورد منها في models.py لـ User, Geofence) ───
user_accessible_departments = db.Table(
    "user_accessible_departments",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("department.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)

employee_departments = db.Table(
    "employee_departments",
    db.Column("employee_id", db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("department.id", ondelete="CASCADE"), primary_key=True),
)

employee_geofences = db.Table(
    "employee_geofences",
    db.Column("employee_id", db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True),
    db.Column("geofence_id", db.Integer, db.ForeignKey("geofences.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
    extend_existing=True
)


class Department(db.Model):
    """Department model for organizing employees."""
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey("employee.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employees = db.relationship("Employee", secondary=employee_departments, back_populates="departments")
    manager = db.relationship("Employee", foreign_keys=[manager_id], backref="managed_departments")
    accessible_users = db.relationship(
        "User", secondary=user_accessible_departments, back_populates="departments"
    )
    mobile_devices = db.relationship("MobileDevice", backref="department", lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"


class Nationality(db.Model):
    """جدول الجنسيات."""
    __tablename__ = "nationalities"

    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(100), nullable=False, unique=True)
    name_en = db.Column(db.String(100), nullable=True, unique=True)
    country_code = db.Column(db.String(3), nullable=True)

    employees = db.relationship("Employee", back_populates="nationality_rel")

    def __repr__(self):
        return f"<Nationality {self.name_ar}>"


class Employee(db.Model):
    """Employee model — معلومات شخصية ومهنية."""
    __tablename__ = "employee"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    national_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    mobilePersonal = db.Column(db.String(20), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id", ondelete="SET NULL"), nullable=True)
    email = db.Column(db.String(100))
    job_title = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    location = db.Column(db.String(100))
    project = db.Column(db.String(100))
    join_date = db.Column(db.Date)
    birth_date = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(50))
    nationality_id = db.Column(
        db.Integer, db.ForeignKey("nationalities.id", name="fk_employee_nationality_id"), nullable=True
    )
    contract_type = db.Column(db.String(20), default="foreign")
    basic_salary = db.Column(db.Float, default=0.0)
    daily_wage = db.Column(db.Float, default=0.0)
    attendance_bonus = db.Column(db.Float, default=300.0)
    has_national_balance = db.Column(db.Boolean, default=False)
    profile_image = db.Column(db.String(255))
    national_id_image = db.Column(db.String(255))
    license_image = db.Column(db.String(255))
    job_offer_file = db.Column(db.String(255))
    job_offer_link = db.Column(db.String(500))
    passport_image_file = db.Column(db.String(255))
    passport_image_link = db.Column(db.String(500))
    national_address_file = db.Column(db.String(255))
    national_address_link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contract_status = db.Column(db.String(50), nullable=True)
    license_status = db.Column(db.String(50), nullable=True)
    employee_type = db.Column(db.String(20), default="regular")
    has_mobile_custody = db.Column(db.Boolean, default=False)
    mobile_type = db.Column(db.String(100), nullable=True)
    mobile_imei = db.Column(db.String(20), nullable=True)
    sponsorship_status = db.Column(db.String(20), default="inside", nullable=True)
    current_sponsor_name = db.Column(db.String(100), nullable=True)
    bank_iban = db.Column(db.String(50), nullable=True)
    bank_iban_image = db.Column(db.String(255), nullable=True)
    residence_details = db.Column(db.String(500), nullable=True)
    residence_location_url = db.Column(db.String(500), nullable=True)
    housing_images = db.Column(db.Text, nullable=True)
    housing_drive_links = db.Column(db.Text, nullable=True)
    pants_size = db.Column(db.String(20), nullable=True)
    shirt_size = db.Column(db.String(20), nullable=True)
    exclude_leave_from_deduction = db.Column(db.Boolean, default=True)
    exclude_sick_from_deduction = db.Column(db.Boolean, default=True)

    departments = db.relationship("Department", secondary=employee_departments, back_populates="employees")
    assigned_geofences = db.relationship(
        "Geofence", secondary=employee_geofences, back_populates="assigned_employees"
    )
    attendances = db.relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    salaries = db.relationship("Salary", back_populates="employee", cascade="all, delete-orphan")
    documents = db.relationship("Document", back_populates="employee", cascade="all, delete-orphan")
    nationality_rel = db.relationship("Nationality", back_populates="employees")
    handovers_as_driver = db.relationship(
        "VehicleHandover",
        foreign_keys="VehicleHandover.employee_id",
        back_populates="driver_employee",
        cascade="all, delete",
    )
    handovers_as_supervisor = db.relationship(
        "VehicleHandover",
        foreign_keys="VehicleHandover.supervisor_employee_id",
        back_populates="supervisor_employee",
        cascade="all, delete",
    )

    __table_args__ = (
        db.Index("idx_employee_status", "status"),
        db.Index("idx_employee_id", "employee_id"),
    )

    @property
    def department(self):
        return self.departments[0] if self.departments else None

    def to_dict(self):
        departments_list = [{"id": d.id, "name": d.name} for d in (self.departments or [])]
        department_id = self.departments[0].id if self.departments else None
        department = (
            {"id": self.departments[0].id, "name": self.departments[0].name}
            if self.departments
            else None
        )
        return {
            "id": self.id,
            "name": self.name,
            "employee_id": self.employee_id,
            "national_id": self.national_id,
            "department_id": department_id,
            "department": department,
            "departments": departments_list,
        }

    def __repr__(self):
        return f"<Employee {self.name} ({self.employee_id})>"


class EmployeeLocation(db.Model):
    """تتبع مواقع الموظفين."""
    __tablename__ = "employee_locations"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    accuracy_m = db.Column(db.Numeric(6, 2), nullable=True)
    speed_kmh = db.Column(db.Numeric(6, 2), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="SET NULL"), nullable=True)
    source = db.Column(db.String(50), default="android_app")
    recorded_at = db.Column(db.DateTime, nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    employee = db.relationship(
        "Employee", backref=db.backref("locations", lazy="dynamic", cascade="all, delete-orphan")
    )
    vehicle = db.relationship("Vehicle", backref=db.backref("location_history", lazy="dynamic"))

    __table_args__ = (db.Index("idx_employee_time", "employee_id", "recorded_at"),)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy": float(self.accuracy_m) if self.accuracy_m else None,
            "speed": float(self.speed_kmh) if self.speed_kmh else None,
            "vehicle_id": self.vehicle_id,
            "source": self.source,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "notes": self.notes,
        }

    def __repr__(self):
        return f"<EmployeeLocation {getattr(self.employee, 'name', 'Unknown')} at {self.recorded_at}>"


class Attendance(db.Model):
    """سجلات الحضور."""
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="present")
    notes = db.Column(db.Text)
    sick_leave_file = db.Column(db.String(255), nullable=True)
    check_in_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    check_in_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    check_in_accuracy = db.Column(db.Numeric(10, 2), nullable=True)
    check_in_face_image = db.Column(db.String(255), nullable=True)
    check_in_confidence = db.Column(db.Numeric(5, 4), nullable=True)
    check_in_liveness_score = db.Column(db.Numeric(5, 4), nullable=True)
    check_in_device_info = db.Column(db.JSON, nullable=True)
    check_in_verification_id = db.Column(db.String(255), nullable=True)
    check_out_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    check_out_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    check_out_accuracy = db.Column(db.Numeric(10, 2), nullable=True)
    check_out_face_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="attendances")

    __table_args__ = (
        db.Index("idx_attendance_date", "date"),
        db.Index("idx_attendance_employee_date", "employee_id", "date"),
    )

    def __repr__(self):
        return f"<Attendance {getattr(self.employee, 'name', '')} on {self.date}>"


class Salary(db.Model):
    """معلومات الرواتب."""
    __tablename__ = "salary"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    attendance_bonus = db.Column(db.Float, default=0.0)
    allowances = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False, nullable=False)
    overtime_hours = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    attendance_deduction = db.Column(db.Float, default=0.0)
    absent_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    leave_days = db.Column(db.Integer, default=0)
    sick_days = db.Column(db.Integer, default=0)
    attendance_calculated = db.Column(db.Boolean, default=False)
    attendance_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="salaries")

    def __repr__(self):
        return f"<Salary {getattr(self.employee, 'name', '')} for {self.month}/{self.year}>"


class Document(db.Model):
    """مستندات الموظف."""
    __tablename__ = "document"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    document_number = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="documents")

    __table_args__ = (
        db.Index("idx_document_expiry", "expiry_date"),
        db.Index("idx_document_employee", "employee_id"),
    )

    def __repr__(self):
        return f"<Document {self.document_type} for {getattr(self.employee, 'name', '')}>"
