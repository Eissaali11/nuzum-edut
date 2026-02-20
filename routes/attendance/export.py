# -*- coding: utf-8 -*-
"""
تصدير بيانات الحضور
Export attendance data to various formats

الدوال:
- export_excel: تصدير إلى Excel
- export_page: صفحة التصدير
- export_department_data: تصدير بيانات قسم
- export_department_period: تصدير فترة قسمية
"""

from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from datetime import datetime
from models import Department
import logging

logger = logging.getLogger(__name__)

# Blueprint will be set in __init__.py
attendance_bp = None


@login_required
def export_excel():
    """Export attendance data to Excel"""
    return redirect(url_for('attendance.export_page'))


@login_required
def export_page():
    """Display export page"""
    departments = Department.query.all()
    today = datetime.now().date()
    return render_template('attendance/export.html', departments=departments, today=today)


@login_required
def export_department_data():
    """Export department attendance data"""
    return redirect(url_for('attendance.export_page'))


@login_required
def export_department_period():
    """Export department attendance for a period"""
    return redirect(url_for('attendance.export_page'))
