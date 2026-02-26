"""Shared salaries v1 blueprint/context."""

import pandas as pd
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime
from core.extensions import db
from models import Salary, Employee, Department, SystemAudit, Attendance
from utils.audit_logger import log_activity
from utils.excel import parse_salary_excel, generate_salary_excel, generate_comprehensive_employee_report, generate_employee_salary_simple_excel
# from utils.simple_pdf_generator import create_vehicle_handover_pdf as generate_salary_report_pdf
# from utils.reports import generate_salary_report_pdf
# from utils.salary_pdf_generator import

from utils.ultra_safe_pdf import create_ultra_safe_salary_pdf
from utils.salary_pdf_generator import generate_salary_summary_pdf
from utils.salary_report_pdf import generate_salary_report_pdf

from utils.salary_notification import generate_salary_notification_pdf, generate_batch_salary_notifications
from utils.whatsapp_notification import (
    send_salary_notification_whatsapp, 
    send_salary_deduction_notification_whatsapp,
    send_batch_salary_notifications_whatsapp,
    send_batch_deduction_notifications_whatsapp
)
from utils.salary_calculator import (
    calculate_salary_with_attendance,
    get_attendance_statistics,
    get_attendance_summary_text,
    compute_net_salary,
    calculate_gosi_deduction
)

salaries_bp = Blueprint('salaries', __name__)
