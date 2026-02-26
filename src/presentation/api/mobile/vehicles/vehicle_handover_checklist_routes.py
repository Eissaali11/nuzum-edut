"""Auto-split from vehicle_routes.py: mobile vehicle domain routes."""

"""
مسارات المركبات (السيارات، الورشة، التسليم/الاستلام، التصريحات الخارجية) للجوال.
مستخرجة من routes/mobile.py. تُسجّل على mobile_bp عبر register_vehicle_routes(mobile_bp).
"""
import base64
import io
import os
import uuid
from datetime import datetime, timedelta, date

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from models import (
    Department,
    Employee,
    ExternalAuthorization,
    GeofenceSession,
    OperationNotification,
    OperationRequest,
    Vehicle,
    VehicleAccident,
    VehicleChecklist,
    VehicleChecklistImage,
    VehicleChecklistItem,
    VehicleDamageMarker,
    VehicleFuelConsumption,
    VehicleHandover,
    VehicleHandoverImage,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehiclePeriodicInspection,
    VehicleProject,
    VehicleRental,
    VehicleSafetyCheck,
    VehicleWorkshop,
    VehicleWorkshopImage,
    employee_departments,
)
from src.core.extensions import db
from src.routes.operations import create_operation_request
from src.modules.vehicles.application.vehicle_service import update_vehicle_driver
from src.utils.audit_logger import log_activity
from src.utils.decorators import module_access_required, permission_required
from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state

def register_vehicle_handover_checklist_routes(bp):
    @bp.route('/vehicles/<int:vehicle_id>/handover/create', methods=['GET', 'POST'])
    @login_required
    def create_handover_mobile(vehicle_id):
        """
        الراوت الموحد والكامل لإنشاء نموذج تسليم/استلام جديد من واجهة الموبايل.
        - يحدد نوع العملية تلقائياً.
        - يتكامل مع نظام الموافقات عبر OperationRequest.
        """
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        status_arabic_map = {
            'available': 'متاحة',
            'rented': 'مؤجرة',
            'in_project': 'في المشروع',
            'in_workshop': 'في الورشة',
            'accident': 'حادث',
            'out_of_service': 'خارج الخدمة'
        }
    
        current_status_ar = status_arabic_map.get(vehicle.status, vehicle.status) # إذا لم يجد الترجمة، يستخدم الاسم الإنجليزي
    
    
        unsuitable_statuses = {
            'in_workshop': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"',
            'accident': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"',
            'out_of_service': f'لا يمكن إجراء العملية لأن حالة المركبة "{current_status_ar}"'
        }
        # احصل على الترجمة للحالة الحالية للمركبة
    
    
        # === الخطوة 1: التحقق من أهلية السيارة للعملية ===
    
        if vehicle.status in unsuitable_statuses:
            flash(unsuitable_statuses[vehicle.status], 'danger')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
        # === الخطوة 2: المنطق الذكي لتحديد نوع العملية (GET & POST) ===
        # هذا المنطق يُستخدم للتحقق من صحة الطلب عند الحفظ (POST)
        # ولإعداد النموذج بشكل صحيح عند العرض (GET)
        force_mode = 'delivery'
        info_message = "المركبة متاحة حالياً. النموذج معد لعملية التسليم لسائق جديد."
        current_driver_info = None
    
        # نستخدم نفس منطق الويب للبحث عن آخر عملية رسمية معتمدة
        approved_handover_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.status == 'approved',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()
    
        all_handover_request_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()
    
        base_official_query = VehicleHandover.query.filter(
            VehicleHandover.vehicle_id == vehicle_id,
            or_(
                VehicleHandover.id.in_(approved_handover_ids_subquery),
                ~VehicleHandover.id.in_(all_handover_request_ids_subquery)
            )
        )
    
        latest_delivery = base_official_query.filter(VehicleHandover.handover_type == 'delivery').order_by(VehicleHandover.created_at.desc()).first()
        latest_return = base_official_query.filter(VehicleHandover.handover_type == 'return').order_by(VehicleHandover.created_at.desc()).first()
    
        if latest_delivery and (not latest_return or latest_delivery.created_at > latest_return.created_at):
            force_mode = 'return'
            current_driver_info = latest_delivery # كائن كامل
            info_message = f"تنبيه: المركبة مسلمة حالياً لـِ '{latest_delivery.person_name}'. النموذج معد لعملية الاستلام فقط."
    
        # === معالجة طلب GET (عرض النموذج) ===
        if request.method == 'GET':
            employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
            departments = Department.query.order_by(Department.name).all()
    
            return render_template(
                'mobile/vehicle_checklist.html',
                is_editing=False,
                form_action=url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id),
                vehicle=vehicle,
                force_mode=force_mode,
                current_driver_info=current_driver_info.to_dict() if current_driver_info else None,
                info_message=info_message,
                employees=employees,
                departments=departments
            )
    
        # === معالجة طلب POST (إنشاء السجل) ===
        if request.method == 'POST':
            try:
                handover_type_from_form = request.form.get('handover_type')
                if handover_type_from_form != force_mode:
                    flash("خطأ في منطق العملية. تم تحديث الصفحة، يرجى المحاولة مرة أخرى.", "danger")
                    return redirect(url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id))
    
                # --- 3. استخراج شامل للبيانات من النموذج ---
                handover_date_str = request.form.get('handover_date')
                handover_time_str = request.form.get('handover_time')
                employee_id_str = request.form.get('employee_id')
                supervisor_employee_id_str = request.form.get('supervisor_employee_id')
                person_name_from_form = request.form.get('person_name', '').strip()
                supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
                mileage = int(request.form.get('mileage', 0))
                fuel_level = request.form.get('fuel_level')
                project_name = request.form.get('project_name')
                city = request.form.get('city')
                reason_for_change = request.form.get('reason_for_change')
                vehicle_status_summary = request.form.get('vehicle_status_summary')
                notes = request.form.get('notes')
                reason_for_authorization = request.form.get('reason_for_authorization')
                authorization_details = request.form.get('authorization_details')
                movement_officer_name = request.form.get('movement_officer_name')
                form_link = request.form.get('form_link')
                form_link_2 = request.form.get('form_link_2')
                custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
                # Checklist
                has_spare_tire = 'has_spare_tire' in request.form
                has_fire_extinguisher = 'has_fire_extinguisher' in request.form
                has_first_aid_kit = 'has_first_aid_kit' in request.form
                has_warning_triangle = 'has_warning_triangle' in request.form
                has_tools = 'has_tools' in request.form
                has_oil_leaks = 'has_oil_leaks' in request.form
                has_gear_issue = 'has_gear_issue' in request.form
                has_clutch_issue = 'has_clutch_issue' in request.form
                has_engine_issue = 'has_engine_issue' in request.form
                has_windows_issue = 'has_windows_issue' in request.form
                has_tires_issue = 'has_tires_issue' in request.form
                has_body_issue = 'has_body_issue' in request.form
                has_electricity_issue = 'has_electricity_issue' in request.form
                has_lights_issue = 'has_lights_issue' in request.form
                has_ac_issue = 'has_ac_issue' in request.form
    
                handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
                handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
                saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams') or None
                saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures') or None
                saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures') or None
                movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature_data'), 'signatures') # تصحيح الاسم هنا
                custom_logo_file = request.files.get('custom_logo_file')
                saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
                driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
                # إذا لم يتم اختيار موظف من القائمة، ابحث عنه بالاسم
                if not driver and person_name_from_form:
                    driver = Employee.query.filter(Employee.name.ilike(f"%{person_name_from_form.strip()}%")).first()
                
                supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
                # --- 4. إنشاء كائن VehicleHandover وتعبئته ---
                handover = VehicleHandover(
                    vehicle_id=vehicle.id, handover_type=handover_type_from_form, handover_date=handover_date,
                    handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
                    vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
                    vehicle_model_year=str(vehicle.year), employee_id=driver.id if driver else (current_driver_info.employee_id if force_mode == 'return' else None),
                    person_name=driver.name if driver else (person_name_from_form if force_mode == 'delivery' else current_driver_info.person_name),
                    driver_company_id=driver.employee_id if driver else (current_driver_info.driver_company_id if force_mode == 'return' else None),
                    driver_work_phone=driver.mobile if driver else (current_driver_info.driver_work_phone if force_mode == 'return' else None),
                    driver_phone_number=driver.mobilePersonal if driver else (current_driver_info.driver_phone_number if force_mode == 'return' else None),
                    driver_residency_number=driver.national_id if driver else (current_driver_info.driver_residency_number if force_mode == 'return' else None),
                    driver_contract_status=driver.contract_status if driver else None,
                    driver_license_status=driver.license_status if driver else None,
                    driver_signature_path=saved_driver_sig_path,
                    supervisor_employee_id=supervisor.id if supervisor else None,
                    supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
                    supervisor_company_id=supervisor.mobile if supervisor else None,
                    supervisor_phone_number=supervisor.mobilePersonal if supervisor else None,
                    supervisor_residency_number=supervisor.national_id if supervisor else None,
                    supervisor_contract_status=supervisor.contract_status if supervisor else None,
                    supervisor_license_status=supervisor.license_status if supervisor else None,
                    supervisor_signature_path=saved_supervisor_sig_path, reason_for_change=reason_for_change,
                    vehicle_status_summary=vehicle_status_summary, notes=notes,
                    reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
                    fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
                    has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
                    has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
                    has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
                    has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
                    has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
                    has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
                    movement_officer_name=movement_officer_name,
                    movement_officer_signature_path=movement_officer_signature_path,
                    damage_diagram_path=saved_diagram_path, form_link=form_link, form_link_2=form_link_2,
                    custom_company_name=custom_company_name, custom_logo_path=saved_custom_logo_path
                )
    
                db.session.add(handover)
                db.session.flush()
    
                # --- 5. إنشاء طلب موافقة (Operation Request) ---
                action_type = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
                operation_title = f"موافقة على {action_type} مركبة {vehicle.plate_number} (جوال)"
                operation_description = f"تم إنشاء نموذج {action_type} للمركبة {vehicle.plate_number} بواسطة {current_user.username} عبر الجوال. الرجاء المراجعة والموافقة."
    
                create_operation_request(
                    operation_type="handover", 
                    related_record_id=handover.id, 
                    vehicle_id=vehicle.id,
                    title=operation_title, 
                    description=operation_description, 
                    requested_by=current_user.id
                )
    
                # --- 6. حفظ المرفقات الإضافية ---
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename:
                        file_path, file_type = save_file(file, 'handover')
                        if file_path:
                            desc = request.form.get(f'description_{file.filename}', '')
                            attachment = VehicleHandoverImage(
                                handover_record_id=handover.id, file_path=file_path, file_type=file_type, 
                                image_path=file_path, file_description=desc, image_description=desc
                            )
                            db.session.add(attachment)
    
                db.session.commit()
    
                log_activity('create', 'vehicle_handover', handover.id, f"إنشاء طلب {action_type} للمركبة {vehicle.plate_number} عبر الجوال (بانتظار الموافقة)")
    
                flash(f'تم إنشاء طلب {action_type} بنجاح، وهو الآن بانتظار الموافقة.', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
                return redirect(url_for('mobile.create_handover_mobile', vehicle_id=vehicle.id))
    
    
    
    
    
    
    # في ملف mobile_bp.py
    
    # ... تأكد من وجود كل الاستيرادات اللازمة والدوال المساعدة ...
    
    
    @bp.route('/handover/<int:handover_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_handover_mobile(handover_id):
        """
        راوت لتعديل نموذج تسليم/استلام حالي.
        """
        existing_handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = existing_handover.vehicle
    
        # === معالجة طلب GET (عرض النموذج مع البيانات الحالية) ===
        if request.method == 'GET':
            employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
            departments = Department.query.order_by(Department.name).all()
    
            return render_template(
                'mobile/vehicle_checklist.html',
                is_editing=True,
                form_action=url_for('mobile.edit_handover_mobile', handover_id=handover_id),
                vehicle=vehicle,
                existing_handover=existing_handover.to_dict(),
                employees=employees,
                departments=departments
            )
    
        # === معالجة طلب POST (حفظ التعديلات على السجل الحالي) ===
        if request.method == 'POST':
            try:
                # --- استخراج شامل للبيانات من النموذج ---
                handover_type = request.form.get('handover_type')
                handover_date_str = request.form.get('handover_date')
                handover_time_str = request.form.get('handover_time')
                employee_id_str = request.form.get('employee_id')
                supervisor_employee_id_str = request.form.get('supervisor_employee_id')
                person_name_from_form = request.form.get('person_name', '').strip()
                supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
                mileage = int(request.form.get('mileage', 0))
                fuel_level = request.form.get('fuel_level')
                project_name = request.form.get('project_name')
                city = request.form.get('city')
                reason_for_change = request.form.get('reason_for_change')
                vehicle_status_summary = request.form.get('vehicle_status_summary')
                notes = request.form.get('notes')
                reason_for_authorization = request.form.get('reason_for_authorization')
                authorization_details = request.form.get('authorization_details')
                movement_officer_name = request.form.get('movement_officer_name')
                form_link = request.form.get('form_link')
                form_link_2 = request.form.get('form_link_2')
                custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
                # Checklist
                has_spare_tire = 'has_spare_tire' in request.form
                has_fire_extinguisher = 'has_fire_extinguisher' in request.form
                has_first_aid_kit = 'has_first_aid_kit' in request.form
                has_warning_triangle = 'has_warning_triangle' in request.form
                has_tools = 'has_tools' in request.form
                has_oil_leaks = 'has_oil_leaks' in request.form
                has_gear_issue = 'has_gear_issue' in request.form
                has_clutch_issue = 'has_clutch_issue' in request.form
                has_engine_issue = 'has_engine_issue' in request.form
                has_windows_issue = 'has_windows_issue' in request.form
                has_tires_issue = 'has_tires_issue' in request.form
                has_body_issue = 'has_body_issue' in request.form
                has_electricity_issue = 'has_electricity_issue' in request.form
                has_lights_issue = 'has_lights_issue' in request.form
                has_ac_issue = 'has_ac_issue' in request.form
    
                existing_handover.handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else existing_handover.handover_date
                existing_handover.handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else existing_handover.handover_time
    
                driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
                supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
                # --- تحديث حقول السجل `existing_handover` ---
                existing_handover.handover_type = handover_type
                existing_handover.mileage = mileage
                existing_handover.project_name = project_name
                existing_handover.city = city
                existing_handover.employee_id = driver.id if driver else None
                existing_handover.person_name = driver.name if driver else person_name_from_form
                existing_handover.supervisor_employee_id = supervisor.id if supervisor else None
                existing_handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
                existing_handover.reason_for_change = reason_for_change
                existing_handover.vehicle_status_summary = vehicle_status_summary
                existing_handover.notes = notes
                existing_handover.reason_for_authorization = reason_for_authorization
                existing_handover.authorization_details = authorization_details
                existing_handover.fuel_level = fuel_level
                existing_handover.has_spare_tire, existing_handover.has_fire_extinguisher, existing_handover.has_first_aid_kit, existing_handover.has_warning_triangle, existing_handover.has_tools = has_spare_tire, has_fire_extinguisher, has_first_aid_kit, has_warning_triangle, has_tools
                existing_handover.has_oil_leaks, existing_handover.has_gear_issue, existing_handover.has_clutch_issue, existing_handover.has_engine_issue, existing_handover.has_windows_issue, existing_handover.has_tires_issue, existing_handover.has_body_issue, existing_handover.has_electricity_issue, existing_handover.has_lights_issue, existing_handover.has_ac_issue = has_oil_leaks, has_gear_issue, has_clutch_issue, has_engine_issue, has_windows_issue, has_tires_issue, has_body_issue, has_electricity_issue, has_lights_issue, has_ac_issue
                existing_handover.movement_officer_name = movement_officer_name
                existing_handover.form_link = form_link
                existing_handover.form_link_2 = form_link_2
                existing_handover.custom_company_name = custom_company_name
                existing_handover.updated_at = datetime.utcnow()
    
                # تحديث الصور والتواقيع فقط إذا تم تقديم بيانات جديدة
                new_diagram_data = request.form.get('damage_diagram_data')
                if new_diagram_data: existing_handover.damage_diagram_path = save_base64_image(new_diagram_data, 'diagrams')
    
                new_supervisor_sig = request.form.get('supervisor_signature_data')
                if new_supervisor_sig: existing_handover.supervisor_signature_path = save_base64_image(new_supervisor_sig, 'signatures')
    
                new_driver_sig = request.form.get('driver_signature_data')
                if new_driver_sig: existing_handover.driver_signature_path = save_base64_image(new_driver_sig, 'signatures')
    
                new_movement_sig = request.form.get('movement_officer_signature_data')
                if new_movement_sig: existing_handover.movement_officer_signature_path = save_base64_image(new_movement_sig, 'signatures')
    
                # معالجة رفع الملفات الجديدة
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename:
                        try:
                            file_path, file_type = save_file(file, 'handover')
                            if file_path:
                                file_description = request.form.get(f'description_{file.filename}', '')
                                file_record = VehicleHandoverImage(
                                    handover_record_id=existing_handover.id, 
                                    image_path=file_path,
                                    image_description=file_description,
                                    file_path=file_path, 
                                    file_type=file_type,
                                    file_description=file_description
                                )
                                db.session.add(file_record)
                        except Exception as e:
                            import logging
                            logging.error(f"خطأ في حفظ الملف {file.filename}: {str(e)}")
                            flash(f'خطأ في حفظ الملف {file.filename}', 'warning')
    
                db.session.commit()
                log_activity('update', 'vehicle_handover', existing_handover.id, f"تعديل نموذج {existing_handover.handover_type} للمركبة {vehicle.plate_number} عبر الجوال")
    
                flash('تم تحديث النموذج بنجاح.', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
            except Exception as e:
                db.session.rollback()
                import traceback
                traceback.print_exc()
                flash(f'حدث خطأ أثناء تحديث النموذج: {str(e)}', 'danger')
                return redirect(url_for('mobile.edit_handover_mobile', handover_id=handover_id))
    
    @bp.route('/handover/<int:handover_id>/save_as_next', methods=['POST'])
    @login_required
    def save_as_next_handover_mobile(handover_id):
        """
        راوت لإنشاء سجل جديد بناءً على تعديلات سجل حالي، مع عكس نوع العملية.
        """
        original_handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = original_handover.vehicle
    
        try:
            # --- استخراج شامل للبيانات من النموذج ---
            handover_type = request.form.get('handover_type') # هذا سيكون نوع العملية القديمة
            handover_date_str = request.form.get('handover_date')
            handover_time_str = request.form.get('handover_time')
            employee_id_str = request.form.get('employee_id')
            supervisor_employee_id_str = request.form.get('supervisor_employee_id')
            person_name_from_form = request.form.get('person_name', '').strip()
            supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
            mileage = int(request.form.get('mileage', 0))
            fuel_level = request.form.get('fuel_level')
            project_name = request.form.get('project_name')
            city = request.form.get('city')
            reason_for_change = request.form.get('reason_for_change')
            vehicle_status_summary = request.form.get('vehicle_status_summary')
            notes = request.form.get('notes')
            reason_for_authorization = request.form.get('reason_for_authorization')
            authorization_details = request.form.get('authorization_details')
            movement_officer_name = request.form.get('movement_officer_name')
            form_link = request.form.get('form_link')
            form_link_2 = request.form.get('form_link_2')
            custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
            # Checklist
            has_spare_tire = 'has_spare_tire' in request.form; has_fire_extinguisher = 'has_fire_extinguisher' in request.form; has_first_aid_kit = 'has_first_aid_kit' in request.form; has_warning_triangle = 'has_warning_triangle' in request.form; has_tools = 'has_tools' in request.form; has_oil_leaks = 'has_oil_leaks' in request.form; has_gear_issue = 'has_gear_issue' in request.form; has_clutch_issue = 'has_clutch_issue' in request.form; has_engine_issue = 'has_engine_issue' in request.form; has_windows_issue = 'has_windows_issue' in request.form; has_tires_issue = 'has_tires_issue' in request.form; has_body_issue = 'has_body_issue' in request.form; has_electricity_issue = 'has_electricity_issue' in request.form; has_lights_issue = 'has_lights_issue' in request.form; has_ac_issue = 'has_ac_issue' in request.form
    
            handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
            handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
            # --- إنشاء كائن `VehicleHandover` جديد وتعبئته بالبيانات ---
            new_handover = VehicleHandover(
                vehicle_id=vehicle.id, handover_date=handover_date,
                handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
                vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
                vehicle_model_year=str(vehicle.year), 
                # (سيتم تعبئة حقول السائق والمشرف أدناه)
                reason_for_change=reason_for_change,
                vehicle_status_summary=vehicle_status_summary, notes=notes,
                reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
                fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
                has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
                has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
                has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
                has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
                has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
                has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
                movement_officer_name=movement_officer_name,
                form_link=form_link, form_link_2=form_link_2,
                custom_company_name=custom_company_name,
                # created_by=current_user.id
            )
    
            # !! --- المنطق الذكي: عكس نوع العملية وتحديد السائق والمشرف --- !!
            driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
            supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
            # المشرف دائماً هو من تم اختياره في الفورم
            new_handover.supervisor_employee_id = supervisor.id if supervisor else None
            new_handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
    
            if original_handover.handover_type == 'delivery':
                new_handover.handover_type = 'return'
                # السائق هو نفس سائق عملية التسليم الأصلية
                new_handover.person_name = original_handover.person_name
                new_handover.employee_id = original_handover.employee_id
            else: # إذا كانت العملية الأصلية 'return'
                new_handover.handover_type = 'delivery'
                # السائق هو من تم اختياره في النموذج الحالي
                new_handover.employee_id = driver.id if driver else None
                new_handover.person_name = driver.name if driver else person_name_from_form
    
            db.session.add(new_handover)
            db.session.flush()
    
            # --- إنشاء طلب موافقة للسجل الجديد ---
            action_type = 'تسليم' if new_handover.handover_type == 'delivery' else 'استلام'
            operation_title = f"موافقة على {action_type} (نسخة جديدة) لمركبة {vehicle.plate_number}"
            create_operation_request(
                operation_type="handover", related_record_id=new_handover.id, vehicle_id=vehicle.id,
                title=operation_title, description=f"تم إنشاؤها كنسخة من سجل سابق بواسطة {current_user.username}.", 
                requested_by=current_user.id
            )
    
            db.session.commit()
    
            flash(f'تم حفظ نسخة جديدة كعملية "{action_type}" وهي الآن بانتظار الموافقة.', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'حدث خطأ أثناء حفظ النسخة الجديدة: {str(e)}', 'danger')
            return redirect(url_for('mobile.edit_handover_mobile', handover_id=handover_id))
    
    
    
    # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # @bp.route('/vehicles/checklist/<int:handover_id>', methods=['GET', 'POST'])
    # @login_required
    # def create_handover_mobile(handover_id=None):
        
    #     """
    #     النسخة المحسنة لإنشاء وتعديل نموذج تسليم/استلام السيارة (للموبايل).
    #     تدمج هذه النسخة المنطق الكامل من نسخة الويب مع واجهة الموبايل.
    #     """
    
    #     # === معالجة طلب GET (عرض النموذج) ===
    #     if request.method == 'GET':
    #         vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    #         employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    #         departments = Department.query.order_by(Department.name).all()
    #         employees_as_dicts = [e.to_dict() for e in employees]
    
    #         now_date = datetime.now().strftime('%Y-%m-%d')
    #         now_time = datetime.now().strftime('%H:%M')
    
    #         existing_handover_data = None
    #         is_editing = False
    #         if handover_id:
    #             existing_handover = VehicleHandover.query.get(handover_id)
    #             if existing_handover:
    #                 is_editing = True
    #                 existing_handover_data = existing_handover.to_dict()
    #                 now_date = existing_handover.handover_date.strftime('%Y-%m-%d') if existing_handover.handover_date else now_date
    #                 now_time = existing_handover.handover_time.strftime('%H:%M') if existing_handover.handover_time else now_time
    
    #         return render_template(
    #             'mobile/vehicle_checklist.html', 
    #             vehicles=vehicles,
    #             employees=employees,
    #             departments=departments,
    #             handover_types=HANDOVER_TYPE_CHOICES,
    #             employeeData=employees_as_dicts,
    #             now_date=now_date,
    #             now_time=now_time,
    #             existing_handover=existing_handover_data,
    #             is_editing=is_editing
    #         )
    
    #     # === معالجة طلب POST (حفظ النموذج) ===
    #     if request.method == 'POST':
    #         vehicle_id_str = request.form.get('vehicle_id')
    #         if not vehicle_id_str:
    #             flash('يجب اختيار مركبة أولاً.', 'danger')
    #             return redirect(url_for('mobile.create_handover_mobile'))
    
    #         vehicle = Vehicle.query.get_or_404(int(vehicle_id_str))
    
    #         # 1. التحقق من حالة السيارة (منطق من نسخة الويب)
    #         unsuitable_statuses = {
    #             'in_workshop': 'لا يمكن تسليم أو استلام المركبة لأنها حالياً في الورشة.',
    #             'accident': 'لا يمكن تسليم أو استلام المركبة لأنه مسجل عليها حادث نشط.',
    #             'out_of_service': 'لا يمكن تسليم أو استلام المركبة لأنها "خارج الخدمة".'
    #         }
    #         if vehicle.status in unsuitable_statuses:
    #             flash(f'❌ عملية مرفوضة: {unsuitable_statuses[vehicle.status]}', 'danger')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         try:
    #             # 2. استخراج شامل للبيانات من النموذج (مطابق لنسخة الويب)
    #             handover_type = request.form.get('handover_type')
    #             handover_date_str = request.form.get('handover_date')
    #             handover_time_str = request.form.get('handover_time')
    #             employee_id_str = request.form.get('employee_id')
    #             supervisor_employee_id_str = request.form.get('supervisor_employee_id')
    #             person_name_from_form = request.form.get('person_name', '').strip()
    #             supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
    #             mileage = int(request.form.get('mileage', 0))
    #             fuel_level = request.form.get('fuel_level')
    #             project_name = request.form.get('project_name')
    #             city = request.form.get('city')
    #             reason_for_change = request.form.get('reason_for_change')
    #             vehicle_status_summary = request.form.get('vehicle_status_summary')
    #             notes = request.form.get('notes')
    #             reason_for_authorization = request.form.get('reason_for_authorization')
    #             authorization_details = request.form.get('authorization_details')
    #             movement_officer_name = request.form.get('movement_officer_name')
    #             form_link = request.form.get('form_link')
    #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    #             # Checklist
    #             has_spare_tire = 'has_spare_tire' in request.form
    #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    #             has_warning_triangle = 'has_warning_triangle' in request.form
    #             has_tools = 'has_tools' in request.form
    #             has_oil_leaks = 'has_oil_leaks' in request.form
    #             has_gear_issue = 'has_gear_issue' in request.form
    #             has_clutch_issue = 'has_clutch_issue' in request.form
    #             has_engine_issue = 'has_engine_issue' in request.form
    #             has_windows_issue = 'has_windows_issue' in request.form
    #             has_tires_issue = 'has_tires_issue' in request.form
    #             has_body_issue = 'has_body_issue' in request.form
    #             has_electricity_issue = 'has_electricity_issue' in request.form
    #             has_lights_issue = 'has_lights_issue' in request.form
    #             has_ac_issue = 'has_ac_issue' in request.form
    
    #             handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
    #             handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
    #             # حفظ الصور والتواقيع
    #             saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams')
    #             saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures')
    #             saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures')
    #             movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature'), 'signatures')
    #             custom_logo_file = request.files.get('custom_logo_file')
    #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
    #             driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
    #             supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
    
    #             # 3. إنشاء كائن VehicleHandover وتعبئته بالبيانات الكاملة
    #             handover = VehicleHandover(
    #                 vehicle_id=vehicle.id, handover_type=handover_type, handover_date=handover_date,
    #                 handover_time=handover_time, mileage=mileage, project_name=project_name, city=city,
    #                 vehicle_car_type=f"{vehicle.make} {vehicle.model}", vehicle_plate_number=vehicle.plate_number,
    #                 vehicle_model_year=str(vehicle.year), employee_id=driver.id if driver else None,
    #                 person_name=driver.name if driver else person_name_from_form,
    #                 driver_company_id=driver.employee_id if driver else None,
    #                 driver_phone_number=driver.mobile if driver else None,
    #                 driver_residency_number=driver.national_id if driver else None,
    #                 driver_contract_status=driver.contract_status if driver else None,
    #                 driver_license_status=driver.license_status if driver else None,
    #                 driver_signature_path=saved_driver_sig_path,
    #                 supervisor_employee_id=supervisor.id if supervisor else None,
    #                 supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
    #                 supervisor_company_id=supervisor.employee_id if supervisor else None,
    #                 supervisor_phone_number=supervisor.mobile if supervisor else None,
    #                 supervisor_residency_number=supervisor.national_id if supervisor else None,
    #                 supervisor_contract_status=supervisor.contract_status if supervisor else None,
    #                 supervisor_license_status=supervisor.license_status if supervisor else None,
    #                 supervisor_signature_path=saved_supervisor_sig_path, reason_for_change=reason_for_change,
    #                 vehicle_status_summary=vehicle_status_summary, notes=notes,
    #                 reason_for_authorization=reason_for_authorization, authorization_details=authorization_details,
    #                 fuel_level=fuel_level, has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
    #                 has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
    #                 has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
    #                 has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
    #                 has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
    #                 has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    #                 has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
    #                 movement_officer_name=movement_officer_name,
    #                 movement_officer_signature_path=movement_officer_signature_path,
    #                 damage_diagram_path=saved_diagram_path, form_link=form_link,
    #                 custom_company_name=custom_company_name, custom_logo_path=saved_custom_logo_path
    #             )
    
    #             db.session.add(handover)
    #             db.session.flush() # الحصول على ID
    
    #             # 4. إنشاء طلب عملية تلقائي (منطق الويب)
    #             action_type = 'تسليم' if handover_type == 'delivery' else 'استلام'
    #             operation_title = f"طلب موافقة على {action_type} مركبة {vehicle.plate_number}"
    #             operation_description = f"تم إنشاء {action_type} للمركبة {vehicle.plate_number} عبر الجوال ويحتاج للموافقة."
    
    #             create_operation_request(
    #                 operation_type="handover", 
    #                 related_record_id=handover.id, 
    #                 vehicle_id=vehicle.id,
    #                 title=operation_title, 
    #                 description=operation_description, 
    #                 requested_by=current_user.id
    #             )
    
    #             # 5. حفظ المرفقات الإضافية (منطق الويب)
    #             files = request.files.getlist('files')
    #             for file in files:
    #                 if file and file.filename:
    #                     file_path, file_type = save_file(file, 'handover')
    #                     if file_path:
    #                         desc = request.form.get(f'description_{file.filename}', '')
    #                         attachment = VehicleHandoverImage(
    #                             handover_record_id=handover.id, file_path=file_path, file_type=file_type, 
    #                             image_path=file_path, file_description=desc, image_description=desc
    #                         )
    #                         db.session.add(attachment)
    
    #             db.session.commit()
    
    #             flash(f'تم إنشاء طلب {action_type} بنجاح، وهو الآن بانتظار الموافقة.', 'success')
    #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    #         except Exception as e:
    #             db.session.rollback()
    #             import traceback
    #             traceback.print_exc()
    #             flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
    #             return redirect(url_for('mobile.create_handover_mobile', handover_id=handover_id))
    
    
    # # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # # @bp.route('/vehicles/checklist/<int:handover_id>', methods=['GET', 'POST'])
    # # @login_required
    # # def create_handover_mobile(handover_id=None):
    # #     """
    # #     عرض ومعالجة نموذج تسليم/استلام السيارة (نسخة الهواتف المحمولة).
    # #     هذه النسخة مطابقة للمنطق الشامل الموجود في نسخة الويب.
    # #     """
    
    
        
    # #     # === معالجة طلب POST (عند إرسال النموذج) ===
    # #     if request.method == 'POST':
    # #         # فحص حجم البيانات المرسلة
    # #         content_length = request.content_length
    # #         if content_length and content_length > 20 * 1024 * 1024:  # 20 MB
    # #             size_mb = content_length / (1024 * 1024)
    # #             flash(f'حجم البيانات كبير جداً ({size_mb:.1f} ميجابايت). الحد الأقصى 20 ميجابايت. يرجى تقليل عدد الصور أو ضغطها قبل الإرسال.', 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #         # يجب اختيار المركبة أولاً في نسخة الموبايل
    # #         vehicle_id_str = request.form.get('vehicle_id')
    # #         if not vehicle_id_str:
    # #             flash('يجب اختيار مركبة أولاً.', 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile')) # أعد توجيه المستخدم لنفس الصفحة
    
    # #         vehicle = Vehicle.query.get_or_404(int(vehicle_id_str))
    
    # #         unsuitable_statuses = {
    # #             'in_workshop': 'لا يمكن تسليم أو استلام المركبة لأنها حالياً في الورشة.',
    # #             'accident': 'لا يمكن تسليم أو استلام المركبة لأنه مسجل عليها حادث نشط.',
    # #             'out_of_service': 'لا يمكن تسليم أو استلام المركبة لأنها "خارج الخدمة".'
    # #         }
    
    # #         if vehicle.status in unsuitable_statuses:
    # #             flash(f'❌ عملية مرفوضة: {unsuitable_statuses[vehicle.status]}', 'danger')
    # #             # أعد توجيهه إلى صفحة تفاصيل السيارة حيث يمكنه رؤية المشكلة
    # #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    # #         # 3. التحقق من منطق تسليم/استلام (نفس منطقك الحالي ولكن بشكل أنظف)
    # #         handover_type = request.form.get('handover_type')
    # #         if vehicle.status != 'available' and handover_type == 'delivery':
    # #             flash('⚠️ تنبيه: هذه المركبة غير متاحة للتسليم. النموذج تم تعديله لعملية "استلام" تلقائياً.', 'warning')
    # #             # يمكن أن يقوم Javasript في الواجهة بتغيير نوع العملية تلقائياً
    # #             # حالياً سنخبره أن يصحح ويعيد الإرسال
    # #             return redirect(url_for('mobile.create_handover_mobile', handover_id=handover_id))
            
    # #         print(vehicle)
    # #         if vehicle.status != 'available':
    # #                 # تحقق من أن العملية استلام أو تسليم
    # #                 handover_type = request.form.get('handover_type')
    # #                 if handover_type != 'return':
    # #                     flash('هذه المركبة غير متاحة للتسليم. يمكن فقط إجراء عملية استلام.', 'warning')
    # #                     return redirect(url_for('mobile.create_handover_mobile'))
    
    
    # #         # فحص قيود العمليات للمركبات خارج الخدمة
    # #         from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions
    # #         restrictions = check_vehicle_operation_restrictions(vehicle)
    # #         if restrictions['blocked']:
    # #             flash(restrictions['message'], 'danger')
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #         try:
    # #             # === 1. استخراج كل البيانات من النموذج (نفس منطق الويب) ===
    
    # #             # --- البيانات الأساسية للعملية ---
    # #             handover_type = request.form.get('handover_type')
    # #             handover_date_str = request.form.get('handover_date')
    # #             handover_time_str = request.form.get('handover_time')
                
    # #             # --- تحديد ما إذا كنا نعدل سجل موجود أم ننشئ جديد ---
    # #             is_editing = handover_id is not None
    # #             existing_handover = None
    # #             action = request.form.get('action', 'create')  # 'update', 'save_as_new', or 'create'
                
    # #             if is_editing:
    # #                 existing_handover = VehicleHandover.query.get_or_404(handover_id)
                
    # #             # --- معرفات الموظفين (السائق والمشرف) ---
    # #             employee_id_str = request.form.get('employee_id')
    # #             supervisor_employee_id_str = request.form.get('supervisor_employee_id')
    
    # #             # --- البيانات النصية والمتغيرة الأخرى ---
    # #             person_name_from_form = request.form.get('person_name', '').strip()
    # #             supervisor_name_from_form = request.form.get('supervisor_name', '').strip()
    # #             mileage = int(request.form.get('mileage', 0))
    # #             fuel_level = request.form.get('fuel_level')
    # #             project_name = request.form.get('project_name')
    # #             city = request.form.get('city')
    # #             reason_for_change = request.form.get('reason_for_change')
    # #             vehicle_status_summary = request.form.get('vehicle_status_summary')
    # #             notes = request.form.get('notes')
    # #             reason_for_authorization = request.form.get('reason_for_authorization')
    # #             authorization_details = request.form.get('authorization_details')
    # #             movement_officer_name = request.form.get('movement_officer_name')
    # #             form_link = request.form.get('form_link')
    # #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    # #             # --- بيانات قائمة الفحص (Checklist) ---
    # #             has_spare_tire = 'has_spare_tire' in request.form
    # #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    # #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    # #             has_warning_triangle = 'has_warning_triangle' in request.form
    # #             has_tools = 'has_tools' in request.form
    # #             has_oil_leaks = 'has_oil_leaks' in request.form
    # #             has_gear_issue = 'has_gear_issue' in request.form
    # #             has_clutch_issue = 'has_clutch_issue' in request.form
    # #             has_engine_issue = 'has_engine_issue' in request.form
    # #             has_windows_issue = 'has_windows_issue' in request.form
    # #             has_tires_issue = 'has_tires_issue' in request.form
    # #             has_body_issue = 'has_body_issue' in request.form
    # #             has_electricity_issue = 'has_electricity_issue' in request.form
    # #             has_lights_issue = 'has_lights_issue' in request.form
    # #             has_ac_issue = 'has_ac_issue' in request.form
    
    # #             # --- معالجة التواريخ والأوقات ---
    # #             handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
    # #             handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
    
    # #             # --- معالجة الصور والتواقيع (Base64) والملفات ---
    # #             saved_diagram_path = save_base64_image(request.form.get('damage_diagram_data'), 'diagrams')
    # #             saved_supervisor_sig_path = save_base64_image(request.form.get('supervisor_signature_data'), 'signatures')
    # #             saved_driver_sig_path = save_base64_image(request.form.get('driver_signature_data'), 'signatures')
    # #             movement_officer_signature_path = save_base64_image(request.form.get('movement_officer_signature'), 'signatures')
    
    # #             custom_logo_file = request.files.get('custom_logo_file')
    # #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    
    # #             # === 2. جلب الكائنات الكاملة من قاعدة البيانات ===
    # #             driver = Employee.query.get(employee_id_str) if employee_id_str and employee_id_str.isdigit() else None
    # #             supervisor = Employee.query.get(supervisor_employee_id_str) if supervisor_employee_id_str and supervisor_employee_id_str.isdigit() else None
                
    # #             # === 3. إنشاء أو تحديث كائن VehicleHandover ===
    # #             if is_editing and action == 'update':
    # #                 # تحديث السجل الموجود
    # #                 handover = existing_handover
    # #                 handover.vehicle_id = vehicle.id
    # #                 handover.handover_type = handover_type
    # #                 handover.handover_date = handover_date
    # #                 handover.handover_time = handover_time
    # #                 handover.mileage = mileage
    # #                 handover.project_name = project_name
    # #                 handover.city = city
                    
    # #                 # تحديث بيانات المركبة
    # #                 handover.vehicle_car_type = f"{vehicle.make} {vehicle.model}"
    # #                 handover.vehicle_plate_number = vehicle.plate_number
    # #                 handover.vehicle_model_year = str(vehicle.year)
    
    # #                 # تحديث بيانات السائق
    # #                 handover.employee_id = driver.id if driver else None
    # #                 handover.person_name = driver.name if driver else person_name_from_form
    # #                 handover.driver_company_id = driver.employee_id if driver else None
    # #                 handover.driver_phone_number = driver.mobile if driver else None
    # #                 handover.driver_residency_number = driver.national_id if driver else None
    # #                 handover.driver_contract_status = driver.contract_status if driver else None
    # #                 handover.driver_license_status = driver.license_status if driver else None
    # #                 if saved_driver_sig_path:
    # #                     handover.driver_signature_path = saved_driver_sig_path
    
    # #                 # تحديث بيانات المشرف
    # #                 handover.supervisor_employee_id = supervisor.id if supervisor else None
    # #                 handover.supervisor_name = supervisor.name if supervisor else supervisor_name_from_form
    # #                 handover.supervisor_company_id = supervisor.employee_id if supervisor else None
    # #                 handover.supervisor_phone_number = supervisor.mobile if supervisor else None
    # #                 handover.supervisor_residency_number = supervisor.national_id if supervisor else None
    # #                 handover.supervisor_contract_status = supervisor.contract_status if supervisor else None
    # #                 handover.supervisor_license_status = supervisor.license_status if supervisor else None
    # #                 if saved_supervisor_sig_path:
    # #                     handover.supervisor_signature_path = saved_supervisor_sig_path
                    
    # #                 # تحديث باقي الحقول
    # #                 handover.reason_for_change = reason_for_change
    # #                 handover.vehicle_status_summary = vehicle_status_summary
    # #                 handover.notes = notes
    # #                 handover.reason_for_authorization = reason_for_authorization
    # #                 handover.authorization_details = authorization_details
    # #                 handover.fuel_level = fuel_level
                    
    # #                 # تحديث قائمة الفحص
    # #                 handover.has_spare_tire = has_spare_tire
    # #                 handover.has_fire_extinguisher = has_fire_extinguisher
    # #                 handover.has_first_aid_kit = has_first_aid_kit
    # #                 handover.has_warning_triangle = has_warning_triangle
    # #                 handover.has_tools = has_tools
    # #                 handover.has_oil_leaks = has_oil_leaks
    # #                 handover.has_gear_issue = has_gear_issue
    # #                 handover.has_clutch_issue = has_clutch_issue
    # #                 handover.has_engine_issue = has_engine_issue
    # #                 handover.has_windows_issue = has_windows_issue
    # #                 handover.has_tires_issue = has_tires_issue
    # #                 handover.has_body_issue = has_body_issue
    # #                 handover.has_electricity_issue = has_electricity_issue
    # #                 handover.has_lights_issue = has_lights_issue
    # #                 handover.has_ac_issue = has_ac_issue
                    
    # #                 # تحديث الحقول الإضافية
    # #                 handover.movement_officer_name = movement_officer_name
    # #                 if movement_officer_signature_path:
    # #                     handover.movement_officer_signature_path = movement_officer_signature_path
    # #                 if saved_diagram_path:
    # #                     handover.damage_diagram_path = saved_diagram_path
    # #                 handover.form_link = form_link
    # #                 handover.custom_company_name = custom_company_name
    # #                 if saved_custom_logo_path:
    # #                     handover.custom_logo_path = saved_custom_logo_path
    # #             else:
    # #                 # إنشاء سجل جديد (إما إنشاء جديد أو حفظ كنسخة جديدة)
    # #                 handover = VehicleHandover(
    # #                     vehicle_id=vehicle.id,
    # #                     handover_type=handover_type,
    # #                     handover_date=handover_date,
    # #                     handover_time=handover_time,
    # #                     mileage=mileage,
    # #                     project_name=project_name,
    # #                     city=city,
                        
    # #                     # نسخ بيانات المركبة "وقت التسليم"
    # #                     vehicle_car_type=f"{vehicle.make} {vehicle.model}",
    # #                     vehicle_plate_number=vehicle.plate_number,
    # #                     vehicle_model_year=str(vehicle.year),
    
    # #                 # نسخ بيانات السائق "وقت التسليم"
    # #                 employee_id=driver.id if driver else None,
    # #                 person_name=driver.name if driver else person_name_from_form,
    # #                 driver_company_id=driver.employee_id if driver else None,
    # #                 driver_phone_number=driver.mobile if driver else None,
    # #                 driver_residency_number=driver.national_id if driver else None,
    # #                 driver_contract_status=driver.contract_status if driver else None,
    # #                 driver_license_status=driver.license_status if driver else None,
    # #                 driver_signature_path=saved_driver_sig_path,
    
    # #                 # نسخ بيانات المشرف "وقت التسليم"
    # #                 supervisor_employee_id=supervisor.id if supervisor else None,
    # #                 supervisor_name=supervisor.name if supervisor else supervisor_name_from_form,
    # #                 supervisor_company_id=supervisor.employee_id if supervisor else None,
    # #                 supervisor_phone_number=supervisor.mobile if supervisor else None,
    # #                 supervisor_residency_number=supervisor.national_id if supervisor else None,
    # #                 supervisor_contract_status=supervisor.contract_status if supervisor else None,
    # #                 supervisor_license_status=supervisor.license_status if supervisor else None,
    # #                 supervisor_signature_path=saved_supervisor_sig_path,
    
    # #                 # باقي الحقول التفصيلية
    # #                 reason_for_change=reason_for_change,
    # #                 vehicle_status_summary=vehicle_status_summary,
    # #                 notes=notes,
    # #                 reason_for_authorization=reason_for_authorization,
    # #                 authorization_details=authorization_details,
    # #                 fuel_level=fuel_level,
    
    # #                 # قائمة الفحص
    # #                 has_spare_tire=has_spare_tire, has_fire_extinguisher=has_fire_extinguisher,
    # #                 has_first_aid_kit=has_first_aid_kit, has_warning_triangle=has_warning_triangle,
    # #                 has_tools=has_tools, has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue,
    # #                 has_clutch_issue=has_clutch_issue, has_engine_issue=has_engine_issue,
    # #                 has_windows_issue=has_windows_issue, has_tires_issue=has_tires_issue,
    # #                 has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    # #                 has_lights_issue=has_lights_issue, has_ac_issue=has_ac_issue,
    
    # #                 # حقول إضافية
    # #                 movement_officer_name=movement_officer_name,
    # #                 movement_officer_signature_path=movement_officer_signature_path,
    # #                 damage_diagram_path=saved_diagram_path,
    # #                 form_link=form_link,
    # #                 custom_company_name=custom_company_name,
    # #                 custom_logo_path=saved_custom_logo_path
    # #             )
    
    # #             db.session.add(handover)
                
    # #             # تحديث حالة السيارة تلقائياً إلى "متاحة" بعد عملية الاستلام
    # #             if handover_type == 'return':
    # #                 vehicle.status = 'available'
    # #                 vehicle.updated_at = datetime.utcnow()
    # #                 log_audit('update', 'vehicle_status', vehicle.id, 
    # #                          f'تم تحديث حالة السيارة {vehicle.plate_number} إلى "متاحة" بعد عملية الاستلام')
                
    # #             db.session.commit()
    
    # #             # === 4. حفظ المرفقات الإضافية وتحديث حالة السائق ===
    # #             # (استخدام نفس منطق الويب المنظم)
    # #             update_vehicle_driver(vehicle.id) # دالة مساعدة لتحديث السائق المرتبط بالمركبة
    # #             update_vehicle_state(vehicle.id)
    
    # #             files = request.files.getlist('files')
    # #             for file in files:
    # #                 if file and file.filename:
    # #                     file_path, file_type = save_file(file, 'handover')
    # #                     if file_path:
    # #                         file_description = request.form.get(f'description_{file.filename}', '')
    # #                         file_record = VehicleHandoverImage(
    # #                             handover_record_id=handover.id,
    # #                             file_path=file_path, file_type=file_type, file_description=file_description,
    # #                             image_path=file_path, image_description=file_description # للتوافق
    # #                         )
    # #                         db.session.add(file_record)
    # #             db.session.commit()
    
    # #             action_type = 'تسليم' if handover_type == 'delivery' else 'استلام'
    # #             if is_editing and action == 'update':
    # #                 log_audit('update', 'vehicle_handover', handover.id, f'تم تعديل نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم تحديث نموذج {action_type} بنجاح!', 'success')
    # #             elif is_editing and action == 'save_as_new':
    # #                 log_audit('create', 'vehicle_handover', handover.id, f'تم إنشاء نسخة جديدة من نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم حفظ نسخة جديدة من نموذج {action_type} بنجاح!', 'success')
    # #             else:
    # #                 log_audit('create', 'vehicle_handover', handover.id, f'تم إنشاء نموذج {action_type} (موبايل) للسيارة: {vehicle.plate_number}')
    # #                 flash(f'تم إنشاء نموذج {action_type} بنجاح!', 'success')
                
    
    # #             # إنشاء طلب عملية تلقائياً لإدارة العمليات
    # #             try:
    # #                 operation_title = f"طلب موافقة على {action_type} مركبة {vehicle.plate_number}"
    # #                 operation_description = f"تم إنشاء {action_type} للمركبة {vehicle.plate_number} من قبل {current_user.username} ويحتاج للموافقة الإدارية"
                    
    # #                 operation = create_operation_request(
    # #                     operation_type="handover",
    # #                     related_record_id=handover.id,
    # #                     vehicle_id=vehicle.id,
    # #                     title=operation_title,
    # #                     description=operation_description,
    # #                     requested_by=current_user.id,
    # #                     priority="normal"
    # #                 )
                    
    # #                 # حفظ طلب العملية والإشعارات
    # #                 db.session.commit()
                    
    # #                 print(f"تم تسجيل عملية {action_type} بنجاح: {operation.id}")
    # #                 current_app.logger.debug(f"تم إنشاء طلب عملية للتسليم والاستلام: {handover.id} برقم عملية: {operation.id}")
                    
    # #                 # التحقق من وجود العملية في قاعدة البيانات
    # #                 saved_operation = OperationRequest.query.get(operation.id)
    # #                 if saved_operation:
    # #                     print(f"تأكيد: عملية {action_type} {operation.id} محفوظة في قاعدة البيانات")
    # #                 else:
    # #                     print(f"تحذير: عملية {action_type} {operation.id} غير موجودة في قاعدة البيانات!")
                    
    # #             except Exception as e:
    # #                 print(f"خطأ في إنشاء طلب العملية للتسليم والاستلام: {str(e)}")
    # #                 current_app.logger.error(f"خطأ في إنشاء طلب العملية للتسليم والاستلام: {str(e)}")
    # #                 import traceback
    # #                 current_app.logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
    # #                 # لا نوقف العملية إذا فشل إنشاء طلب العملية
    # #             return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle.id))
    
    # #         except Exception as e:
    # #             db.session.rollback()
    # #             import traceback
    # #             traceback.print_exc()
    # #             flash(f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', 'danger')
    # #             # لا حاجة لإعادة عرض الصفحة مع البيانات، الأفضل إعادة التوجيه مع رسالة خطأ
    # #             return redirect(url_for('mobile.create_handover_mobile'))
    
    # #     # === معالجة طلب GET (عند عرض الصفحة لأول مرة) ===
    # #     # جلب القوائم اللازمة لعرضها في النموذج
    # #     vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    
    # #     # جلب الموظفين مع تحميل علاقة الأقسام
    # #     from sqlalchemy.orm import joinedload
    # #     employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    # #     departments = Department.query.order_by(Department.name).all()
    
    # #     # تحويل بيانات الموظفين إلى JSON لاستخدامها في JavaScript
    # #     employees_as_dicts = [e.to_dict() for e in employees]
    # #     now = datetime.now()
    # #     now_date = now.strftime('%Y-%m-%d')
    # #     now_time = now.strftime('%H:%M')
        
    # #     # جلب بيانات التعديل إذا كان موجوداً
    # #     existing_handover = None
    # #     is_editing = False
    # #     if handover_id:
    # #         existing_handover = VehicleHandover.query.get(handover_id)
    # #         if existing_handover:
    # #             is_editing = True
    # #             # استخدام بيانات السجل الموجود للتاريخ والوقت
    # #             now_date = existing_handover.handover_date.strftime('%Y-%m-%d') if existing_handover.handover_date else now_date
    # #             now_time = existing_handover.handover_time.strftime('%H:%M') if existing_handover.handover_time else now_time
    # #             # تحويل الكائن إلى قاموس للاستخدام في JavaScript
    # #             existing_handover = existing_handover.to_dict()
        
    # #     return render_template(
    # #         'mobile/vehicle_checklist.html', 
    # #         vehicles=vehicles,
    # #         employees=employees,
    # #         departments=departments,
    # #         handover_types=HANDOVER_TYPE_CHOICES, # استخدام نفس قائمة الويب
    # #         employeeData=employees_as_dicts,
    # #         now_date=now_date,
    # #         now_time=now_time,
    # #         existing_handover=existing_handover,  # تمرير بيانات التعديل
    # #         is_editing=is_editing  # تمرير حالة التعديل
    # #     )
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # # @bp.route('/vehicles/checklist', methods=['GET', 'POST'])
    # # @login_required
    # # def create_handover_mobile():
    # #     """
    # #     عرض ومعالجة نموذج تسليم/استلام السيارة (نسخة الهواتف المحمولة).
    # #     """
    # #      # 1. جلب البيانات الأساسية
    # #     vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    
    # #     # 1. معالجة إرسال النموذج (POST request)
    # #     if request.method == 'POST':
    # #         try:
    # #             vehicle_id = request.form.get('vehicle_id')
    # #             if not vehicle_id:
    # #                 flash('يجب اختيار مركبة أولاً.', 'danger')
    
    # #                 # إعادة تحميل الصفحة مع البيانات القديمة (سنتعامل مع هذا لاحقاً إذا لزم الأمر)
    
    # #             # --- استخراج البيانات من النموذج ---
    # #             # القسم 1: معلومات أساسية
    # #             handover_type = request.form.get('handover_type')
    # #             handover_date = datetime.strptime(request.form.get('handover_date'), '%Y-%m-%d').date()
    # #             mileage = int(request.form.get('mileage'))
    # #             fuel_level = request.form.get('fuel_level')
    # #             person_name = request.form.get('person_name')
    # #             employee_id = request.form.get('employee_id')
    
    # #             # القسم 2: فحص وتجهيزات
    # #             # التجهيزات
    # #             has_spare_tire = 'has_spare_tire' in request.form
    # #             has_fire_extinguisher = 'has_fire_extinguisher' in request.form
    # #             has_first_aid_kit = 'has_first_aid_kit' in request.form
    # #             has_warning_triangle = 'has_warning_triangle' in request.form
    # #             has_tools = 'has_tools' in request.form
    # #             # فحص المشاكل
    # #             has_oil_leaks = 'has_oil_leaks' in request.form
    # #             has_gear_issue = 'has_gear_issue' in request.form
    # #             has_clutch_issue = 'has_clutch_issue' in request.form
    # #             has_engine_issue = 'has_engine_issue' in request.form
    # #             has_ac_issue = 'has_ac_issue' in request.form
    # #             has_windows_issue = 'has_windows_issue' in request.form
    # #             has_tires_issue = 'has_tires_issue' in request.form
    # #             has_body_issue = 'has_body_issue' in request.form
    # #             has_electricity_issue = 'has_electricity_issue' in request.form
    # #             has_lights_issue = 'has_lights_issue' in request.form
    
    # #             # القسم 4: ملاحظات وتوثيق
    # #             vehicle_condition = request.form.get('vehicle_condition')
    # #             notes = request.form.get('notes')
    # #             form_link = request.form.get('form_link')
    
    # #             # القسم 5: تخصيص التقرير
    # #             custom_company_name = request.form.get('custom_company_name', '').strip() or None
    
    # #             # --- معالجة الملفات المرفوعة والتواقيع المرسومة ---
    # #             # (سنستخدم نفس الدوال المساعدة التي أنشأناها سابقاً)
    # #             custom_logo_file = request.files.get('custom_logo_file')
    # #             damage_diagram_base64 = request.form.get('damage_diagram_data')
    # #             supervisor_sig_base64 = request.form.get('supervisor_signature_data')
    # #             driver_sig_base64 = request.form.get('driver_signature_data')
    
    # #             saved_custom_logo_path = save_uploaded_file(custom_logo_file, 'logos')
    # #             saved_diagram_path = save_base64_image(damage_diagram_base64, 'diagrams')
    # #             saved_supervisor_sig_path = save_base64_image(supervisor_sig_base64, 'signatures')
    # #             saved_driver_sig_path = save_base64_image(driver_sig_base64, 'signatures')
    
    # #             # --- إنشاء السجل في قاعدة البيانات ---
    # #             new_handover = VehicleHandover(
    # #                 vehicle_id=int(vehicle_id),
    # #                 handover_type=handover_type,
    # #                 handover_date=handover_date,
    # #                 mileage=mileage,
    # #                 fuel_level=fuel_level,
    # #                 person_name=person_name,
    # #                 employee_id=int(employee_id) if employee_id else None,
    # #                 # التجهيزات
    # #                 has_spare_tire=has_spare_tire,
    # #                 has_fire_extinguisher=has_fire_extinguisher,
    # #                 has_first_aid_kit=has_first_aid_kit,
    # #                 has_warning_triangle=has_warning_triangle,
    # #                 has_tools=has_tools,
    # #                 # فحص المشاكل
    # #                 has_oil_leaks=has_oil_leaks, has_gear_issue=has_gear_issue, has_clutch_issue=has_clutch_issue,
    # #                 has_engine_issue=has_engine_issue, has_ac_issue=has_ac_issue, has_windows_issue=has_windows_issue,
    # #                 has_tires_issue=has_tires_issue, has_body_issue=has_body_issue, has_electricity_issue=has_electricity_issue,
    # #                 has_lights_issue=has_lights_issue,
    # #                 # التوثيق
    # #                 vehicle_condition=vehicle_condition, notes=notes, form_link=form_link,
    # #                 # التخصيص
    # #                 custom_company_name=custom_company_name,
    # #                 custom_logo_path=saved_custom_logo_path,
    # #                 # الصور المحفوظة
    # #                 damage_diagram_path=saved_diagram_path,
    # #                 supervisor_signature_path=saved_supervisor_sig_path,
    # #                 driver_signature_path=saved_driver_sig_path
    # #             )
    
    # #             db.session.add(new_handover)
    # #             db.session.commit()
    
    # #             # معالجة رفع الملفات المتعددة
    # #             files = request.files.getlist('files')
    # #             for file in files:
    # #                 # استخدم دالة حفظ الملفات التي لديك
    # #                 saved_path, file_type = save_file(file, 'handover_docs')
    # #                 if saved_path:
    # #                     # احفظ المسار في جدول الملفات المرتبط
    # #                     pass # أضف هنا منطق حفظ الملفات في جدول VehicleHandoverImage
    
    # #             # تحديث حالة السيارة إذا لزم الأمر
    # #             vehicle = Vehicle.query.get_or_404(vehicle_id)
    # #             if handover_type == 'return': vehicle.status = 'available'
    # #             elif handover_type == 'delivery': vehicle.status = 'in_project'
    # #             db.session.commit()
    
    # #             flash('تم حفظ النموذج بنجاح!', 'success')
    # #             return redirect(url_for('mobile.vehicle_checklist_list', id=id))
    
    # #         except Exception as e:
    # #             db.session.rollback()
    # #             flash(f'حدث خطأ أثناء حفظ النموذج: {e}', 'danger')
    
    
    
    
    # #     # 2. جلب القوائم اللازمة للنموذج (الموظفين، الأقسام)
    # #     # من الأفضل جلبها دائماً لتعمل واجهة البحث بشكل صحيح
    # #     employees = Employee.query.order_by(Employee.name).all()
    # #     departments = Department.query.order_by(Department.name).all()
    
    # #     # 3. تعريف أنواع العمليات كنص удобочитаемый
    # #     handover_types = {
    # #         'delivery': 'تسليم سيارة جديدة',
    # #         'return': 'استلام سيارة عائدة'
    # #     }
    
    # #     # 3. تحديد نوع العملية الافتراضي (إذا تم تمريره كمعلمة)
    # #     # هذا مفيد إذا أتيت من زر "تسليم" أو "استلام" محدد
    
    # #     # تعريف أنواع العمليات كنص удобочитаемый
    # #     handover_types = {
    # #         'delivery': 'تسليم السيارة',
    # #         'return': 'استلام السيارة'
    # #         # يمكنك إضافة أنواع أخرى هنا مثل 'receive_from_workshop'
    # #     }
    
    # #     # في أعلى ملف الـ routes
    
    # #       # داخل دالة create_handover_mobile، عند استدعاء render_template
    # #     # الكود الجديد والأبسط في route
    # #     employees_as_dicts = [e.to_dict() for e in employees]
    
    # #    # 4. عرض القالب وتمرير قائمة المركبات إليه
    
    # #     # 5. عرض القالب للـ GET request
    # #     return render_template(
    # #         'mobile/vehicle_checklist.html',
    # #         vehicles=vehicles, # <<-- المتغير الجديد والمهم
    # #         employees=employees,
    # #         departments=departments,
    # #         handover_types=handover_types,
    # #         employeeData=employees_as_dicts # إرسال البيانات كقائمة من القواميس
    # #     )
    
    
    
    
    
    
    # # قائمة فحوصات السيارة - النسخة المحمولة
    # @bp.route('/vehicles/checklist/list')
    # @login_required
    # def vehicle_checklist_list():
    #     """قائمة فحوصات السيارة للنسخة المحمولة"""
    #     page = request.args.get('page', 1, type=int)
    #     per_page = 20  # عدد العناصر في الصفحة الواحدة
    
    #     # فلترة حسب السيارة
    #     vehicle_id = request.args.get('vehicle_id', '')
    #     # فلترة حسب نوع الفحص
    #     inspection_type = request.args.get('inspection_type', '')
    #     # فلترة حسب التاريخ
    #     from_date = request.args.get('from_date', '')
    #     to_date = request.args.get('to_date', '')
    
    #     # بناء استعلام قاعدة البيانات
    #     query = VehicleChecklist.query
    
    #     # تطبيق الفلاتر إذا تم تحديدها
    #     if vehicle_id:
    #         query = query.filter(VehicleChecklist.vehicle_id == vehicle_id)
    
    #     if inspection_type:
    #         query = query.filter(VehicleChecklist.inspection_type == inspection_type)
    
    #     if from_date:
    #         try:
    #             from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
    #             query = query.filter(VehicleChecklist.inspection_date >= from_date_obj)
    #         except ValueError:
    #             pass
    
    #     if to_date:
    #         try:
    #             to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    #             query = query.filter(VehicleChecklist.inspection_date <= to_date_obj)
    #         except ValueError:
    #             pass
    
    #     # تنفيذ الاستعلام مع الترتيب والتصفح
    #     paginator = query.order_by(VehicleChecklist.inspection_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    #     checklists = paginator.items
    
    #     # الحصول على بيانات السيارات لعرضها في القائمة
    #     vehicles = Vehicle.query.all()
    
    #     print(vehicles)
    
    #     # تحويل بيانات الفحوصات إلى تنسيق مناسب للعرض
    #     checklists_data = []
    #     for checklist in checklists:
    #         vehicle = Vehicle.query.get(checklist.vehicle_id)
    #         if vehicle:
    #             checklist_data = {
    #                 'id': checklist.id,
    #                 'vehicle_name': f"{vehicle.make} {vehicle.model}",
    #                 'vehicle_plate': vehicle.plate_number,
    #                 'inspection_date': checklist.inspection_date,
    #                 'inspection_type': checklist.inspection_type,
    #                 'inspector_name': checklist.inspector_name,
    #                 'status': checklist.status,
    #                 'completion_percentage': checklist.completion_percentage,
    #                 'summary': checklist.summary
    #             }
    #             checklists_data.append(checklist_data)
    
    #     return render_template('mobile/vehicle_checklist_list.html',
    #                           checklists=checklists_data,
    #                           pagination=paginator,
    #                           vehicles=vehicles,
    #                           selected_vehicle=vehicle_id,
    #                           selected_type=inspection_type,
    #                           from_date=from_date,
    #                           to_date=to_date)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # # تفاصيل فحص السيارة - النسخة المحمولة
    # @bp.route('/vehicles/checklist/<int:checklist_id>')
    # @login_required
    # def vehicle_checklist_details(checklist_id):
    #     """تفاصيل فحص السيارة للنسخة المحمولة"""
    #     # الحصول على بيانات الفحص من قاعدة البيانات
    #     checklist = VehicleChecklist.query.get_or_404(checklist_id)
    
        
    #     # الحصول على بيانات السيارة وإضافة تحذير عند المراجعة
    #     vehicle = Vehicle.query.get(checklist.vehicle_id)
        
    #     # فحص حالة السيارة لإضافة تحذير في واجهة المراجعة
    #     from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions
    #     restrictions = check_vehicle_operation_restrictions(vehicle)
    #     vehicle_warning = restrictions['message'] if restrictions['blocked'] else None
        
    
    #     # جمع بيانات عناصر الفحص مرتبة حسب الفئة
    #     checklist_items = {}
    #     for item in checklist.checklist_items:
    #         if item.category not in checklist_items:
    #             checklist_items[item.category] = []
    
    #         checklist_items[item.category].append(item)
    
    #     # الحصول على علامات التلف المرتبطة بهذا الفحص
    #     damage_markers = VehicleDamageMarker.query.filter_by(checklist_id=checklist_id).all()
    
    #     # الحصول على صور الفحص المرفقة
    #     checklist_images = VehicleChecklistImage.query.filter_by(checklist_id=checklist_id).all()
    
    #     return render_template('mobile/vehicle_checklist_details.html',
    #                           checklist=checklist,
    #                           vehicle=vehicle,
    #                           checklist_items=checklist_items,
    #                           damage_markers=damage_markers,
    #                           checklist_images=checklist_images,
    #                           vehicle_warning=vehicle_warning)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # تصدير فحص السيارة إلى PDF - النسخة المحمولة
    @bp.route('/vehicles/checklist/<int:checklist_id>/pdf')
    @login_required
    def mobile_vehicle_checklist_pdf(checklist_id):
        """تصدير تقرير فحص المركبة إلى PDF مع عرض علامات التلف"""
        try:
            # الحصول على بيانات الفحص
            checklist = VehicleChecklist.query.get_or_404(checklist_id)
    
            
            # الحصول على بيانات المركبة وفحص حالتها
            vehicle = Vehicle.query.get_or_404(checklist.vehicle_id)
            
            # فحص حالة السيارة - إضافة تحذير للسيارات خارج الخدمة
            from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions
            restrictions = check_vehicle_operation_restrictions(vehicle)
            if restrictions['blocked']:
                print(f"تحذير: {restrictions['message']}")
            
    
            # جمع بيانات عناصر الفحص مرتبة حسب الفئة
            checklist_items = {}
            for item in checklist.checklist_items:
                if item.category not in checklist_items:
                    checklist_items[item.category] = []
    
                checklist_items[item.category].append(item)
    
            # الحصول على علامات التلف المرتبطة بهذا الفحص
            damage_markers = VehicleDamageMarker.query.filter_by(checklist_id=checklist_id).all()
    
            # الحصول على صور الفحص المرفقة
            checklist_images = VehicleChecklistImage.query.filter_by(checklist_id=checklist_id).all()
    
            # استيراد تابع إنشاء PDF
            from src.utils.vehicle_checklist_pdf import create_vehicle_checklist_pdf
    
            # إنشاء ملف PDF
            pdf_buffer = create_vehicle_checklist_pdf(
                checklist=checklist,
                vehicle=vehicle,
                checklist_items=checklist_items,
                damage_markers=damage_markers,
                checklist_images=checklist_images
            )
    
            # إنشاء استجابة تحميل للملف
            from flask import make_response
            response = make_response(pdf_buffer.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=vehicle_checklist_{checklist_id}.pdf'
    
            return response
    
        except Exception as e:
            # تسجيل الخطأ للمساعدة في تشخيص المشكلة
            import traceback
            error_traceback = traceback.format_exc()
            app.logger.error(f"خطأ في إنشاء PDF لفحص المركبة: {str(e)}\n{error_traceback}")
            flash(f'حدث خطأ أثناء إنشاء ملف PDF: {str(e)}', 'danger')
            return redirect(url_for('mobile.vehicle_checklist_details', checklist_id=checklist_id))
    
    
    # صفحة الرسوم والتكاليف - النسخة المحمولة (النسخة الأصلية)
