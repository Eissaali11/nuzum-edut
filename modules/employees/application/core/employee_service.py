"""Employee application services (Phase 1)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, Any, List, Dict

from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError

from core.extensions import db
from modules.employees.application.file_service import save_employee_image
from modules.employees.domain.models import Employee, Department, employee_departments
from utils.audit_logger import log_activity
from utils.date_converter import parse_date


@dataclass
class ServiceResult:
    success: bool
    message: str
    category: str
    data: Dict[str, Any] = field(default_factory=dict)


def get_employee_by_id(employee_id: int) -> Optional[Employee]:
    """Fetch a single employee by primary key."""
    return Employee.query.get(employee_id)


def list_employees_page_data(
    department_filter: str = "",
    status_filter: str = "",
    multi_department_filter: str = "",
    no_department_filter: str = "",
    duplicate_names_filter: str = "",
    location_filter: str = "",
    assigned_department_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> dict:
    """Build list data and stats for the employees index page."""
    query = Employee.query.options(
        db.joinedload(Employee.departments),
        db.joinedload(Employee.nationality_rel),
    )

    if assigned_department_id:
        query = query.join(employee_departments).join(Department).filter(
            Department.id == assigned_department_id
        )
    elif department_filter:
        query = query.join(employee_departments).join(Department).filter(
            Department.id == department_filter
        )

    if status_filter:
        query = query.filter(Employee.status == status_filter)

    if location_filter:
        query = query.filter(Employee.location == location_filter)

    if duplicate_names_filter == "yes":
        duplicate_subq = (
            db.session.query(Employee.name, func.count(Employee.name).label("name_count"))
            .group_by(Employee.name)
            .having(func.count(Employee.name) > 1)
            .subquery()
        )
        query = query.join(duplicate_subq, Employee.name == duplicate_subq.c.name)

    if no_department_filter == "yes":
        query = query.outerjoin(employee_departments).filter(
            employee_departments.c.employee_id.is_(None)
        )
    elif multi_department_filter == "yes":
        subq = (
            db.session.query(
                employee_departments.c.employee_id,
                func.count(employee_departments.c.department_id).label("dept_count"),
            )
            .group_by(employee_departments.c.employee_id)
            .having(func.count(employee_departments.c.department_id) > 1)
            .subquery()
        )
        query = query.join(subq, Employee.id == subq.c.employee_id)
    elif multi_department_filter == "no":
        subq = (
            db.session.query(
                employee_departments.c.employee_id,
                func.count(employee_departments.c.department_id).label("dept_count"),
            )
            .group_by(employee_departments.c.employee_id)
            .having(func.count(employee_departments.c.department_id) <= 1)
            .subquery()
        )
        query = query.outerjoin(subq, Employee.id == subq.c.employee_id).filter(
            or_(subq.c.employee_id.is_(None), subq.c.dept_count <= 1)
        )

    if limit and limit > 0:
        query = query.limit(limit)

    employees: List[Any] = query.all()

    if assigned_department_id:
        departments = Department.query.filter(Department.id == assigned_department_id).all()
    else:
        departments = Department.query.all()

    if limit and limit > 0:
        multi_dept_count = 0
        no_dept_count = 0
        duplicate_names_count = 0
        duplicate_names_set: Set[str] = set()
        single_dept_count = 0
    else:
        multi_dept_count = (
            db.session.query(Employee.id)
            .join(employee_departments)
            .group_by(Employee.id)
            .having(func.count(employee_departments.c.department_id) > 1)
            .count()
        )
        no_dept_count = (
            db.session.query(Employee.id)
            .outerjoin(employee_departments)
            .filter(employee_departments.c.employee_id.is_(None))
            .count()
        )
        duplicate_names_rows = (
            db.session.query(Employee.name, func.count(Employee.id).label("name_count"))
            .group_by(Employee.name)
            .having(func.count(Employee.id) > 1)
            .all()
        )
        duplicate_names_set = {name for name, _ in duplicate_names_rows}
        duplicate_names_count = sum(name_count for _, name_count in duplicate_names_rows)

        total = db.session.query(Employee).count()
        single_dept_count = total - multi_dept_count - no_dept_count

    return {
        "employees": employees,
        "departments": departments,
        "current_department": department_filter,
        "current_status": status_filter,
        "current_multi_department": multi_department_filter,
        "current_no_department": no_department_filter,
        "current_duplicate_names": duplicate_names_filter,
        "current_location": location_filter,
        "multi_dept_count": multi_dept_count,
        "single_dept_count": single_dept_count,
        "no_dept_count": no_dept_count,
        "duplicate_names_count": duplicate_names_count,
        "duplicate_names_set": duplicate_names_set,
    }


def _unlink_sim_and_devices_for_inactive(employee: Employee) -> Dict[str, Any]:
    from flask import current_app
    from models import SimCard, DeviceAssignment

    sim_cards = SimCard.query.filter_by(employee_id=employee.id).all()
    device_assignments = DeviceAssignment.query.filter_by(
        employee_id=employee.id,
        is_active=True,
    ).all()

    current_app.logger.info(
        "Employee %s (%s) became inactive - checking for SIM cards and devices",
        employee.id,
        employee.name,
    )
    current_app.logger.info(
        "Found %s SIM cards directly linked to employee %s",
        len(sim_cards),
        employee.id,
    )
    current_app.logger.info(
        "Found %s active device assignments for employee %s",
        len(device_assignments),
        employee.id,
    )

    sim_count = len(sim_cards)
    assignment_count = len(device_assignments)
    warning = False

    try:
        for sim_card in sim_cards:
            current_app.logger.info(
                "Unlinking SIM card %s (ID: %s) from employee %s",
                sim_card.phone_number,
                sim_card.id,
                employee.id,
            )
            sim_card.employee_id = None
            sim_card.assigned_date = None
            sim_card.status = "متاح"

            try:
                log_activity(
                    action="unassign_auto",
                    entity_type="SIM",
                    entity_id=sim_card.id,
                    details=(
                        "Auto-unassigned SIM %s due to employee %s becoming inactive"
                        % (sim_card.phone_number, employee.name)
                    ),
                )
            except Exception as audit_error:
                current_app.logger.error("Failed to log SIM audit: %s", str(audit_error))

        for assignment in device_assignments:
            current_app.logger.info(
                "Deactivating device assignment %s for employee %s",
                assignment.id,
                employee.id,
            )
            assignment.is_active = False
            assignment.end_date = datetime.now()
            assignment.end_reason = "Auto-unassigned - employee became inactive"

            if assignment.device:
                assignment.device.employee_id = None
                assignment.device.status = "متاح"

            if assignment.sim_card:
                assignment.sim_card.employee_id = None
                assignment.sim_card.assigned_date = None
                assignment.sim_card.status = "متاح"

            try:
                device_info = (
                    f"Device {assignment.device.brand} {assignment.device.model}"
                    if assignment.device
                    else "No device"
                )
                sim_info = (
                    f"SIM {assignment.sim_card.phone_number}"
                    if assignment.sim_card
                    else "No SIM"
                )
                log_activity(
                    action="unassign_auto",
                    entity_type="DeviceAssignment",
                    entity_id=assignment.id,
                    details=(
                        "Auto-unassigned device assignment (%s - %s) due to employee %s becoming inactive"
                        % (device_info, sim_info, employee.name)
                    ),
                )
            except Exception as audit_error:
                current_app.logger.error(
                    "Failed to log device assignment audit: %s", str(audit_error)
                )
    except Exception as error:
        current_app.logger.error(
            "Error unassigning SIM cards for inactive employee: %s", str(error)
        )
        warning = True

    return {
        "sim_count": sim_count,
        "assignment_count": assignment_count,
        "warning": warning,
    }


def create_employee(form_data, files) -> ServiceResult:
    try:
        name = form_data["name"]
        employee_id = form_data["employee_id"]
        national_id = form_data["national_id"]
        mobile = form_data["mobile"]
        status = form_data["status"]
        job_title = form_data["job_title"]
        location = form_data["location"]
        project = form_data["project"]
        email = form_data.get("email", "")
        department_id = form_data.get("department_id", None)
        join_date = parse_date(form_data.get("join_date", ""))
        birth_date = parse_date(form_data.get("birth_date", ""))
        mobile_personal = form_data.get("mobilePersonal")
        nationality_id = form_data.get("nationality_id")
        contract_status = form_data.get("contract_status")
        license_status = form_data.get("license_status")

        employee_type = form_data.get("employee_type", "regular")
        has_mobile_custody = "has_mobile_custody" in form_data
        mobile_type = form_data.get("mobile_type", "") if has_mobile_custody else None
        mobile_imei = form_data.get("mobile_imei", "") if has_mobile_custody else None

        sponsorship_status = form_data.get("sponsorship_status", "inside")
        current_sponsor_name = form_data.get("current_sponsor_name", "")

        residence_details = form_data.get("residence_details", "").strip() or None
        residence_location_url = (
            form_data.get("residence_location_url", "").strip() or None
        )
        housing_drive_links = form_data.get("housing_drive_links", "").strip() or None
        pants_size = form_data.get("pants_size", "").strip() or None
        shirt_size = form_data.get("shirt_size", "").strip() or None

        basic_salary_str = form_data.get("basic_salary", "").strip()
        basic_salary = float(basic_salary_str) if basic_salary_str else 0.0
        attendance_bonus_str = form_data.get("attendance_bonus", "").strip()
        attendance_bonus = float(attendance_bonus_str) if attendance_bonus_str else 0.0

        selected_dept_ids = {int(dept_id) for dept_id in form_data.getlist("department_ids")}

        if department_id == "":
            department_id = None

        employee = Employee(
            name=name,
            employee_id=employee_id,
            national_id=national_id,
            mobile=mobile,
            status=status,
            job_title=job_title,
            location=location,
            project=project,
            email=email,
            department_id=department_id,
            join_date=join_date,
            birth_date=birth_date,
            mobilePersonal=mobile_personal,
            nationality_id=int(nationality_id) if nationality_id else None,
            contract_status=contract_status,
            license_status=license_status,
            employee_type=employee_type,
            has_mobile_custody=has_mobile_custody,
            mobile_type=mobile_type,
            mobile_imei=mobile_imei,
            sponsorship_status=sponsorship_status,
            current_sponsor_name=current_sponsor_name,
            residence_details=residence_details,
            residence_location_url=residence_location_url,
            housing_drive_links=housing_drive_links,
            pants_size=pants_size,
            shirt_size=shirt_size,
            basic_salary=basic_salary,
            attendance_bonus=attendance_bonus,
        )

        if selected_dept_ids:
            departments_to_assign = Department.query.filter(
                Department.id.in_(selected_dept_ids)
            ).all()
            employee.departments.extend(departments_to_assign)

        db.session.add(employee)
        db.session.commit()

        housing_images_files = files.getlist("housing_images")
        if housing_images_files and any(upload.filename for upload in housing_images_files):
            saved_images = []
            for img_file in housing_images_files:
                if img_file and img_file.filename:
                    try:
                        saved_path = save_employee_image(img_file, employee.id, "housing")
                        if saved_path:
                            saved_images.append(saved_path)
                    except Exception:
                        pass
            if saved_images:
                employee.housing_images = ",".join(saved_images)

        job_offer_file = files.get("job_offer_file")
        if job_offer_file and job_offer_file.filename:
            employee.job_offer_file = save_employee_image(
                job_offer_file, employee.id, "job_offer"
            )

        passport_image_file = files.get("passport_image_file")
        if passport_image_file and passport_image_file.filename:
            employee.passport_image_file = save_employee_image(
                passport_image_file, employee.id, "passport"
            )

        national_address_file = files.get("national_address_file")
        if national_address_file and national_address_file.filename:
            employee.national_address_file = save_employee_image(
                national_address_file, employee.id, "national_address"
            )

        job_offer_link = form_data.get("job_offer_link", "").strip() or None
        passport_image_link = form_data.get("passport_image_link", "").strip() or None
        national_address_link = form_data.get("national_address_link", "").strip() or None
        if job_offer_link or passport_image_link or national_address_link:
            employee.job_offer_link = job_offer_link
            employee.passport_image_link = passport_image_link
            employee.national_address_link = national_address_link

        db.session.commit()

        log_activity("create", "Employee", employee.id, f"Created employee: {name}")

        return ServiceResult(
            success=True,
            message="employee.created",
            category="success",
            data={"employee_id": employee.id},
        )
    except IntegrityError as exc:
        db.session.rollback()
        error_message = str(exc).lower()
        if "employee_id" in error_message:
            return ServiceResult(
                success=False,
                message="employee.duplicate_employee_id",
                category="danger",
            )
        if "national_id" in error_message:
            return ServiceResult(
                success=False,
                message="employee.duplicate_national_id",
                category="danger",
            )
        return ServiceResult(
            success=False,
            message="employee.duplicate",
            category="danger",
        )
    except Exception as exc:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.create_failed",
            category="danger",
            data={"detail": str(exc)},
        )


def update_employee(employee_id: int, form_data, files) -> ServiceResult:
    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger",
        )

    try:
        new_name = form_data.get("name", "").strip()
        new_employee_id = form_data.get("employee_id", "").strip()
        new_national_id = form_data.get("national_id", "").strip()

        existing_employee = Employee.query.filter(
            Employee.employee_id == new_employee_id, Employee.id != employee_id
        ).first()
        if existing_employee:
            return ServiceResult(
                success=False,
                message="employee.duplicate_employee_id",
                category="danger",
                data={"employee_id": new_employee_id},
            )

        existing_national = Employee.query.filter(
            Employee.national_id == new_national_id, Employee.id != employee_id
        ).first()
        if existing_national:
            return ServiceResult(
                success=False,
                message="employee.duplicate_national_id",
                category="danger",
                data={"national_id": new_national_id},
            )

        employee.name = new_name
        employee.employee_id = new_employee_id
        employee.national_id = new_national_id

        mobile_value = form_data.get("mobile", "")
        if mobile_value == "custom":
            mobile_value = form_data.get("mobile_custom", "")
        employee.mobile = mobile_value

        old_status = employee.status
        new_status = form_data.get("status", "active")
        employee.status = new_status

        employee.job_title = form_data.get("job_title", "")
        employee.location = form_data.get("location", "")
        employee.project = form_data.get("project", "")
        employee.email = form_data.get("email", "")
        employee.mobilePersonal = form_data.get("mobilePersonal", "")
        employee.contract_status = form_data.get("contract_status", "")
        employee.license_status = form_data.get("license_status", "")
        nationality_id = form_data.get("nationality_id")
        employee.nationality_id = int(nationality_id) if nationality_id else None

        employee.employee_type = form_data.get("employee_type", "regular")
        employee.has_mobile_custody = "has_mobile_custody" in form_data
        employee.mobile_type = (
            form_data.get("mobile_type", "") if employee.has_mobile_custody else None
        )
        employee.mobile_imei = (
            form_data.get("mobile_imei", "") if employee.has_mobile_custody else None
        )

        employee.sponsorship_status = form_data.get("sponsorship_status", "inside")
        employee.current_sponsor_name = (
            form_data.get("current_sponsor_name", "")
            if employee.sponsorship_status == "inside"
            else None
        )

        employee.bank_iban = form_data.get("bank_iban", "").strip() or None
        employee.residence_details = (
            form_data.get("residence_details", "").strip() or None
        )
        employee.residence_location_url = (
            form_data.get("residence_location_url", "").strip() or None
        )

        housing_images_files = files.getlist("housing_images")
        if housing_images_files and any(upload.filename for upload in housing_images_files):
            saved_images = []
            if employee.housing_images:
                saved_images = [
                    img.strip()
                    for img in employee.housing_images.split(",")
                    if img.strip()
                ]
            for img_file in housing_images_files:
                if img_file and img_file.filename:
                    try:
                        saved_path = save_employee_image(img_file, employee_id, "housing")
                        if saved_path:
                            saved_images.append(saved_path)
                    except Exception:
                        pass
            employee.housing_images = ",".join(saved_images) if saved_images else None

        employee.housing_drive_links = (
            form_data.get("housing_drive_links", "").strip() or None
        )
        employee.pants_size = form_data.get("pants_size", "").strip() or None
        employee.shirt_size = form_data.get("shirt_size", "").strip() or None

        basic_salary_str = form_data.get("basic_salary", "").strip()
        employee.basic_salary = float(basic_salary_str) if basic_salary_str else 0.0
        attendance_bonus_str = form_data.get("attendance_bonus", "").strip()
        employee.attendance_bonus = (
            float(attendance_bonus_str) if attendance_bonus_str else 0.0
        )

        bank_iban_image_file = files.get("bank_iban_image")
        if bank_iban_image_file and bank_iban_image_file.filename:
            employee.bank_iban_image = save_employee_image(
                bank_iban_image_file, employee_id, "iban"
            )

        job_offer_file = files.get("job_offer_file")
        if job_offer_file and job_offer_file.filename:
            employee.job_offer_file = save_employee_image(
                job_offer_file, employee_id, "job_offer"
            )

        passport_image_file = files.get("passport_image_file")
        if passport_image_file and passport_image_file.filename:
            employee.passport_image_file = save_employee_image(
                passport_image_file, employee_id, "passport"
            )

        national_address_file = files.get("national_address_file")
        if national_address_file and national_address_file.filename:
            employee.national_address_file = save_employee_image(
                national_address_file, employee_id, "national_address"
            )

        employee.job_offer_link = form_data.get("job_offer_link", "").strip() or None
        employee.passport_image_link = (
            form_data.get("passport_image_link", "").strip() or None
        )
        employee.national_address_link = (
            form_data.get("national_address_link", "").strip() or None
        )

        join_date_str = form_data.get("join_date")
        employee.join_date = parse_date(join_date_str) if join_date_str else None
        birth_date_str = form_data.get("birth_date")
        employee.birth_date = parse_date(birth_date_str) if birth_date_str else None

        selected_dept_ids = {int(dept_id) for dept_id in form_data.getlist("department_ids")}
        current_dept_ids = {dept.id for dept in employee.departments}

        depts_to_add_ids = selected_dept_ids - current_dept_ids
        if depts_to_add_ids:
            depts_to_add = Department.query.filter(Department.id.in_(depts_to_add_ids)).all()
            for dept in depts_to_add:
                employee.departments.append(dept)

        depts_to_remove_ids = current_dept_ids - selected_dept_ids
        if depts_to_remove_ids:
            depts_to_remove = Department.query.filter(
                Department.id.in_(depts_to_remove_ids)
            ).all()
            for dept in depts_to_remove:
                employee.departments.remove(dept)

        from models import User

        user_linked = User.query.filter_by(employee_id=employee.id).first()
        if user_linked:
            final_departments = Department.query.filter(
                Department.id.in_(selected_dept_ids)
            ).all()
            user_linked.departments = final_departments

        unlink_info = None
        if new_status == "inactive" and old_status != "inactive":
            unlink_info = _unlink_sim_and_devices_for_inactive(employee)

        db.session.commit()

        log_activity("update", "Employee", employee.id, f"Updated employee: {employee.name}")

        return ServiceResult(
            success=True,
            message="employee.updated",
            category="success",
            data={"employee_id": employee.id, "unlink": unlink_info},
        )
    except Exception as exc:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.update_failed",
            category="danger",
            data={"detail": str(exc), "employee_id": employee.id},
        )


def delete_employee(employee_id: int) -> ServiceResult:
    from sqlalchemy import inspect
    from models import EmployeeRequest, Geofence

    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger",
        )

    pending_requests = EmployeeRequest.query.filter_by(
        employee_id=employee_id,
        status="PENDING",
    ).count()
    if pending_requests > 0:
        return ServiceResult(
            success=False,
            message="employee.pending_requests",
            category="danger",
            data={"pending_count": pending_requests},
        )

    try:
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        tables_to_clean = [
            ("geofence_attendance", "employee_id", "delete"),
            ("salary", "employee_id", "delete"),
            ("geofence_sessions", "employee_id", "delete"),
            ("document", "employee_id", "delete"),
            ("attendance", "employee_id", "delete"),
            ("government_fee", "employee_id", "delete"),
            ("fee", "employee_id", "delete"),
            ("employee_departments", "employee_id", "delete"),
            ("sim_cards", "employee_id", "unlink"),
            ("imported_phone_numbers", "employee_id", "unlink"),
            ("device_assignments", "employee_id", "delete"),
            ("transactions", "employee_id", "delete"),
            ("voicehub_calls", "employee_id", "delete"),
            ("property_employees", "employee_id", "delete"),
            ("geofence_events", "employee_id", "delete"),
            ("employee_geofences", "employee_id", "delete"),
            ("employee_locations", "employee_id", "delete"),
            ("employee_requests", "employee_id", "delete"),
            ("employee_liabilities", "employee_id", "delete"),
            ("request_notifications", "employee_id", "delete"),
            ("external_authorization", "employee_id", "delete"),
            ("mobile_devices", "employee_id", "unlink"),
            ("safety_inspection", "employee_id", "delete"),
        ]

        for table, column, action in tables_to_clean:
            if table not in existing_tables:
                continue
            if action == "delete":
                db.session.execute(
                    text(f"DELETE FROM {table} WHERE {column} = :id"),
                    {"id": employee_id},
                )
            elif action == "unlink":
                db.session.execute(
                    text(f"UPDATE {table} SET {column} = NULL WHERE {column} = :id"),
                    {"id": employee_id},
                )

        if "vehicle_handover" in existing_tables:
            db.session.execute(
                text(
                    "UPDATE vehicle_handover SET employee_id = NULL WHERE employee_id = :id"
                ),
                {"id": employee_id},
            )
            db.session.execute(
                text(
                    "UPDATE vehicle_handover SET supervisor_employee_id = NULL "
                    "WHERE supervisor_employee_id = :id"
                ),
                {"id": employee_id},
            )

        try:
            for geofence in Geofence.query.all():
                if employee in geofence.assigned_employees:
                    geofence.assigned_employees.remove(employee)
        except Exception:
            pass

        db.session.delete(employee)
        db.session.commit()

        log_activity("delete", "Employee", employee_id, f"Deleted employee: {employee.name}")

        return ServiceResult(
            success=True,
            message="employee.deleted",
            category="success",
        )
    except Exception as exc:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.delete_failed",
            category="danger",
            data={"detail": str(exc)},
        )


def update_employee_status(employee_id: int, new_status: str, note: str = "") -> ServiceResult:
    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger",
        )

    if new_status not in ["active", "inactive", "on_leave"]:
        return ServiceResult(
            success=False,
            message="employee.invalid_status",
            category="danger",
        )

    old_status = employee.status
    employee.status = new_status

    unlink_info = None
    if new_status == "inactive" and old_status != "inactive":
        unlink_info = _unlink_sim_and_devices_for_inactive(employee)

    status_names = {
        "active": "نشط",
        "inactive": "غير نشط",
        "on_leave": "في إجازة",
    }

    details = (
        "تم تغيير حالة الموظف %s من \"%s\" إلى \"%s\""
        % (
            employee.name,
            status_names.get(old_status, old_status),
            status_names.get(new_status, new_status),
        )
    )
    if note:
        details += f" - ملاحظات: {note}"

    try:
        from models import SystemAudit

        audit = SystemAudit(
            action="update_status",
            entity_type="employee",
            entity_id=employee.id,
            details=details,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.status_update_failed",
            category="danger",
            data={"detail": str(exc)},
        )

    return ServiceResult(
        success=True,
        message="employee.status_updated",
        category="success",
        data={
            "employee_name": employee.name,
            "old_status": old_status,
            "new_status": new_status,
            "note": note,
            "status_names": status_names,
            "unlink": unlink_info,
        },
    )


def prepare_employee_form_context(employee_id: Optional[int] = None) -> dict:
    """
    Prepare all form context data for create/edit employee forms.
    Returns departments, nationalities, available SIMs/devices, and current assignments.
    """
    from models import ImportedPhoneNumber, MobileDevice, DeviceAssignment, SimCard, Nationality

    departments = Department.query.all()
    nationalities = Nationality.query.order_by(Nationality.name_ar).all()
    
    available_phone_numbers = ImportedPhoneNumber.query.filter(
        ImportedPhoneNumber.employee_id.is_(None)
    ).order_by(ImportedPhoneNumber.phone_number).all()
    
    available_imei_numbers = MobileDevice.query.filter(
        MobileDevice.status == 'متاح',
        MobileDevice.employee_id.is_(None)
    ).order_by(MobileDevice.imei).all()

    context = {
        'departments': departments,
        'nationalities': nationalities,
        'available_phone_numbers': available_phone_numbers,
        'available_imei_numbers': available_imei_numbers,
    }

    # For edit mode, include current assignments
    if employee_id:
        employee = Employee.query.get(employee_id)
        if employee:
            context['employee'] = employee
            
            active_assignment = DeviceAssignment.query.filter_by(
                employee_id=employee_id,
                is_active=True
            ).first()
            
            context['active_assignment'] = active_assignment
            
            if active_assignment:
                if active_assignment.device_id:
                    assigned_device = MobileDevice.query.get(active_assignment.device_id)
                    context['assigned_device'] = assigned_device
                
                if active_assignment.sim_card_id:
                    assigned_sim = SimCard.query.get(active_assignment.sim_card_id)
                    context['assigned_sim'] = assigned_sim

    return context


def get_employee_view_context(employee_id: int) -> Optional[dict]:
    """
    Get all data needed for employee view page.
    Returns employee info, documents, attendance, salaries, vehicles, devices, housing.
    """
    from models import (
        Document, Attendance, Salary, VehicleHandover, Vehicle,
        MobileDevice, DeviceAssignment
    )
    
    employee = Employee.query.options(
        db.joinedload(Employee.departments),
        db.joinedload(Employee.nationality_rel)
    ).get(employee_id)
    
    if not employee:
        return None
    
    documents = Document.query.filter_by(employee_id=employee_id).all()
    
    document_types_map = {
        'national_id': 'الهوية الوطنية',
        'passport': 'جواز السفر',
        'health_certificate': 'الشهادة الصحية',
        'work_permit': 'تصريح العمل',
        'education_certificate': 'الشهادة الدراسية',
        'driving_license': 'رخصة القيادة',
        'annual_leave': 'الإجازة السنوية',
        'other': 'أخرى'
    }
    
    documents_by_type = {doc_type: None for doc_type in document_types_map.keys()}
    today = datetime.now().date()
    
    for doc in documents:
        expiry_date = getattr(doc, 'expiry_date', None)

        if not expiry_date:
            doc.status_class = "secondary"
            doc.status_text = "تاريخ الانتهاء غير محدد"
        else:
            try:
                normalized_expiry = expiry_date.date() if hasattr(expiry_date, 'date') else expiry_date
                days_to_expiry = (normalized_expiry - today).days
                if days_to_expiry < 0:
                    doc.status_class = "danger"
                    doc.status_text = "منتهية"
                elif days_to_expiry < 30:
                    doc.status_class = "warning"
                    doc.status_text = f"تنتهي خلال {days_to_expiry} يوم"
                else:
                    doc.status_class = "success"
                    doc.status_text = "سارية"
            except Exception:
                doc.status_class = "secondary"
                doc.status_text = "تاريخ الانتهاء غير صالح"

        doc_type_key = doc.document_type if doc.document_type in documents_by_type else 'other'
        documents_by_type[doc_type_key] = doc
    
    attendances = Attendance.query.filter_by(employee_id=employee_id).order_by(
        Attendance.date.desc()
    ).all()
    
    salaries = Salary.query.filter_by(employee_id=employee_id).order_by(
        Salary.year.desc(), Salary.month.desc()
    ).all()
    
    vehicle_handovers = VehicleHandover.query.filter_by(employee_id=employee_id).order_by(
        VehicleHandover.handover_date.desc()
    ).all()
    
    current_assigned_vehicle = Vehicle.query.filter_by(driver_name=employee.name).first()
    
    mobile_devices = MobileDevice.query.filter_by(employee_id=employee_id).order_by(
        MobileDevice.assigned_date.desc()
    ).all()
    
    device_assignments = DeviceAssignment.query.filter_by(
        employee_id=employee_id,
        is_active=True
    ).options(
        db.joinedload(DeviceAssignment.device),
        db.joinedload(DeviceAssignment.sim_card)
    ).all()
    
    all_departments = Department.query.order_by(Department.name).all()
    housing_properties = employee.housing_properties

    return {
        'employee': employee,
        'documents': documents,
        'documents_by_type': documents_by_type,
        'document_types_map': document_types_map,
        'attendances': attendances,
        'salaries': salaries,
        'vehicle_handovers': vehicle_handovers,
        'current_assigned_vehicle': current_assigned_vehicle,
        'mobile_devices': mobile_devices,
        'device_assignments': device_assignments,
        'departments': all_departments,
        'housing_properties': housing_properties,
    }


def update_employee_iban(employee_id: int, bank_iban: str, iban_file) -> ServiceResult:
    """Update employee's bank IBAN number and/or image."""
    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger"
        )
    
    try:
        if bank_iban:
            employee.bank_iban = bank_iban
        
        if iban_file and iban_file.filename:
            image_path = save_employee_image(iban_file, employee_id, 'iban')
            if image_path:
                employee.bank_iban_image = image_path
        
        db.session.commit()
        log_activity('update', 'Employee', employee_id, f'تم تحديث بيانات الإيبان البنكي للموظف: {employee.name}')
        
        return ServiceResult(
            success=True,
            message="employee.iban_updated",
            category="success"
        )
    except Exception as e:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.iban_update_failed",
            category="danger",
            data={"detail": str(e)}
        )


def delete_employee_iban_image(employee_id: int) -> ServiceResult:
    """Delete employee's IBAN image."""
    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger"
        )
    
    try:
        employee.bank_iban_image = None
        db.session.commit()
        log_activity('delete', 'Employee', employee_id, f'تم حذف صورة الإيبان البنكي للموظف: {employee.name}')
        
        return ServiceResult(
            success=True,
            message="employee.iban_image_deleted",
            category="success"
        )
    except Exception as e:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.iban_image_delete_failed",
            category="danger",
            data={"detail": str(e)}
        )


def delete_employee_housing_image(employee_id: int) -> ServiceResult:
    """Delete employee's housing image."""
    employee = Employee.query.get(employee_id)
    if not employee:
        return ServiceResult(
            success=False,
            message="employee.not_found",
            category="danger"
        )
    
    try:
        employee.housing_image = None
        db.session.commit()
        log_activity('delete', 'Employee', employee_id, f'تم حذف صورة السكن للموظف: {employee.name}')
        
        return ServiceResult(
            success=True,
            message="employee.housing_image_deleted",
            category="success"
        )
    except Exception as e:
        db.session.rollback()
        return ServiceResult(
            success=False,
            message="employee.housing_image_delete_failed",
            category="danger",
            data={"detail": str(e)}
        )
