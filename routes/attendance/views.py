# -*- coding: utf-8 -*-
"""
مسارات عرض الحضور
View routes for attendance dashboard and main pages

ملاحظة:
- هذا الملف يحتوي على تعريفات المسارات فقط.
- لا يتم تسجيل المسارات إلا عند استدعاء register_views_routes().
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func, or_
from datetime import datetime, time, timedelta, date
from core.extensions import db
from models import Attendance, Employee, Department, employee_departments
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from services.attendance_analytics import AttendanceAnalytics
from services.attendance_engine import AttendanceEngine
import calendar
import logging
import time as time_module

logger = logging.getLogger(__name__)


def register_views_routes(attendance_bp):
    """Register attendance view routes on the provided blueprint."""

    @attendance_bp.route('/')
    def index():
        """List attendance records with filtering options - shows all employees

        CHUNK #1 REFACTORED:
        - Uses AttendanceEngine.get_unified_attendance_list() instead of 8 direct queries
        - Maintains 100% backward compatibility with templates
        - Improved performance: 8 queries → 2 queries (-75%)
        """
        try:
            from flask_login import current_user

            # Get filter parameters
            date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
            department_id = request.args.get('department_id', '')
            status = request.args.get('status', '')

            # Parse date with fallback
            try:
                date_obj = parse_date(date_str)
            except (ValueError, TypeError):
                date_obj = datetime.now().date()
                logger.warning(f'Invalid date provided: {date_str}, using today')

            # Get departments (with user permission checks)
            if current_user.is_authenticated:
                departments = current_user.get_accessible_departments()
                # Auto-filter to user's assigned department if applicable
                if current_user.assigned_department_id and not department_id:
                    department_id = str(current_user.assigned_department_id)
            else:
                departments = Department.query.all()

            # Single call to AttendanceEngine for all attendance data
            unified_attendances = AttendanceEngine.get_unified_attendance_list(
                att_date=date_obj,
                department_id=int(department_id) if department_id else None,
                status_filter=status if status else None
            )

            # Calculate statistics from unified list
            present_count = sum(1 for rec in unified_attendances if rec['status'] == 'present')
            absent_count = sum(1 for rec in unified_attendances if rec['status'] == 'absent')
            leave_count = sum(1 for rec in unified_attendances if rec['status'] == 'leave')
            sick_count = sum(1 for rec in unified_attendances if rec['status'] == 'sick')

            # Format dates for display
            hijri_date = format_date_hijri(date_obj)
            gregorian_date = format_date_gregorian(date_obj)

            logger.info(f'Index: Loaded {len(unified_attendances)} records for {date_obj.isoformat()}')

            # Render with identical template signature for 100% compatibility
            return render_template('attendance/index.html',
                                  attendances=unified_attendances,
                                  departments=departments,
                                  date=date_obj,
                                  hijri_date=hijri_date,
                                  gregorian_date=gregorian_date,
                                  selected_department=department_id,
                                  selected_status=status,
                                  present_count=present_count,
                                  absent_count=absent_count,
                                  leave_count=leave_count,
                                  sick_count=sick_count)

        except Exception as e:
            logger.error(f'Critical error in index(): {str(e)}', exc_info=True)
            flash('حدث خطأ في تحميل البيانات. الرجاء المحاولة مرة أخرى.', 'danger')
            return render_template('error.html', error_title='خطأ في النظام', error_message='فشل تحميل بيانات الحضور'), 500

    @attendance_bp.route('/department', methods=['GET', 'POST'])
    def department_attendance():
        """Record attendance for an entire department at once"""
        if request.method == 'POST':
            try:
                department_id = request.form['department_id']
                date_str = request.form['date']
                status = request.form['status']

                # التحقق من صلاحيات المستخدم للوصول إلى هذا القسم
                from flask_login import current_user

                if current_user.is_authenticated and not current_user.can_access_department(int(department_id)):
                    flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                    return redirect(url_for('attendance.department_attendance'))

                # Parse date
                date_obj = parse_date(date_str)

                # Use AttendanceEngine to bulk record attendance
                count, message = AttendanceEngine.bulk_record_department(
                    department_id=department_id,
                    att_date=date_obj,
                    status=status
                )

                if count > 0:
                    flash(f'تم تسجيل الحضور لـ {count} موظف بنجاح', 'success')
                else:
                    flash(message, 'danger')

                return redirect(url_for('attendance.index', date=date_str))

            except Exception as e:
                logger.error(f'Error in department_attendance() POST: {str(e)}', exc_info=True)
                flash(f'حدث خطأ: {str(e)}', 'danger')
                return redirect(url_for('attendance.department_attendance'))

        # Get departments based on user permissions
        from flask_login import current_user

        if current_user.is_authenticated:
            departments = current_user.get_accessible_departments()
        else:
            departments = Department.query.all()

        # Default to today's date
        today = datetime.now().date()
        hijri_date = format_date_hijri(today)
        gregorian_date = format_date_gregorian(today)

        return render_template('attendance/department.html',
                              departments=departments,
                              today=today,
                              hijri_date=hijri_date,
                              gregorian_date=gregorian_date)

    @attendance_bp.route('/api/departments/<int:department_id>/employees')
    def get_department_employees(department_id):
        """API endpoint to get all employees in a department"""
        try:
            # الحصول على القسم أولاً
            department = Department.query.get_or_404(department_id)

            # جلب جميع الموظفين النشطين في هذا القسم باستخدام العلاقة many-to-many
            employees = [emp for emp in department.employees if emp.status == 'active']

            employee_data = []
            for employee in employees:
                employee_data.append({
                    'id': employee.id,
                    'name': employee.name,
                    'employee_id': employee.employee_id,
                    'job_title': employee.job_title or 'غير محدد',
                    'status': employee.status
                })

            logger.info(f"تم جلب {len(employee_data)} موظف نشط من القسم {department_id} ({department.name})")
            return jsonify(employee_data)

        except Exception as e:
            logger.error(f"خطأ في جلب موظفي القسم {department_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @attendance_bp.route('/dashboard')
    def dashboard():
        """لوحة معلومات الحضور مع إحصائيات يومية وأسبوعية وشهرية"""

        # إضافة آلية إعادة المحاولة للتعامل مع أخطاء الاتصال المؤقتة
        max_retries = 3  # عدد محاولات إعادة الاتصال
        retry_count = 0
        retry_delay = 1  # ثانية واحدة للمحاولة الأولى

        while retry_count < max_retries:
            try:
                # إعادة تحميل جميع البيانات من قاعدة البيانات للتأكد من أن البيانات محدثة
                db.session.expire_all()

                # 1. الحصول على المشروع المحدد (إذا وجد)
                project_name = request.args.get('project', None)

                # 2. الحصول على التاريخ الحالي
                today = datetime.now().date()
                current_month = today.month
                current_year = today.year

                # 3. حساب تاريخ بداية ونهاية الأسبوع الحالي بناءً على تاريخ بداية الشهر
                start_of_month = today.replace(day=1)  # أول يوم في الشهر الحالي

                # نحسب عدد الأيام منذ بداية الشهر حتى اليوم الحالي
                days_since_month_start = (today - start_of_month).days

                # نحسب عدد الأسابيع الكاملة منذ بداية الشهر (كل أسبوع 7 أيام)
                weeks_since_month_start = days_since_month_start // 7

                # نحسب بداية الأسبوع الحالي (بناءً على أسابيع من بداية الشهر)
                start_of_week = start_of_month + timedelta(days=weeks_since_month_start * 7)

                # نهاية الأسبوع بعد 6 أيام من البداية
                end_of_week = start_of_week + timedelta(days=6)

                # إذا كانت نهاية الأسبوع بعد نهاية الشهر، نجعلها آخر يوم في الشهر
                last_day = calendar.monthrange(current_year, current_month)[1]
                end_of_month = today.replace(day=last_day)
                if end_of_week > end_of_month:
                    end_of_week = end_of_month

                # 4. حساب تاريخ بداية ونهاية الشهر الحالي
                start_of_month = today.replace(day=1)
                last_day = calendar.monthrange(current_year, current_month)[1]
                end_of_month = today.replace(day=last_day)

                # 5. إنشاء قاعدة الاستعلام
                query_base = db.session.query(
                    Attendance.status,
                    func.count(Attendance.id).label('count')
                )

                # 6. إحصائيات الحضور حسب المشروع أو عامة
                # تعريف قائمة معرفات الموظفين (سيكون None للكل)
                employee_ids = None

                if project_name:
                    # استعلام للموظفين في مشروع محدد
                    # نحتاج للحصول على قائمة الموظفين المرتبطين بالمشروع
                    project_employees = db.session.query(Employee.id).filter(
                        Employee.project == project_name,
                        ~Employee.status.in_(['terminated', 'inactive'])
                    ).all()

                    # تحويل النتائج إلى قائمة بسيطة من المعرفات
                    employee_ids = [emp[0] for emp in project_employees]

                # تعريف ونهيئة متغيرات إحصائية
                daily_stats = []
                weekly_stats = []
                monthly_stats = []

                # إذا كان هناك مشروع محدد ولا يوجد موظفين فيه، نترك الإحصائيات فارغة
                if project_name and not employee_ids:
                    # لا يوجد موظفين في هذا المشروع، نترك الإحصائيات فارغة
                    pass
                else:
                    # بناء استعلامات الإحصائيات إما لجميع الموظفين أو لموظفي مشروع محدد
                    if employee_ids:
                        # إحصائيات الموظفين في المشروع المحدد

                        # إحصائيات اليوم
                        daily_stats = query_base.filter(
                            Attendance.date == today,
                            Attendance.employee_id.in_(employee_ids)
                        ).group_by(Attendance.status).all()

                        # إحصائيات الأسبوع
                        weekly_stats = query_base.filter(
                            Attendance.date >= start_of_week,
                            Attendance.date <= end_of_week,
                            Attendance.employee_id.in_(employee_ids)
                        ).group_by(Attendance.status).all()

                        # إحصائيات الشهر
                        monthly_stats = query_base.filter(
                            Attendance.date >= start_of_month,
                            Attendance.date <= end_of_month,
                            Attendance.employee_id.in_(employee_ids)
                        ).group_by(Attendance.status).all()
                    else:
                        # إحصائيات عامة لجميع الموظفين

                        # إحصائيات اليوم
                        daily_stats = query_base.filter(
                            Attendance.date == today
                        ).group_by(Attendance.status).all()

                        # إحصائيات الأسبوع
                        weekly_stats = query_base.filter(
                            Attendance.date >= start_of_week,
                            Attendance.date <= end_of_week
                        ).group_by(Attendance.status).all()

                        # إحصائيات الشهر
                        monthly_stats = query_base.filter(
                            Attendance.date >= start_of_month,
                            Attendance.date <= end_of_month
                        ).group_by(Attendance.status).all()

                # 7. إحصائيات الحضور اليومي خلال الشهر الحالي لعرضها في المخطط البياني
                daily_attendance_data = []

                for day in range(1, last_day + 1):
                    current_date = date(current_year, current_month, day)

                    # تخطي التواريخ المستقبلية
                    if current_date > today:
                        break

                    # استخدام employee_ids مباشرة بعد التأكد من أنه تم تعريفه في خطوة سابقة
                    if employee_ids:
                        present_count = db.session.query(func.count(Attendance.id)).filter(
                            Attendance.date == current_date,
                            Attendance.status == 'present',
                            Attendance.employee_id.in_(employee_ids)
                        ).scalar() or 0

                        absent_count = db.session.query(func.count(Attendance.id)).filter(
                            Attendance.date == current_date,
                            Attendance.status == 'absent',
                            Attendance.employee_id.in_(employee_ids)
                        ).scalar() or 0
                    else:
                        present_count = db.session.query(func.count(Attendance.id)).filter(
                            Attendance.date == current_date,
                            Attendance.status == 'present'
                        ).scalar() or 0

                        absent_count = db.session.query(func.count(Attendance.id)).filter(
                            Attendance.date == current_date,
                            Attendance.status == 'absent'
                        ).scalar() or 0

                    daily_attendance_data.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'day': str(day),
                        'present': present_count,
                        'absent': absent_count
                    })

                # 8. الحصول على قائمة المشاريع للفلتر (استبعاد المنتهية خدمتهم فقط)
                active_projects = db.session.query(Employee.project).filter(
                    ~Employee.status.in_(['terminated', 'inactive']),
                    Employee.project.isnot(None)
                ).distinct().all()

                active_projects = [project[0] for project in active_projects if project[0]]

                # 9. تحويل البيانات إلى قاموس
                def stats_to_dict(stats_data):
                    result = {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0}
                    for item in stats_data:
                        result[item[0]] = item[1]
                    return result

                daily_stats_dict = stats_to_dict(daily_stats)
                weekly_stats_dict = stats_to_dict(weekly_stats)
                monthly_stats_dict = stats_to_dict(monthly_stats)

                # 10. إعداد البيانات للمخططات البيانية
                # 10.أ. مخطط توزيع الحضور اليومي
                daily_chart_data = {
                    'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                    'datasets': [{
                        'data': [
                            daily_stats_dict['present'],
                            daily_stats_dict['absent'],
                            daily_stats_dict['leave'],
                            daily_stats_dict['sick']
                        ],
                        'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                    }]
                }

                # 10.ب. مخطط توزيع الحضور الأسبوعي
                weekly_chart_data = {
                    'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                    'datasets': [{
                        'data': [
                            weekly_stats_dict['present'],
                            weekly_stats_dict['absent'],
                            weekly_stats_dict['leave'],
                            weekly_stats_dict['sick']
                        ],
                        'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                    }]
                }

                # 10.ج. مخطط توزيع الحضور الشهري
                monthly_chart_data = {
                    'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
                    'datasets': [{
                        'data': [
                            monthly_stats_dict['present'],
                            monthly_stats_dict['absent'],
                            monthly_stats_dict['leave'],
                            monthly_stats_dict['sick']
                        ],
                        'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                    }]
                }

                # 10.د. مخطط الحضور اليومي خلال الشهر
                daily_trend_chart_data = {
                    'labels': [item['day'] for item in daily_attendance_data],
                    'datasets': [
                        {
                            'label': 'الحضور',
                            'data': [item['present'] for item in daily_attendance_data],
                            'backgroundColor': 'rgba(40, 167, 69, 0.2)',
                            'borderColor': 'rgba(40, 167, 69, 1)',
                            'borderWidth': 1,
                            'tension': 0.4
                        },
                        {
                            'label': 'الغياب',
                            'data': [item['absent'] for item in daily_attendance_data],
                            'backgroundColor': 'rgba(220, 53, 69, 0.2)',
                            'borderColor': 'rgba(220, 53, 69, 1)',
                            'borderWidth': 1,
                            'tension': 0.4
                        }
                    ]
                }

                # 11. حساب معدل الحضور
                # إجمالي سجلات الحضور اليومية
                total_days = (
                    daily_stats_dict['present'] +
                    daily_stats_dict['absent'] +
                    daily_stats_dict['leave'] +
                    daily_stats_dict['sick']
                )

                # إجمالي سجلات الحضور المتوقعة لليوم (جميع الموظفين النشطين)
                # حساب إجمالي الموظفين النشطين يتم في سطور لاحقة من الكود

                daily_attendance_rate = 0
                if total_days > 0:
                    daily_attendance_rate = round((daily_stats_dict['present'] / total_days) * 100)

                # حساب إجمالي الموظفين - استخدام علاقة many-to-many الصحيحة (استبعاد المنتهية خدمتهم فقط)
                if employee_ids:
                    active_employees_count = len(employee_ids)
                else:
                    # عد الموظفين المرتبطين بأقسام عبر علاقة many-to-many
                    active_employees_count = db.session.query(func.count(func.distinct(Employee.id))).join(
                        employee_departments, Employee.id == employee_departments.c.employee_id
                    ).filter(
                        ~Employee.status.in_(['terminated', 'inactive'])
                    ).scalar() or 0

                # حساب كامل الأسبوع (7 أيام) × عدد الموظفين النشطين
                # حساب عدد الأيام في الأسبوع (من بداية الأسبوع إلى نهايته)
                days_in_week = (end_of_week - start_of_week).days + 1

                # إجمالي سجلات الحضور والغياب في الأسبوع
                total_days_week = (
                    weekly_stats_dict['present'] +
                    weekly_stats_dict['absent'] +
                    weekly_stats_dict['leave'] +
                    weekly_stats_dict['sick']
                )

                # حساب إجمالي سجلات الحضور المفترضة للأسبوع
                expected_days_week = days_in_week * active_employees_count

                weekly_attendance_rate = 0
                if total_days_week > 0:
                    weekly_attendance_rate = round((weekly_stats_dict['present'] / total_days_week) * 100)

                # حساب معدل الحضور الشهري
                # إجمالي سجلات الحضور والغياب في الشهر
                total_days_month = (
                    monthly_stats_dict['present'] +
                    monthly_stats_dict['absent'] +
                    monthly_stats_dict['leave'] +
                    monthly_stats_dict['sick']
                )

                # حساب عدد الأيام في الشهر حتى اليوم الحالي
                days_in_month = (today - start_of_month).days + 1

                # حساب إجمالي سجلات الحضور المفترضة للشهر
                expected_days_month = days_in_month * active_employees_count

                monthly_attendance_rate = 0
                if total_days_month > 0:
                    monthly_attendance_rate = round((monthly_stats_dict['present'] / total_days_month) * 100)

                # 12. تنسيق التواريخ للعرض
                formatted_today = {
                    'gregorian': format_date_gregorian(today),
                    'hijri': format_date_hijri(today)
                }

                formatted_start_of_week = {
                    'gregorian': format_date_gregorian(start_of_week),
                    'hijri': format_date_hijri(start_of_week)
                }

                formatted_end_of_week = {
                    'gregorian': format_date_gregorian(end_of_week),
                    'hijri': format_date_hijri(end_of_week)
                }

                formatted_start_of_month = {
                    'gregorian': format_date_gregorian(start_of_month),
                    'hijri': format_date_hijri(start_of_month)
                }

                formatted_end_of_month = {
                    'gregorian': format_date_gregorian(end_of_month),
                    'hijri': format_date_hijri(end_of_month)
                }

                # 13. إعداد اسم الشهر الحالي
                month_names = [
                    'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
                    'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
                ]
                current_month_name = month_names[current_month - 1]

                # 14. جلب بيانات الغياب التفصيلية بأسماء الموظفين لكل قسم
                daily_summary = AttendanceAnalytics.get_department_summary(
                    start_date=today,
                    end_date=today,
                    project_name=project_name
                )

                monthly_summary = AttendanceAnalytics.get_department_summary(
                    start_date=start_of_month,
                    end_date=end_of_month,
                    project_name=project_name
                )

                # 15. إعداد البيانات للعرض على الصفحة
                return render_template('attendance/dashboard_new.html',
                                    today=today,
                                    current_month=current_month,
                                    current_year=current_year,
                                    current_month_name=current_month_name,
                                    formatted_today=formatted_today,
                                    formatted_start_of_week=formatted_start_of_week,
                                    formatted_end_of_week=formatted_end_of_week,
                                    formatted_start_of_month=formatted_start_of_month,
                                    formatted_end_of_month=formatted_end_of_month,
                                    start_of_week=start_of_week,
                                    end_of_week=end_of_week,
                                    start_of_month=start_of_month,
                                    end_of_month=end_of_month,
                                    daily_stats=daily_stats_dict,
                                    weekly_stats=weekly_stats_dict,
                                    monthly_stats=monthly_stats_dict,
                                    daily_chart_data=daily_chart_data,
                                    weekly_chart_data=weekly_chart_data,
                                    monthly_chart_data=monthly_chart_data,
                                    daily_trend_chart_data=daily_trend_chart_data,
                                    daily_attendance_rate=daily_attendance_rate,
                                    weekly_attendance_rate=weekly_attendance_rate,
                                    monthly_attendance_rate=monthly_attendance_rate,
                                    active_employees_count=active_employees_count,
                                    active_projects=active_projects,
                                    selected_project=project_name,
                                    daily_summary=daily_summary,
                                    monthly_summary=monthly_summary)

                # Si todo funciona bien, sal del bucle
                break

            except Exception as e:
                # Si hay un error, incrementa el contador y espera
                retry_count += 1
                logger.error(f"Error al cargar el dashboard (intento {retry_count}): {str(e)}")

                if retry_count < max_retries:
                    # Espera un tiempo exponencial antes de reintentar
                    time_module.sleep(retry_delay)
                    retry_delay *= 2  # Duplica el tiempo de espera para el próximo intento
                else:
                    # Si se han agotado los reintentos, muestra un mensaje de error
                    logger.critical(f"Error al cargar el dashboard después de {max_retries} intentos: {str(e)}")
                    return render_template('error.html',
                                          error_title="خطأ في الاتصال",
                                          error_message="حدث خطأ أثناء الاتصال بقاعدة البيانات. الرجاء المحاولة مرة أخرى.",
                                          error_details=str(e))

    @attendance_bp.route('/employee/<int:employee_id>')
    def employee_attendance(employee_id):
        """عرض سجلات الحضور التفصيلية للموظف مرتبة حسب الشهر والسنة - Dashboard مميز"""
        # الحصول على الموظف
        employee = Employee.query.get_or_404(employee_id)

        # الحصول على التاريخ الحالي
        today = datetime.now().date()

        # الحصول على السنة والشهر من URL أو استخدام الحالي
        selected_year = request.args.get('year', today.year, type=int)
        selected_month = request.args.get('month', today.month, type=int)

        # تحديد فترة الاستعلام (الشهر المختار)
        year = selected_year
        month = selected_month
        start_of_month = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_of_month = date(year, month, last_day)

        # الحصول على سجلات الحضور للشهر المختار
        attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_of_month,
            Attendance.date <= end_of_month
        ).order_by(Attendance.date).all()

        # تنظيم السجلات حسب اليوم للتقويم
        attendance_by_day = {}
        for record in attendances:
            attendance_by_day[record.date.day] = record

        # حساب الإحصائيات الشاملة
        present_count = sum(1 for a in attendances if a.status == 'present')
        absent_count = sum(1 for a in attendances if a.status == 'absent')
        leave_count = sum(1 for a in attendances if a.status == 'leave')
        sick_count = sum(1 for a in attendances if a.status == 'sick')
        total_records = len(attendances)

        # حساب النسب المئوية
        present_percentage = (present_count / total_records * 100) if total_records > 0 else 0
        absent_percentage = (absent_count / total_records * 100) if total_records > 0 else 0
        leave_percentage = (leave_count / total_records * 100) if total_records > 0 else 0
        sick_percentage = (sick_count / total_records * 100) if total_records > 0 else 0

        # حساب معدل الحضور
        attendance_rate = round(present_percentage, 1) if total_records > 0 else 0

        # جمع كل الفترات المتاحة (السنوات والأشهر التي لديها سجلات)
        all_records = Attendance.query.filter(Attendance.employee_id == employee_id).all()
        attendance_periods = {}
        for record in all_records:
            if record.date.year not in attendance_periods:
                attendance_periods[record.date.year] = set()
            attendance_periods[record.date.year].add(record.date.month)

        # معلومات التقويم
        first_day_weekday = calendar.monthrange(year, month)[0]
        days_in_month = last_day

        # تنسيق التواريخ للعرض
        hijri_today = format_date_hijri(today)
        gregorian_today = format_date_gregorian(today)

        return render_template('attendance/employee_attendance.html',
                              employee=employee,
                              attendances=attendances,
                              attendance_by_day=attendance_by_day,
                              year=year,
                              month=month,
                              selected_year=selected_year,
                              selected_month=selected_month,
                              first_day_weekday=first_day_weekday,
                              days_in_month=days_in_month,
                              attendance_periods=attendance_periods,
                              present_count=present_count,
                              absent_count=absent_count,
                              leave_count=leave_count,
                              sick_count=sick_count,
                              total_records=total_records,
                              present_percentage=present_percentage,
                              absent_percentage=absent_percentage,
                              leave_percentage=leave_percentage,
                              sick_percentage=sick_percentage,
                              attendance_rate=attendance_rate,
                              today=today,
                              hijri_today=hijri_today,
                              gregorian_today=gregorian_today)

    return {
        'index': index,
        'department_attendance': department_attendance,
        'get_department_employees': get_department_employees,
        'dashboard': dashboard,
        'employee_attendance': employee_attendance,
    }
