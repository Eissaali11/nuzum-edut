# -*- coding: utf-8 -*-
"""
إحصائيات وتحليلات الحضور
Attendance statistics and analytics

ملاحظة:
- هذا الملف يحتوي على تعريفات المسارات فقط.
- لا يتم تسجيل المسارات إلا عند استدعاء register_statistics_routes().
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta
from src.core.extensions import db
from models import Attendance, Employee, Department
from src.utils.date_converter import parse_date
import logging

logger = logging.getLogger(__name__)


def register_statistics_routes(attendance_bp):
    """Register attendance statistics routes on the provided blueprint."""

    @attendance_bp.route('/stats')
    def stats():
        """Get attendance statistics for a date range"""
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        department_id = request.args.get('department_id', '')

        try:
            start_date = parse_date(start_date_str) if start_date_str else datetime.now().date().replace(day=1)
            end_date = parse_date(end_date_str) if end_date_str else datetime.now().date()
        except ValueError:
            start_date = datetime.now().date().replace(day=1)
            end_date = datetime.now().date()

        query = db.session.query(
            Attendance.status,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )

        if department_id and department_id != '':
            query = query.join(Employee).filter(Employee.department_id == department_id)

        stats_rows = query.group_by(Attendance.status).all()

        # Convert to a dict for easier consumption by charts
        result = {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0}
        for status, count in stats_rows:
            result[status] = count

        return jsonify(result)

    @attendance_bp.route('/department-stats')
    def department_stats():
        """API لجلب إحصائيات الحضور حسب الأقسام"""
        period = request.args.get('period', 'monthly')  # weekly أو monthly
        project_name = request.args.get('project', None)

        today = datetime.now().date()

        # تحديد الفترة الزمنية - استخدام البيانات الشهرية الحقيقية
        start_date = today.replace(day=1)  # بداية الشهر الحالي
        end_date = today  # حتى اليوم الحالي

        # جلب الأقسام المسموح بالوصول إليها حسب صلاحيات المستخدم
        from flask_login import current_user

        if current_user.is_authenticated:
            # إذا كان المستخدم مسجل دخوله، عرض الأقسام المسموحة فقط
            departments = current_user.get_accessible_departments()
        else:
            # إذا لم يكن مسجل دخوله، عرض جميع الأقسام (للعرض العام)
            departments = Department.query.all()

        department_stats_rows = []

        for dept in departments:
            # جلب الموظفين في القسم - استخدام علاقة many-to-many (استبعاد المنتهية خدمتهم فقط)
            employees = [emp for emp in dept.employees if emp.status not in ['terminated', 'inactive']]

            # فلترة حسب المشروع إذا تم تحديده
            if project_name:
                employees = [emp for emp in employees if emp.project == project_name]

            total_employees = len(employees)

            # حساب الإحصائيات
            employee_ids = [emp.id for emp in employees]

            # جلب سجلات الحضور للفترة المحددة
            attendance_records = []
            if employee_ids:
                attendance_records = Attendance.query.filter(
                    Attendance.employee_id.in_(employee_ids),
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                ).all()

            # حساب الإحصائيات
            present_count = sum(1 for record in attendance_records if record.status == 'present')
            absent_count = sum(1 for record in attendance_records if record.status == 'absent')
            leave_count = sum(1 for record in attendance_records if record.status == 'leave')
            sick_count = sum(1 for record in attendance_records if record.status == 'sick')
            total_records = len(attendance_records)

            # حساب الأيام والسجلات المتوقعة
            working_days = (end_date - start_date).days + 1
            expected_total_records = total_employees * working_days

            # للفترة الشهرية، نحسب أيام العمل الفعلية (عدا الجمع والسبوت)
            if period == 'monthly':
                working_days_actual = 0
                current = start_date
                while current <= end_date:
                    # حساب أيام العمل (الأحد-الخميس في النظام السعودي)
                    if current.weekday() < 5:  # 0-4 (الاثنين-الجمعة) نحسبها أيام عمل
                        working_days_actual += 1
                    current += timedelta(days=1)
                working_days = working_days_actual

            # حساب معدل الحضور بناء على السجلات الفعلية الموجودة
            if total_records > 0:
                attendance_rate = (present_count / total_records) * 100
            else:
                attendance_rate = 0

            department_stats_rows.append({
                'id': dept.id,
                'name': dept.name,
                'total_employees': total_employees,
                'present': present_count,
                'absent': absent_count,
                'leave': leave_count,
                'sick': sick_count,
                'attendance_rate': round(attendance_rate, 1),
                'total_records': total_records,
                'working_days': working_days,
                'expected_records': expected_total_records
            })

        # ترتيب الأقسام حسب معدل الحضور (تنازلي)
        department_stats_rows.sort(key=lambda x: x['attendance_rate'], reverse=True)

        return jsonify({
            'departments': department_stats_rows,
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'project': project_name
        })

    @attendance_bp.route('/department-details')
    def department_details():
        """صفحة تفاصيل الحضور لقسم معين"""
        department_name = request.args.get('department')
        period = request.args.get('period', 'weekly')
        project_name = request.args.get('project', None)

        if not department_name:
            flash('يجب تحديد القسم', 'error')
            return redirect(url_for('attendance.dashboard'))

        # جلب القسم
        department = Department.query.filter_by(name=department_name).first()
        if not department:
            flash('القسم غير موجود', 'error')
            return redirect(url_for('attendance.dashboard'))

        today = datetime.now().date()

        # تحديد الفترة الزمنية - دائماً عرض الشهر الكامل للتفاصيل
        start_date = today.replace(day=1)  # بداية الشهر الحالي
        end_date = today  # حتى اليوم الحالي

        # إنشاء قائمة بجميع أيام الشهر حتى اليوم
        date_range = []
        current = start_date
        while current <= end_date:
            date_range.append(current)
            current += timedelta(days=1)

        # جلب الموظفين النشطين في القسم
        employees_query = Employee.query.filter_by(
            department_id=department.id,
            status='active'
        )

        if project_name and project_name != 'None' and project_name.strip():
            employees_query = employees_query.filter_by(project=project_name)

        employees = employees_query.all()

        # تسجيل عدد الموظفين للتشخيص
        print(f"تفاصيل القسم - عدد الموظفين المجلوبين: {len(employees)} للقسم {department.name}")
        for emp in employees:
            print(f"  - {emp.name} (ID: {emp.id})")

        # جلب سجلات الحضور للموظفين في الفترة المحددة
        employee_attendance = {}
        for employee in employees:
            attendance_records = Attendance.query.filter(
                Attendance.employee_id == employee.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).order_by(Attendance.date).all()

            employee_attendance[employee.id] = {
                'employee': employee,
                'records': attendance_records,
                'stats': {
                    'present': sum(1 for r in attendance_records if r.status == 'present'),
                    'absent': sum(1 for r in attendance_records if r.status == 'absent'),
                    'leave': sum(1 for r in attendance_records if r.status == 'leave'),
                    'sick': sum(1 for r in attendance_records if r.status == 'sick')
                }
            }

        # حساب الإحصائيات الإجمالية للقسم
        total_stats = {
            'total_employees': len(employees),
            'present': 0,
            'absent': 0,
            'leave': 0,
            'sick': 0,
            'total_records': 0,
            'working_days': len(date_range),
            'attendance_rate': 0
        }

        for emp_data in employee_attendance.values():
            total_stats['present'] += emp_data['stats']['present']
            total_stats['absent'] += emp_data['stats']['absent']
            total_stats['leave'] += emp_data['stats']['leave']
            total_stats['sick'] += emp_data['stats']['sick']
            total_stats['total_records'] += len(emp_data['records'])

        # حساب معدل الحضور
        if total_stats['total_records'] > 0:
            total_stats['attendance_rate'] = round((total_stats['present'] / total_stats['total_records']) * 100, 1)

        # حساب الإحصائيات اليومية للقسم
        daily_stats = {}
        for day_date in date_range:
            daily_count = {
                'present': 0,
                'absent': 0,
                'leave': 0,
                'sick': 0,
                'total': 0
            }

            for emp_data in employee_attendance.values():
                for record in emp_data['records']:
                    if record.date == day_date:
                        daily_count[record.status] += 1
                        daily_count['total'] += 1
                        break

            daily_stats[day_date] = daily_count

        # إحصائيات أسبوعية
        weekly_stats = []
        week_start = start_date
        while week_start <= end_date:
            week_end = min(week_start + timedelta(days=6), end_date)

            week_data = {
                'start_date': week_start,
                'end_date': week_end,
                'present': 0,
                'absent': 0,
                'leave': 0,
                'sick': 0
            }

            current = week_start
            while current <= week_end:
                if current in daily_stats:
                    week_data['present'] += daily_stats[current]['present']
                    week_data['absent'] += daily_stats[current]['absent']
                    week_data['leave'] += daily_stats[current]['leave']
                    week_data['sick'] += daily_stats[current]['sick']
                current += timedelta(days=1)

            weekly_stats.append(week_data)
            week_start += timedelta(days=7)

        return render_template('attendance/department_details_enhanced.html',
                              department=department,
                              employee_attendance=employee_attendance,
                              date_range=date_range,
                              daily_stats=daily_stats,
                              weekly_stats=weekly_stats,
                              total_stats=total_stats,
                              period='monthly',  # دائماً عرض شهري
                              start_date=start_date,
                              end_date=end_date,
                              project_name=project_name)

    return {
        'stats': stats,
        'department_stats': department_stats,
        'department_details': department_details,
    }
