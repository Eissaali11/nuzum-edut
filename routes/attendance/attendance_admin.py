# -*- coding: utf-8 -*-
"""
موتاتات إدارة الحضور - Attendance Admin Routes
العمليات الإدارية والجماعية للحضور
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime
from core.extensions import db
from models import Department, Employee
from utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from utils.user_helpers import check_module_access
from utils.decorators import module_access_required
from services.attendance_engine import AttendanceEngine
import logging

logger = logging.getLogger(__name__)

attendance_admin_bp = Blueprint('attendance_admin', __name__, url_prefix='/attendance/admin')


@attendance_admin_bp.route('/department', methods=['GET', 'POST'])
@login_required
@module_access_required('attendance')
def department_attendance():
    """تسجيل الحضور الجماعي لقسم كامل"""
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            date_str = request.form['date']
            status = request.form['status']
            
            # جلب التاريخ
            att_date = parse_date(date_str)
            
            # تسجيل الحضور الجماعي
            count, message = AttendanceEngine.bulk_record_department(
                department_id, att_date, status
            )
            
            if count > 0:
                flash(message, 'success')
                return redirect(url_for('attendance.index', date=date_str))
            else:
                flash(message, 'error')
        
        except Exception as e:
            logger.error(f"Error in department attendance: {str(e)}")
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    # جلب أقسام يمكن للمستخدم الوصول إليها
    from flask_login import current_user
    
    if current_user.is_authenticated:
        departments = current_user.get_accessible_departments()
    else:
        departments = Department.query.all()
    
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return render_template('attendance/admin/department.html', 
                          departments=departments,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@attendance_admin_bp.route('/bulk-record', methods=['GET', 'POST'])
@login_required
@module_access_required('attendance')
def bulk_record():
    """تسجيل الحضور بفترات مختلفة لعدة موظفين"""
    from flask_login import current_user
    
    # التحقق من وجود قسم مخصص
    if not current_user.assigned_department_id and current_user.role.value != 'ADMIN':
        flash('يجب تخصيص قسم لك', 'error')
        return redirect(url_for('attendance.index'))
    
    if request.method == 'POST':
        try:
            department_id = request.form['department_id']
            date_str = request.form['date']
            status = request.form['status']
            
            att_date = parse_date(date_str)
            
            # تسجيل حضور جماعي
            count, message = AttendanceEngine.bulk_record_department(
                department_id, att_date, status
            )
            
            flash(message, 'success' if count > 0 else 'error')
            return redirect(url_for('attendance.index', date=date_str))
        
        except Exception as e:
            logger.error(f"Error in bulk record: {str(e)}")
            flash(f'خطأ: {str(e)}', 'danger')
    
    if current_user.is_authenticated:
        departments = current_user.get_accessible_departments()
    else:
        departments = Department.query.all()
    
    today = datetime.now().date()
    hijri_date = format_date_hijri(today)
    gregorian_date = format_date_gregorian(today)
    
    return render_template('attendance/admin/bulk_record.html',
                          departments=departments,
                          today=today,
                          hijri_date=hijri_date,
                          gregorian_date=gregorian_date)


@attendance_admin_bp.route('/delete/<int:attendance_id>', methods=['POST'])
@login_required
@module_access_required('attendance')
def delete_attendance(attendance_id):
    """حذف سجل حضور"""
    try:
        success, message = AttendanceEngine.delete_attendance(attendance_id)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 404
    
    except Exception as e:
        logger.error(f"Error deleting attendance: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@attendance_admin_bp.route('/stats', methods=['GET'])
@login_required
@module_access_required('attendance')
def attendance_stats():
    """عرض إحصائيات الحضور"""
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        department_id = request.args.get('department_id')
        
        att_date = parse_date(date_str)
        
        # جلب الإحصائيات باستخدام المحرك
        stats = AttendanceEngine.get_attendance_stats(att_date, department_id)
        
        hijri_date = format_date_hijri(att_date)
        gregorian_date = format_date_gregorian(att_date)
        
        from flask_login import current_user
        if current_user.is_authenticated:
            departments = current_user.get_accessible_departments()
        else:
            departments = Department.query.all()
        
        return render_template('attendance/admin/stats.html',
                              stats=stats,
                              date=att_date,
                              hijri_date=hijri_date,
                              gregorian_date=gregorian_date,
                              departments=departments,
                              selected_department=department_id or '')
    
    except Exception as e:
        logger.error(f"Error getting attendance stats: {str(e)}")
        flash(f'خطأ: {str(e)}', 'danger')
        return redirect(url_for('attendance.index'))
