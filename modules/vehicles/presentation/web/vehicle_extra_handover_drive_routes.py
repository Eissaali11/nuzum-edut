"""Handover, license-image, and Google Drive utility routes."""

import os

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from core.extensions import db
from domain.employees.models import Department, Employee, employee_departments
from modules.vehicles.application.vehicle_service import (
    get_vehicle_current_employee_id,
    update_all_vehicle_drivers,
)
from modules.vehicles.domain.models import Vehicle, VehicleHandover
from utils.vehicle_helpers import allowed_file, log_audit


def register_vehicle_extra_handover_drive_routes(bp):
    @bp.route('/update-drivers', methods=['POST'])
    @login_required
    def update_drivers():
        try:
            updated_count = update_all_vehicle_drivers()
            flash(f'تم تحديث أسماء السائقين لـ {updated_count} سيارة بنجاح!', 'success')
        except Exception as e:
            flash(f'حدث خطأ أثناء التحديث: {str(e)}', 'danger')

        return redirect(url_for('vehicles.detailed'))

    @bp.route('/<int:vehicle_id>/current_employee')
    @login_required
    def get_current_employee(vehicle_id):
        try:
            employee_id = get_vehicle_current_employee_id(vehicle_id)
            return jsonify({'employee_id': employee_id})
        except Exception as e:
            return jsonify({'employee_id': None, 'error': str(e)}), 500

    @bp.route('/handovers')
    @login_required
    def handovers_list():
        try:
            vehicles_query = Vehicle.query

            if (
                current_user.is_authenticated
                and hasattr(current_user, 'assigned_department_id')
                and current_user.assigned_department_id
            ):
                dept_employee_ids = (
                    db.session.query(Employee.id)
                    .join(employee_departments)
                    .join(Department)
                    .filter(Department.id == current_user.assigned_department_id)
                    .all()
                )
                dept_employee_ids = [emp.id for emp in dept_employee_ids]

                if dept_employee_ids:
                    vehicle_ids_with_handovers = (
                        db.session.query(VehicleHandover.vehicle_id)
                        .filter(
                            VehicleHandover.handover_type == 'delivery',
                            VehicleHandover.employee_id.in_(dept_employee_ids),
                        )
                        .distinct()
                        .all()
                    )
                    vehicle_ids = [h.vehicle_id for h in vehicle_ids_with_handovers]
                    vehicles_query = vehicles_query.filter(Vehicle.id.in_(vehicle_ids)) if vehicle_ids else vehicles_query.filter(Vehicle.id == -1)
                else:
                    vehicles_query = vehicles_query.filter(Vehicle.id == -1)

            vehicles = vehicles_query.all()
            vehicles_data = []
            for vehicle in vehicles:
                latest_delivery = (
                    VehicleHandover.query.filter_by(vehicle_id=vehicle.id, handover_type='delivery')
                    .order_by(VehicleHandover.handover_date.desc())
                    .first()
                )
                latest_return = (
                    VehicleHandover.query.filter_by(vehicle_id=vehicle.id, handover_type='return')
                    .order_by(VehicleHandover.handover_date.desc())
                    .first()
                )

                current_status = 'متاح'
                current_employee = None
                if latest_delivery and (not latest_return or latest_delivery.handover_date > latest_return.handover_date):
                    current_status = 'مُسلم'
                    current_employee = latest_delivery.person_name

                vehicles_data.append(
                    {
                        'vehicle': vehicle,
                        'latest_delivery': latest_delivery,
                        'latest_return': latest_return,
                        'current_status': current_status,
                        'current_employee': current_employee,
                    }
                )

            return render_template('vehicles/handovers/handovers_list.html', vehicles_data=vehicles_data)
        except Exception as e:
            flash(f'حدث خطأ أثناء تحميل البيانات: {str(e)}', 'danger')
            return redirect(url_for('vehicles.index'))

    @bp.route('/<int:vehicle_id>/license-image', methods=['GET', 'POST'])
    @login_required
    def vehicle_license_image(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'delete':
                if vehicle.license_image:
                    try:
                        vehicle.license_image = None
                        db.session.commit()
                        log_audit('delete', 'vehicle', vehicle.id, f'تم حذف صورة رخصة السيارة {vehicle.plate_number}')
                        flash('تم حذف صورة الرخصة بنجاح', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'خطأ في حذف صورة الرخصة: {str(e)}', 'error')
                else:
                    flash('لا توجد صورة رخصة لحذفها', 'warning')
                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

            if 'license_image' not in request.files:
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

            file = request.files['license_image']
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'danger')
                return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

            if file and allowed_file(file.filename, ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                try:
                    upload_dir = os.path.join('static', 'uploads', 'vehicles')
                    os.makedirs(upload_dir, exist_ok=True)

                    filename = secure_filename(file.filename)
                    from datetime import datetime

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'license_{vehicle.plate_number}_{timestamp}_{filename}'
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)

                    try:
                        from PIL import Image

                        with Image.open(filepath) as img:
                            if img.mode == 'RGBA':
                                img = img.convert('RGB')
                            if img.width > 1500 or img.height > 1500:
                                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
                                img.save(filepath, 'JPEG', quality=85, optimize=True)
                    except Exception:
                        pass

                    old_had_image = bool(vehicle.license_image)
                    vehicle.license_image = filename
                    db.session.commit()

                    action_text = 'update' if old_had_image else 'create'
                    log_audit(
                        action=action_text,
                        entity_type='vehicle',
                        entity_id=vehicle.id,
                        details=f'تم {"تحديث" if action_text == "update" else "رفع"} صورة رخصة للسيارة {vehicle.plate_number}',
                    )
                    flash('تم رفع صورة الرخصة بنجاح', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'خطأ في رفع صورة الرخصة: {str(e)}', 'error')
            else:
                flash('نوع الملف غير مدعوم. يرجى رفع صورة بصيغة JPG, PNG, GIF أو WEBP', 'error')

            return redirect(url_for('vehicles.vehicle_license_image', vehicle_id=vehicle_id))

        return render_template('vehicles/utilities/license_image.html', vehicle=vehicle)

    @bp.route('/<int:vehicle_id>/drive-link', methods=['POST'])
    @login_required
    def update_drive_link(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        action = request.form.get('action')

        if action == 'remove':
            vehicle.drive_folder_link = None
            db.session.commit()
            log_audit('delete', 'vehicle', vehicle.id, f'تم حذف رابط Google Drive للسيارة {vehicle.plate_number}')
            flash('تم حذف رابط Google Drive بنجاح', 'success')
        else:
            drive_link = request.form.get('drive_link', '').strip()
            if not drive_link:
                flash('يرجى إدخال رابط Google Drive', 'danger')
                return redirect(url_for('vehicles.view', id=vehicle_id))
            if not (drive_link.startswith('https://drive.google.com') or drive_link.startswith('https://docs.google.com')):
                flash('يرجى إدخال رابط Google Drive صحيح', 'danger')
                return redirect(url_for('vehicles.view', id=vehicle_id))

            old_link = vehicle.drive_folder_link
            vehicle.drive_folder_link = drive_link
            db.session.commit()
            if old_link:
                log_audit('update', 'vehicle', vehicle.id, f'تم تحديث رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم تحديث رابط Google Drive بنجاح', 'success')
            else:
                log_audit('create', 'vehicle', vehicle.id, f'تم إضافة رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم إضافة رابط Google Drive بنجاح', 'success')

        return redirect(url_for('vehicles.view', id=vehicle_id))

    @bp.route('/<int:vehicle_id>/drive-files')
    @login_required
    def vehicle_drive_files(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        return render_template('vehicles/utilities/drive_files.html', title=f'ملفات Google Drive - {vehicle.plate_number}', vehicle=vehicle)

    @bp.route('/<int:vehicle_id>/drive-management', methods=['GET', 'POST'])
    @login_required
    def drive_management(vehicle_id):
        vehicle = Vehicle.query.get_or_404(vehicle_id)

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'delete':
                vehicle.drive_folder_link = None
                db.session.commit()
                log_audit('delete', 'vehicle', vehicle.id, f'تم حذف رابط Google Drive للسيارة {vehicle.plate_number}')
                flash('تم حذف رابط Google Drive بنجاح', 'success')
            elif action == 'save':
                drive_link = request.form.get('drive_link', '').strip()
                if not drive_link:
                    flash('يرجى إدخال رابط Google Drive', 'danger')
                    return render_template('vehicles/utilities/drive_management.html', vehicle=vehicle)
                if not (drive_link.startswith('https://drive.google.com') or drive_link.startswith('https://docs.google.com')):
                    flash('يرجى إدخال رابط Google Drive صحيح', 'danger')
                    return render_template('vehicles/utilities/drive_management.html', vehicle=vehicle)

                old_link = vehicle.drive_folder_link
                vehicle.drive_folder_link = drive_link
                db.session.commit()
                if old_link:
                    log_audit('update', 'vehicle', vehicle.id, f'تم تحديث رابط Google Drive للسيارة {vehicle.plate_number}')
                    flash('تم تحديث رابط Google Drive بنجاح', 'success')
                else:
                    log_audit('create', 'vehicle', vehicle.id, f'تم إضافة رابط Google Drive للسيارة {vehicle.plate_number}')
                    flash('تم إضافة رابط Google Drive بنجاح', 'success')

            return redirect(url_for('vehicles.drive_management', vehicle_id=vehicle_id))

        return render_template('vehicles/utilities/drive_management.html', vehicle=vehicle)
