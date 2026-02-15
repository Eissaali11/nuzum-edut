"""Employee tracking application services."""
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
import json

from sqlalchemy import func, or_, and_

from core.extensions import db
from models import (
    Employee,
    Department,
    employee_departments,
    EmployeeLocation,
    Geofence,
    Vehicle,
)


def format_time_12hr_arabic(dt):
    """Convert time to 12-hour format with Arabic labels."""
    hour = dt.hour
    minute = dt.minute
    second = dt.second

    if hour == 0:
        hour_12 = 12
        period = "ليلاً"
    elif hour < 12:
        hour_12 = hour
        period = "صباحاً"
    elif hour == 12:
        hour_12 = 12
        period = "ظهراً"
    else:
        hour_12 = hour - 12
        period = "مساءً"

    date_str = dt.strftime("%Y-%m-%d")
    return f"{date_str} {hour_12:02d}:{minute:02d}:{second:02d} {period}"


def _employee_photo_url(employee):
    if not employee.profile_image:
        return None
    if employee.profile_image.startswith("http"):
        return employee.profile_image
    if employee.profile_image.startswith("static/"):
        return "/" + employee.profile_image
    if employee.profile_image.startswith("uploads/"):
        return f"/{employee.profile_image}"
    return f"/uploads/{employee.profile_image}"


def get_tracking_page_data(department_filter="", search_query=""):
    query = Employee.query.filter(Employee.status == "active").options(
        db.joinedload(Employee.departments)
    )

    if department_filter:
        query = query.join(employee_departments).join(Department).filter(
            Department.id == department_filter
        )

    if search_query:
        query = query.filter(
            or_(
                Employee.name.contains(search_query),
                Employee.employee_id.contains(search_query),
            )
        )

    all_employees = query.all()
    employee_ids = [emp.id for emp in all_employees]

    latest_locations_subq = (
        db.session.query(
            EmployeeLocation.employee_id,
            EmployeeLocation.id.label("location_id"),
            func.row_number()
            .over(
                partition_by=EmployeeLocation.employee_id,
                order_by=EmployeeLocation.recorded_at.desc(),
            )
            .label("rn"),
        )
        .filter(EmployeeLocation.employee_id.in_(employee_ids))
        .subquery()
    )

    latest_locations_query = (
        db.session.query(EmployeeLocation)
        .join(
            latest_locations_subq,
            and_(
                EmployeeLocation.id == latest_locations_subq.c.location_id,
                latest_locations_subq.c.rn == 1,
            ),
        )
        .all()
    )

    locations_by_employee = {loc.employee_id: loc for loc in latest_locations_query}

    employee_locations = {}
    employees_with_location = []
    employees_without_location = []

    for emp in all_employees:
        latest_location = locations_by_employee.get(emp.id)

        if latest_location:
            age_seconds = (datetime.utcnow() - latest_location.recorded_at).total_seconds()
            age_minutes = age_seconds / 60
            age_hours = age_seconds / 3600

            if age_minutes < 5:
                color = "green"
                status_text = "متصل"
                connection_status = "connected"
            elif age_minutes < 30:
                color = "orange"
                status_text = "نشط مؤخراً"
                connection_status = "recently_active"
            elif age_hours < 6:
                color = "red"
                status_text = "غير متصل"
                connection_status = "disconnected"
            else:
                color = "gray"
                status_text = "غير نشط"
                connection_status = "inactive"

            employee_locations[emp.id] = {
                "latitude": latest_location.latitude,
                "longitude": latest_location.longitude,
                "accuracy": getattr(latest_location, "accuracy_m", None),
                "recorded_at": latest_location.recorded_at,
                "age_minutes": age_minutes,
                "age_hours": age_hours,
                "color": color,
                "status_text": status_text,
                "connection_status": connection_status,
                "vehicle_id": latest_location.vehicle_id,
            }
            employees_with_location.append(emp)
        else:
            employees_without_location.append(emp)

    employees = employees_with_location + employees_without_location

    all_geofences = Geofence.query.filter_by(is_active=True).all()

    vehicle_ids = [
        loc_data["vehicle_id"]
        for loc_data in employee_locations.values()
        if loc_data.get("vehicle_id")
    ]
    vehicles_dict = {}
    if vehicle_ids:
        vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all()
        vehicles_dict = {v.id: v for v in vehicles}

    for emp_id, location_data in employee_locations.items():
        latest_location = locations_by_employee.get(emp_id)

        if latest_location:
            for gf in all_geofences:
                R = 6371000
                lat1, lon1 = (
                    radians(float(latest_location.latitude)),
                    radians(float(latest_location.longitude)),
                )
                lat2, lon2 = (
                    radians(float(gf.center_latitude)),
                    radians(float(gf.center_longitude)),
                )
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                distance = R * c

                if distance <= gf.radius_meters:
                    location_data["geofence_name"] = gf.name
                    break

            if latest_location.vehicle_id and latest_location.vehicle_id in vehicles_dict:
                vehicle = vehicles_dict[latest_location.vehicle_id]
                location_data["vehicle_name"] = vehicle.plate_number

    employees_data = []
    for emp in employees:
        dept_name = emp.departments[0].name if emp.departments else "غير محدد"
        photo_url = None
        if emp.profile_image:
            photo_url = _employee_photo_url(emp)

        employees_data.append(
            {
                "id": emp.id,
                "name": emp.name,
                "employee_number": emp.employee_id,
                "photo_url": photo_url,
                "department_name": dept_name,
            }
        )

    employee_locations_json = {}
    for emp_id, loc_data in employee_locations.items():
        employee_locations_json[emp_id] = {
            "latitude": float(loc_data["latitude"]),
            "longitude": float(loc_data["longitude"]),
            "color": loc_data["color"],
            "status_text": loc_data["status_text"],
            "connection_status": loc_data.get("connection_status", "disconnected"),
            "age_minutes": loc_data.get("age_minutes", 0),
            "geofence_name": loc_data.get("geofence_name"),
            "vehicle_name": loc_data.get("vehicle_name"),
        }

    geofences = Geofence.query.filter_by(is_active=True).all()
    geofences_data = [
        {
            "id": gf.id,
            "name": gf.name,
            "latitude": float(gf.center_latitude),
            "longitude": float(gf.center_longitude),
            "radius": gf.radius_meters,
        }
        for gf in geofences
    ]

    departments = Department.query.all()

    return {
        "employees": employees,
        "employee_locations": employee_locations,
        "employees_json": json.dumps(employees_data, ensure_ascii=False),
        "employee_locations_json": json.dumps(
            employee_locations_json, ensure_ascii=False
        ),
        "geofences_json": json.dumps(geofences_data, ensure_ascii=False),
        "departments": departments,
        "department_filter": department_filter,
        "search_query": search_query,
    }


def get_tracking_dashboard_data():
    cutoff_time_active = datetime.utcnow() - timedelta(hours=1)
    cutoff_time_location = datetime.utcnow() - timedelta(hours=24)

    all_employees = Employee.query.options(db.joinedload(Employee.departments)).all()
    employee_ids = [emp.id for emp in all_employees]

    latest_locations_subq = (
        db.session.query(
            EmployeeLocation.employee_id,
            EmployeeLocation.id.label("location_id"),
            func.row_number()
            .over(
                partition_by=EmployeeLocation.employee_id,
                order_by=EmployeeLocation.recorded_at.desc(),
            )
            .label("rn"),
        )
        .filter(EmployeeLocation.employee_id.in_(employee_ids))
        .subquery()
    )

    latest_locations_query = (
        db.session.query(EmployeeLocation)
        .join(
            latest_locations_subq,
            and_(
                EmployeeLocation.id == latest_locations_subq.c.location_id,
                latest_locations_subq.c.rn == 1,
            ),
        )
        .all()
    )

    locations_by_employee = {loc.employee_id: loc for loc in latest_locations_query}

    active_employees = []
    inactive_employees = []
    employees_with_vehicles = []

    for emp in all_employees:
        latest_location = locations_by_employee.get(emp.id)

        if latest_location and latest_location.recorded_at >= cutoff_time_active:
            active_employees.append(
                {
                    "employee": emp,
                    "location": latest_location,
                    "departments": [d.name for d in emp.departments],
                }
            )

            if latest_location.vehicle_id:
                employees_with_vehicles.append(
                    {
                        "employee": emp,
                        "location": latest_location,
                        "vehicle": latest_location.vehicle,
                    }
                )
        else:
            inactive_employees.append(emp)

    all_geofences = Geofence.query.filter_by(is_active=True).all()

    employees_inside_geofences = []
    employees_outside_geofences = []
    geofence_stats = []
    employees_inside_any_geofence = set()

    for geofence in all_geofences:
        inside_count = 0
        inside_employees = []

        for emp in all_employees:
            latest_location = locations_by_employee.get(emp.id)

            if latest_location and latest_location.recorded_at >= cutoff_time_location:
                lat1, lon1 = float(latest_location.latitude), float(
                    latest_location.longitude
                )
                lat2, lon2 = float(geofence.center_latitude), float(
                    geofence.center_longitude
                )

                R = 6371000
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(
                    radians(lat2)
                ) * sin(dlon / 2) ** 2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                distance = R * c

                if distance <= geofence.radius_meters:
                    inside_count += 1
                    inside_employees.append(
                        {
                            "employee": emp,
                            "location": latest_location,
                            "distance": distance,
                        }
                    )
                    employees_inside_any_geofence.add(emp.id)

        geofence_stats.append(
            {
                "geofence": geofence,
                "inside_count": inside_count,
                "inside_employees": inside_employees,
            }
        )

    for emp in all_employees:
        latest_location = locations_by_employee.get(emp.id)

        if latest_location and latest_location.recorded_at >= cutoff_time_location:
            if emp.id in employees_inside_any_geofence:
                if not any(e["employee"].id == emp.id for e in employees_inside_geofences):
                    employees_inside_geofences.append(
                        {"employee": emp, "location": latest_location}
                    )
            else:
                employees_outside_geofences.append(
                    {"employee": emp, "location": latest_location}
                )

    stats = {
        "total_employees": len(all_employees),
        "active_count": len(active_employees),
        "inactive_count": len(inactive_employees),
        "with_vehicles_count": len(employees_with_vehicles),
        "inside_geofences_count": len(employees_inside_geofences),
        "outside_geofences_count": len(employees_outside_geofences),
        "total_geofences": len(all_geofences),
    }

    return {
        "stats": stats,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "employees_with_vehicles": employees_with_vehicles,
        "employees_inside_geofences": employees_inside_geofences,
        "employees_outside_geofences": employees_outside_geofences,
        "geofence_stats": geofence_stats,
    }


def get_track_history_page_data(employee_id):
    from flask import url_for

    employee = Employee.query.get_or_404(employee_id)
    employee_photo_url = None
    if employee.profile_image:
        if employee.profile_image.startswith("http"):
            employee_photo_url = employee.profile_image
        elif employee.profile_image.startswith("static/"):
            employee_photo_url = url_for(
                "static",
                filename=employee.profile_image.replace("static/", ""),
                _external=False,
            )
        elif employee.profile_image.startswith("uploads/"):
            employee_photo_url = url_for(
                "static", filename=employee.profile_image, _external=False
            )
        else:
            employee_photo_url = url_for(
                "static",
                filename=f"uploads/{employee.profile_image}",
                _external=False,
            )

    cutoff_time = datetime.utcnow() - timedelta(hours=24)

    locations = (
        EmployeeLocation.query.filter(
            EmployeeLocation.employee_id == employee_id,
            EmployeeLocation.recorded_at >= cutoff_time,
        )
        .order_by(EmployeeLocation.recorded_at.asc())
        .all()
    )

    locations_data = []
    for loc in locations:
        loc_dict = {
            "latitude": float(loc.latitude),
            "longitude": float(loc.longitude),
            "speed": float(loc.speed_kmh) if loc.speed_kmh else 0,
            "vehicle_id": loc.vehicle_id,
            "recorded_at": format_time_12hr_arabic(loc.recorded_at),
            "accuracy": float(loc.accuracy_m) if loc.accuracy_m else None,
        }

        if loc.vehicle_id and loc.vehicle:
            loc_dict["vehicle"] = {
                "id": loc.vehicle.id,
                "plate_number": loc.vehicle.plate_number,
                "make": loc.vehicle.make,
                "model": loc.vehicle.model,
            }

        locations_data.append(loc_dict)

    departments = Department.query.all()

    return {
        "employee": employee,
        "employee_photo_url": employee_photo_url,
        "locations": locations_data,
        "departments": departments,
    }
