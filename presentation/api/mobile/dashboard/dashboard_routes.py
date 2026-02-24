"""
مسارات لوحة التحكم والبداية (Splash / Root / Dashboard) — مستخرجة من routes/mobile.py.
تُسجَّل على mobile_bp عبر register_dashboard_routes(mobile_bp).
نفس القوالب ومتغيرات السياق.
"""
import json
from datetime import datetime

from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from core.extensions import db
from models import (
    Employee,
    Department,
    Document,
    Vehicle,
    Attendance,
    Module,
    UserRole,
    EmployeeLocation,
    Geofence,
)

from application.mobile.tracking_services import location_status_from_age_minutes


def register_dashboard_routes(mobile_bp):
    """تسجيل مسارات Splash والجذر ولوحة التحكم."""

    @mobile_bp.route("/splash")
    def splash():
        """صفحة البداية الترحيبية للنسخة المحمولة"""
        return render_template("mobile/splash.html")

    @mobile_bp.route("/")
    def root():
        """إعادة توجيه إلى صفحة البداية الترحيبية"""
        return redirect(url_for("mobile.splash"))

    @mobile_bp.route("/dashboard")
    @login_required
    def index():
        """الصفحة الرئيسية للنسخة المحمولة"""
        if not (
            current_user.role == UserRole.ADMIN
            or current_user.has_module_access(Module.DASHBOARD)
        ):
            if current_user.has_module_access(Module.EMPLOYEES):
                return redirect(url_for("mobile.employees"))
            if current_user.has_module_access(Module.DEPARTMENTS):
                return redirect(url_for("mobile.departments"))
            if current_user.has_module_access(Module.ATTENDANCE):
                return redirect(url_for("mobile.attendance"))
            if current_user.has_module_access(Module.SALARIES):
                return redirect(url_for("mobile.salaries"))
            if current_user.has_module_access(Module.DOCUMENTS):
                return redirect(url_for("mobile.documents"))
            if current_user.has_module_access(Module.VEHICLES):
                return redirect(url_for("mobile.vehicles"))
            if current_user.has_module_access(Module.REPORTS):
                return redirect(url_for("mobile.reports"))
            if current_user.has_module_access(Module.FEES):
                return redirect(url_for("mobile.fees"))
            if current_user.has_module_access(Module.USERS):
                return redirect(url_for("mobile.users"))

        stats = {
            "employees_count": Employee.query.count(),
            "departments_count": Department.query.count(),
            "documents_count": Document.query.count(),
            "vehicles_count": Vehicle.query.count(),
        }
        notifications_count = 3
        today = datetime.now().date()
        expiring_documents = (
            Document.query.filter(Document.expiry_date >= today)
            .order_by(Document.expiry_date)
            .limit(5)
            .all()
        )
        for doc in expiring_documents:
            doc.days_remaining = (doc.expiry_date - today).days

        today_str = today.strftime("%Y-%m-%d")
        absences = Attendance.query.filter_by(date=today_str, status="غائب").all()

        all_employees = Employee.query.options(
            db.joinedload(Employee.departments)
        ).all()
        departments = Department.query.all()

        employee_locations = {}
        for emp in all_employees:
            location = (
                EmployeeLocation.query.filter_by(employee_id=emp.id)
                .order_by(EmployeeLocation.recorded_at.desc())
                .first()
            )
            if location and location.latitude is not None and location.longitude is not None:
                try:
                    age_minutes = (
                        datetime.utcnow() - location.recorded_at
                    ).total_seconds() / 60
                    status = location_status_from_age_minutes(age_minutes)
                    employee_locations[str(emp.id)] = {
                        "latitude": float(location.latitude),
                        "longitude": float(location.longitude),
                        "name": emp.name,
                        "employee_id": emp.employee_id,
                        "status": status,
                        "age_minutes": int(age_minutes),
                    }
                except Exception:
                    employee_locations[str(emp.id)] = {"status": "error"}
            else:
                employee_locations[str(emp.id)] = {"status": "not_registered"}

        geofences = Geofence.query.all()
        geofences_data = [
            {
                "id": gf.id,
                "name": gf.name,
                "latitude": float(gf.center_latitude),
                "longitude": float(gf.center_longitude),
                "radius": gf.radius_meters,
                "color": gf.color,
                "department_id": gf.department_id,
            }
            for gf in geofences
        ]

        employees_json = json.dumps([
            {
                "id": emp.id,
                "name": emp.name,
                "employee_id": emp.employee_id,
                "photo_url": emp.profile_image,
                "department_name": (
                    emp.department.name if emp.department else "غير محدد"
                ),
                "department_id": emp.departments[0].id if emp.departments else None,
                "status": emp.status,
            }
            for emp in all_employees
        ])
        employee_locations_json = json.dumps(employee_locations)
        geofences_json = json.dumps(geofences_data)

        return render_template(
            "mobile/dashboard_new.html",
            stats=stats,
            expiring_documents=expiring_documents,
            absences=absences,
            notifications_count=notifications_count,
            now=datetime.now(),
            employees=all_employees,
            employees_json=employees_json,
            employee_locations_json=employee_locations_json,
            geofences_json=geofences_json,
            departments=departments,
        )
