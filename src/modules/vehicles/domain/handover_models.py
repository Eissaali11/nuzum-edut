"""
نماذج تسليم/استلام المركبات — VehicleHandover, VehicleHandoverImage.
مستخرجة من models.py لتفكيك نطاق المركبات. لا يتجاوز 400 سطر.
"""
from datetime import datetime
from src.core.extensions import db


class VehicleHandover(db.Model):
    """تسليم واستلام السيارة — snapshot للبيانات وقت العملية."""
    __tablename__ = "vehicle_handover"

    id = db.Column(db.Integer, primary_key=True)
    handover_type = db.Column(db.String(20), nullable=False)
    handover_date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    handover_time = db.Column(db.Time, nullable=True)
    project_name = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", name="fk_handover_driver_employee_id"), nullable=True)
    supervisor_employee_id = db.Column(db.Integer, db.ForeignKey("employee.id", name="fk_handover_supervisor_employee_id"), nullable=True)
    vehicle_car_type = db.Column(db.String(100), nullable=True)
    vehicle_plate_number = db.Column(db.String(20), nullable=True)
    vehicle_model_year = db.Column(db.String(10), nullable=True)
    person_name = db.Column(db.String(100), nullable=False)
    driver_company_id = db.Column(db.String(50), nullable=True)
    driver_phone_number = db.Column(db.String(20), nullable=True)
    driver_work_phone = db.Column(db.String(20), nullable=True)
    driver_residency_number = db.Column(db.String(50), nullable=True)
    driver_contract_status = db.Column(db.String(50), nullable=True)
    driver_license_status = db.Column(db.String(50), nullable=True)
    driver_signature_path = db.Column(db.String(255), nullable=True)
    supervisor_name = db.Column(db.String(100))
    supervisor_company_id = db.Column(db.String(50), nullable=True)
    supervisor_phone_number = db.Column(db.String(20), nullable=True)
    supervisor_residency_number = db.Column(db.String(50), nullable=True)
    supervisor_contract_status = db.Column(db.String(50), nullable=True)
    supervisor_license_status = db.Column(db.String(50), nullable=True)
    supervisor_signature_path = db.Column(db.String(255), nullable=True)
    reason_for_change = db.Column(db.Text, nullable=True)
    vehicle_status_summary = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text)
    reason_for_authorization = db.Column(db.Text, nullable=True)
    authorization_details = db.Column(db.String(255), nullable=True)
    fuel_level = db.Column(db.String(20), nullable=False)
    has_spare_tire = db.Column(db.Boolean, default=True)
    has_fire_extinguisher = db.Column(db.Boolean, default=True)
    has_first_aid_kit = db.Column(db.Boolean, default=True)
    has_warning_triangle = db.Column(db.Boolean, default=True)
    has_tools = db.Column(db.Boolean, default=True)
    has_oil_leaks = db.Column(db.Boolean, nullable=False, default=False)
    has_gear_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_clutch_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_engine_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_windows_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_tires_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_body_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_electricity_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_lights_issue = db.Column(db.Boolean, nullable=False, default=False)
    has_ac_issue = db.Column(db.Boolean, nullable=False, default=False)
    movement_officer_name = db.Column(db.String(100), nullable=True)
    movement_officer_signature_path = db.Column(db.String(255), nullable=True)
    damage_diagram_path = db.Column(db.String(255), nullable=True)
    form_link = db.Column(db.String(255), nullable=True)
    form_link_2 = db.Column(db.String(500), nullable=True)
    custom_company_name = db.Column(db.String(100), nullable=True)
    custom_logo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    drive_folder_id = db.Column(db.String(200), nullable=True)
    drive_pdf_link = db.Column(db.String(500), nullable=True)
    drive_images_links = db.Column(db.Text, nullable=True)
    drive_upload_status = db.Column(db.String(20), nullable=True)
    drive_uploaded_at = db.Column(db.DateTime, nullable=True)

    images = db.relationship("VehicleHandoverImage", back_populates="handover_record", cascade="all, delete-orphan")
    vehicle = db.relationship("Vehicle", back_populates="handover_records")
    driver_employee = db.relationship(
        "Employee", foreign_keys=[employee_id], back_populates="handovers_as_driver"
    )
    supervisor_employee = db.relationship(
        "Employee", foreign_keys=[supervisor_employee_id], back_populates="handovers_as_supervisor"
    )

    @property
    def get_images(self):
        if not hasattr(self, "_cached_images") or not self._cached_images:
            self._cached_images = VehicleHandoverImage.query.filter_by(handover_record_id=self.id).all()
        return self._cached_images

    def __repr__(self):
        return f"<VehicleHandover {self.id} for vehicle {self.vehicle_plate_number} on {self.handover_date}>"

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "handover_type": self.handover_type,
            "handover_date": self.handover_date.strftime("%Y-%m-%d") if self.handover_date else None,
            "handover_time": self.handover_time.strftime("%H:%M") if self.handover_time else None,
            "mileage": self.mileage,
            "project_name": self.project_name,
            "city": self.city,
            "vehicle_car_type": self.vehicle_car_type,
            "vehicle_plate_number": self.vehicle_plate_number,
            "vehicle_model_year": self.vehicle_model_year,
            "employee_id": self.employee_id,
            "person_name": self.person_name,
            "driver_company_id": self.driver_company_id,
            "driver_phone_number": self.driver_phone_number,
            "driver_residency_number": self.driver_residency_number,
            "driver_contract_status": self.driver_contract_status,
            "driver_license_status": self.driver_license_status,
            "driver_signature_path": self.driver_signature_path,
            "supervisor_employee_id": self.supervisor_employee_id,
            "supervisor_name": self.supervisor_name,
            "supervisor_company_id": self.supervisor_company_id,
            "supervisor_phone_number": self.supervisor_phone_number,
            "supervisor_residency_number": self.supervisor_residency_number,
            "supervisor_contract_status": self.supervisor_contract_status,
            "supervisor_license_status": self.supervisor_license_status,
            "supervisor_signature_path": self.supervisor_signature_path,
            "reason_for_change": self.reason_for_change,
            "vehicle_status_summary": self.vehicle_status_summary,
            "notes": self.notes,
            "reason_for_authorization": self.reason_for_authorization,
            "authorization_details": self.authorization_details,
            "fuel_level": self.fuel_level,
            "has_spare_tire": self.has_spare_tire,
            "has_fire_extinguisher": self.has_fire_extinguisher,
            "has_first_aid_kit": self.has_first_aid_kit,
            "has_warning_triangle": self.has_warning_triangle,
            "has_tools": self.has_tools,
            "has_oil_leaks": self.has_oil_leaks,
            "has_gear_issue": self.has_gear_issue,
            "has_clutch_issue": self.has_clutch_issue,
            "has_engine_issue": self.has_engine_issue,
            "has_windows_issue": self.has_windows_issue,
            "has_tires_issue": self.has_tires_issue,
            "has_body_issue": self.has_body_issue,
            "has_electricity_issue": self.has_electricity_issue,
            "has_lights_issue": self.has_lights_issue,
            "has_ac_issue": self.has_ac_issue,
            "movement_officer_name": self.movement_officer_name,
            "movement_officer_signature_path": self.movement_officer_signature_path,
            "damage_diagram_path": self.damage_diagram_path,
            "form_link": self.form_link,
            "custom_company_name": self.custom_company_name,
            "custom_logo_path": self.custom_logo_path,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class VehicleHandoverImage(db.Model):
    """صور/ملفات توثيقية لتسليم واستلام السيارة."""
    id = db.Column(db.Integer, primary_key=True)
    handover_record_id = db.Column(db.Integer, db.ForeignKey("vehicle_handover.id", ondelete="CASCADE"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    image_description = db.Column(db.String(100))
    file_path = db.Column(db.String(255))
    file_type = db.Column(db.String(20), default="image")
    file_description = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    handover_record = db.relationship("VehicleHandover", back_populates="images")

    def __repr__(self):
        return f"<VehicleHandoverImage {self.handover_record_id}>"

    def get_path(self):
        return self.file_path or self.image_path

    def get_description(self):
        return self.file_description or self.image_description

    def get_type(self):
        return self.file_type or "image"

    def is_pdf(self):
        path = self.get_path()
        return self.get_type() == "pdf" or (path and path.lower().endswith(".pdf"))

    def file_exists(self):
        import os
        from flask import current_app
        path = self.get_path()
        if not path:
            return False
        for p in (path, os.path.join(current_app.root_path, path)):
            if os.path.exists(p):
                return True
        return False
