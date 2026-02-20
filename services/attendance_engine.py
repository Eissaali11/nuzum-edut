# -*- coding: utf-8 -*-
"""
محرك الحضور - Attendance Engine
يحتوي على جميع عمليات الحضور الأساسية
Business logic for attendance operations
"""

from datetime import datetime, time, date as date_type, timedelta
from core.extensions import db
from models import Attendance, Employee, Department, employee_departments
from utils.audit_logger import log_attendance_activity
from sqlalchemy import func, and_
import logging

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """محرك الحضور - يتعامل مع جميع عمليات الحضور"""
    
    @staticmethod
    def record_attendance(employee_id, att_date, status, check_in=None, check_out=None, notes='', sick_leave_file=None):
        """
        تسجيل حضور موظف
        
        Args:
            employee_id: معرف الموظف
            att_date: تاريخ الحضور
            status: حالة الحضور (present, absent, leave, sick)
            check_in: وقت دخول الموظف
            check_out: وقت خروج الموظف
            notes: ملاحظات
            sick_leave_file: ملف الإجازة المرضية (إن وجد)
            
        Returns:
            tuple: (attendance_record, is_new, message)
        """
        try:
            employee = Employee.query.get(employee_id)
            if not employee:
                return None, False, 'الموظف غير موجود'
            
            # البحث عن سجل حضور موجود
            existing = Attendance.query.filter_by(
                employee_id=employee_id,
                date=att_date
            ).first()
            
            is_new = existing is None
            
            if existing:
                # تحديث السجل الموجود
                existing.status = status
                existing.notes = notes
                existing.check_in = check_in if status == 'present' else None
                existing.check_out = check_out if status == 'present' else None
                if sick_leave_file:
                    existing.sick_leave_file = sick_leave_file
                
                db.session.commit()
                
                log_attendance_activity(
                    action='update',
                    attendance_data={
                        'id': existing.id,
                        'employee_id': employee_id,
                        'date': att_date.isoformat(),
                        'status': status
                    },
                    employee_name=employee.name or 'Unknown'
                )
                
                return existing, is_new, 'تم تحديث سجل الحضور بنجاح'
            else:
                # إنشاء سجل جديد
                new_attendance = Attendance(
                    employee_id=employee_id,
                    date=att_date,
                    status=status,
                    notes=notes,
                    check_in=check_in if status == 'present' else None,
                    check_out=check_out if status == 'present' else None,
                    sick_leave_file=sick_leave_file
                )
                
                db.session.add(new_attendance)
                db.session.commit()
                
                log_attendance_activity(
                    action='create',
                    attendance_data={
                        'id': new_attendance.id,
                        'employee_id': employee_id,
                        'date': att_date.isoformat(),
                        'status': status
                    },
                    employee_name=employee.name or 'Unknown'
                )
                
                return new_attendance, is_new, 'تم تسجيل الحضور بنجاح'
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording attendance: {str(e)}")
            return None, False, f'خطأ: {str(e)}'
    
    @staticmethod
    def bulk_record_department(department_id, att_date, status):
        """
        تسجيل حضور جماعي لقسم كامل
        
        Args:
            department_id: معرف القسم
            att_date: تاريخ الحضور
            status: حالة الحضور
            
        Returns:
            tuple: (count, message)
        """
        try:
            department = Department.query.get(department_id)
            if not department:
                return 0, 'القسم غير موجود'
            
            employees = [emp for emp in department.employees 
                        if emp.status not in ['terminated', 'inactive']]
            
            count = 0
            for employee in employees:
                existing = Attendance.query.filter_by(
                    employee_id=employee.id,
                    date=att_date
                ).first()
                
                if existing:
                    existing.status = status
                    if status != 'present':
                        existing.check_in = None
                        existing.check_out = None
                else:
                    new_attendance = Attendance(
                        employee_id=employee.id,
                        date=att_date,
                        status=status
                    )
                    db.session.add(new_attendance)
                    count += 1
            
            db.session.commit()
            
            log_attendance_activity(
                action='bulk_create',
                attendance_data={
                    'department_id': department_id,
                    'date': att_date.isoformat(),
                    'status': status,
                    'count': count
                },
                employee_name=f'جميع موظفي قسم {department.name}'
            )
            
            return count, f'تم تسجيل الحضور لـ {count} موظف بنجاح'
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error bulk recording attendance: {str(e)}")
            return 0, f'خطأ: {str(e)}'
    
    @staticmethod
    def get_attendance_stats(att_date, department_id=None):
        """
        الحصول على إحصائيات الحضور لتاريخ معين
        
        Args:
            att_date: التاريخ
            department_id: معرف القسم (اختياري)
            
        Returns:
            dict: قاموس به الإحصائيات
        """
        query = Attendance.query.filter(Attendance.date == att_date)
        
        if department_id:
            query = query.join(Employee).join(employee_departments).filter(
                employee_departments.c.department_id == department_id
            )
        
        total = query.count()
        present = query.filter_by(status='present').count()
        absent = query.filter_by(status='absent').count()
        leave = query.filter_by(status='leave').count()
        sick = query.filter_by(status='sick').count()
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'leave': leave,
            'sick': sick,
            'present_percentage': (present / total * 100) if total > 0 else 0
        }
    
    @staticmethod
    def get_unified_attendance_list(att_date, department_id=None, status_filter=None):
        """
        الحصول على قائمة موحدة للحضور (موظفين مع سجلاتهم)
        
        Args:
            att_date: التاريخ
            department_id: معرف القسم (اختياري)
            status_filter: عامل التصفية على الحالة (اختياري)
            
        Returns:
            list: قائمة موحدة للحضور
        """
        # جلب الموظفين النشطين
        employee_query = Employee.query.filter_by(status='active')
        
        if department_id and department_id != '':
            employee_query = employee_query.join(employee_departments).filter(
                employee_departments.c.department_id == int(department_id)
            )
        
        employees = employee_query.all()
        
        # جلب سجلات الحضور
        attendance_query = Attendance.query.filter(Attendance.date == att_date)
        if department_id and department_id != '':
            attendance_query = attendance_query.join(Employee).join(employee_departments).filter(
                employee_departments.c.department_id == int(department_id)
            )
        
        attendance_map = {att.employee_id: att for att in attendance_query.all()}
        
        # بناء قائمة موحدة
        unified_list = []
        for emp in employees:
            att_record = attendance_map.get(emp.id)
            if att_record:
                record = {
                    'id': att_record.id,
                    'employee': emp,
                    'date': att_date,
                    'status': att_record.status,
                    'check_in': att_record.check_in,
                    'check_out': att_record.check_out,
                    'notes': att_record.notes,
                    'sick_leave_file': att_record.sick_leave_file,
                    'has_record': True
                }
            else:
                record = {
                    'id': None,
                    'employee': emp,
                    'date': att_date,
                    'status': 'absent',
                    'check_in': None,
                    'check_out': None,
                    'notes': None,
                    'sick_leave_file': None,
                    'has_record': False
                }
            
            unified_list.append(record)
        
        # تطبيق عامل التصفية
        if status_filter and status_filter != '':
            unified_list = [rec for rec in unified_list if rec['status'] == status_filter]
        
        return unified_list
    
    @staticmethod
    def delete_attendance(attendance_id):
        """
        حذف سجل حضور
        
        Args:
            attendance_id: معرف السجل
            
        Returns:
            tuple: (success, message)
        """
        try:
            attendance = Attendance.query.get(attendance_id)
            if not attendance:
                return False, 'السجل غير موجود'
            
            employee = attendance.employee
            db.session.delete(attendance)
            db.session.commit()
            
            log_attendance_activity(
                action='delete',
                attendance_data={'id': attendance_id},
                employee_name=employee.name if employee else 'Unknown'
            )
            
            return True, 'تم حذف السجل بنجاح'
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting attendance: {str(e)}")
            return False, f'خطأ: {str(e)}'
    
    @staticmethod
    def get_employee_attendance_range(employee_id, start_date, end_date):
        """
        الحصول على سجلات الحضور لموظف في فترة زمنية
        
        Args:
            employee_id: معرف الموظف
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            
        Returns:
            list: قائمة سجلات الحضور
        """
        return Attendance.query.filter(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            )
        ).order_by(Attendance.date).all()
    
    @staticmethod
    def bulk_record_period(employee_ids, period_type, default_status, period_params, 
                          skip_weekends=False, overwrite_existing=False):
        """
        تسجيل حضور جماعي لفترة زمنية محددة
        
        Args:
            employee_ids: قائمة معرفات الموظفين
            period_type: نوع الفترة (daily, weekly, monthly, custom)
            default_status: حالة الحضور الافتراضية
            period_params: معاملات الفترة (تختلف حسب النوع)
                - daily: {'single_date': date}
                - weekly: {'week_start': date}
                - monthly: {'month_year': 'YYYY-MM'}
                - custom: {'start_date': date, 'end_date': date}
            skip_weekends: هل يتم تجاهل عطلة نهاية الأسبوع
            overwrite_existing: هل يتم استبدال السجلات الموجودة
            
        Returns:
            tuple: (count, message)
        """
        try:
            # تحديد قائمة التواريخ بناءً على نوع الفترة
            dates = []
            
            if period_type == 'daily':
                dates = [period_params['single_date']]
                
            elif period_type == 'weekly':
                week_start = period_params['week_start']
                dates = [week_start + timedelta(days=i) for i in range(7)]
                
            elif period_type == 'monthly':
                month_year = period_params['month_year']
                year, month = map(int, month_year.split('-'))
                import calendar
                days_in_month = calendar.monthrange(year, month)[1]
                dates = [date_type(year, month, day) for day in range(1, days_in_month + 1)]
                
            elif period_type == 'custom':
                start_date = period_params['start_date']
                end_date = period_params['end_date']
                current_date = start_date
                while current_date <= end_date:
                    dates.append(current_date)
                    current_date += timedelta(days=1)
            else:
                return 0, f'نوع الفترة غير معروف: {period_type}'
            
            # تصفية عطلة نهاية الأسبوع إذا كان مطلوباً
            if skip_weekends:
                dates = [d for d in dates if d.weekday() not in [4, 5]]  # الجمعة والسبت
            
            if not dates:
                return 0, 'لا توجد تواريخ صالحة للفترة المحددة'
            
            # التحقق من الموظفين
            if not employee_ids:
                return 0, 'لا يوجد موظفين مختاري'
            
            # تسجيل الحضور
            count = 0
            for employee_id in employee_ids:
                employee = Employee.query.get(employee_id)
                if not employee:
                    continue
                
                for att_date in dates:
                    # التحقق من وجود سجل سابق
                    existing = Attendance.query.filter_by(
                        employee_id=employee_id,
                        date=att_date
                    ).first()
                    
                    if existing:
                        if overwrite_existing:
                            existing.status = default_status
                            if default_status != 'present':
                                existing.check_in = None
                                existing.check_out = None
                            count += 1
                    else:
                        attendance = Attendance(
                            employee_id=employee_id,
                            date=att_date,
                            status=default_status
                        )
                        db.session.add(attendance)
                        count += 1
            
            db.session.commit()
            
            # تسجيل العملية في سجل النشاط
            emp_count = len(employee_ids)
            date_count = len(dates)
            log_attendance_activity(
                action='bulk_record_period',
                attendance_data={
                    'employee_count': emp_count,
                    'date_count': date_count,
                    'period_type': period_type,
                    'status': default_status,
                    'records_count': count
                },
                employee_name=f'{emp_count} موظف × {date_count} يوم'
            )
            
            if count > 0:
                return count, f'تم تسجيل {count} سجل حضور بنجاح'
            else:
                return 0, 'لم يتم إضافة أي سجلات جديدة'
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk_record_period: {str(e)}", exc_info=True)
            return 0, f'خطأ: {str(e)}'
