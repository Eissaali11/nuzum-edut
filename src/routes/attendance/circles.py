# -*- coding: utf-8 -*-
"""
عمليات الدوائر والمجموعات
Circle and group operations for attendance

ملاحظة:
- هذا الملف يحتوي على تعريفات المسارات فقط.
- لا يتم تسجيل المسارات إلا عند استدعاء register_circles_routes().
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, time, timedelta
from io import BytesIO
import pandas as pd
import logging

from src.core.extensions import db
from models import Attendance, Employee, Department, EmployeeLocation, GeofenceSession
from src.utils.date_converter import format_date_hijri
from .helpers import format_time_12h_ar, format_time_12h_ar_short

logger = logging.getLogger(__name__)


def register_circles_routes(attendance_bp):
    """Register all circle-related routes with the blueprint."""

    @attendance_bp.route('/departments-circles-overview')
    @login_required
    def departments_circles_overview():
        """لوحة تحكم شاملة تعرض الأقسام والدوائر وبيانات الحضور مع فلاتر"""
        date_str = request.args.get('date')
        department_filter = request.args.get('department_id')

        try:
            if date_str:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                selected_date = datetime.now().date()
        except ValueError:
            selected_date = datetime.now().date()

        # حساب التاريخ: من اليوم الحالي أو التاريخ المختار
        # نجلب بيانات الحضور من آخر 18 ساعة من الصباح (6 صباحاً)
        now = datetime.now()
        today_date = datetime.now().date()
        eighteen_hours_ago_date = (now - timedelta(hours=18)).date()

        # نطاق التواريخ المراد البحث فيها
        start_date = min(selected_date, eighteen_hours_ago_date)
        end_date = today_date

        all_departments = Department.query.order_by(Department.name).all()

        if department_filter:
            try:
                departments = [Department.query.get(int(department_filter))]
                if not departments[0]:
                    departments = all_departments
            except (ValueError, TypeError):
                departments = all_departments
        else:
            departments = all_departments

        departments_data = []

        for dept in departments:
            # جلب جميع الموظفين النشطين في القسم
            active_employees = [emp for emp in dept.employees if emp.status == 'active']

            # تجميع الموظفين حسب الدوائر الجغرافية - مع تنظيف المسافات الزائدة
            locations_dict = {}
            employees_without_location = []

            for emp in active_employees:
                if emp.location:
                    # تنظيف المسافات وتوحيد الأسماء
                    location_name = emp.location.strip()
                    if location_name not in locations_dict:
                        locations_dict[location_name] = []
                    locations_dict[location_name].append(emp)
                else:
                    employees_without_location.append(emp)

            circles_data = []
            total_dept_present = 0
            total_dept_absent = 0
            total_dept_leave = 0
            total_dept_sick = 0

            # إذا لم تكن هناك دوائر جغرافية
            if not locations_dict:
                # إذا تم اختيار قسم معين، نعرضه مع رسالة أنه لا توجد دوائر
                if department_filter:
                    departments_data.append({
                        'name': dept.name,
                        'id': dept.id,
                        'total_employees': len(active_employees),
                        'total_present': 0,
                        'total_absent': 0,
                        'total_leave': 0,
                        'total_sick': 0,
                        'circles': [],
                        'no_circles': True
                    })
                # وإذا كان عرض جميع الأقسام، نتخطى هذا القسم
                continue

            # معالجة كل دائرة جغرافية
            for location in sorted(locations_dict.keys()):
                emp_in_circle = locations_dict[location]
                emp_ids = [e.id for e in emp_in_circle]

                if emp_ids:
                    # جلب بيانات الحضور لهذه الدائرة من آخر 18 ساعة
                    present = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.employee_id.in_(emp_ids),
                        Attendance.date >= start_date,
                        Attendance.date <= end_date,
                        Attendance.status == 'present'
                    ).scalar() or 0

                    absent = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.employee_id.in_(emp_ids),
                        Attendance.date >= start_date,
                        Attendance.date <= end_date,
                        Attendance.status == 'absent'
                    ).scalar() or 0

                    leave = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.employee_id.in_(emp_ids),
                        Attendance.date >= start_date,
                        Attendance.date <= end_date,
                        Attendance.status == 'leave'
                    ).scalar() or 0

                    sick = db.session.query(func.count(Attendance.id)).filter(
                        Attendance.employee_id.in_(emp_ids),
                        Attendance.date >= start_date,
                        Attendance.date <= end_date,
                        Attendance.status == 'sick'
                    ).scalar() or 0

                    not_registered = len(emp_ids) - (present + absent + leave + sick)
                else:
                    present = absent = leave = sick = not_registered = 0

                total_dept_present += present
                total_dept_absent += absent
                total_dept_leave += leave
                total_dept_sick += sick

                # جلب تفاصيل الموظفين في هذه الدائرة (آخر سجل خلال 18 ساعة)
                employees_details = []
                accessed_count = 0
                accessed_employees = []

                for emp in emp_in_circle:
                    attendance = Attendance.query.filter(
                        Attendance.employee_id == emp.id,
                        Attendance.date >= start_date,
                        Attendance.date <= end_date
                    ).order_by(Attendance.date.desc()).first()

                    # جلب بيانات التتبع الجغرافي (GPS)
                    emp_location = db.session.query(EmployeeLocation).filter(
                        EmployeeLocation.employee_id == emp.id,
                        EmployeeLocation.recorded_at >= datetime.combine(start_date, time(0, 0, 0)),
                        EmployeeLocation.recorded_at <= datetime.combine(end_date, time(23, 59, 59))
                    ).order_by(EmployeeLocation.recorded_at.desc()).first()

                    # جلب بيانات الوصول إلى الدوائر (GeofenceSession)
                    geo_session = db.session.query(GeofenceSession).filter(
                        GeofenceSession.employee_id == emp.id,
                        GeofenceSession.entry_time >= datetime.combine(start_date, time(0, 0, 0)),
                        GeofenceSession.entry_time <= datetime.combine(end_date, time(23, 59, 59))
                    ).order_by(GeofenceSession.entry_time.desc()).first()

                    # تحديد ما إذا كان الموظف قد دخل الدائرة
                    accessed = geo_session is not None
                    if accessed:
                        accessed_count += 1
                        accessed_employees.append(emp.name)

                    duration_minutes = geo_session.duration_minutes if geo_session and geo_session.duration_minutes else 0

                    emp_data = {
                        'id': emp.id,
                        'name': emp.name,
                        'employee_id': emp.employee_id,
                        'status': attendance.status if attendance else 'لم يتم التسجيل',
                        'check_in': attendance.check_in.strftime('%H:%M') if attendance and attendance.check_in else '-',
                        'check_out': attendance.check_out.strftime('%H:%M') if attendance and attendance.check_out else '-',
                        # بيانات التتبع الجغرافي
                        'gps_latitude': emp_location.latitude if emp_location else None,
                        'gps_longitude': emp_location.longitude if emp_location else None,
                        'gps_recorded_at': emp_location.recorded_at if emp_location else None,
                        # بيانات الوصول إلى الدائرة
                        'accessed_circle': accessed,
                        'circle_enter_time': geo_session.entry_time.strftime('%H:%M:%S') if geo_session and geo_session.entry_time else None,
                        'circle_exit_time': geo_session.exit_time.strftime('%H:%M:%S') if geo_session and geo_session.exit_time else None,
                        'duration_minutes': duration_minutes,
                        'duration_display': f'{duration_minutes // 60}س {duration_minutes % 60}د' if duration_minutes > 0 else '-',
                    }
                    employees_details.append(emp_data)

                # إضافة بيانات الدائرة مع معلومات الوصول
                circles_data.append({
                    'name': location,
                    'total': len(emp_in_circle),
                    'present': present,
                    'absent': absent,
                    'leave': leave,
                    'sick': sick,
                    'not_registered': not_registered,
                    'accessed_count': accessed_count,
                    'accessed_employees': ', '.join(accessed_employees) if accessed_employees else 'لا أحد',
                    'employees': employees_details
                })

            # معالجة الموظفين بدون دائرة جغرافية محددة
            if employees_without_location:
                emp_ids = [e.id for e in employees_without_location]
                present = db.session.query(func.count(Attendance.id)).filter(
                    Attendance.employee_id.in_(emp_ids),
                    Attendance.date >= start_date,
                    Attendance.date <= end_date,
                    Attendance.status == 'present'
                ).scalar() or 0

                absent = db.session.query(func.count(Attendance.id)).filter(
                    Attendance.employee_id.in_(emp_ids),
                    Attendance.date >= start_date,
                    Attendance.date <= end_date,
                    Attendance.status == 'absent'
                ).scalar() or 0

                leave = db.session.query(func.count(Attendance.id)).filter(
                    Attendance.employee_id.in_(emp_ids),
                    Attendance.date >= start_date,
                    Attendance.date <= end_date,
                    Attendance.status == 'leave'
                ).scalar() or 0

                sick = db.session.query(func.count(Attendance.id)).filter(
                    Attendance.employee_id.in_(emp_ids),
                    Attendance.date >= start_date,
                    Attendance.date <= end_date,
                    Attendance.status == 'sick'
                ).scalar() or 0

                not_registered = len(emp_ids) - (present + absent + leave + sick)

                total_dept_present += present
                total_dept_absent += absent
                total_dept_leave += leave
                total_dept_sick += sick

                employees_details = []
                for emp in employees_without_location:
                    attendance = Attendance.query.filter(
                        Attendance.employee_id == emp.id,
                        Attendance.date >= start_date,
                        Attendance.date <= end_date
                    ).order_by(Attendance.date.desc()).first()

                    emp_data = {
                        'name': emp.name,
                        'employee_id': emp.employee_id,
                        'status': attendance.status if attendance else 'لم يتم التسجيل',
                        'check_in': attendance.check_in.strftime('%H:%M') if attendance and attendance.check_in else '-',
                        'check_out': attendance.check_out.strftime('%H:%M') if attendance and attendance.check_out else '-',
                    }
                    employees_details.append(emp_data)

                circles_data.append({
                    'name': '🔵 بدون دائرة محددة',
                    'total': len(employees_without_location),
                    'present': present,
                    'absent': absent,
                    'leave': leave,
                    'sick': sick,
                    'not_registered': not_registered,
                    'employees': employees_details
                })

            # إضافة بيانات القسم
            departments_data.append({
                'name': dept.name,
                'id': dept.id,
                'total_employees': len(active_employees),
                'total_present': total_dept_present,
                'total_absent': total_dept_absent,
                'total_leave': total_dept_leave,
                'total_sick': total_dept_sick,
                'circles': circles_data
            })

        # جلب بيانات التتبع الجغرافي للموظفين
        from sqlalchemy import and_
        from sqlalchemy import func as sql_func

        all_active_emp_ids = [e_data['id'] for dept in departments_data for circle in dept['circles'] for e_data in circle['employees']]

        # بناء dictionary لبيانات التتبع
        locations_by_employee = {}
        if all_active_emp_ids:
            latest_locations_subq = db.session.query(
                EmployeeLocation.employee_id,
                EmployeeLocation.id.label('location_id'),
                sql_func.row_number().over(
                    partition_by=EmployeeLocation.employee_id,
                    order_by=EmployeeLocation.recorded_at.desc()
                ).label('rn')
            ).filter(
                EmployeeLocation.employee_id.in_(all_active_emp_ids)
            ).subquery()

            latest_locations = db.session.query(EmployeeLocation).join(
                latest_locations_subq,
                and_(
                    EmployeeLocation.id == latest_locations_subq.c.location_id,
                    latest_locations_subq.c.rn == 1
                )
            ).all()

            for loc in latest_locations:
                locations_by_employee[loc.employee_id] = {
                    'latitude': loc.latitude,
                    'longitude': loc.longitude,
                    'recorded_at': loc.recorded_at
                }

        return render_template(
            'attendance/departments_circles_overview.html',
            departments_data=departments_data,
            all_departments=all_departments,
            selected_date=selected_date,
            selected_date_formatted=format_date_hijri(selected_date),
            selected_department_id=int(department_filter) if department_filter else None,
            locations_by_employee=locations_by_employee
        )

    @attendance_bp.route('/circle-accessed-details/<int:department_id>/<circle_name>')
    @login_required
    def circle_accessed_details(department_id, circle_name):
        """صفحة منفصلة لعرض تفاصيل الموظفين الواصلين للدائرة"""
        date_str = request.args.get('date')

        # منطقة زمنية السعودية (UTC+3)
        saudi_tz = timedelta(hours=3)

        try:
            if date_str:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                selected_date = datetime.now().date()
        except ValueError:
            selected_date = datetime.now().date()

        # حساب نطاق التواريخ - من التاريخ المختار إلى اليوم
        start_date = selected_date
        end_date = datetime.now().date()

        dept = Department.query.get(department_id)
        if not dept:
            flash('القسم غير موجود', 'danger')
            return redirect(url_for('attendance.departments_circles_overview'))

        # جلب الموظفين النشطين في القسم والدائرة المحددة
        active_employees = [emp for emp in dept.employees if emp.status == 'active' and emp.location and emp.location.strip() == circle_name]

        employees_accessed = []

        for emp in active_employees:
            # جلب جميع جلسات الدائرة الجغرافية (GeofenceSession)
            geo_sessions = db.session.query(GeofenceSession).filter(
                GeofenceSession.employee_id == emp.id,
                GeofenceSession.entry_time >= datetime.combine(start_date, time(0, 0, 0)),
                GeofenceSession.entry_time <= datetime.combine(end_date, time(23, 59, 59))
            ).order_by(GeofenceSession.entry_time.asc()).all()

            if geo_sessions:
                emp_location = db.session.query(EmployeeLocation).filter(
                    EmployeeLocation.employee_id == emp.id,
                    EmployeeLocation.recorded_at >= datetime.combine(start_date, time(0, 0, 0)),
                    EmployeeLocation.recorded_at <= datetime.combine(end_date, time(23, 59, 59))
                ).order_by(EmployeeLocation.recorded_at.desc()).first()

                # استخراج دخول وخروج الصباح والمساء من GeofenceSession
                morning_check_in = None
                morning_check_out = None
                evening_check_in = None
                evening_check_out = None

                # معالجة جميع جلسات الدائرة
                for geo in geo_sessions:
                    # استخراج أول دخول صباحي من الدائرة
                    if geo.entry_time and not morning_check_in:
                        entry_sa = geo.entry_time + saudi_tz
                        if entry_sa.hour < 12:
                            morning_check_in = entry_sa

                    # استخراج أول دخول مسائي من الدائرة
                    if geo.entry_time and not evening_check_in:
                        entry_sa = geo.entry_time + saudi_tz
                        if entry_sa.hour >= 12:
                            evening_check_in = entry_sa

                    # استخراج أخر خروج صباحي من الدائرة
                    if geo.exit_time:
                        exit_sa = geo.exit_time + saudi_tz
                        if exit_sa.hour < 12:
                            morning_check_out = exit_sa

                    # استخراج أخر خروج مسائي من الدائرة
                    if geo.exit_time:
                        exit_sa = geo.exit_time + saudi_tz
                        if exit_sa.hour >= 12:
                            evening_check_out = exit_sa

                # جلب آخر جلسة للحصول على البيانات الأساسية
                latest_geo = geo_sessions[-1]

                # جلب سجلات الحضور (للحالة فقط)
                attendance = Attendance.query.filter(
                    Attendance.employee_id == emp.id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                ).order_by(Attendance.date.desc()).first()

                duration_minutes = latest_geo.duration_minutes if latest_geo.duration_minutes else 0

                # تحويل الأوقات إلى توقيت السعودية
                entry_time_sa = (latest_geo.entry_time + saudi_tz) if latest_geo.entry_time else None
                exit_time_sa = (latest_geo.exit_time + saudi_tz) if latest_geo.exit_time else None

                # حساب ساعات العمل من الدخول الصباحي إلى الخروج المسائي
                work_hours = 0
                work_minutes = 0
                if morning_check_in and evening_check_out:
                    total_seconds = (evening_check_out - morning_check_in).total_seconds()
                    if total_seconds > 0:
                        work_hours = int(total_seconds // 3600)
                        work_minutes = int((total_seconds % 3600) // 60)

                employees_accessed.append({
                    'name': emp.name,
                    'employee_id': emp.employee_id,
                    'status': 'حضور' if (attendance and attendance.status) else 'حضور من الدائرة',
                    'check_in': '-',
                    'check_out': '-',
                    'morning_check_in': format_time_12h_ar_short(morning_check_in) if morning_check_in else '-',
                    'morning_check_in_hours': morning_check_in.hour if morning_check_in else None,
                    'morning_check_in_minutes': morning_check_in.minute if morning_check_in else None,
                    'morning_check_out': format_time_12h_ar_short(morning_check_out) if morning_check_out else '-',
                    'evening_check_in': format_time_12h_ar_short(evening_check_in) if evening_check_in else '-',
                    'evening_check_out': format_time_12h_ar_short(evening_check_out) if evening_check_out else '-',
                    'evening_check_out_hours': evening_check_out.hour if evening_check_out else None,
                    'evening_check_out_minutes': evening_check_out.minute if evening_check_out else None,
                    'work_hours': work_hours,
                    'work_minutes': work_minutes,
                    'work_hours_display': f'{work_hours} س {work_minutes} د' if (work_hours > 0 or work_minutes > 0) else '-',
                    'circle_enter_time': format_time_12h_ar(entry_time_sa) if entry_time_sa else None,
                    'circle_exit_time': format_time_12h_ar(exit_time_sa) if exit_time_sa else None,
                    'duration_minutes': duration_minutes,
                    'duration_display': f'{duration_minutes // 60}س {duration_minutes % 60}د' if duration_minutes > 0 else '-',
                    'gps_latitude': emp_location.latitude if emp_location else None,
                    'gps_longitude': emp_location.longitude if emp_location else None,
                    'profile_image': emp.profile_image,
                })

        return render_template(
            'attendance/circle_accessed_details.html',
            circle_name=circle_name,
            department_name=dept.name,
            department_id=department_id,
            employees_accessed=employees_accessed,
            selected_date=selected_date,
            selected_date_formatted=format_date_hijri(selected_date)
        )

    @attendance_bp.route('/circle-accessed-details/<int:department_id>/<circle_name>/export-excel')
    @login_required
    def export_circle_details_excel(department_id, circle_name):
        """تصدير تفاصيل الموظفين الواصلين للدائرة إلى ملف Excel"""
        date_str = request.args.get('date')
        export_type = request.args.get('type', 'all')  # 'all' أو employee_id
        employee_id_filter = request.args.get('employee_id', None)

        # منطقة زمنية السعودية (UTC+3)
        saudi_tz = timedelta(hours=3)

        try:
            if date_str:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                selected_date = datetime.now().date()
        except ValueError:
            selected_date = datetime.now().date()

        # حساب نطاق التواريخ - من التاريخ المختار إلى اليوم
        start_date = selected_date
        end_date = datetime.now().date()

        dept = Department.query.get(department_id)
        if not dept:
            flash('القسم غير موجود', 'danger')
            return redirect(url_for('attendance.departments_circles_overview'))

        # جلب الموظفين النشطين في القسم والدائرة المحددة
        active_employees = [emp for emp in dept.employees if emp.status == 'active' and emp.location and emp.location.strip() == circle_name]

        # إذا كان هناك فلتر موظف معين
        if export_type == 'single' and employee_id_filter:
            try:
                active_employees = [emp for emp in active_employees if emp.employee_id == str(employee_id_filter)]
            except Exception:
                pass

        data = []

        for emp in active_employees:
            # جلب جميع جلسات الدائرة الجغرافية (GeofenceSession)
            geo_sessions = db.session.query(GeofenceSession).filter(
                GeofenceSession.employee_id == emp.id,
                GeofenceSession.entry_time >= datetime.combine(start_date, time(0, 0, 0)),
                GeofenceSession.entry_time <= datetime.combine(end_date, time(23, 59, 59))
            ).order_by(GeofenceSession.entry_time.asc()).all()

            if geo_sessions:
                # استخراج دخول وخروج الصباح والمساء من GeofenceSession
                morning_check_in = None
                morning_check_out = None
                evening_check_in = None
                evening_check_out = None

                # معالجة جميع جلسات الدائرة
                for geo in geo_sessions:
                    # استخراج أول دخول صباحي من الدائرة
                    if geo.entry_time and not morning_check_in:
                        entry_sa = geo.entry_time + saudi_tz
                        if entry_sa.hour < 12:
                            morning_check_in = entry_sa

                    # استخراج أول دخول مسائي من الدائرة
                    if geo.entry_time and not evening_check_in:
                        entry_sa = geo.entry_time + saudi_tz
                        if entry_sa.hour >= 12:
                            evening_check_in = entry_sa

                    # استخراج أخر خروج صباحي من الدائرة
                    if geo.exit_time:
                        exit_sa = geo.exit_time + saudi_tz
                        if exit_sa.hour < 12:
                            morning_check_out = exit_sa

                    # استخراج أخر خروج مسائي من الدائرة
                    if geo.exit_time:
                        exit_sa = geo.exit_time + saudi_tz
                        if exit_sa.hour >= 12:
                            evening_check_out = exit_sa

                # جلب آخر جلسة للحصول على البيانات الأساسية
                latest_geo = geo_sessions[-1]

                # جلب آخر موقع للموظف
                emp_location = db.session.query(EmployeeLocation).filter(
                    EmployeeLocation.employee_id == emp.id,
                    EmployeeLocation.recorded_at >= datetime.combine(start_date, time(0, 0, 0)),
                    EmployeeLocation.recorded_at <= datetime.combine(end_date, time(23, 59, 59))
                ).order_by(EmployeeLocation.recorded_at.desc()).first()

                duration_minutes = latest_geo.duration_minutes if latest_geo.duration_minutes else 0

                # تحويل الأوقات إلى توقيت السعودية
                entry_time_sa = (latest_geo.entry_time + saudi_tz) if latest_geo.entry_time else None
                exit_time_sa = (latest_geo.exit_time + saudi_tz) if latest_geo.exit_time else None

                data.append({
                    'اسم الموظف': emp.name,
                    'رقم الموظف': emp.employee_id,
                    'رقم الهوية': emp.national_id,
                    'رقم الجوال': emp.mobile,
                    'الوظيفة': emp.job_title,
                    'حالة الحضور': 'حضور من الدائرة' if geo_sessions else 'لم يتم التسجيل',
                    'دخول الدائرة': format_time_12h_ar(entry_time_sa) if entry_time_sa else '-',
                    'خروج الدائرة': format_time_12h_ar(exit_time_sa) if exit_time_sa else '-',
                    'المدة بالدقائق': duration_minutes,
                    'المدة (ساعات ودقائق)': f'{duration_minutes // 60}س {duration_minutes % 60}د' if duration_minutes > 0 else '-',
                    'دخول صباحي': format_time_12h_ar_short(morning_check_in) if morning_check_in else '-',
                    'خروج صباحي': format_time_12h_ar_short(morning_check_out) if morning_check_out else '-',
                    'دخول مسائي': format_time_12h_ar_short(evening_check_in) if evening_check_in else '-',
                    'خروج مسائي': format_time_12h_ar_short(evening_check_out) if evening_check_out else '-',
                    'GPS - Latitude': emp_location.latitude if emp_location else '-',
                    'GPS - Longitude': emp_location.longitude if emp_location else '-',
                })

        if not data:
            flash('لا توجد بيانات للتصدير', 'warning')
            return redirect(url_for('attendance.circle_accessed_details', department_id=department_id, circle_name=circle_name, date=date_str))

        # إنشاء DataFrame
        df = pd.DataFrame(data)

        # إنشاء ملف Excel في الذاكرة
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='البيانات', index=False, startrow=0)

            # تنسيق الـ worksheet
            worksheet = writer.sheets['البيانات']
            worksheet.sheet_properties.orientation = 'rtl'

            # تعديل عرض الأعمدة
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # اسم الملف
        if export_type == 'single' and employee_id_filter:
            emp = next((e for e in active_employees if e.employee_id == str(employee_id_filter)), None)
            filename = f'تفاصيل_الموظف_{emp.name if emp else "unknown"}_{selected_date.strftime("%Y-%m-%d")}.xlsx'
        else:
            filename = f'تفاصيل_الدائرة_{circle_name}_{selected_date.strftime("%Y-%m-%d")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    @attendance_bp.route('/mark-circle-employees-attendance/<int:department_id>/<circle_name>', methods=['POST'])
    @login_required
    def mark_circle_employees_attendance(department_id, circle_name):
        """تسجيل الموظفين الواصلين للدائرة كحاضرين مع أوقات الدخول والخروج"""
        try:
            date_str = request.args.get('date')
            saudi_tz = timedelta(hours=3)

            try:
                if date_str:
                    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    selected_date = datetime.now().date()
            except ValueError:
                selected_date = datetime.now().date()

            dept = Department.query.get(department_id)
            if not dept:
                return jsonify({'success': False, 'message': 'القسم غير موجود'}), 404

            # جلب الموظفين النشطين في القسم والدائرة المحددة
            active_employees = [emp for emp in dept.employees if emp.status == 'active' and emp.location and emp.location.strip() == circle_name]

            # جلب جميع جلسات الدائرة من التاريخ المختار إلى اليوم
            start_date = selected_date
            end_date = datetime.now().date()

            marked_count = 0

            for emp in active_employees:
                # جلب جميع جلسات الدائرة الجغرافية لهذا الموظف
                geo_sessions = db.session.query(GeofenceSession).filter(
                    GeofenceSession.employee_id == emp.id,
                    GeofenceSession.entry_time >= datetime.combine(start_date, time(0, 0, 0)),
                    GeofenceSession.entry_time <= datetime.combine(end_date, time(23, 59, 59))
                ).order_by(GeofenceSession.entry_time.asc()).all()

                if geo_sessions:
                    # استخراج أول دخول صباحي وآخر خروج مسائي
                    morning_check_in = None
                    evening_check_out = None

                    for geo in geo_sessions:
                        # أول دخول صباحي
                        if geo.entry_time and not morning_check_in:
                            entry_sa = geo.entry_time + saudi_tz
                            if entry_sa.hour < 12:
                                morning_check_in = entry_sa  # احفظ الوقت بعد التحويل للتوقيت السعودي

                        # آخر خروج مسائي
                        if geo.exit_time:
                            exit_sa = geo.exit_time + saudi_tz
                            if exit_sa.hour >= 12:
                                evening_check_out = exit_sa  # احفظ الوقت بعد التحويل للتوقيت السعودي

                    # إذا لم نجد دخول صباحي، نأخذ أول دخول عام + تحويل للتوقيت السعودي
                    if not morning_check_in and geo_sessions:
                        morning_check_in = geo_sessions[0].entry_time + saudi_tz

                    # إذا لم نجد خروج مسائي، نأخذ آخر خروج عام + تحويل للتوقيت السعودي
                    if not evening_check_out and geo_sessions:
                        evening_check_out = geo_sessions[-1].exit_time + saudi_tz

                    # حفظ الأوقات بعد تحويلها للتوقيت السعودي
                    check_in_time = None
                    check_out_time = None

                    if morning_check_in:
                        if isinstance(morning_check_in, datetime):
                            check_in_time = morning_check_in.time()
                        else:
                            check_in_time = morning_check_in

                    if evening_check_out:
                        if isinstance(evening_check_out, datetime):
                            check_out_time = evening_check_out.time()
                        else:
                            check_out_time = evening_check_out

                    # تحديث أو إنشاء سجل الحضور
                    existing_attendance = Attendance.query.filter(
                        Attendance.employee_id == emp.id,
                        Attendance.date == selected_date
                    ).first()

                    if existing_attendance:
                        # تحديث السجل الموجود
                        if check_in_time:
                            existing_attendance.check_in = check_in_time
                        if check_out_time:
                            existing_attendance.check_out = check_out_time
                        existing_attendance.status = 'present'
                        existing_attendance.updated_at = datetime.utcnow()
                    else:
                        # إنشاء سجل حضور جديد
                        attendance = Attendance(
                            employee_id=emp.id,
                            date=selected_date,
                            status='present',
                            check_in=check_in_time,
                            check_out=check_out_time,
                        )
                        db.session.add(attendance)

                    marked_count += 1

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'تم تسجيل {marked_count} موظف كحاضرين مع أوقات الدخول والخروج',
                'count': marked_count
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"خطأ في تسجيل الحضور: {str(e)}")
            return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 500

    return {
        'departments_circles_overview': departments_circles_overview,
        'circle_accessed_details': circle_accessed_details,
        'export_circle_details_excel': export_circle_details_excel,
        'mark_circle_employees_attendance': mark_circle_employees_attendance,
    }
