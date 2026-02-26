"""
Attendance Recording Routes
===========================
Extracted from _attendance_main.py as part of modularization.
Handles all attendance recording operations (individual & bulk).

Routes:
    - GET/POST /record          : Record attendance for individual employees
    - GET/POST /bulk-record     : Bulk record attendance for multiple employees
    - GET/POST /department      : Record attendance for entire department at once
    - GET/POST /all-departments : Record attendance for multiple departments
    - GET/POST /department/bulk : Bulk record attendance for department over period
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from datetime import datetime, time, timedelta
import logging

from src.core.extensions import db
from models import Attendance, Employee, Department
from src.utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from src.services.attendance_engine import AttendanceEngine
from src.utils.audit_logger import log_attendance_activity

logger = logging.getLogger(__name__)

# Create blueprint
record_bp = Blueprint('record', __name__)


@record_bp.route('/record', methods=['GET', 'POST'])
def record():
    """Record attendance for individual employees"""
    if request.method == 'POST':
        try:
            employee_id = request.form['employee_id']
            date_str = request.form['date']
            status = request.form['status']
            notes = request.form.get('notes', '')
            
            # Parse date
            date = parse_date(date_str)
            
            # Process check-in and check-out times if present
            check_in = None
            check_out = None
            if status == 'present':
                check_in_str = request.form.get('check_in', '')
                check_out_str = request.form.get('check_out', '')
                
                if check_in_str:
                    hours, minutes = map(int, check_in_str.split(':'))
                    check_in = time(hours, minutes)
                
                if check_out_str:
                    hours, minutes = map(int, check_out_str.split(':'))
                    check_out = time(hours, minutes)
            
            # Use AttendanceEngine to record attendance
            attendance, is_new, message = AttendanceEngine.record_attendance(
                employee_id=employee_id,
                att_date=date,
                status=status,
                check_in=check_in,
                check_out=check_out,
                notes=notes
            )
            
            if attendance:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            
            return redirect(url_for('attendance.index', date=date_str))
        
        except Exception as e:
            logger.error(f'Error in record() POST: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.record'))
    
    # GET Request - الحصول على الموظفين النشطين حسب صلاحيات المستخدم
    employees = []
    if current_user.is_authenticated:
        try:
            user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            logger.debug(f"Current user: {current_user.name}, Role: {user_role}, Dept: {current_user.assigned_department_id}")
            
            if user_role in ['ADMIN', 'MANAGER', 'SUPERVISOR']:
                # المديرون والمشرفون يمكنهم رؤية جميع الموظفين (استبعاد المنتهية خدمتهم فقط)
                employees = Employee.query.filter(~Employee.status.in_(['terminated', 'inactive'])).order_by(Employee.name).all()
            elif current_user.assigned_department_id:
                # المستخدمون مع قسم مخصص يرون موظفي قسمهم فقط
                dept = Department.query.get(current_user.assigned_department_id)
                if dept:
                    employees = [emp for emp in dept.employees if emp.status not in ['terminated', 'inactive']]
                    employees.sort(key=lambda x: x.name)
            else:
                # كحل بديل، عرض جميع الموظفين للمستخدمين المسجلين (استبعاد المنتهية خدمتهم فقط)
                employees = Employee.query.filter(~Employee.status.in_(['terminated', 'inactive'])).order_by(Employee.name).all()
        except Exception as e:
            logger.error(f"Error determining user permissions: {e}")
            # كحل بديل في حالة الخطأ، عرض جميع الموظفين (استبعاد المنتهية خدمتهم فقط)
            employees = Employee.query.filter(~Employee.status.in_(['terminated', 'inactive'])).order_by(Employee.name).all()
    
    # Default to today's date
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return render_template('attendance/record.html', 
                          employees=employees, 
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@record_bp.route('/department', methods=['GET', 'POST'])
def department_attendance():
    """Record attendance for an entire department at once"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            date_str = request.form['date']
            status = request.form['status']
            
            # التحقق من صلاحيات المستخدم للوصول إلى هذا القسم
            if current_user.is_authenticated and not current_user.can_access_department(int(department_id)):
                flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                return redirect(url_for('attendance.department_attendance'))
            
            # Parse date
            date = parse_date(date_str)
            
            # Use AttendanceEngine to bulk record attendance
            count, message = AttendanceEngine.bulk_record_department(
                department_id=department_id,
                att_date=date,
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
    
    # GET - Get departments based on user permissions
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


@record_bp.route('/bulk-record', methods=['GET', 'POST'])
def bulk_record():
    """تسجيل الحضور الجماعي للموظفين بفترات مختلفة"""
    # التحقق من تسجيل الدخول
    if not current_user.is_authenticated:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('auth.login'))
    
    # التحقق من وجود قسم مخصص للمستخدم
    if not current_user.assigned_department_id and current_user.role.value != 'admin':
        flash('يجب تخصيص قسم لك لتتمكن من تسجيل الحضور', 'error')
        return redirect(url_for('attendance.index'))
    
    if request.method == 'POST':
        try:
            period_type = request.form['period_type']
            default_status = request.form['default_status']
            employee_ids = request.form.getlist('employee_ids')
            skip_weekends = 'skip_weekends' in request.form
            overwrite_existing = 'overwrite_existing' in request.form
            
            if not employee_ids:
                flash('يجب اختيار موظف واحد على الأقل', 'error')
                return redirect(url_for('attendance.bulk_record'))
            
            # إعداد معاملات الفترة حسب النوع
            period_params = {}
            
            if period_type == 'daily':
                period_params['single_date'] = parse_date(request.form['single_date'])
                
            elif period_type == 'weekly':
                period_params['week_start'] = parse_date(request.form['week_start'])
                
            elif period_type == 'monthly':
                period_params['month_year'] = request.form['month_year']
                
            elif period_type == 'custom':
                period_params['start_date'] = parse_date(request.form['start_date'])
                period_params['end_date'] = parse_date(request.form['end_date'])
            else:
                flash('نوع الفترة غير معروف', 'danger')
                return redirect(url_for('attendance.bulk_record'))
            
            # استخدام AttendanceEngine للتسجيل الجماعي
            count, message = AttendanceEngine.bulk_record_period(
                employee_ids=employee_ids,
                period_type=period_type,
                default_status=default_status,
                period_params=period_params,
                skip_weekends=skip_weekends,
                overwrite_existing=overwrite_existing
            )
            
            if count > 0:
                flash(f'تم تسجيل {count} سجل حضور بنجاح', 'success')
            else:
                flash(message, 'warning')
            
            return redirect(url_for('attendance.index'))
            
        except Exception as e:
            logger.error(f'Error in bulk_record() POST: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.bulk_record'))
    
    # GET - الحصول على موظفي القسم المخصص للمستخدم
    try:
        if hasattr(current_user, 'role') and current_user.role and current_user.role.value == 'admin':
            # المديرون العامون يمكنهم رؤية جميع الموظفين
            employees = Employee.query.filter_by(status='active').order_by(Employee.name).all()
        elif current_user.assigned_department_id:
            # المستخدمون مع قسم مخصص يرون موظفي قسمهم فقط
            employees = Employee.query.filter_by(
                status='active',
                department_id=current_user.assigned_department_id
            ).order_by(Employee.name).all()
        else:
            # جرب جلب جميع الموظفين النشطين للاختبار
            employees = Employee.query.filter_by(status='active').order_by(Employee.name).all()
    except Exception as e:
        logger.error(f"Error loading employees: {str(e)}")
        employees = []
    
    today = datetime.now().date()
    
    return render_template('attendance/bulk_record.html', 
                         employees=employees,
                         today=today)


@record_bp.route('/all-departments', methods=['GET', 'POST'])
def all_departments_attendance():
    """تسجيل حضور لعدة أقسام لفترة زمنية محددة"""
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    if request.method == 'POST':
        try:
            department_ids = request.form.getlist('department_ids')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            status = request.form.get('status', 'present')
            
            if not department_ids:
                flash('يجب اختيار قسم واحد على الأقل.', 'danger')
                return redirect(url_for('attendance.all_departments_attendance'))
            
            if not start_date_str or not end_date_str:
                flash('يجب تحديد تاريخ البداية والنهاية.', 'danger')
                return redirect(url_for('attendance.all_departments_attendance'))
            
            try:
                start_date = parse_date(start_date_str)
                end_date = parse_date(end_date_str)
                
                if not start_date or not end_date:
                    flash('تاريخ غير صالح، يرجى التحقق من التنسيق.', 'danger')
                    return redirect(url_for('attendance.all_departments_attendance'))
                
                if end_date < start_date:
                    flash('تاريخ النهاية يجب أن يكون بعد تاريخ البداية أو مساوياً له.', 'danger')
                    return redirect(url_for('attendance.all_departments_attendance'))
            except (ValueError, TypeError) as e:
                flash(f'خطأ في تنسيق التاريخ: {str(e)}', 'danger')
                return redirect(url_for('attendance.all_departments_attendance'))
            
            # جمع جميع معرفات الموظفين من الأقسام المختارة
            all_employee_ids = []
            total_departments = 0
            total_employees = 0
            
            for dept_id in department_ids:
                try:
                    department = Department.query.get(int(dept_id))
                    if not department:
                        continue
                    
                    total_departments += 1
                    
                    # حصول على معرفات موظفي القسم
                    employees = Employee.query.filter_by(
                        department_id=int(dept_id),
                        status='active'
                    ).all()
                    
                    employee_ids = [emp.id for emp in employees]
                    all_employee_ids.extend(employee_ids)
                    total_employees += len(employee_ids)
                    
                except Exception as e:
                    logger.error(f"Error processing department {dept_id}: {str(e)}")
                    continue
            
            if not all_employee_ids:
                flash('لا توجد موظفين نشطين في الأقسام المختارة.', 'warning')
                return redirect(url_for('attendance.all_departments_attendance'))
            
            # استخدام AttendanceEngine للتسجيل الجماعي
            period_params = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            count, message = AttendanceEngine.bulk_record_period(
                employee_ids=all_employee_ids,
                period_type='custom',
                default_status=status,
                period_params=period_params,
                skip_weekends=False,
                overwrite_existing=True
            )
            
            if count > 0:
                delta = end_date - start_date
                days_count = delta.days + 1
                flash(f'تم تسجيل الحضور لـ {total_departments} قسم و {total_employees} موظف عن {days_count} يوم بنجاح ({count} سجل)', 'success')
            else:
                flash(message, 'warning')
            
            return redirect(url_for('attendance.index', date=start_date_str))
        
        except Exception as e:
            logger.error(f'Error in all_departments_attendance: {str(e)}', exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.all_departments_attendance'))
    
    # GET - الحصول على جميع الأقسام مع عدد الموظفين النشطين
    try:
        departments = []
        all_dept = Department.query.all()
        for dept in all_dept:
            active_count = Employee.query.filter_by(department_id=dept.id, status='active').count()
            dept.active_employees_count = active_count
            departments.append(dept)
    except Exception as e:
        logger.error(f'Error loading departments: {str(e)}')
        departments = []
        flash(f'خطأ في تحميل الأقسام: {str(e)}', 'warning')
    
    return render_template('attendance/all_departments.html', 
                          departments=departments,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@record_bp.route('/department/bulk', methods=['GET', 'POST'])
def department_bulk_attendance():
    """تسجيل حضور قسم كامل لفترة زمنية محددة"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            start_date_str = request.form['start_date']
            end_date_str = request.form['end_date']
            status = request.form['status']
            skip_weekends = 'skip_weekends' in request.form
            overwrite_existing = 'overwrite_existing' in request.form
            
            # التحقق من صلاحيات المستخدم
            if current_user.is_authenticated and not current_user.can_access_department(int(department_id)):
                flash('ليس لديك صلاحية لتسجيل حضور هذا القسم', 'error')
                return redirect(url_for('attendance.department_bulk_attendance'))
            
            # تحليل التواريخ
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            
            # التحقق من صحة الفترة
            if start_date > end_date:
                flash('تاريخ البداية يجب أن يكون قبل تاريخ النهاية', 'error')
                return redirect(url_for('attendance.department_bulk_attendance'))
            
            # الحد الأقصى للفترة (90 يوم)
            if (end_date - start_date).days > 90:
                flash('الفترة الزمنية لا يمكن أن تتجاوز 90 يوم', 'error')
                return redirect(url_for('attendance.department_bulk_attendance'))
            
            # الحصول على القسم والموظفين
            department = Department.query.get_or_404(department_id)
            employees = [emp for emp in department.employees if emp.status not in ['terminated', 'inactive']]
            
            if not employees:
                flash('لا يوجد موظفين نشطين في هذا القسم', 'warning')
                return redirect(url_for('attendance.department_bulk_attendance'))
            
            # إنشاء قائمة التواريخ
            date_list = []
            current_date = start_date
            while current_date <= end_date:
                # تخطي عطلة نهاية الأسبوع إذا تم تحديد الخيار
                if skip_weekends:
                    # 4 = الجمعة، 5 = السبت في Python (0=الإثنين)
                    if current_date.weekday() in [4, 5]:
                        current_date += timedelta(days=1)
                        continue
                
                date_list.append(current_date)
                current_date += timedelta(days=1)
            
            # حساب الإحصائيات
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            # تسجيل الحضور لكل موظف في كل يوم
            for employee in employees:
                for attendance_date in date_list:
                    # البحث عن سجل موجود
                    existing = Attendance.query.filter_by(
                        employee_id=employee.id,
                        date=attendance_date
                    ).first()
                    
                    if existing:
                        if overwrite_existing:
                            # تحديث السجل الموجود
                            existing.status = status
                            if status != 'present':
                                existing.check_in = None
                                existing.check_out = None
                            updated_count += 1
                        else:
                            # تخطي السجل الموجود
                            skipped_count += 1
                    else:
                        # إنشاء سجل جديد
                        new_attendance = Attendance(
                            employee_id=employee.id,
                            date=attendance_date,
                            status=status
                        )
                        db.session.add(new_attendance)
                        created_count += 1
            
            # حفظ التغييرات
            db.session.commit()
            
            # تسجيل العملية في سجل النشاط
            log_attendance_activity(
                action='bulk_create_period',
                attendance_data={
                    'department_id': department_id,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'status': status,
                    'created': created_count,
                    'updated': updated_count,
                    'skipped': skipped_count
                },
                employee_name=f"جميع موظفي قسم {department.name}"
            )
            
            # رسالة النجاح
            message_parts = []
            if created_count > 0:
                message_parts.append(f'تم إنشاء {created_count} سجل جديد')
            if updated_count > 0:
                message_parts.append(f'تم تحديث {updated_count} سجل')
            if skipped_count > 0:
                message_parts.append(f'تم تخطي {skipped_count} سجل موجود')
            
            flash(' | '.join(message_parts), 'success')
            return redirect(url_for('attendance.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk department attendance: {str(e)}", exc_info=True)
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.department_bulk_attendance'))
    
    # GET request
    if current_user.is_authenticated:
        departments = current_user.get_accessible_departments()
    else:
        departments = Department.query.all()
    
    return render_template('attendance/department_bulk.html', departments=departments)
