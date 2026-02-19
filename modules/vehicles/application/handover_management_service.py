"""
HandoverManagementService - Service Layer for Vehicle Handover Operations

This module encapsulates all business logic for vehicle handover (delivery/return) operations.
Extracted from presentation/api/mobile/vehicle_routes.py as part of Phase 3 refactoring.

Responsibilities:
- Handover type determination (delivery vs return)
- Form data processing and validation
- Employee/driver lookup and assignment
- Image and signature processing (base64 and file uploads)
- Operation request creation for approval workflow
- Vehicle driver history tracking
- File attachment handling

Created: 2026-02-15
Phase: 3 - Handover Module Refactoring
"""

import os
import uuid
import base64
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple, List
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from core.extensions import db
from modules.vehicles.domain.models import Vehicle, VehicleHandover, VehicleHandoverImage
from domain.employees.models import Employee, Department
from modules.operations.domain.models import OperationRequest
from services.helper_functions import log_activity
from services.operation_requests import create_operation_request
from utils.vehicle_route_helpers import update_vehicle_driver, update_vehicle_state


# ============================================================================
# HELPER FUNCTIONS - Image and File Processing
# ============================================================================

def _save_base64_image(base64_string: str, subfolder: str, static_folder: str) -> Optional[str]:
    """
    Save Base64 encoded image data to file system.
    
    Args:
        base64_string: Base64 encoded image data with header (data:image/png;base64,...)
        subfolder: Subfolder within static/uploads/ (e.g., 'signatures', 'diagrams')
        static_folder: Flask app.static_folder path
    
    Returns:
        Relative path to saved image (e.g., 'signatures/abc123.png') or None if failed
    """
    if not base64_string or not base64_string.startswith('data:image/'):
        return None
    
    try:
        # Prepare upload directory
        upload_folder = os.path.join(static_folder, 'uploads', subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Decode Base64 data
        header, encoded_data = base64_string.split(',', 1)
        image_data = base64.b64decode(encoded_data)
        
        # Generate unique filename and save
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(upload_folder, filename)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Return relative path for database storage
        return os.path.join(subfolder, filename)
    
    except Exception as e:
        print(f"Error saving Base64 image: {e}")
        return None


def _save_uploaded_file(file: FileStorage, subfolder: str, static_folder: str) -> Optional[str]:
    """
    Save uploaded file to file system with unique name.
    
    Args:
        file: Werkzeug FileStorage object from request.files
        subfolder: Subfolder within static/uploads/
        static_folder: Flask app.static_folder path
    
    Returns:
        Relative path to saved file (e.g., 'static/uploads/logos/file_abc123.png') or None
    """
    if not file or not file.filename:
        return None
    
    try:
        # Prepare upload directory
        upload_folder = os.path.join(static_folder, 'uploads', subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate secure unique filename
        filename_secure = secure_filename(file.filename)
        name, ext = os.path.splitext(filename_secure)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Return full relative path (matching original save_uploaded_file pattern)
        return f"static/uploads/{subfolder}/{unique_filename}"
    
    except Exception as e:
        print(f"Error saving uploaded file: {e}")
        return None


def _save_handover_file(file: FileStorage, folder: str, static_folder: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Save handover attachment file (image or PDF) to file system.
    
    Args:
        file: Werkzeug FileStorage object
        folder: Target folder name (e.g., 'handover')
        static_folder: Flask app.static_folder path
    
    Returns:
        Tuple of (file_path, file_type) or (None, None) if failed
    """
    if not file or not file.filename:
        return None, None
    
    try:
        # Extract filename parts
        original_filename = file.filename
        name_part, ext_part = os.path.splitext(original_filename)
        
        # Secure filename (name only, preserve extension)
        safe_name = secure_filename(name_part) or 'file'
        unique_filename = f"{uuid.uuid4()}_{safe_name}{ext_part}"
        
        # Ensure upload directory exists
        upload_folder = os.path.join(static_folder, 'uploads', folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Determine file type
        ext_lower = ext_part.lower()
        if ext_lower in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.heif'):
            file_type = 'image'
        elif ext_lower == '.pdf':
            file_type = 'pdf'
        else:
            file_type = 'other'
        
        # Return relative path for database
        return f"uploads/{folder}/{unique_filename}", file_type
    
    except Exception as e:
        print(f"Error saving handover file: {e}")
        return None, None


# ============================================================================
# HANDOVER LOGIC HELPERS
# ============================================================================

def _determine_handover_mode(vehicle_id: int) -> Dict[str, Any]:
    """
    Smart logic to determine handover type (delivery vs return) based on vehicle history.
    
    Analyzes approved and pending handover records to determine:
    - If vehicle should be delivered (to new driver)
    - If vehicle should be returned (from current driver)
    
    Args:
        vehicle_id: Vehicle ID to analyze
    
    Returns:
        Dictionary containing:
            - force_mode: 'delivery' or 'return'
            - current_driver_info: VehicleHandover object if return mode, else None
            - info_message: User-friendly description of the mode
    """
    # Query for approved handover IDs
    approved_handover_ids_subquery = db.session.query(
        OperationRequest.related_record_id
    ).filter(
        OperationRequest.operation_type == 'handover',
        OperationRequest.status == 'approved',
        OperationRequest.vehicle_id == vehicle_id
    ).subquery()
    
    # Query for all handover request IDs (any status)
    all_handover_request_ids_subquery = db.session.query(
        OperationRequest.related_record_id
    ).filter(
        OperationRequest.operation_type == 'handover',
        OperationRequest.vehicle_id == vehicle_id
    ).subquery()
    
    # Base query for "official" handovers (approved OR not in any operation request)
    base_official_query = VehicleHandover.query.filter(
        VehicleHandover.vehicle_id == vehicle_id,
        or_(
            VehicleHandover.id.in_(approved_handover_ids_subquery),
            ~VehicleHandover.id.in_(all_handover_request_ids_subquery)
        )
    )
    
    # Find latest delivery and return
    latest_delivery = base_official_query.filter(
        VehicleHandover.handover_type == 'delivery'
    ).order_by(VehicleHandover.created_at.desc()).first()
    
    latest_return = base_official_query.filter(
        VehicleHandover.handover_type == 'return'
    ).order_by(VehicleHandover.created_at.desc()).first()
    
    # Determine mode based on latest operation
    if latest_delivery and (not latest_return or latest_delivery.created_at > latest_return.created_at):
        # Vehicle was delivered and not returned yet → force return mode
        return {
            'force_mode': 'return',
            'current_driver_info': latest_delivery,
            'info_message': f"تنبيه: المركبة مسلمة حالياً لـِ '{latest_delivery.person_name}'. النموذج معد لعملية الاستلام فقط."
        }
    else:
        # Vehicle is available → force delivery mode
        return {
            'force_mode': 'delivery',
            'current_driver_info': None,
            'info_message': "المركبة متاحة حالياً. النموذج معد لعملية التسليم لسائق جديد."
        }


def _lookup_employee_by_id_or_name(employee_id_str: str, person_name: str) -> Optional[Employee]:
    """
    Lookup employee by ID first, fallback to name search if not found.
    
    Args:
        employee_id_str: Employee ID as string (may be empty or non-digit)
        person_name: Person name to search if ID lookup fails
    
    Returns:
        Employee object or None if not found
    """
    # Try ID lookup first
    if employee_id_str and employee_id_str.isdigit():
        employee = Employee.query.get(employee_id_str)
        if employee:
            return employee
    
    # Fallback to name search
    if person_name and person_name.strip():
        return Employee.query.filter(
            Employee.name.ilike(f"%{person_name.strip()}%")
        ).first()
    
    return None


# ============================================================================
# PUBLIC SERVICE METHODS
# ============================================================================

def create_handover_record(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files: Dict[str, Any],
    static_folder: str,
    current_user_id: int
) -> Tuple[bool, str, Optional[int]]:
    """
    Create new handover record with automatic type determination and approval workflow.
    
    Args:
        vehicle_id: Target vehicle ID
        form_data: Dictionary of form fields (handover_date, person_name, mileage, etc.)
        files: Dictionary of file uploads (files list, custom_logo_file)
        static_folder: Flask app.static_folder path
        current_user_id: ID of user creating the handover
    
    Returns:
        Tuple of (success: bool, message: str, handover_id: int or None)
    """
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, "المركبة غير موجودة", None
        
        # Check vehicle operation restrictions
        from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            return False, restrictions['message'], None
        
        # Determine handover mode (delivery vs return)
        mode_info = _determine_handover_mode(vehicle_id)
        force_mode = mode_info['force_mode']
        current_driver_info = mode_info['current_driver_info']
        
        # Validate handover type matches forced mode
        handover_type_from_form = form_data.get('handover_type')
        if handover_type_from_form != force_mode:
            return False, "خطأ في منطق العملية. يرجى المحاولة مرة أخرى.", None
        
        # Parse dates
        handover_date_str = form_data.get('handover_date')
        handover_time_str = form_data.get('handover_time')
        handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
        handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
        
        # Process base64 images (signatures and diagrams)
        saved_diagram_path = _save_base64_image(form_data.get('damage_diagram_data'), 'diagrams', static_folder)
        saved_supervisor_sig_path = _save_base64_image(form_data.get('supervisor_signature_data'), 'signatures', static_folder)
        saved_driver_sig_path = _save_base64_image(form_data.get('driver_signature_data'), 'signatures', static_folder)
        saved_movement_sig_path = _save_base64_image(form_data.get('movement_officer_signature_data'), 'signatures', static_folder)
        
        # Process custom logo upload
        custom_logo_file = files.get('custom_logo_file')
        saved_custom_logo_path = _save_uploaded_file(custom_logo_file, 'logos', static_folder)
        
        # Lookup driver and supervisor employees
        driver = _lookup_employee_by_id_or_name(
            form_data.get('employee_id', ''),
            form_data.get('person_name', '')
        )
        
        supervisor_id_str = form_data.get('supervisor_employee_id', '')
        supervisor = Employee.query.get(supervisor_id_str) if supervisor_id_str and supervisor_id_str.isdigit() else None
        
        # Create handover record
        handover = VehicleHandover(
            vehicle_id=vehicle.id,
            handover_type=handover_type_from_form,
            handover_date=handover_date,
            handover_time=handover_time,
            mileage=int(form_data.get('mileage', 0)),
            project_name=form_data.get('project_name'),
            city=form_data.get('city'),
            vehicle_car_type=f"{vehicle.make} {vehicle.model}",
            vehicle_plate_number=vehicle.plate_number,
            vehicle_model_year=str(vehicle.year),
            
            # Driver fields (with fallback logic for return mode)
            employee_id=driver.id if driver else (current_driver_info.employee_id if force_mode == 'return' else None),
            person_name=driver.name if driver else (form_data.get('person_name') if force_mode == 'delivery' else current_driver_info.person_name),
            driver_company_id=driver.employee_id if driver else (current_driver_info.driver_company_id if force_mode == 'return' else None),
            driver_work_phone=driver.mobile if driver else (current_driver_info.driver_work_phone if force_mode == 'return' else None),
            driver_phone_number=driver.mobilePersonal if driver else (current_driver_info.driver_phone_number if force_mode == 'return' else None),
            driver_residency_number=driver.national_id if driver else (current_driver_info.driver_residency_number if force_mode == 'return' else None),
            driver_contract_status=driver.contract_status if driver else None,
            driver_license_status=driver.license_status if driver else None,
            driver_signature_path=saved_driver_sig_path,
            
            # Supervisor fields
            supervisor_employee_id=supervisor.id if supervisor else None,
            supervisor_name=supervisor.name if supervisor else form_data.get('supervisor_name'),
            supervisor_company_id=supervisor.mobile if supervisor else None,
            supervisor_phone_number=supervisor.mobilePersonal if supervisor else None,
            supervisor_residency_number=supervisor.national_id if supervisor else None,
            supervisor_contract_status=supervisor.contract_status if supervisor else None,
            supervisor_license_status=supervisor.license_status if supervisor else None,
            supervisor_signature_path=saved_supervisor_sig_path,
            
            # Additional fields
            reason_for_change=form_data.get('reason_for_change'),
            vehicle_status_summary=form_data.get('vehicle_status_summary'),
            notes=form_data.get('notes'),
            reason_for_authorization=form_data.get('reason_for_authorization'),
            authorization_details=form_data.get('authorization_details'),
            fuel_level=form_data.get('fuel_level'),
            
            # Checklist items
            has_spare_tire=form_data.get('has_spare_tire', False),
            has_fire_extinguisher=form_data.get('has_fire_extinguisher', False),
            has_first_aid_kit=form_data.get('has_first_aid_kit', False),
            has_warning_triangle=form_data.get('has_warning_triangle', False),
            has_tools=form_data.get('has_tools', False),
            has_oil_leaks=form_data.get('has_oil_leaks', False),
            has_gear_issue=form_data.get('has_gear_issue', False),
            has_clutch_issue=form_data.get('has_clutch_issue', False),
            has_engine_issue=form_data.get('has_engine_issue', False),
            has_windows_issue=form_data.get('has_windows_issue', False),
            has_tires_issue=form_data.get('has_tires_issue', False),
            has_body_issue=form_data.get('has_body_issue', False),
            has_electricity_issue=form_data.get('has_electricity_issue', False),
            has_lights_issue=form_data.get('has_lights_issue', False),
            has_ac_issue=form_data.get('has_ac_issue', False),
            
            # Movement officer
            movement_officer_name=form_data.get('movement_officer_name'),
            movement_officer_signature_path=saved_movement_sig_path,
            
            # Other
            damage_diagram_path=saved_diagram_path,
            form_link=form_data.get('form_link'),
            form_link_2=form_data.get('form_link_2'),
            custom_company_name=form_data.get('custom_company_name') or None,
            custom_logo_path=saved_custom_logo_path
        )
        
        db.session.add(handover)
        db.session.flush()  # Get handover ID
        
        # Create operation request for approval
        action_type = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
        operation_title = f"موافقة على {action_type} مركبة {vehicle.plate_number} (جوال)"
        operation_description = f"تم إنشاء نموذج {action_type} للمركبة {vehicle.plate_number} عبر الجوال. الرجاء المراجعة والموافقة."
        
        create_operation_request(
            operation_type="handover",
            related_record_id=handover.id,
            vehicle_id=vehicle.id,
            title=operation_title,
            description=operation_description,
            requested_by=current_user_id
        )
        
        # Save file attachments
        file_list = files.get('files', [])
        for file in file_list:
            if file and file.filename:
                file_path, file_type = _save_handover_file(file, 'handover', static_folder)
                if file_path:
                    # Get description from form if provided
                    description = form_data.get(f'description_{file.filename}', '')
                    attachment = VehicleHandoverImage(
                        handover_record_id=handover.id,
                        file_path=file_path,
                        file_type=file_type,
                        image_path=file_path,
                        file_description=description,
                        image_description=description
                    )
                    db.session.add(attachment)
        
        db.session.commit()
        
        # Log activity
        log_activity(
            'create',
            'vehicle_handover',
            handover.id,
            f"إنشاء طلب {action_type} للمركبة {vehicle.plate_number} عبر الجوال (بانتظار الموافقة)"
        )
        
        return True, f'تم إنشاء طلب {action_type} بنجاح، وهو الآن بانتظار الموافقة.', handover.id
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return False, f'حدث خطأ غير متوقع أثناء الحفظ: {str(e)}', None


def update_handover_record(
    handover_id: int,
    form_data: Dict[str, Any],
    files: Dict[str, Any],
    static_folder: str
) -> Tuple[bool, str, Optional[int]]:
    """
    Update existing handover record with new data and files.
    
    Args:
        handover_id: ID of handover record to update
        form_data: Dictionary of form fields
        files: Dictionary of file uploads
        static_folder: Flask app.static_folder path
    
    Returns:
        Tuple of (success: bool, message: str, vehicle_id: int or None)
    """
    try:
        existing_handover = VehicleHandover.query.get(handover_id)
        if not existing_handover:
            return False, "سجل التسليم/الاستلام غير موجود", None
        
        vehicle = existing_handover.vehicle
        
        # Parse dates
        handover_date_str = form_data.get('handover_date')
        handover_time_str = form_data.get('handover_time')
        
        existing_handover.handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else existing_handover.handover_date
        existing_handover.handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else existing_handover.handover_time
        
        # Lookup employees
        driver = _lookup_employee_by_id_or_name(
            form_data.get('employee_id', ''),
            form_data.get('person_name', '')
        )
        
        supervisor_id_str = form_data.get('supervisor_employee_id', '')
        supervisor = Employee.query.get(supervisor_id_str) if supervisor_id_str and supervisor_id_str.isdigit() else None
        
        # Update handover fields
        existing_handover.handover_type = form_data.get('handover_type')
        existing_handover.mileage = int(form_data.get('mileage', 0))
        existing_handover.project_name = form_data.get('project_name')
        existing_handover.city = form_data.get('city')
        existing_handover.employee_id = driver.id if driver else None
        existing_handover.person_name = driver.name if driver else form_data.get('person_name')
        existing_handover.supervisor_employee_id = supervisor.id if supervisor else None
        existing_handover.supervisor_name = supervisor.name if supervisor else form_data.get('supervisor_name')
        existing_handover.reason_for_change = form_data.get('reason_for_change')
        existing_handover.vehicle_status_summary = form_data.get('vehicle_status_summary')
        existing_handover.notes = form_data.get('notes')
        existing_handover.reason_for_authorization = form_data.get('reason_for_authorization')
        existing_handover.authorization_details = form_data.get('authorization_details')
        existing_handover.fuel_level = form_data.get('fuel_level')
        
        # Update checklist
        existing_handover.has_spare_tire = form_data.get('has_spare_tire', False)
        existing_handover.has_fire_extinguisher = form_data.get('has_fire_extinguisher', False)
        existing_handover.has_first_aid_kit = form_data.get('has_first_aid_kit', False)
        existing_handover.has_warning_triangle = form_data.get('has_warning_triangle', False)
        existing_handover.has_tools = form_data.get('has_tools', False)
        existing_handover.has_oil_leaks = form_data.get('has_oil_leaks', False)
        existing_handover.has_gear_issue = form_data.get('has_gear_issue', False)
        existing_handover.has_clutch_issue = form_data.get('has_clutch_issue', False)
        existing_handover.has_engine_issue = form_data.get('has_engine_issue', False)
        existing_handover.has_windows_issue = form_data.get('has_windows_issue', False)
        existing_handover.has_tires_issue = form_data.get('has_tires_issue', False)
        existing_handover.has_body_issue = form_data.get('has_body_issue', False)
        existing_handover.has_electricity_issue = form_data.get('has_electricity_issue', False)
        existing_handover.has_lights_issue = form_data.get('has_lights_issue', False)
        existing_handover.has_ac_issue = form_data.get('has_ac_issue', False)
        
        existing_handover.movement_officer_name = form_data.get('movement_officer_name')
        existing_handover.form_link = form_data.get('form_link')
        existing_handover.form_link_2 = form_data.get('form_link_2')
        existing_handover.custom_company_name = form_data.get('custom_company_name') or None
        existing_handover.updated_at = datetime.utcnow()
        
        # Update images/signatures only if new data provided
        new_diagram_data = form_data.get('damage_diagram_data')
        if new_diagram_data:
            existing_handover.damage_diagram_path = _save_base64_image(new_diagram_data, 'diagrams', static_folder)
        
        new_supervisor_sig = form_data.get('supervisor_signature_data')
        if new_supervisor_sig:
            existing_handover.supervisor_signature_path = _save_base64_image(new_supervisor_sig, 'signatures', static_folder)
        
        new_driver_sig = form_data.get('driver_signature_data')
        if new_driver_sig:
            existing_handover.driver_signature_path = _save_base64_image(new_driver_sig, 'signatures', static_folder)
        
        new_movement_sig = form_data.get('movement_officer_signature_data')
        if new_movement_sig:
            existing_handover.movement_officer_signature_path = _save_base64_image(new_movement_sig, 'signatures', static_folder)
        
        # Process new file uploads
        file_list = files.get('files', [])
        for file in file_list:
            if file and file.filename:
                try:
                    file_path, file_type = _save_handover_file(file, 'handover', static_folder)
                    if file_path:
                        file_description = form_data.get(f'description_{file.filename}', '')
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
        
        db.session.commit()
        
        # Log activity
        log_activity(
            'update',
            'vehicle_handover',
            existing_handover.id,
            f"تعديل نموذج {existing_handover.handover_type} للمركبة {vehicle.plate_number} عبر الجوال"
        )
        
        return True, 'تم تحديث النموذج بنجاح.', vehicle.id
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return False, f'حدث خطأ أثناء تحديث النموذج: {str(e)}', None


def create_next_handover_from_existing(
    source_handover_id: int,
    form_data: Dict[str, Any],
    static_folder: str,
    current_user_id: int
) -> Tuple[bool, str, Optional[int]]:
    """
    Create new handover record based on existing one with reversed type.
    
    This is the "Save as Next" functionality - creates a new handover with:
    - Reversed type (delivery → return or return → delivery)
    - Same vehicle
    - Updated form data
    - New operation request
    
    Args:
        source_handover_id: ID of handover to use as template
        form_data: Dictionary of form fields for new record
        static_folder: Flask app.static_folder path
        current_user_id: ID of user creating the handover
    
    Returns:
        Tuple of (success: bool, message: str, vehicle_id: int or None)
    """
    try:
        original_handover = VehicleHandover.query.get(source_handover_id)
        if not original_handover:
            return False, "سجل التسليم/الاستلام الأصلي غير موجود", None
        
        vehicle = original_handover.vehicle
        
        # Parse dates
        handover_date_str = form_data.get('handover_date')
        handover_time_str = form_data.get('handover_time')
        handover_date = datetime.strptime(handover_date_str, '%Y-%m-%d').date() if handover_date_str else date.today()
        handover_time = datetime.strptime(handover_time_str, '%H:%M').time() if handover_time_str else None
        
        # Lookup employees
        driver = _lookup_employee_by_id_or_name(
            form_data.get('employee_id', ''),
            form_data.get('person_name', '')
        )
        
        supervisor_id_str = form_data.get('supervisor_employee_id', '')
        supervisor = Employee.query.get(supervisor_id_str) if supervisor_id_str and supervisor_id_str.isdigit() else None
        
        # Create new handover record
        new_handover = VehicleHandover(
            vehicle_id=vehicle.id,
            handover_date=handover_date,
            handover_time=handover_time,
            mileage=int(form_data.get('mileage', 0)),
            project_name=form_data.get('project_name'),
            city=form_data.get('city'),
            vehicle_car_type=f"{vehicle.make} {vehicle.model}",
            vehicle_plate_number=vehicle.plate_number,
            vehicle_model_year=str(vehicle.year),
            reason_for_change=form_data.get('reason_for_change'),
            vehicle_status_summary=form_data.get('vehicle_status_summary'),
            notes=form_data.get('notes'),
            reason_for_authorization=form_data.get('reason_for_authorization'),
            authorization_details=form_data.get('authorization_details'),
            fuel_level=form_data.get('fuel_level'),
            
            # Checklist
            has_spare_tire=form_data.get('has_spare_tire', False),
            has_fire_extinguisher=form_data.get('has_fire_extinguisher', False),
            has_first_aid_kit=form_data.get('has_first_aid_kit', False),
            has_warning_triangle=form_data.get('has_warning_triangle', False),
            has_tools=form_data.get('has_tools', False),
            has_oil_leaks=form_data.get('has_oil_leaks', False),
            has_gear_issue=form_data.get('has_gear_issue', False),
            has_clutch_issue=form_data.get('has_clutch_issue', False),
            has_engine_issue=form_data.get('has_engine_issue', False),
            has_windows_issue=form_data.get('has_windows_issue', False),
            has_tires_issue=form_data.get('has_tires_issue', False),
            has_body_issue=form_data.get('has_body_issue', False),
            has_electricity_issue=form_data.get('has_electricity_issue', False),
            has_lights_issue=form_data.get('has_lights_issue', False),
            has_ac_issue=form_data.get('has_ac_issue', False),
            
            movement_officer_name=form_data.get('movement_officer_name'),
            form_link=form_data.get('form_link'),
            form_link_2=form_data.get('form_link_2'),
            custom_company_name=form_data.get('custom_company_name') or None,
        )
        
        # Smart logic: Reverse handover type and assign driver accordingly
        new_handover.supervisor_employee_id = supervisor.id if supervisor else None
        new_handover.supervisor_name = supervisor.name if supervisor else form_data.get('supervisor_name')
        
        if original_handover.handover_type == 'delivery':
            # Original was delivery → new is return
            new_handover.handover_type = 'return'
            # Driver is same as original delivery
            new_handover.person_name = original_handover.person_name
            new_handover.employee_id = original_handover.employee_id
        else:
            # Original was return → new is delivery
            new_handover.handover_type = 'delivery'
            # Driver is from form
            new_handover.employee_id = driver.id if driver else None
            new_handover.person_name = driver.name if driver else form_data.get('person_name')
        
        db.session.add(new_handover)
        db.session.flush()
        
        # Create operation request for approval
        action_type = 'تسليم' if new_handover.handover_type == 'delivery' else 'استلام'
        operation_title = f"موافقة على {action_type} (نسخة جديدة) لمركبة {vehicle.plate_number}"
        create_operation_request(
            operation_type="handover",
            related_record_id=new_handover.id,
            vehicle_id=vehicle.id,
            title=operation_title,
            description=f"تم إنشاؤها كنسخة من سجل سابق.",
            requested_by=current_user_id
        )
        
        db.session.commit()
        
        return True, f'تم حفظ نسخة جديدة كعملية "{action_type}" وهي الآن بانتظار الموافقة.', vehicle.id
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return False, f'حدث خطأ أثناء حفظ النسخة الجديدة: {str(e)}', None


def delete_handover_record(handover_id: int) -> Tuple[bool, str, Optional[int]]:
    """
    Delete handover record and related images.
    
    Performs soft deletion by removing DB records only (files preserved for safety).
    Updates vehicle driver history after deletion.
    
    Args:
        handover_id: ID of handover record to delete
    
    Returns:
        Tuple of (success: bool, message: str, vehicle_id: int or None)
    """
    try:
        handover = VehicleHandover.query.get(handover_id)
        if not handover:
            return False, "سجل التسليم/الاستلام غير موجود", None
        
        vehicle_id = handover.vehicle_id
        handover_type = handover.handover_type
        person_name = handover.person_name
        
        # Delete related images (DB records only, files preserved)
        images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
        for image in images:
            db.session.delete(image)
        
        # Delete handover record
        db.session.delete(handover)
        db.session.commit()
        
        # Log activity
        log_activity(
            action='delete',
            entity_type='vehicle_handover',
            entity_id=handover_id,
            details=f'تم حذف سجل {"تسليم" if handover_type == "delivery" else "استلام"} للسيارة - الشخص: {person_name}'
        )
        
        # Update vehicle driver info
        update_vehicle_driver(vehicle_id)
        
        action_arabic = "التسليم" if handover_type == "delivery" else "الاستلام"
        return True, f'تم حذف سجل {action_arabic} بنجاح', vehicle_id
    
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في حذف سجل التسليم/الاستلام: {str(e)}")
        return False, f'حدث خطأ أثناء حذف السجل: {str(e)}', None


def get_handover_details_context(handover_id: int) -> Optional[Dict[str, Any]]:
    """
    Get handover details with related data for view rendering.
    
    Args:
        handover_id: ID of handover record to fetch
    
    Returns:
        Dictionary with handover, vehicle, images, and display data or None if not found
    """
    try:
        handover = VehicleHandover.query.get(handover_id)
        if not handover:
            return None
        
        vehicle = Vehicle.query.get(handover.vehicle_id)
        images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
        
        # Format date for display
        handover.formatted_handover_date = handover.handover_date.strftime('%Y-%m-%d')
        
        handover_type_name = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
        
        return {
            'handover': handover,
            'vehicle': vehicle,
            'images': images,
            'handover_type_name': handover_type_name
        }
    
    except Exception as e:
        print(f"خطأ في جلب تفاصيل التسليم/الاستلام: {str(e)}")
        return None


def get_handover_form_context(vehicle_id: int) -> Dict[str, Any]:
    """
    Get context data for handover form rendering.
    
    Includes:
    - Vehicle data
    - Employees list
    - Departments list
    - Handover mode determination (delivery vs return)
    
    Args:
        vehicle_id: Target vehicle ID
    
    Returns:
        Dictionary with all form context data
    """
    from sqlalchemy.orm import joinedload
    
    vehicle = Vehicle.query.get(vehicle_id)
    employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    departments = Department.query.order_by(Department.name).all()
    
    # Determine handover mode
    mode_info = _determine_handover_mode(vehicle_id)
    
    return {
        'vehicle': vehicle,
        'employees': employees,
        'departments': departments,
        'force_mode': mode_info['force_mode'],
        'current_driver_info': mode_info['current_driver_info'].to_dict() if mode_info['current_driver_info'] else None,
        'info_message': mode_info['info_message']
    }


def get_edit_handover_form_context(handover_id: int) -> Optional[Dict[str, Any]]:
    """
    Get context data for editing existing handover.
    
    Args:
        handover_id: ID of handover to edit
    
    Returns:
        Dictionary with handover, vehicle, employees, departments or None if not found
    """
    from sqlalchemy.orm import joinedload
    
    existing_handover = VehicleHandover.query.get(handover_id)
    if not existing_handover:
        return None
    
    vehicle = existing_handover.vehicle
    employees = Employee.query.options(joinedload(Employee.departments)).order_by(Employee.name).all()
    departments = Department.query.order_by(Department.name).all()
    
    return {
        'existing_handover': existing_handover.to_dict(),
        'vehicle': vehicle,
        'employees': employees,
        'departments': departments
    }
