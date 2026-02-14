# -*- coding: utf-8 -*-
"""Extract route handlers from routes/vehicles.py into vehicle_extra_routes.py."""
import os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
vehicles_path = os.path.join(base, 'routes', 'vehicles.py')
out_path = os.path.join(base, 'presentation', 'web', 'vehicles', 'vehicle_extra_routes.py')

with open(vehicles_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

block = lines[83:2177]
content = ''.join(block).replace('@vehicles_bp.route', '@bp.route')

header = r'''"""
مسارات إضافية للمركبات — تُسجّل على الـ blueprint عبر register_vehicle_extra_routes(bp).
"""
from datetime import datetime, timedelta, date
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, make_response, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_, case
import os
import io

from core.extensions import db
from utils.id_encoder import decode_vehicle_id
from models import (
    Vehicle, VehicleRental, VehicleWorkshop, VehicleWorkshopImage,
    VehicleProject, VehicleHandover, VehicleHandoverImage,
    VehiclePeriodicInspection, VehicleSafetyCheck, Employee,
    Department, ExternalAuthorization, Module, Permission, UserRole,
    VehicleExternalSafetyCheck,
)
from utils.vehicle_route_helpers import format_date_arabic, save_image, check_vehicle_operation_restrictions
from application.vehicles.vehicle_service import (
    INSPECTION_TYPE_CHOICES, INSPECTION_STATUS_CHOICES,
    SAFETY_CHECK_TYPE_CHOICES, SAFETY_CHECK_STATUS_CHOICES,
    update_vehicle_driver, update_all_vehicle_drivers, get_vehicle_current_employee_id,
)
from utils.vehicle_helpers import log_audit, allowed_file
from forms.vehicle_forms import VehicleDocumentsForm
from modules.vehicles.application.vehicle_document_service import get_view_documents_context, get_valid_documents_context
from modules.vehicles.application.vehicle_export_service import (
    build_vehicle_report_pdf, build_vehicle_report_excel, process_import_vehicles,
)


def register_vehicle_extra_routes(bp):
'''

indented = []
for line in content.splitlines():
    indented.append('    ' + line if line.strip() else '')
body = '\n'.join(indented)

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as out:
    out.write(header + body + '\n')
print('Wrote', out_path, 'Total lines:', len(header.splitlines()) + len(body.splitlines()))
