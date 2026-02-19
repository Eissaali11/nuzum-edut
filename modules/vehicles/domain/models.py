"""
نماذج نطاق المركبات — Vehicle, Workshop, Handover والجداول المرتبطة.
مستخرجة من models.py. لا يتجاوز 400 سطر.
"""
from datetime import datetime
from core.extensions import db

# جدول الربط بين المركبات والمستخدمين
vehicle_user_access = db.Table(
    "vehicle_user_access",
    db.Column("vehicle_id", db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)


class Vehicle(db.Model):
    """نموذج المركبة مع المعلومات الأساسية."""
    __tablename__ = "vehicle"
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False, unique=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="available")
    driver_name = db.Column(db.String(100), nullable=True)
    type_of_car = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    authorization_expiry_date = db.Column(db.Date)
    registration_expiry_date = db.Column(db.Date)
    inspection_expiry_date = db.Column(db.Date)
    license_image = db.Column(db.String(255), nullable=True)
    registration_form_image = db.Column(db.String(255), nullable=True)
    plate_image = db.Column(db.String(255), nullable=True)
    insurance_file = db.Column(db.String(255), nullable=True)
    project = db.Column(db.String(100), nullable=True)
    drive_folder_link = db.Column(db.String(500), nullable=True)
    owned_by = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rental_records = db.relationship("VehicleRental", back_populates="vehicle", cascade="all, delete-orphan")
    workshop_records = db.relationship("VehicleWorkshop", back_populates="vehicle", cascade="all, delete-orphan")
    project_assignments = db.relationship("VehicleProject", back_populates="vehicle", cascade="all, delete-orphan")
    handover_records = db.relationship(
        "VehicleHandover", back_populates="vehicle", cascade="all, delete-orphan"
    )
    periodic_inspections = db.relationship("VehiclePeriodicInspection", back_populates="vehicle", cascade="all, delete-orphan")
    safety_checks = db.relationship("VehicleSafetyCheck", back_populates="vehicle", cascade="all, delete-orphan")
    accidents = db.relationship("VehicleAccident", back_populates="vehicle", cascade="all, delete-orphan")
    authorized_users = db.relationship("User", secondary=vehicle_user_access, back_populates="accessible_vehicles")
    department = db.relationship("Department", backref="vehicles")

    @property
    def status_arabic(self):
        m = {
            "available": "متاحة",
            "rented": "مؤجرة",
            "in_project": "نشطة مع سائق",
            "in_workshop": "في الورشة صيانة",
            "accident": "في الورشة حادث",
            "out_of_service": "خارج الخدمة",
        }
        return m.get(self.status, self.status)

    def __repr__(self):
        return f"<Vehicle {self.plate_number} {self.make} {self.model}>"


class VehicleRental(db.Model):
    """معلومات إيجار المركبة."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    monthly_cost = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    lessor_name = db.Column(db.String(100))
    lessor_contact = db.Column(db.String(100))
    contract_number = db.Column(db.String(50))
    city = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vehicle = db.relationship("Vehicle", back_populates="rental_records")

    def __repr__(self):
        return f"<VehicleRental {self.vehicle_id} {self.start_date} to {self.end_date}>"


class VehicleWorkshop(db.Model):
    """دخول/خروج المركبة من الورشة."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    exit_date = db.Column(db.Date)
    reason = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    repair_status = db.Column(db.String(30), nullable=False, default="in_progress")
    cost = db.Column(db.Float, default=0.0)
    workshop_name = db.Column(db.String(100))
    technician_name = db.Column(db.String(100))
    delivery_link = db.Column(db.String(255))
    reception_link = db.Column(db.String(255))
    delivery_receipt = db.Column(db.String(255))
    pickup_receipt = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    drive_folder_id = db.Column(db.String(200), nullable=True)
    drive_pdf_link = db.Column(db.String(500), nullable=True)
    drive_images_links = db.Column(db.Text, nullable=True)
    drive_upload_status = db.Column(db.String(20), nullable=True)
    drive_uploaded_at = db.Column(db.DateTime, nullable=True)
    vehicle = db.relationship("Vehicle", back_populates="workshop_records")
    images = db.relationship("VehicleWorkshopImage", back_populates="workshop_record", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VehicleWorkshop {self.vehicle_id} {self.entry_date} {self.reason}>"


class VehicleWorkshopImage(db.Model):
    """صور توثيقية للمركبة في الورشة."""
    id = db.Column(db.Integer, primary_key=True)
    workshop_record_id = db.Column(db.Integer, db.ForeignKey("vehicle_workshop.id", ondelete="CASCADE"), nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    workshop_record = db.relationship("VehicleWorkshop", back_populates="images")

    def __repr__(self):
        return f"<VehicleWorkshopImage {self.workshop_record_id} {self.image_type}>"


class VehicleProject(db.Model):
    """تخصيص المركبة لمشروع."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    manager_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vehicle = db.relationship("Vehicle", back_populates="project_assignments")

    def __repr__(self):
        return f"<VehicleProject {self.vehicle_id} {self.project_name}>"


# VehicleHandover و VehicleHandoverImage في ملف منفصل لتجاوز حد 400 سطر
from modules.vehicles.domain.handover_models import VehicleHandover, VehicleHandoverImage  # noqa: E402
from modules.vehicles.domain.vehicle_maintenance_models import (  # noqa: E402
    VehiclePeriodicInspection,
    VehicleSafetyCheck,
    VehicleAccident,
    VehicleAccidentImage,
    ExternalAuthorization,
    VehicleExternalSafetyCheck,
)

__all__ = [
    "vehicle_user_access",
    "Vehicle",
    "VehicleRental",
    "VehicleWorkshop",
    "VehicleWorkshopImage",
    "VehicleProject",
    "VehicleHandover",
    "VehicleHandoverImage",
    "VehiclePeriodicInspection",
    "VehicleSafetyCheck",
    "VehicleAccident",
    "VehicleAccidentImage",
    "ExternalAuthorization",
    "VehicleExternalSafetyCheck",
]
