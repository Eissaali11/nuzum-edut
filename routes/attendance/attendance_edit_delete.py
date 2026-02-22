"""
Attendance Edit & Delete Routes
================================
Extracted from _attendance_main.py as part of modularization.
Handles all attendance editing and deletion operations.

Routes:
    - GET  /delete/<id>/confirm : Confirmation page for deletion
    - POST /delete/<id>         : Delete single attendance record
    - POST /bulk_delete         : Delete multiple attendance records (JSON API)
    - GET  /edit/<id>           : Edit page for attendance record
    - POST /edit/<id>           : Update attendance record
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from datetime import time as dt_time
import logging

from core.extensions import db
from models import Attendance, Employee, SystemAudit
from utils.audit_logger import log_attendance_activity

logger = logging.getLogger(__name__)

# Create blueprint
edit_delete_bp = Blueprint('edit_delete', __name__)


@edit_delete_bp.route('/delete/<int:id>/confirm', methods=['GET'])
def confirm_delete_attendance(id):
    """عرض صفحة تأكيد حذف سجل الحضور"""
    attendance = Attendance.query.get_or_404(id)
    return render_template('attendance/confirm_delete.html', attendance=attendance)


@edit_delete_bp.route('/delete/<int:id>', methods=['POST'])
def delete_attendance(id):
    """Delete an attendance record"""
    attendance = Attendance.query.get_or_404(id)
    
    try:
        # Get associated employee
        employee = Employee.query.get(attendance.employee_id)
        
        # Store date for redirect
        attendance_date = attendance.date
        
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
        logger.error(f'Error deleting attendance {id}: {str(e)}', exc_info=True)
        flash(f'حدث خطأ: {str(e)}', 'danger')
        attendance_date = attendance.date
    
    return redirect(url_for('attendance.index', date=attendance_date))


@edit_delete_bp.route('/bulk_delete', methods=['POST'])
def bulk_delete_attendance():
    """حذف سجلات حضور متعددة - JSON API endpoint"""
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
                logger.error(f'Error deleting attendance {attendance_id}: {str(e)}')
                errors.append(f'خطأ في حذف السجل {attendance_id}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Bulk delete error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


@edit_delete_bp.route('/edit/<int:id>', methods=['GET'])
def edit_attendance_page(id):
    """عرض صفحة تعديل سجل الحضور"""
    # الحصول على سجل الحضور
    attendance = Attendance.query.get_or_404(id)
    
    # التحقق من صلاحيات المستخدم
    if current_user.is_authenticated:
        employee_departments = [dept.id for dept in attendance.employee.departments]
        if employee_departments and not any(current_user.can_access_department(dept_id) for dept_id in employee_departments):
            flash('ليس لديك صلاحية لتعديل هذا السجل', 'error')
            return redirect(url_for('attendance.department_attendance_view'))
    
    return render_template('attendance/edit_attendance.html', attendance=attendance)


@edit_delete_bp.route('/edit/<int:id>', methods=['POST'])
def update_attendance_page(id):
    """تحديث سجل حضور موجود من صفحة التعديل"""
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
                except:
                    attendance.check_in = None
            
            if check_out_str:
                try:
                    hours, minutes = map(int, check_out_str.split(':'))
                    attendance.check_out = dt_time(hours, minutes)
                except:
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
        logger.error(f"Error updating attendance {id}: {str(e)}", exc_info=True)
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('attendance.edit_attendance_page', id=id))
