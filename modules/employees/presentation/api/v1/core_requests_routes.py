import os
import uuid
import logging
import tempfile
import shutil
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from core.extensions import db
from models import (
    EmployeeRequest, InvoiceRequest, AdvancePaymentRequest, CarWashRequest, CarInspectionRequest,
    CarWashMedia, CarInspectionMedia, RequestType, RequestStatus, MediaType, FileType
)
from modules.employees.presentation.api.v1.auth_routes import token_required
from utils.employee_requests_drive_uploader import EmployeeRequestsDriveUploader

logger = logging.getLogger(__name__)

core_requests_api_v1 = Blueprint('core_requests_api_v1', __name__, url_prefix='/api/v1')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'mp4', 'mov', 'avi', 'pdf'}
    if not filename or not isinstance(filename, str):
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@core_requests_api_v1.route('/requests', methods=['GET'])
@token_required
def get_requests(current_employee):
    """
    الحصول على قائمة طلبات الموظف
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    query = EmployeeRequest.query.filter_by(employee_id=current_employee.id)

    if status_filter:
        try:
            query = query.filter_by(status=RequestStatus[status_filter])
        except KeyError:
            return jsonify({'success': False, 'message': f'حالة غير صحيحة: {status_filter}'}), 400

    if type_filter:
        try:
            query = query.filter_by(request_type=RequestType[type_filter])
        except KeyError:
            return jsonify({'success': False, 'message': f'نوع غير صحيح: {type_filter}'}), 400

    pagination = query.order_by(EmployeeRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    type_names = {
        'INVOICE': 'فاتورة',
        'CAR_WASH': 'غسيل سيارة',
        'CAR_INSPECTION': 'فحص وتوثيق',
        'ADVANCE_PAYMENT': 'سلفة مالية'
    }

    status_names = {
        'PENDING': 'قيد الانتظار',
        'APPROVED': 'موافق عليها',
        'REJECTED': 'مرفوضة'
    }

    requests_list = []
    for req in pagination.items:
        request_data = {
            'id': req.id,
            'type': req.request_type.name,
            'type_display': type_names.get(req.request_type.name, req.request_type.name),
            'status': req.status.name,
            'status_display': status_names.get(req.status.name, req.status.name),
            'title': req.title,
            'description': req.description,
            'amount': float(req.amount) if req.amount else None,
            'created_at': req.created_at.isoformat(),
            'updated_at': req.updated_at.isoformat() if req.updated_at else None,
            'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
            'admin_notes': req.admin_notes,
            'google_drive_folder_url': req.google_drive_folder_url
        }
        requests_list.append(request_data)

    return jsonify({
        'success': True,
        'requests': requests_list,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200

@core_requests_api_v1.route('/requests/<int:request_id>', methods=['GET'])
@token_required
def get_request_details(current_employee, request_id):
    """
    الحصول على تفاصيل طلب معين
    """
    emp_request = EmployeeRequest.query.filter_by(
        id=request_id,
        employee_id=current_employee.id
    ).first()

    if not emp_request:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

    type_names = {
        'INVOICE': 'فاتورة',
        'CAR_WASH': 'غسيل سيارة',
        'CAR_INSPECTION': 'فحص وتوثيق',
        'ADVANCE_PAYMENT': 'سلفة مالية'
    }

    status_names = {
        'PENDING': 'قيد الانتظار',
        'APPROVED': 'موافق عليها',
        'REJECTED': 'مرفوضة'
    }

    request_data = {
        'id': emp_request.id,
        'type': emp_request.request_type.name,
        'type_display': type_names.get(emp_request.request_type.name, emp_request.request_type.name),
        'status': emp_request.status.name,
        'status_display': status_names.get(emp_request.status.name, emp_request.status.name),
        'title': emp_request.title,
        'description': emp_request.description,
        'amount': float(emp_request.amount) if emp_request.amount else None,
        'created_at': emp_request.created_at.isoformat(),
        'updated_at': emp_request.updated_at.isoformat() if emp_request.updated_at else None,
        'reviewed_at': emp_request.reviewed_at.isoformat() if emp_request.reviewed_at else None,
        'admin_notes': emp_request.admin_notes,
        'google_drive_folder_url': emp_request.google_drive_folder_url
    }

    if emp_request.request_type == RequestType.INVOICE and emp_request.invoice_data:
        invoice = emp_request.invoice_data
        request_data['details'] = {
            'vendor_name': invoice.vendor_name,
            'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            'drive_view_url': invoice.drive_view_url,
            'file_size': invoice.file_size
        }

    elif emp_request.request_type == RequestType.ADVANCE_PAYMENT and emp_request.advance_data:
        advance = emp_request.advance_data
        request_data['details'] = {
            'requested_amount': float(advance.requested_amount),
            'reason': advance.reason,
            'installments': advance.installments,
            'installment_amount': float(advance.installment_amount) if advance.installment_amount else None
        }

    elif emp_request.request_type == RequestType.CAR_WASH and emp_request.car_wash_data:
        wash = emp_request.car_wash_data
        media_files = []
        for media in wash.media_files:
            media_files.append({
                'id': media.id,
                'file_type': media.file_type,
                'drive_file_id': media.drive_file_id,
                'drive_view_url': media.drive_view_url,
                'uploaded_at': media.uploaded_at.isoformat()
            })

        request_data['details'] = {
            'service_type': wash.service_type,
            'scheduled_date': wash.scheduled_date.isoformat() if wash.scheduled_date else None,
            'vehicle': {
                'id': wash.vehicle.id,
                'plate_number': wash.vehicle.plate_number,
                'make': wash.vehicle.make,
                'model': wash.vehicle.model
            } if wash.vehicle else None,
            'media_files': media_files
        }

    elif emp_request.request_type == RequestType.CAR_INSPECTION and emp_request.inspection_data:
        inspection = emp_request.inspection_data
        media_files = []
        for media in inspection.media_files:
            media_files.append({
                'id': media.id,
                'file_type': media.file_type,
                'drive_file_id': media.drive_file_id,
                'drive_view_url': media.drive_view_url,
                'file_size': media.file_size,
                'uploaded_at': media.uploaded_at.isoformat()
            })

        request_data['details'] = {
            'inspection_type': inspection.inspection_type,
            'inspection_date': inspection.inspection_date.isoformat() if inspection.inspection_date else None,
            'vehicle': {
                'id': inspection.vehicle.id,
                'plate_number': inspection.vehicle.plate_number,
                'make': inspection.vehicle.make,
                'model': inspection.vehicle.model
            } if inspection.vehicle else None,
            'media_files': media_files
        }

    return jsonify({
        'success': True,
        'request': request_data
    }), 200

@core_requests_api_v1.route('/public/requests/<int:request_id>', methods=['GET'])
def get_public_request_details(request_id):
    """
    الحصول على تفاصيل طلب معين - Endpoint عام بدون مصادقة
    """
    emp_request = EmployeeRequest.query.get(request_id)

    if not emp_request:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

    type_names = {
        'INVOICE': 'فاتورة',
        'CAR_WASH': 'غسيل سيارة',
        'CAR_INSPECTION': 'فحص وتوثيق',
        'ADVANCE_PAYMENT': 'سلفة مالية'
    }

    status_names = {
        'PENDING': 'قيد الانتظار',
        'APPROVED': 'موافق عليها',
        'REJECTED': 'مرفوضة'
    }

    request_data = {
        'id': emp_request.id,
        'employee': {
            'id': emp_request.employee.id,
            'name': emp_request.employee.name,
            'employee_id': emp_request.employee.employee_id
        } if emp_request.employee else None,
        'type': emp_request.request_type.name,
        'type_display': type_names.get(emp_request.request_type.name, emp_request.request_type.name),
        'status': emp_request.status.name,
        'status_display': status_names.get(emp_request.status.name, emp_request.status.name),
        'title': emp_request.title,
        'description': emp_request.description,
        'amount': float(emp_request.amount) if emp_request.amount else None,
        'created_at': emp_request.created_at.isoformat(),
        'updated_at': emp_request.updated_at.isoformat() if emp_request.updated_at else None,
        'reviewed_at': emp_request.reviewed_at.isoformat() if emp_request.reviewed_at else None,
        'admin_notes': emp_request.admin_notes,
        'google_drive_folder_url': emp_request.google_drive_folder_url
    }

    if emp_request.request_type == RequestType.INVOICE and emp_request.invoice_data:
        invoice = emp_request.invoice_data
        request_data['details'] = {
            'vendor_name': invoice.vendor_name,
            'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            'drive_view_url': invoice.drive_view_url,
            'drive_file_id': invoice.drive_file_id,
            'file_size': invoice.file_size,
            'local_file_path': invoice.local_image_path
        }

    elif emp_request.request_type == RequestType.ADVANCE_PAYMENT and emp_request.advance_data:
        advance = emp_request.advance_data
        request_data['details'] = {
            'requested_amount': float(advance.requested_amount),
            'reason': advance.reason,
            'installments': advance.installments,
            'installment_amount': float(advance.installment_amount) if advance.installment_amount else None
        }

    elif emp_request.request_type == RequestType.CAR_WASH and emp_request.car_wash_data:
        wash = emp_request.car_wash_data
        media_files = []
        for media in wash.media_files:
            media_files.append({
                'id': media.id,
                'media_type': media.media_type.value if media.media_type else None,
                'drive_file_id': media.drive_file_id,
                'drive_view_url': media.drive_view_url,
                'local_file_path': media.local_path,
                'file_size': media.file_size,
                'uploaded_at': media.uploaded_at.isoformat() if media.uploaded_at else None
            })

        request_data['details'] = {
            'service_type': wash.service_type,
            'scheduled_date': wash.scheduled_date.isoformat() if wash.scheduled_date else None,
            'vehicle': {
                'id': wash.vehicle.id,
                'plate_number': wash.vehicle.plate_number,
                'make': wash.vehicle.make,
                'model': wash.vehicle.model
            } if wash.vehicle else None,
            'media_files': media_files
        }

    elif emp_request.request_type == RequestType.CAR_INSPECTION and emp_request.inspection_data:
        inspection = emp_request.inspection_data
        media_files = []
        for media in inspection.media_files:
            media_files.append({
                'id': media.id,
                'file_type': media.file_type.value if media.file_type else None,
                'drive_file_id': media.drive_file_id,
                'drive_view_url': media.drive_view_url,
                'file_size': media.file_size,
                'local_file_path': media.local_path,
                'uploaded_at': media.uploaded_at.isoformat() if media.uploaded_at else None
            })

        request_data['details'] = {
            'inspection_type': inspection.inspection_type,
            'inspection_date': inspection.inspection_date.isoformat() if inspection.inspection_date else None,
            'vehicle': {
                'id': inspection.vehicle.id,
                'plate_number': inspection.vehicle.plate_number,
                'make': inspection.vehicle.make,
                'model': inspection.vehicle.model
            } if inspection.vehicle else None,
            'media_files': media_files
        }

    return jsonify({
        'success': True,
        'request': request_data
    }), 200

@core_requests_api_v1.route('/requests', methods=['POST'])
@token_required
def create_request(current_employee):
    """
    إنشاء طلب جديد
    """
    data = request.get_json()

    if not data or not data.get('type') or not data.get('title'):
        return jsonify({'success': False, 'message': 'النوع والعنوان مطلوبان'}), 400

    try:
        request_type = RequestType[data['type']]
    except KeyError:
        return jsonify({'success': False, 'message': f'نوع طلب غير صحيح: {data["type"]}'}), 400

    new_request = EmployeeRequest()
    new_request.employee_id = current_employee.id
    new_request.request_type = request_type
    new_request.title = data['title']
    new_request.description = data.get('description')
    new_request.amount = data.get('amount')
    new_request.status = RequestStatus.PENDING

    db.session.add(new_request)
    db.session.flush()

    details = data.get('details', {})

    if request_type == RequestType.INVOICE:
        invoice = InvoiceRequest()
        invoice.request_id = new_request.id
        invoice.vendor_name = details.get('vendor_name', '')
        invoice.invoice_date = datetime.strptime(details['invoice_date'], '%Y-%m-%d').date() if details.get('invoice_date') else None
        db.session.add(invoice)

    elif request_type == RequestType.ADVANCE_PAYMENT:
        advance = AdvancePaymentRequest()
        advance.request_id = new_request.id
        advance.employee_name = current_employee.name
        advance.employee_number = current_employee.employee_id
        advance.national_id = current_employee.national_id or ''
        advance.job_title = current_employee.job_title or ''
        advance.department_name = current_employee.department.name if current_employee.department else ''
        advance.requested_amount = details.get('requested_amount', 0)
        advance.reason = details.get('reason')
        advance.installments = details.get('installments')
        advance.installment_amount = details.get('installment_amount')
        db.session.add(advance)

    elif request_type == RequestType.CAR_WASH:
        wash = CarWashRequest()
        wash.request_id = new_request.id
        wash.vehicle_id = details.get('vehicle_id')
        wash.service_type = details.get('service_type', 'غسيل عادي')
        wash.scheduled_date = datetime.strptime(details['scheduled_date'], '%Y-%m-%d').date() if details.get('scheduled_date') else None
        db.session.add(wash)

    elif request_type == RequestType.CAR_INSPECTION:
        inspection = CarInspectionRequest()
        inspection.request_id = new_request.id
        inspection.vehicle_id = details.get('vehicle_id')
        inspection.inspection_type = details.get('inspection_type', 'فحص دوري')
        inspection.inspection_date = datetime.strptime(details['inspection_date'], '%Y-%m-%d').date() if details.get('inspection_date') else datetime.now().date()
        db.session.add(inspection)

    db.session.commit()

    return jsonify({
        'success': True,
        'request_id': new_request.id,
        'message': 'تم إنشاء الطلب بنجاح'
    }), 201

@core_requests_api_v1.route('/requests/<int:request_id>/upload', methods=['POST'])
@token_required
def upload_files(current_employee, request_id):
    """
    رفع ملفات (صور أو فيديوهات) لطلب معين
    """
    emp_request = EmployeeRequest.query.filter_by(
        id=request_id,
        employee_id=current_employee.id
    ).first()

    if not emp_request:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'لا يوجد ملفات مرفقة'}), 400

    files = request.files.getlist('files')

    if not files:
        return jsonify({'success': False, 'message': 'لا يوجد ملفات مرفقة'}), 400

    drive_uploader = EmployeeRequestsDriveUploader()

    if not drive_uploader.is_available():
        return jsonify({'success': False, 'message': 'خدمة Google Drive غير متاحة حالياً'}), 503

    type_map = {
        RequestType.INVOICE: 'invoice',
        RequestType.CAR_WASH: 'car_wash',
        RequestType.CAR_INSPECTION: 'car_inspection',
        RequestType.ADVANCE_PAYMENT: 'advance_payment'
    }

    vehicle_number = None
    if emp_request.request_type in [RequestType.CAR_WASH, RequestType.CAR_INSPECTION]:
        if emp_request.request_type == RequestType.CAR_WASH and emp_request.car_wash_data and emp_request.car_wash_data.vehicle:
            vehicle_number = emp_request.car_wash_data.vehicle.plate_number
        elif emp_request.request_type == RequestType.CAR_INSPECTION and emp_request.inspection_data and emp_request.inspection_data.vehicle:
            vehicle_number = emp_request.inspection_data.vehicle.plate_number

    vehicle_number_str = vehicle_number if vehicle_number else ''

    folder_result = drive_uploader.create_request_folder(
        request_type=type_map.get(emp_request.request_type, 'other'),
        request_id=emp_request.id,
        employee_name=current_employee.name,
        vehicle_number=vehicle_number_str
    )

    if not folder_result:
        return jsonify({'success': False, 'message': 'فشل إنشاء مجلد على Google Drive'}), 500

    emp_request.google_drive_folder_id = folder_result['folder_id']
    emp_request.google_drive_folder_url = folder_result['folder_url']
    db.session.commit()

    uploaded_files = []

    for file in files:
        if not file.filename or file.filename == '':
            continue

        if not allowed_file(file.filename):
            continue

        if '.' not in file.filename:
            continue

        temp_file = None
        temp_path = None
        try:
            file_ext = file.filename.rsplit('.', 1)[1].lower()

            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name

            result = None
            local_path = None

            if emp_request.request_type == RequestType.INVOICE:
                safe_filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{safe_filename}"
                local_path = os.path.join('uploads', 'invoices', unique_filename)
                full_path = os.path.join('static', local_path)

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                shutil.copy(temp_path, full_path)

                result = drive_uploader.upload_invoice_image(
                    file_path=temp_path,
                    folder_id=folder_result['folder_id'],
                    custom_name=file.filename
                )

                invoice = emp_request.invoice_data
                if invoice:
                    invoice.local_image_path = local_path
                    if result:
                        invoice.drive_file_id = result['file_id']
                        invoice.drive_view_url = result['view_url']
                        invoice.drive_download_url = result.get('download_url')
                        invoice.file_size = result.get('file_size')

            elif emp_request.request_type == RequestType.CAR_WASH:
                existing_count = len(emp_request.car_wash_data.media_files) if emp_request.car_wash_data else 0
                media_types_order = [MediaType.PLATE, MediaType.FRONT, MediaType.BACK, MediaType.RIGHT, MediaType.LEFT]
                if existing_count < 5:
                    media_type = media_types_order[existing_count]
                    images_dict = {media_type.value: temp_path}

                    results = drive_uploader.upload_car_wash_images(
                        images_dict=images_dict,
                        folder_id=folder_result['folder_id']
                    )

                    result = results.get(media_type.value)

                    if result:
                        media = CarWashMedia()
                        media.wash_request_id = emp_request.car_wash_data.id
                        media.media_type = media_type
                        media.drive_file_id = result['file_id']
                        media.drive_view_url = result['view_url']
                        media.file_size = result.get('file_size')
                        db.session.add(media)

            elif emp_request.request_type == RequestType.CAR_INSPECTION:
                is_video = file_ext in ['mp4', 'mov', 'avi']
                inspection_file_type = FileType.VIDEO if is_video else FileType.IMAGE
                if is_video:
                    result = drive_uploader.upload_large_video_resumable(
                        file_path=temp_path,
                        folder_id=folder_result['folder_id'],
                        filename=file.filename
                    )
                else:
                    results = drive_uploader.upload_inspection_images_batch(
                        images_list=[temp_path],
                        folder_id=folder_result['folder_id']
                    )
                    result = results[0] if results else None

                if result:
                    media = CarInspectionMedia()
                    media.inspection_request_id = emp_request.inspection_data.id
                    media.file_type = inspection_file_type
                    media.drive_file_id = result['file_id']
                    media.drive_view_url = result['view_url']
                    media.drive_download_url = result.get('download_url')
                    media.original_filename = file.filename
                    media.file_size = result.get('file_size')
                    media.upload_status = 'completed'
                    media.upload_progress = 100
                    db.session.add(media)

            if result:
                uploaded_files.append({
                    'filename': file.filename,
                    'drive_url': result['view_url'],
                    'file_id': result['file_id']
                })

        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            continue
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    db.session.commit()

    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files,
        'google_drive_folder_url': folder_result['folder_url'],
        'message': f'تم رفع {len(uploaded_files)} ملف بنجاح إلى Google Drive'
    }), 200

@core_requests_api_v1.route('/requests/<int:request_id>/upload-inspection-image', methods=['POST'])
@token_required
def upload_inspection_image(current_employee, request_id):
    """
    رفع صورة واحدة لطلب فحص السيارة
    """
    emp_request = EmployeeRequest.query.filter_by(
        id=request_id,
        employee_id=current_employee.id
    ).first()

    if not emp_request:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

    if emp_request.request_type != RequestType.CAR_INSPECTION:
        return jsonify({'success': False, 'message': 'هذا الطلب ليس طلب فحص سيارة'}), 400

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'لا توجد صورة مرفقة'}), 400

    file = request.files['image']

    if not file or not file.filename or file.filename == '':
        return jsonify({'success': False, 'message': 'الصورة فارغة'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'نوع الملف غير مدعوم. الأنواع المدعومة: jpg, jpeg, png, heic'}), 400

    try:
        safe_filename = secure_filename(file.filename)
        file_ext = safe_filename.rsplit('.', 1)[1].lower() if '.' in safe_filename else 'jpg'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"inspection_{request_id}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_ext}"
        upload_folder = os.path.join('static', 'uploads', 'car_inspections')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        file_size = os.path.getsize(filepath)
        relative_path = f"static/uploads/car_inspections/{unique_filename}"
        public_url = f"https://nuzum.site/{relative_path}"

        media = CarInspectionMedia()
        media.inspection_request_id = emp_request.inspection_data.id
        media.file_type = FileType.IMAGE
        media.local_path = relative_path
        media.original_filename = file.filename
        media.file_size = file_size
        media.upload_status = 'completed'
        media.upload_progress = 100
        db.session.add(media)
        db.session.commit()

        drive_uploader = EmployeeRequestsDriveUploader()
        if drive_uploader.is_available():
            try:
                vehicle_number = None
                if emp_request.inspection_data and emp_request.inspection_data.vehicle:
                    vehicle_number = emp_request.inspection_data.vehicle.plate_number
                if not emp_request.google_drive_folder_id:
                    folder_result = drive_uploader.create_request_folder(
                        request_type='car_inspection',
                        request_id=emp_request.id,
                        employee_name=current_employee.name,
                        vehicle_number=vehicle_number if vehicle_number else ''
                    )
                    if folder_result:
                        emp_request.google_drive_folder_id = folder_result['folder_id']
                        emp_request.google_drive_folder_url = folder_result['folder_url']
                if emp_request.google_drive_folder_id:
                    results = drive_uploader.upload_inspection_images_batch(
                        images_list=[filepath],
                        folder_id=emp_request.google_drive_folder_id
                    )
                    if results and results[0]:
                        media.drive_file_id = results[0]['file_id']
                        media.drive_view_url = results[0]['view_url']
                        media.drive_download_url = results[0].get('download_url')
                db.session.commit()
            except Exception as drive_error:
                logger.warning(f"Google Drive upload failed (non-blocking): {str(drive_error)}")
        return jsonify({
            'success': True,
            'data': {
                'media_id': media.id,
                'image_url': public_url,
                'local_path': relative_path,
                'drive_url': media.drive_view_url if media.drive_view_url else None
            },
            'message': 'تم رفع الصورة بنجاح'
        }), 200

    except Exception as e:
        logger.error(f"Error uploading inspection image: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء رفع الصورة', 'error': str(e)}), 500

@core_requests_api_v1.route('/requests/<int:request_id>/upload-image', methods=['POST'])
@token_required
def upload_image_alias(current_employee, request_id):
    """مسار بديل لرفع صورة الفحص"""
    return upload_inspection_image(current_employee, request_id)

@core_requests_api_v1.route('/requests/statistics', methods=['GET'])
@token_required
def get_statistics(current_employee):
    """
    الحصول على إحصائيات طلبات الموظف
    """
    total = EmployeeRequest.query.filter_by(employee_id=current_employee.id).count()
    pending = EmployeeRequest.query.filter_by(employee_id=current_employee.id, status=RequestStatus.PENDING).count()
    approved = EmployeeRequest.query.filter_by(employee_id=current_employee.id, status=RequestStatus.APPROVED).count()
    rejected = EmployeeRequest.query.filter_by(employee_id=current_employee.id, status=RequestStatus.REJECTED).count()
    completed = EmployeeRequest.query.filter_by(employee_id=current_employee.id, status=RequestStatus.COMPLETED).count()
    closed = EmployeeRequest.query.filter_by(employee_id=current_employee.id, status=RequestStatus.CLOSED).count()

    by_type = {}
    for req_type in RequestType:
        count = EmployeeRequest.query.filter_by(
            employee_id=current_employee.id,
            request_type=req_type
        ).count()
        by_type[req_type.name] = count

    return jsonify({
        'success': True,
        'statistics': {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'completed': completed,
            'closed': closed,
            'by_type': by_type
        }
    }), 200

@core_requests_api_v1.route('/requests/types', methods=['GET'])
def get_request_types():
    """
    الحصول على أنواع الطلبات المتاحة
    """
    types = []
    type_labels = {
        'INVOICE': 'فاتورة',
        'CAR_WASH': 'غسيل سيارة',
        'CAR_INSPECTION': 'فحص وتوثيق سيارة',
        'ADVANCE_PAYMENT': 'سلفة مالية'
    }

    for req_type in RequestType:
        types.append({
            'value': req_type.name,
            'label_ar': type_labels.get(req_type.name, req_type.name)
        })

    return jsonify({
        'success': True,
        'types': types
    }), 200

@core_requests_api_v1.route('/requests/<int:request_id>', methods=['DELETE'])
@token_required
def delete_request(current_employee, request_id):
    """
    حذف طلب (يجب أن يكون بحالة PENDING)
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id
        ).first()

        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو ليس لديك صلاحية'}), 404

        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'لا يمكن حذف طلب تمت معالجته'}), 400

        if emp_request.request_type == RequestType.CAR_WASH:
            car_wash = CarWashRequest.query.filter_by(request_id=request_id).first()
            if car_wash:
                logger.info(f"💾 ملفات غسيل السيارة محفوظة للأمان ({len(car_wash.media_files)} ملف)")
        elif emp_request.request_type == RequestType.CAR_INSPECTION:
            inspection = CarInspectionRequest.query.filter_by(request_id=request_id).first()
            if inspection:
                logger.info(f"💾 ملفات الفحص محفوظة للأمان ({len(inspection.media_files)} ملف)")

        db.session.delete(emp_request)
        db.session.commit()

        logger.info(f"Employee {current_employee.job_number} deleted request #{request_id}")
        return jsonify({'success': True, 'message': 'تم حذف الطلب بنجاح'}), 200

    except Exception as e:
        logger.error(f"Error deleting request {request_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف الطلب', 'error': str(e)}), 500

@core_requests_api_v1.route('/requests/<int:request_id>/approve', methods=['POST'])
@token_required
def approve_request_api(current_employee, request_id):
    """
    الموافقة على طلب (للإداريين فقط)
    """
    try:
        emp_request = EmployeeRequest.query.get(request_id)

        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'الطلب تمت معالجته مسبقاً'}), 400

        data = request.get_json() or {}
        admin_notes = data.get('admin_notes', '')

        emp_request.status = RequestStatus.APPROVED
        emp_request.reviewed_at = datetime.utcnow()
        emp_request.reviewed_by = current_employee.id
        emp_request.admin_notes = admin_notes

        db.session.commit()

        logger.info(f"Request #{request_id} approved by employee {current_employee.job_number}")
        return jsonify({
            'success': True,
            'message': 'تمت الموافقة على الطلب',
            'request': {
                'id': emp_request.id,
                'status': emp_request.status.value,
                'reviewed_at': emp_request.reviewed_at.isoformat(),
                'reviewed_by': {
                    'id': current_employee.id,
                    'name': current_employee.name
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error approving request {request_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الموافقة'}), 500

@core_requests_api_v1.route('/requests/<int:request_id>/reject', methods=['POST'])
@token_required
def reject_request_api(current_employee, request_id):
    """
    رفض طلب (للإداريين فقط)
    """
    try:
        emp_request = EmployeeRequest.query.get(request_id)

        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'الطلب تمت معالجته مسبقاً'}), 400

        data = request.get_json() or {}
        rejection_reason = data.get('rejection_reason', '').strip()

        if not rejection_reason:
            return jsonify({'success': False, 'message': 'يجب إدخال سبب الرفض'}), 400

        emp_request.status = RequestStatus.REJECTED
        emp_request.reviewed_at = datetime.utcnow()
        emp_request.reviewed_by = current_employee.id
        emp_request.admin_notes = rejection_reason

        db.session.commit()

        logger.info(f"Request #{request_id} rejected by employee {current_employee.job_number}")
        return jsonify({
            'success': True,
            'message': 'تم رفض الطلب',
            'request': {
                'id': emp_request.id,
                'status': emp_request.status.value,
                'rejection_reason': rejection_reason,
                'reviewed_at': emp_request.reviewed_at.isoformat(),
                'reviewed_by': {
                    'id': current_employee.id,
                    'name': current_employee.name
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error rejecting request {request_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الرفض'}), 500
