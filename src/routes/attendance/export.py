# -*- coding: utf-8 -*-
"""
مسارات تصدير الحضور
Attendance export routes

ملاحظة:
- هذا الملف يحتوي على تعريفات المسارات فقط.
- لا يتم تسجيل المسارات إلا عند استدعاء register_export_routes().
"""

from flask import render_template, request, redirect, url_for, flash, send_file
from sqlalchemy import or_
from datetime import datetime
from models import Attendance, Employee, Department
from src.utils.date_converter import parse_date, format_date_hijri, format_date_gregorian
from src.utils.excel import export_attendance_by_department
from src.utils.excel_dashboard import export_attendance_by_department_with_dashboard
import logging

logger = logging.getLogger(__name__)


def register_export_routes(attendance_bp):
    """Register attendance export routes on the provided blueprint."""

    @attendance_bp.route('/export/excel', methods=['POST', 'GET'])
    def export_excel():
        """تصدير بيانات الحضور إلى ملف Excel"""
        try:
            # الحصول على البيانات من النموذج حسب طريقة الطلب
            if request.method == 'POST':
                start_date_str = request.form.get('start_date')
                end_date_str = request.form.get('end_date')
                department_id = request.form.get('department_id')
            else:  # GET
                start_date_str = request.args.get('start_date')
                end_date_str = request.args.get('end_date')
                department_id = request.args.get('department_id')

            # التحقق من المدخلات
            if not start_date_str:
                flash('تاريخ البداية مطلوب', 'danger')
                return redirect(url_for('attendance.export_page'))

            # تحليل التواريخ
            try:
                start_date = parse_date(start_date_str)
                if end_date_str:
                    end_date = parse_date(end_date_str)
                else:
                    end_date = datetime.now().date()
            except (ValueError, TypeError):
                flash('تاريخ غير صالح', 'danger')
                return redirect(url_for('attendance.export_page'))

            # التحقق من اختيار القسم
            if department_id and department_id != '':
                # تصدير قسم واحد فقط
                department = Department.query.get(department_id)
                if not department:
                    flash('القسم غير موجود', 'danger')
                    return redirect(url_for('attendance.export_page'))

                # جلب جميع سجلات الحضور للفترة المحددة أولاً
                attendances = Attendance.query.filter(
                    Attendance.date.between(start_date, end_date)
                ).all()

                # جلب معرفات الموظفين الذين لديهم حضور
                employee_ids_with_attendance = set([att.employee_id for att in attendances])

                # جلب الموظفين في القسم (استبعاد المنتهية خدمتهم فقط) + الموظفين المنتهية خدمتهم الذين لديهم حضور
                department_employee_ids = [emp.id for emp in department.employees]
                employees_to_export = Employee.query.filter(
                    Employee.id.in_(department_employee_ids),
                    or_(
                        ~Employee.status.in_(['terminated', 'inactive']),
                        Employee.id.in_(employee_ids_with_attendance)
                    )
                ).all()

                # فلترة سجلات الحضور لموظفي هذا القسم فقط
                attendances = [att for att in attendances if att.employee_id in department_employee_ids]

                excel_file = export_attendance_by_department(employees_to_export, attendances, start_date, end_date)

                if end_date_str:
                    filename = f'سجل الحضور - {department.name} - {start_date_str} إلى {end_date_str}.xlsx'
                else:
                    filename = f'سجل الحضور - {department.name} - {start_date_str}.xlsx'
            else:
                # تصدير جميع الأقسام
                attendances = Attendance.query.filter(
                    Attendance.date.between(start_date, end_date)
                ).all()

                # جلب معرفات الموظفين الذين لديهم حضور
                employee_ids_with_attendance = set([att.employee_id for att in attendances])

                # جلب الموظفين (استبعاد المنتهية خدمتهم فقط) + الموظفين المنتهية خدمتهم الذين لديهم حضور في الفترة
                all_employees = Employee.query.filter(
                    or_(
                        ~Employee.status.in_(['terminated', 'inactive']),
                        Employee.id.in_(employee_ids_with_attendance)
                    )
                ).all()

                excel_file = export_attendance_by_department_with_dashboard(all_employees, attendances, start_date, end_date)

                if end_date_str:
                    filename = f'سجل الحضور - جميع الأقسام - {start_date_str} إلى {end_date_str}.xlsx'
                else:
                    filename = f'سجل الحضور - جميع الأقسام - {start_date_str}.xlsx'

            return send_file(
                excel_file,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            flash(f'حدث خطأ أثناء تصدير البيانات: {str(e)}', 'danger')
            return redirect(url_for('attendance.export_page'))

    @attendance_bp.route('/export')
    def export_page():
        """صفحة تصدير بيانات الحضور إلى ملف Excel"""
        departments = Department.query.all()
        today = datetime.now().date()
        start_of_month = today.replace(day=1)

        hijri_today = format_date_hijri(today)
        gregorian_today = format_date_gregorian(today)

        hijri_start = format_date_hijri(start_of_month)
        gregorian_start = format_date_gregorian(start_of_month)

        return render_template('attendance/export.html',
                              departments=departments,
                              today=today,
                              start_of_month=start_of_month,
                              hijri_today=hijri_today,
                              gregorian_today=gregorian_today,
                              hijri_start=hijri_start,
                              gregorian_start=gregorian_start)

    @attendance_bp.route('/export-excel-dashboard')
    def export_excel_dashboard():
        """تصدير لوحة المعلومات إلى Excel"""
        try:
            from src.services.attendance_reports import AttendanceReportService

            selected_department = request.args.get('department', None)
            selected_project = request.args.get('project', None)

            result = AttendanceReportService.export_dashboard_summary(selected_department, selected_project)

            return send_file(
                result['buffer'],
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename']
            )

        except Exception as e:
            logger.error(f"Export Excel Dashboard Error: {type(e).__name__}: {str(e)}", exc_info=True)
            flash('حدث خطأ أثناء تصدير الملف', 'error')
            return redirect(url_for('attendance.dashboard'))

    @attendance_bp.route('/export-excel-department')
    def export_excel_department():
        """تصدير تفاصيل القسم إلى Excel"""
        logger.info("[EXPORT] export_excel_department route called")
        try:
            department_name = request.args.get('department')
            logger.info(f"[EXPORT] Department requested: {department_name}")
            selected_project = request.args.get('project', None)

            if not department_name:
                logger.warning("[EXPORT] No department provided")
                flash('يجب تحديد القسم', 'error')
                return redirect(url_for('attendance.dashboard'))

            logger.info("[EXPORT] Loading AttendanceReportService")
            from src.services.attendance_reports import AttendanceReportService

            logger.info(f"[EXPORT] Calling export_department_details for: {department_name}")
            result = AttendanceReportService.export_department_details(department_name, selected_project)
            logger.info(f"[EXPORT] Service returned result with filename: {result.get('filename')}")

            logger.info("[EXPORT] Sending file...")
            return send_file(
                result['buffer'],
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename']
            )

        except Exception as e:
            logger.error(f"Export Excel Department Error: {type(e).__name__}: {str(e)}", exc_info=True)
            flash(f'خطأ: {str(e)}', 'error')
            return redirect(url_for('attendance.dashboard'))

    return {
        'export_excel': export_excel,
        'export_page': export_page,
        'export_excel_dashboard': export_excel_dashboard,
        'export_excel_department': export_excel_department,
    }
