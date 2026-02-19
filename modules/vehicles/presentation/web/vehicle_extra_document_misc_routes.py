"""Vehicle extra document/import/api utility routes."""

import os
import uuid
from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from core.domain.models import Module, Permission, UserRole
from core.extensions import db
from modules.vehicles.application.vehicle_document_service import get_valid_documents_context
from modules.vehicles.application.vehicle_export_service import process_import_vehicles
from modules.vehicles.domain.models import Vehicle, VehicleExternalSafetyCheck
from utils.audit_logger import log_activity
from utils.vehicle_helpers import allowed_file, log_audit


def register_vehicle_extra_document_misc_routes(bp):
    @bp.route('/<int:id>/upload-document', methods=['POST'])
    @login_required
    def upload_document(id):
        vehicle = Vehicle.query.get_or_404(id)

        try:
            if not current_user.has_permission(Module.VEHICLES, Permission.EDIT):
                flash('ليس لديك صلاحية لتعديل بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))
        except Exception:
            if not hasattr(current_user, 'role') or current_user.role != UserRole.ADMIN:
                flash('ليس لديك صلاحية لتعديل بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))

        document_type = request.form.get('document_type')
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('vehicles.view', id=id))

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"

            if document_type == 'registration_form':
                upload_folder, field_name = 'static/uploads/vehicles/registration_forms', 'registration_form_image'
            elif document_type == 'plate':
                upload_folder, field_name = 'static/uploads/vehicles/plates', 'plate_image'
            elif document_type == 'insurance':
                upload_folder, field_name = 'static/uploads/vehicles/insurance', 'insurance_file'
            else:
                flash('نوع الوثيقة غير صحيح', 'error')
                return redirect(url_for('vehicles.view', id=id))

            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            setattr(vehicle, field_name, file_path)

            try:
                db.session.commit()
                flash('تم رفع الوثيقة بنجاح', 'success')
                log_activity(
                    action='upload',
                    entity_type='Vehicle',
                    entity_id=vehicle.id,
                    details=f'رفع وثيقة {document_type} للسيارة {vehicle.plate_number}',
                )
            except Exception as e:
                db.session.rollback()
                flash(f'خطأ في حفظ الوثيقة: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=id))

    @bp.route('/<int:id>/delete-document', methods=['POST'])
    @login_required
    def delete_document(id):
        vehicle = Vehicle.query.get_or_404(id)

        try:
            if not current_user.has_permission(Module.VEHICLES, Permission.DELETE):
                flash('ليس لديك صلاحية لحذف بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))
        except Exception:
            if not hasattr(current_user, 'role') or current_user.role != UserRole.ADMIN:
                flash('ليس لديك صلاحية لحذف بيانات السيارات', 'error')
                return redirect(url_for('vehicles.view', id=id))

        document_type = request.form.get('document_type')
        if document_type == 'registration_form':
            field_name = 'registration_form_image'
        elif document_type == 'plate':
            field_name = 'plate_image'
        elif document_type == 'insurance':
            field_name = 'insurance_file'
        else:
            flash('نوع الوثيقة غير صحيح', 'error')
            return redirect(url_for('vehicles.view', id=id))

        if getattr(vehicle, field_name):
            setattr(vehicle, field_name, None)
            try:
                db.session.commit()
                flash('تم حذف الوثيقة بنجاح', 'success')
                log_activity(
                    action='delete',
                    entity_type='Vehicle',
                    entity_id=vehicle.id,
                    details=f'حذف وثيقة {document_type} للسيارة {vehicle.plate_number}',
                )
            except Exception as e:
                db.session.rollback()
                flash(f'خطأ في حذف الوثيقة: {str(e)}', 'error')

        return redirect(url_for('vehicles.view', id=id))

    @bp.route('/import', methods=['GET', 'POST'])
    @login_required
    def import_vehicles():
        if request.method == 'GET':
            return render_template('vehicles/utilities/import_vehicles.html')

        if 'file' not in request.files:
            flash('لم يتم اختيار ملف للاستيراد', 'error')
            return redirect(url_for('vehicles.import_vehicles'))

        file = request.files['file']
        if not file or file.filename == '':
            flash('لم يتم اختيار ملف للاستيراد', 'error')
            return redirect(url_for('vehicles.import_vehicles'))

        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('يجب أن يكون الملف من نوع Excel (.xlsx أو .xls)', 'error')
            return redirect(url_for('vehicles.import_vehicles'))

        try:
            success_count, error_count, errors = process_import_vehicles(file.stream)
            flash(f'تم استيراد {success_count} سيارة بنجاح!', 'success')
            if error_count > 0:
                flash(f'حدثت {error_count} أخطاء أثناء الاستيراد', 'warning')
            for err in errors[:10]:
                flash(err, 'error')
            if len(errors) > 10:
                flash(f'وهناك {len(errors) - 10} أخطاء أخرى...', 'info')
            if success_count == 0 and not errors:
                flash('لم يتم استيراد أي سيارة', 'warning')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'خطأ في قراءة الملف: {str(e)}', 'error')

        return redirect(url_for('vehicles.index'))

    @bp.route('/valid-documents')
    @login_required
    def valid_documents():
        plate_number = request.args.get('plate_number', '').strip()
        vehicle_make = request.args.get('vehicle_make', '').strip()
        ctx = get_valid_documents_context(plate_number=plate_number, vehicle_make=vehicle_make)
        return render_template('vehicles/utilities/valid_documents.html', **ctx)

    @bp.route('/<int:id>/edit-documents', methods=['GET', 'POST'])
    @login_required
    def edit_vehicle_documents(id):
        vehicle = Vehicle.query.get_or_404(id)

        if request.method == 'POST':
            registration_expiry = request.form.get('registration_expiry_date')
            inspection_expiry = request.form.get('inspection_expiry_date')
            authorization_expiry = request.form.get('authorization_expiry_date')

            if registration_expiry:
                vehicle.registration_expiry_date = datetime.strptime(registration_expiry, '%Y-%m-%d').date()
            if inspection_expiry:
                vehicle.inspection_expiry_date = datetime.strptime(inspection_expiry, '%Y-%m-%d').date()
            if authorization_expiry:
                vehicle.authorization_expiry_date = datetime.strptime(authorization_expiry, '%Y-%m-%d').date()

            vehicle.updated_at = datetime.utcnow()
            db.session.commit()
            log_audit('update', 'vehicle_documents', vehicle.id, f'تم تعديل تواريخ وثائق السيارة: {vehicle.plate_number}')
            flash('تم تحديث تواريخ الوثائق بنجاح!', 'success')
            return redirect(url_for('vehicles.valid_documents'))

        return render_template('vehicles/forms/edit_documents.html', vehicle=vehicle)

    @bp.route('/api/get_employee_info/<driver_name>')
    @login_required
    def get_employee_info(driver_name):
        from domain.employees.models import Employee

        try:
            employee = Employee.query.filter_by(name=driver_name).first()
            if employee:
                return jsonify({'success': True, 'location': employee.location or '', 'name': employee.name})
            return jsonify({'success': False, 'message': 'لم يتم العثور على الموظف'})
        except Exception as e:
            current_app.logger.error(f"خطأ في جلب معلومات الموظف: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/alerts-count', methods=['GET'])
    @login_required
    def get_vehicle_alerts_count():
        today = datetime.now().date()
        future_date = today + timedelta(days=14)

        try:
            pending_external_checks = (
                db.session.query(func.count(VehicleExternalSafetyCheck.id))
                .filter(VehicleExternalSafetyCheck.approval_status == 'pending')
                .scalar()
                or 0
            )
            expiring_authorizations = (
                db.session.query(func.count(Vehicle.id))
                .filter(
                    Vehicle.authorization_expiry_date.isnot(None),
                    Vehicle.authorization_expiry_date >= today,
                    Vehicle.authorization_expiry_date <= future_date,
                )
                .scalar()
                or 0
            )
            expiring_inspections = (
                db.session.query(func.count(Vehicle.id))
                .filter(
                    Vehicle.inspection_expiry_date.isnot(None),
                    Vehicle.inspection_expiry_date >= today,
                    Vehicle.inspection_expiry_date <= future_date,
                )
                .scalar()
                or 0
            )

            total_alerts = pending_external_checks + expiring_authorizations + expiring_inspections
            return jsonify(
                {
                    'success': True,
                    'total_alerts': total_alerts,
                    'pending_external_checks': pending_external_checks,
                    'expiring_authorizations': expiring_authorizations,
                    'expiring_inspections': expiring_inspections,
                }
            )
        except Exception as e:
            current_app.logger.error(f"خطأ في حساب إشعارات المركبات: {str(e)}")
            return jsonify({'success': False, 'total_alerts': 0, 'error': str(e)}), 500
