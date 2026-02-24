"""
مسارات التتبع المباشر والدوائر الجغرافية و API المواقع الحية — مستخرجة من routes/mobile.py.
تُسجَّل على mobile_bp عبر register_tracking_routes(mobile_bp).
نفس القوالب ومتغيرات السياق واستجابة JSON.
"""
import json
from datetime import datetime, timedelta

from flask import render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import and_, func as sql_func

from core.extensions import db
from models import Employee, Geofence, EmployeeLocation, GeofenceSession, GeofenceEvent

from application.mobile.tracking_services import (
    location_status_from_age_minutes,
    haversine_distance_meters,
    is_inside_geofence,
)


def register_tracking_routes(mobile_bp):
    """تسجيل مسارات التتبع وصفحة تفاصيل الدائرة الجغرافية و API المواقع الحية."""

    @mobile_bp.route("/tracking")
    @login_required
    def mobile_tracking():
        """صفحة تتبع الموظفين المباشر للموبايل - مماثلة لصفحة الكمبيوتر"""
        cutoff_time_active = datetime.utcnow() - timedelta(hours=1)
        cutoff_time_location = datetime.utcnow() - timedelta(hours=24)

        all_employees = Employee.query.options(db.joinedload(Employee.departments)).all()
        employee_ids = [emp.id for emp in all_employees]

        latest_locations_subq = db.session.query(
            EmployeeLocation.employee_id,
            EmployeeLocation.id.label("location_id"),
            sql_func.row_number()
            .over(
                partition_by=EmployeeLocation.employee_id,
                order_by=EmployeeLocation.recorded_at.desc(),
            )
            .label("rn"),
        ).filter(EmployeeLocation.employee_id.in_(employee_ids)).subquery()

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
                active_employees.append({
                    "employee": emp,
                    "location": latest_location,
                    "departments": [d.name for d in emp.departments],
                })
                if latest_location.vehicle_id:
                    employees_with_vehicles.append({
                        "employee": emp,
                        "location": latest_location,
                        "vehicle": latest_location.vehicle,
                    })
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
                    lat1, lon1 = float(latest_location.latitude), float(latest_location.longitude)
                    lat2, lon2 = float(geofence.center_latitude), float(geofence.center_longitude)
                    distance = haversine_distance_meters(lat1, lon1, lat2, lon2)

                    if distance <= geofence.radius_meters:
                        inside_count += 1
                        inside_employees.append({
                            "employee": emp,
                            "location": latest_location,
                            "distance": distance,
                        })
                        employees_inside_any_geofence.add(emp.id)

            geofence_stats.append({
                "geofence": geofence,
                "employees": inside_employees,
                "count": inside_count,
            })

        for emp_data in active_employees:
            emp = emp_data["employee"]
            if emp.id not in employees_inside_any_geofence:
                employees_outside_geofences.append({
                    "employee": emp,
                    "location": emp_data["location"],
                })

        for emp_data in active_employees:
            emp = emp_data["employee"]
            latest_location = locations_by_employee.get(emp.id)
            for geofence in all_geofences:
                if latest_location:
                    lat1, lon1 = float(latest_location.latitude), float(latest_location.longitude)
                    lat2, lon2 = float(geofence.center_latitude), float(geofence.center_longitude)
                    if is_inside_geofence(
                        lat1, lon1, lat2, lon2, geofence.radius_meters
                    ):
                        emp_data["geofence"] = geofence
                        break
            if latest_location and latest_location.vehicle_id and latest_location.vehicle:
                emp_data["vehicle"] = latest_location.vehicle

        stats = {
            "total_employees": len(all_employees),
            "active_employees": len(active_employees),
            "inactive_employees": len(inactive_employees),
            "inside_geofences_count": len(employees_inside_any_geofence),
            "outside_geofences_count": len(employees_outside_geofences),
            "on_vehicles_count": len(employees_with_vehicles),
        }

        employee_locations = {}
        for emp in all_employees:
            location = locations_by_employee.get(emp.id)
            if location and location.latitude is not None and location.longitude is not None:
                try:
                    age_minutes = (datetime.utcnow() - location.recorded_at).total_seconds() / 60
                    status = location_status_from_age_minutes(age_minutes)
                    employee_locations[str(emp.id)] = {
                        "latitude": float(location.latitude),
                        "longitude": float(location.longitude),
                        "name": emp.name,
                        "employee_id": emp.employee_id,
                        "status": status,
                        "age_minutes": int(age_minutes),
                        "photo_url": emp.profile_image,
                    }
                except Exception:
                    employee_locations[str(emp.id)] = {"status": "not_registered"}
            else:
                employee_locations[str(emp.id)] = {"status": "not_registered"}

        geofences_data = [
            {
                "id": gf.id,
                "name": gf.name,
                "center_latitude": float(gf.center_latitude),
                "center_longitude": float(gf.center_longitude),
                "radius_meters": gf.radius_meters,
                "color": gf.color,
            }
            for gf in all_geofences
        ]

        return render_template(
            "mobile/tracking.html",
            stats=stats,
            employees_active=active_employees,
            employees_inactive=inactive_employees,
            employees_by_geofence=geofence_stats,
            employees_outside_geofences=employees_outside_geofences,
            employee_locations_json=json.dumps(employee_locations),
            geofences_json=json.dumps(geofences_data),
            now=datetime.utcnow(),
        )

    @mobile_bp.route("/geofence/<int:geofence_id>")
    @login_required
    def geofence_details(geofence_id):
        """عرض تفاصيل دائرة جغرافية معينة"""
        geofence = Geofence.query.get_or_404(geofence_id)
        filter_type = request.args.get("filter", "all")
        filter_date = request.args.get("date", "")

        assigned_employees = geofence.assigned_employees
        center_lat = float(geofence.center_latitude)
        center_lng = float(geofence.center_longitude)
        radius = geofence.radius_meters

        employees_inside = []
        employees_outside = []
        employees_active = []
        employees_inactive = []
        employees_no_location = []

        for emp in assigned_employees:
            location = (
                EmployeeLocation.query.filter_by(employee_id=emp.id)
                .order_by(EmployeeLocation.recorded_at.desc())
                .first()
            )
            if location and location.latitude and location.longitude:
                distance = haversine_distance_meters(
                    center_lat, center_lng, float(location.latitude), float(location.longitude)
                )
                age_minutes = (datetime.utcnow() - location.recorded_at).total_seconds() / 60
                is_active = age_minutes < 30
                emp_data = {
                    "employee": emp,
                    "location": location,
                    "distance": int(distance),
                    "age_minutes": int(age_minutes),
                    "is_active": is_active,
                }
                if distance <= radius:
                    employees_inside.append(emp_data)
                else:
                    employees_outside.append(emp_data)
                if is_active:
                    employees_active.append(emp_data)
                else:
                    employees_inactive.append(emp_data)
            else:
                emp_data = {
                    "employee": emp,
                    "location": None,
                    "distance": None,
                    "age_minutes": None,
                    "is_active": False,
                }
                employees_outside.append(emp_data)
                employees_inactive.append(emp_data)
                employees_no_location.append(emp_data)

        if filter_date:
            try:
                selected_date = datetime.strptime(filter_date, "%Y-%m-%d").date()
            except ValueError:
                selected_date = datetime.utcnow().date()
        else:
            selected_date = datetime.utcnow().date()

        date_start = datetime.combine(selected_date, datetime.min.time())
        date_end = datetime.combine(selected_date, datetime.max.time())

        entered_employee_ids = (
            db.session.query(GeofenceEvent.employee_id)
            .filter(
                GeofenceEvent.geofence_id == geofence_id,
                GeofenceEvent.event_type == "enter",
                GeofenceEvent.recorded_at >= date_start,
                GeofenceEvent.recorded_at <= date_end,
            )
            .distinct()
            .all()
        )
        entered_ids = [eid[0] for eid in entered_employee_ids]

        employees_entered_today = []
        employees_not_entered_today = []

        for emp in assigned_employees:
            emp_data = None
            for e in employees_inside + employees_outside:
                if e["employee"].id == emp.id:
                    emp_data = e
                    break
            if emp_data is None:
                emp_data = {
                    "employee": emp,
                    "location": None,
                    "distance": None,
                    "age_minutes": None,
                    "is_active": False,
                }
            if emp.id in entered_ids:
                employees_entered_today.append(emp_data)
            else:
                employees_not_entered_today.append(emp_data)

        if filter_date:
            recent_events_raw = (
                GeofenceEvent.query.filter(
                    GeofenceEvent.geofence_id == geofence_id,
                    GeofenceEvent.recorded_at >= date_start,
                    GeofenceEvent.recorded_at <= date_end,
                )
                .order_by(GeofenceEvent.recorded_at.desc())
                .limit(50)
                .all()
            )
        else:
            recent_events_raw = (
                GeofenceEvent.query.filter_by(geofence_id=geofence_id)
                .order_by(GeofenceEvent.recorded_at.desc())
                .limit(20)
                .all()
            )

        recent_events = []
        for event in recent_events_raw:
            event.recorded_at_local = (
                event.recorded_at + timedelta(hours=3) if event.recorded_at else None
            )
            recent_events.append(event)

        active_sessions = GeofenceSession.query.filter_by(
            geofence_id=geofence_id, is_active=True
        ).all()

        today_entries = GeofenceEvent.query.filter(
            GeofenceEvent.geofence_id == geofence_id,
            GeofenceEvent.event_type == "enter",
            GeofenceEvent.recorded_at >= date_start,
            GeofenceEvent.recorded_at <= date_end,
        ).count()
        today_exits = GeofenceEvent.query.filter(
            GeofenceEvent.geofence_id == geofence_id,
            GeofenceEvent.event_type == "exit",
            GeofenceEvent.recorded_at >= date_start,
            GeofenceEvent.recorded_at <= date_end,
        ).count()

        stats = {
            "total_assigned": len(assigned_employees),
            "inside_count": len(employees_inside),
            "outside_count": len(employees_outside),
            "active_count": len(employees_active),
            "inactive_count": len(employees_inactive),
            "active_sessions": len(active_sessions),
            "today_entries": today_entries,
            "today_exits": today_exits,
            "entered_today": len(employees_entered_today),
            "not_entered_today": len(employees_not_entered_today),
        }

        employees_locations_json = []
        for emp_data in employees_inside + employees_outside:
            if emp_data["location"]:
                employees_locations_json.append({
                    "id": emp_data["employee"].id,
                    "name": emp_data["employee"].name,
                    "latitude": float(emp_data["location"].latitude),
                    "longitude": float(emp_data["location"].longitude),
                    "photo_url": emp_data["employee"].profile_image,
                    "is_inside": (
                        emp_data["distance"] <= radius if emp_data["distance"] is not None else False
                    ),
                    "distance": emp_data["distance"],
                    "is_active": emp_data["is_active"],
                })

        return render_template(
            "mobile/geofence_details.html",
            geofence=geofence,
            employees_inside=employees_inside,
            employees_outside=employees_outside,
            employees_active=employees_active,
            employees_inactive=employees_inactive,
            employees_entered_today=employees_entered_today,
            employees_not_entered_today=employees_not_entered_today,
            recent_events=recent_events,
            stats=stats,
            filter_type=filter_type,
            filter_date=filter_date or selected_date.strftime("%Y-%m-%d"),
            employees_json=json.dumps(employees_locations_json),
            now=datetime.utcnow(),
        )

    @mobile_bp.route("/api/live-locations")
    @login_required
    def get_live_locations():
        """جلب مواقع الموظفين الحية مباشرة من قاعدة البيانات"""
        all_employees = Employee.query.options(db.joinedload(Employee.departments)).all()
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
                        "last_update": location.recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "photo_url": emp.profile_image,
                        "department_name": (
                            emp.department.name if emp.department else "غير محدد"
                        ),
                        "department_id": (
                            emp.departments[0].id if emp.departments else None
                        ),
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

        return jsonify({
            "success": True,
            "locations": employee_locations,
            "geofences": geofences_data,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        })
