# -*- coding: utf-8 -*-
"""
عمليات CRUD لسجلات الحضور
CRUD operations for attendance records

ملاحظة:
- هذا الملف يحتوي على تعريفات المسارات فقط.
- لا يتم تسجيل المسارات إلا عند استدعاء register_crud_routes().
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from core.extensions import db
from models import Attendance, Employee, SystemAudit
from utils.audit_logger import log_attendance_activity
import logging

logger = logging.getLogger(__name__)


def register_crud_routes(attendance_bp):
    """Register attendance CRUD routes on the provided blueprint."""

    @attendance_bp.route('/delete/<int:id>/confirm', methods=['GET'])
    def confirm_delete_attendance(id):
        """عرض صفحة تأكيد حذف سجل الحضور"""
        attendance = Attendance.query.get_or_404(id)
        return render_template('attendance/confirm_delete.html', attendance=attendance)

    @attendance_bp.route('/delete/<int:id>', methods=['POST'])
    def delete_attendance(id):
        """Delete an attendance record"""
        attendance = Attendance.query.get_or_404(id)

        try:
            # Get associated employee
            employee = Employee.query.get(attendance.employee_id)

            # Delete attendance record
            db.session.delete(attendance)

            # Log the action
            entity_name = employee.name if employee else f'ID: {id}'
            SystemAudit.create_audit_record(
                user_id=None,  # يمكن تعديلها لاستخدام current_user.id
                action='delete',
                entity_type='attendance',
                entity_id=id,
                entity_name=entity_name,
                details=f'تم حذف سجل حضور للموظف: {employee.name if employee else "غير معروف"} بتاريخ {attendance.date}'
            )
            db.session.commit()

            flash('تم حذف سجل الحضور بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('attendance.index', date=attendance.date))

    @attendance_bp.route('/bulk_delete', methods=['POST'])
    def bulk_delete_attendance():
        """حذف سجلات حضور متعددة"""
        try:
            data = request.json
            attendance_ids = data.get('attendance_ids', [])

            if not attendance_ids:
                return jsonify({
                    'success': False,
                    'message': 'لا توجد سجلات محددة للحذف'
                }), 400

            deleted_count = 0
            errors = []

            for attendance_id in attendance_ids:
                try:
                    attendance = Attendance.query.get(attendance_id)
                    if attendance:
                        employee = Employee.query.get(attendance.employee_id)
                        entity_name = employee.name if employee else f'ID: {attendance_id}'

                        # حذف السجل
                        db.session.delete(attendance)

                        # تسجيل في Audit
                        SystemAudit.create_audit_record(
                            user_id=None,
                            action='delete',
                            entity_type='attendance',
                            entity_id=attendance_id,
                            entity_name=entity_name,
                            details=f'حذف جماعي - تم حذف سجل حضور للموظف: {employee.name if employee else "غير معروف"} بتاريخ {attendance.date}'
                        )

                        deleted_count += 1
                    else:
                        errors.append(f'السجل {attendance_id} غير موجود')

                except Exception as e:
                    errors.append(f'خطأ في حذف السجل {attendance_id}: {str(e)}')

            db.session.commit()

            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'errors': errors
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            }), 500

    @attendance_bp.route('/edit/<int:id>', methods=['GET'])
    def edit_attendance_page(id):
        """عرض صفحة تعديل سجل الحضور"""
        from flask_login import current_user

        # الحصول على سجل الحضور
        attendance = Attendance.query.get_or_404(id)

        # التحقق من صلاحيات المستخدم
        if current_user.is_authenticated:
            employee_departments = [dept.id for dept in attendance.employee.departments]
            if employee_departments and not any(current_user.can_access_department(dept_id) for dept_id in employee_departments):
                flash('ليس لديك صلاحية لتعديل هذا السجل', 'error')
                return redirect(url_for('attendance.department_attendance_view'))

        return render_template('attendance/edit_attendance.html', attendance=attendance)

    @attendance_bp.route('/edit/<int:id>', methods=['POST'])
    def update_attendance_page(id):
        """تحديث سجل حضور موجود من صفحة التعديل"""
        from flask_login import current_user
        from datetime import time as dt_time

        try:
            # الحصول على سجل الحضور
            attendance = Attendance.query.get_or_404(id)

            # التحقق من صلاحيات المستخدم
            if current_user.is_authenticated:
                employee_departments = [dept.id for dept in attendance.employee.departments]
                if employee_departments and not any(current_user.can_access_department(dept_id) for dept_id in employee_departments):
                    flash('ليس لديك صلاحية لتعديل هذا السجل', 'error')
                    return redirect(url_for('attendance.department_attendance_view'))

            # الحصول على البيانات
            status = request.form.get('status')
            check_in_str = request.form.get('check_in', '')
            check_out_str = request.form.get('check_out', '')
            notes = request.form.get('notes', '')

            # تحديث الحالة
            old_status = attendance.status
            attendance.status = status
            attendance.notes = notes if notes else None

            # معالجة رفع ملف الإجازة المرضية
            if status == 'sick' and 'sick_leave_file' in request.files:
                file = request.files['sick_leave_file']
                if file and file.filename:
                    from utils.storage_helper import upload_image
                    from werkzeug.utils import secure_filename

                    # 💾 لا حذف للملفات القديمة - الاحتفاظ بجميع الملفات للأمان
                    # حفظ الملف الجديد
                    filename = secure_filename(file.filename)
                    file_path = upload_image(file, 'sick_leaves', filename)
                    if file_path:
                        # إزالة "static/" من البداية لأن url_for('static') سيضيفها تلقائياً
                        if file_path.startswith('static/'):
                            file_path = file_path[7:]  # إزالة "static/"
                        attendance.sick_leave_file = file_path
            elif status != 'sick':
                # إذا تم تغيير الحالة من مرضي إلى حالة أخرى، نزيل المرجع من قاعدة البيانات
                # 💾 لا حذف للملفات الفعلية - الاحتفاظ بجميع الملفات للأمان
                if attendance.sick_leave_file:
                    attendance.sick_leave_file = None

            # معالجة أوقات الدخول والخروج
            if status == 'present':
                if check_in_str:
                    try:
                        hours, minutes = map(int, check_in_str.split(':'))
                        attendance.check_in = dt_time(hours, minutes)
                    except Exception:
                        attendance.check_in = None

                if check_out_str:
                    try:
                        hours, minutes = map(int, check_out_str.split(':'))
                        attendance.check_out = dt_time(hours, minutes)
                    except Exception:
                        attendance.check_out = None
            else:
                # إذا لم تكن الحالة حاضر، نحذف أوقات الدخول والخروج
                attendance.check_in = None
                attendance.check_out = None

            # حفظ التغييرات
            db.session.commit()

            # تسجيل العملية في سجل النشاط
            log_attendance_activity(
                action='update',
                attendance_data={
                    'id': attendance.id,
                    'employee_id': attendance.employee_id,
                    'date': attendance.date.isoformat(),
                    'old_status': old_status,
                    'new_status': status
                },
                employee_name=attendance.employee.name
            )

            flash('تم تحديث سجل الحضور بنجاح', 'success')

            # العودة لصفحة العرض مع المعاملات
            department_id = request.args.get('department_id', '')
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')

            return redirect(url_for('attendance.department_attendance_view',
                                   department_id=department_id,
                                   start_date=start_date,
                                   end_date=end_date))

        except Exception as e:
            db.session.rollback()
            print(f"خطأ في تحديث سجل الحضور: {str(e)}")
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('attendance.edit_attendance_page', id=id))

    return {
        'confirm_delete_attendance': confirm_delete_attendance,
        'delete_attendance': delete_attendance,
        'bulk_delete_attendance': bulk_delete_attendance,
        'edit_attendance_page': edit_attendance_page,
        'update_attendance_page': update_attendance_page,
    }
