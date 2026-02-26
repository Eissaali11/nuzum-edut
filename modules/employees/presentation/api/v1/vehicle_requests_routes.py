import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from core.extensions import db
from models import (
    Employee, Vehicle, EmployeeRequest, CarWashRequest, CarInspectionRequest,
    CarWashMedia, CarInspectionMedia, RequestType, RequestStatus, MediaType, FileType
)
from modules.employees.presentation.api.v1.auth_routes import token_required

logger = logging.getLogger(__name__)

vehicle_api_v1 = Blueprint('vehicle_api_v1', __name__, url_prefix='/api/v1')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'mp4', 'mov', 'avi', 'pdf'}
    if not filename or not isinstance(filename, str):
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@vehicle_api_v1.route('/vehicles', methods=['GET'])
@token_required
def get_vehicles(current_employee):
    """
    الحصول على قائمة السيارات المتاحة
    """
    vehicles = Vehicle.query.filter_by(status='active').all()
    
    vehicles_list = []
    for vehicle in vehicles:
        vehicles_list.append({
            'id': vehicle.id,
            'plate_number': vehicle.plate_number,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.year,
            'color': vehicle.color
        })
    
    return jsonify({
        'success': True,
        'vehicles': vehicles_list
    }), 200

@vehicle_api_v1.route('/requests/create-car-wash', methods=['POST'])
@token_required
def create_car_wash_request(current_employee):
    """
    إنشاء طلب غسيل سيارة مع صور
    """
    vehicle_id = request.form.get('vehicle_id')
    service_type = request.form.get('service_type')
    
    if not vehicle_id or not service_type:
        return jsonify({
            'success': False,
            'message': 'رقم السيارة ونوع الخدمة مطلوبان'
        }), 400
    
    valid_service_types = ['normal', 'polish', 'full_clean']
    if service_type not in valid_service_types:
        return jsonify({
            'success': False,
            'message': f'نوع الخدمة غير صحيح. الأنواع المتاحة: {", ".join(valid_service_types)}'
        }), 400
    
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({
            'success': False,
            'message': 'السيارة غير موجودة'
        }), 404
    
    try:
        new_request = EmployeeRequest()
        new_request.employee_id = current_employee.id
        new_request.request_type = RequestType.CAR_WASH
        new_request.title = f"طلب غسيل سيارة - {vehicle.plate_number}"
        new_request.status = RequestStatus.PENDING
        
        db.session.add(new_request)
        db.session.flush()
        
        requested_date_str = request.form.get('requested_date')
        requested_date = datetime.strptime(requested_date_str, '%Y-%m-%d').date() if requested_date_str else None
        
        car_wash_request = CarWashRequest()
        car_wash_request.request_id = new_request.id
        car_wash_request.vehicle_id = vehicle_id
        car_wash_request.service_type = service_type
        car_wash_request.scheduled_date = requested_date
        
        db.session.add(car_wash_request)
        
        required_photos = ['photo_plate', 'photo_front', 'photo_back', 'photo_right_side', 'photo_left_side']
        upload_dir = os.path.join('static', 'uploads', 'car_wash')
        os.makedirs(upload_dir, exist_ok=True)
        
        for photo_field in required_photos:
            if photo_field in request.files:
                photo_file = request.files[photo_field]
                if photo_file and photo_file.filename and allowed_file(photo_file.filename):
                    filename = secure_filename(photo_file.filename)
                    file_ext = filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"wash_{new_request.id}_{photo_field}_{uuid.uuid4().hex[:8]}.{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    photo_file.save(file_path)
                    
                    media_type_map = {
                        'photo_plate': MediaType.PLATE,
                        'photo_front': MediaType.FRONT,
                        'photo_back': MediaType.BACK,
                        'photo_right_side': MediaType.RIGHT,
                        'photo_left_side': MediaType.LEFT
                    }
                    
                    car_wash_media = CarWashMedia()
                    car_wash_media.wash_request_id = car_wash_request.id
                    car_wash_media.media_type = media_type_map[photo_field]
                    car_wash_media.local_path = f"uploads/car_wash/{unique_filename}"
                    db.session.add(car_wash_media)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء طلب الغسيل بنجاح',
            'data': {
                'request_id': new_request.id,
                'type': 'car_wash',
                'status': 'pending',
                'vehicle_plate': vehicle.plate_number,
                'service_type': service_type
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating car wash request for employee {current_employee.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إنشاء طلب الغسيل',
            'error': str(e)
        }), 500

@vehicle_api_v1.route('/requests/create-car-inspection', methods=['POST'])
@token_required
def create_car_inspection_request(current_employee):
    """
    إنشاء طلب فحص وتوثيق سيارة
    """
    data = request.get_json()
    
    if not data or not data.get('vehicle_id') or not data.get('inspection_type'):
        return jsonify({
            'success': False,
            'message': 'رقم السيارة ونوع الفحص مطلوبان'
        }), 400
    
    vehicle_id = data.get('vehicle_id')
    inspection_type = data.get('inspection_type')
    
    if inspection_type not in ['delivery', 'receipt']:
        return jsonify({
            'success': False,
            'message': 'نوع الفحص غير صحيح. الأنواع المتاحة: delivery, receipt'
        }), 400
    
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({
            'success': False,
            'message': 'السيارة غير موجودة'
        }), 404
    
    try:
        inspection_type_ar = 'فحص تسليم' if inspection_type == 'delivery' else 'فحص استلام'
        
        new_request = EmployeeRequest()
        new_request.employee_id = current_employee.id
        new_request.request_type = RequestType.CAR_INSPECTION
        new_request.title = f"{inspection_type_ar} - {vehicle.plate_number}"
        new_request.status = RequestStatus.PENDING
        
        db.session.add(new_request)
        db.session.flush()
        
        car_inspection_request = CarInspectionRequest()
        car_inspection_request.request_id = new_request.id
        car_inspection_request.vehicle_id = vehicle_id
        car_inspection_request.inspection_type = inspection_type
        
        db.session.add(car_inspection_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء طلب الفحص بنجاح',
            'data': {
                'request_id': new_request.id,
                'type': 'car_inspection',
                'status': 'pending',
                'inspection_type': inspection_type,
                'inspection_type_ar': inspection_type_ar,
                'vehicle_plate': vehicle.plate_number,
                'upload_instructions': {
                    'max_images': 20,
                    'max_videos': 3,
                    'max_image_size_mb': 10,
                    'max_video_size_mb': 500,
                    'supported_formats': {
                        'images': ['jpg', 'jpeg', 'png', 'heic'],
                        'videos': ['mp4', 'mov']
                    },
                    'upload_endpoint': f'/api/v1/requests/{new_request.id}/upload'
                }
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating car inspection request for employee {current_employee.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إنشاء طلب الفحص',
            'error': str(e)
        }), 500

@vehicle_api_v1.route('/requests/car-wash/<int:request_id>', methods=['PUT'])
@token_required
def update_car_wash_request(current_employee, request_id):
    """
    تعديل طلب غسيل سيارة
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id,
            request_type=RequestType.CAR_WASH
        ).first()
        
        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو ليس لديك صلاحية'}), 404
        
        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب تمت معالجته'}), 400
        
        car_wash_data = CarWashRequest.query.filter_by(request_id=request_id).first()
        if not car_wash_data:
            return jsonify({'success': False, 'message': 'بيانات غسيل السيارة غير موجودة'}), 404
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            vehicle_id = request.form.get('vehicle_id')
            service_type = request.form.get('service_type')
            scheduled_date_str = request.form.get('scheduled_date')
            notes = request.form.get('notes')
        else:
            data = request.get_json() or {}
            vehicle_id = data.get('vehicle_id')
            service_type = data.get('service_type')
            scheduled_date_str = data.get('scheduled_date')
            notes = data.get('notes')
        
        if vehicle_id:
            vehicle = Vehicle.query.get(int(vehicle_id))
            if not vehicle:
                return jsonify({'success': False, 'message': 'السيارة غير موجودة'}), 404
            car_wash_data.vehicle_id = int(vehicle_id)
        
        if service_type and service_type in ['normal', 'polish', 'full_clean']:
            car_wash_data.service_type = service_type
        
        if scheduled_date_str:
            car_wash_data.scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            delete_media_ids = request.form.getlist('delete_media_ids')
        else:
            delete_media_ids = request.get_json().get('delete_media_ids', []) if request.get_json() else []
        
        if delete_media_ids:
            for media_id in delete_media_ids:
                media = CarWashMedia.query.get(int(media_id))
                if media and media.wash_request_id == car_wash_data.id:
                    if media.local_path:
                        logger.info(f"💾 الصورة محفوظة للأمان: {media.local_path}")
                    db.session.delete(media)
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            photo_fields = ['photo_plate', 'photo_front', 'photo_back', 'photo_right_side', 'photo_left_side']
            upload_dir = os.path.join('static', 'uploads', 'car_wash')
            os.makedirs(upload_dir, exist_ok=True)
            
            media_type_map = {
                'photo_plate': MediaType.PLATE,
                'photo_front': MediaType.FRONT,
                'photo_back': MediaType.BACK,
                'photo_right_side': MediaType.RIGHT,
                'photo_left_side': MediaType.LEFT
            }
            
            for photo_field in photo_fields:
                if photo_field in request.files:
                    photo_file = request.files[photo_field]
                    if photo_file and photo_file.filename:
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'heic'}
                        file_extension = photo_file.filename.rsplit('.', 1)[1].lower() if '.' in photo_file.filename else ''
                        
                        if file_extension in allowed_extensions:
                            old_media = CarWashMedia.query.filter_by(
                                wash_request_id=car_wash_data.id,
                                media_type=media_type_map[photo_field]
                            ).first()
                            
                            if old_media:
                                if old_media.local_path:
                                    logger.info(f"💾 الصورة القديمة محفوظة للأمان: {old_media.local_path}")
                                db.session.delete(old_media)
                            
                            unique_filename = f"wash_{request_id}_{photo_field}_{uuid.uuid4().hex[:8]}.{file_extension}"
                            file_path = os.path.join(upload_dir, unique_filename)
                            photo_file.save(file_path)
                            
                            new_media = CarWashMedia()
                            new_media.wash_request_id = car_wash_data.id
                            new_media.media_type = media_type_map[photo_field]
                            new_media.local_path = f"uploads/car_wash/{unique_filename}"
                            db.session.add(new_media)
        
        emp_request.updated_at = datetime.utcnow()
        db.session.commit()
        
        vehicle = Vehicle.query.get(car_wash_data.vehicle_id)
        media_files = CarWashMedia.query.filter_by(wash_request_id=car_wash_data.id).all()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث طلب الغسيل بنجاح',
            'request': {
                'id': emp_request.id,
                'type': 'CAR_WASH',
                'status': emp_request.status.value,
                'vehicle': {'id': vehicle.id, 'plate_number': vehicle.plate_number} if vehicle else None,
                'service_type': car_wash_data.service_type,
                'scheduled_date': car_wash_data.scheduled_date.isoformat() if car_wash_data.scheduled_date else None,
                'media_count': len(media_files),
                'updated_at': emp_request.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating car wash request {request_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الطلب', 'error': str(e)}), 500

@vehicle_api_v1.route('/requests/car-inspection/<int:request_id>', methods=['PUT'])
@token_required
def update_car_inspection_request(current_employee, request_id):
    """
    تعديل طلب فحص سيارة
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id,
            request_type=RequestType.CAR_INSPECTION
        ).first()
        
        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو ليس لديك صلاحية'}), 404
        
        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب تمت معالجته'}), 400
        
        inspection_data = CarInspectionRequest.query.filter_by(request_id=request_id).first()
        if not inspection_data:
            return jsonify({'success': False, 'message': 'بيانات فحص السيارة غير موجودة'}), 404
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            vehicle_id = request.form.get('vehicle_id')
            inspection_type = request.form.get('inspection_type')
            inspection_date_str = request.form.get('inspection_date')
            notes = request.form.get('notes')
        else:
            data = request.get_json() or {}
            vehicle_id = data.get('vehicle_id')
            inspection_type = data.get('inspection_type')
            inspection_date_str = data.get('inspection_date')
            notes = data.get('notes')
        
        if vehicle_id:
            vehicle = Vehicle.query.get(int(vehicle_id))
            if not vehicle:
                return jsonify({'success': False, 'message': 'السيارة غير موجودة'}), 404
            inspection_data.vehicle_id = int(vehicle_id)
        
        if inspection_type and inspection_type in ['periodic', 'comprehensive', 'pre_sale']:
            inspection_data.inspection_type = inspection_type
        
        if inspection_date_str:
            inspection_data.inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date()
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            delete_media_ids = request.form.getlist('delete_media_ids')
        else:
            delete_media_ids = request.get_json().get('delete_media_ids', []) if request.get_json() else []
        
        if delete_media_ids:
            for media_id in delete_media_ids:
                media = CarInspectionMedia.query.get(int(media_id))
                if media and media.inspection_request_id == inspection_data.id:
                    if media.local_path:
                        logger.info(f"💾 الملف محفوظ للأمان: {media.local_path}")
                    db.session.delete(media)
        
        if request.content_type and 'multipart/form-data' in request.content_type and 'files' in request.files:
            files = request.files.getlist('files')
            upload_dir = os.path.join('static', 'uploads', 'car_inspection')
            os.makedirs(upload_dir, exist_ok=True)
            
            for file in files:
                if file and file.filename:
                    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    
                    if file_extension in ['jpg', 'jpeg', 'png', 'heic']:
                        file_type = FileType.IMAGE
                    elif file_extension in ['mp4', 'mov', 'avi']:
                        file_type = FileType.VIDEO
                    else:
                        continue
                    
                    unique_filename = f"inspection_{request_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    
                    new_media = CarInspectionMedia()
                    new_media.inspection_request_id = inspection_data.id
                    new_media.file_type = file_type
                    new_media.original_filename = secure_filename(file.filename)
                    new_media.local_path = f"uploads/car_inspection/{unique_filename}"
                    db.session.add(new_media)
        
        emp_request.updated_at = datetime.utcnow()
        db.session.commit()
        
        vehicle = Vehicle.query.get(inspection_data.vehicle_id)
        media_files = CarInspectionMedia.query.filter_by(inspection_request_id=inspection_data.id).all()
        images_count = sum(1 for m in media_files if m.file_type == FileType.IMAGE)
        videos_count = sum(1 for m in media_files if m.file_type == FileType.VIDEO)
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث طلب الفحص بنجاح',
            'request': {
                'id': emp_request.id,
                'type': 'CAR_INSPECTION',
                'status': emp_request.status.value,
                'vehicle': {'id': vehicle.id, 'plate_number': vehicle.plate_number} if vehicle else None,
                'inspection_type': inspection_data.inspection_type,
                'inspection_date': inspection_data.inspection_date.isoformat() if inspection_data.inspection_date else None,
                'media': {'images_count': images_count, 'videos_count': videos_count},
                'updated_at': emp_request.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating car inspection request {request_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الطلب', 'error': str(e)}), 500

@vehicle_api_v1.route('/requests/car-wash/<int:request_id>/media/<int:media_id>', methods=['DELETE'])
@token_required
def delete_car_wash_media(current_employee, request_id, media_id):
    """
    حذف صورة من طلب غسيل
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id,
            request_type=RequestType.CAR_WASH
        ).first()
        
        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404
        
        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب تمت معالجته'}), 400
        
        car_wash = CarWashRequest.query.filter_by(request_id=request_id).first()
        if not car_wash:
            return jsonify({'success': False, 'message': 'بيانات الغسيل غير موجودة'}), 404
        
        media = CarWashMedia.query.filter_by(id=media_id, wash_request_id=car_wash.id).first()
        if not media:
            return jsonify({'success': False, 'message': 'الصورة غير موجودة'}), 404
        
        if media.local_path:
            logger.info(f"💾 الصورة محفوظة للأمان: {media.local_path}")
        
        db.session.delete(media)
        db.session.commit()
        
        remaining_count = CarWashMedia.query.filter_by(wash_request_id=car_wash.id).count()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الصورة بنجاح',
            'remaining_media_count': remaining_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting car wash media {media_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف الصورة'}), 500

@vehicle_api_v1.route('/requests/car-inspection/<int:request_id>/media/<int:media_id>', methods=['DELETE'])
@token_required
def delete_car_inspection_media(current_employee, request_id, media_id):
    """
    حذف ملف من طلب فحص
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id,
            request_type=RequestType.CAR_INSPECTION
        ).first()
        
        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404
        
        if emp_request.status != RequestStatus.PENDING:
            return jsonify({'success': False, 'message': 'لا يمكن تعديل طلب تمت معالجته'}), 400
        
        inspection = CarInspectionRequest.query.filter_by(request_id=request_id).first()
        if not inspection:
            return jsonify({'success': False, 'message': 'بيانات الفحص غير موجودة'}), 404
        
        media = CarInspectionMedia.query.filter_by(id=media_id, inspection_request_id=inspection.id).first()
        if not media:
            return jsonify({'success': False, 'message': 'الملف غير موجود'}), 404
        
        if media.local_path:
            logger.info(f"💾 الملف محفوظ للأمان: {media.local_path}")
        
        db.session.delete(media)
        db.session.commit()
        
        all_media = CarInspectionMedia.query.filter_by(inspection_request_id=inspection.id).all()
        images_count = sum(1 for m in all_media if m.file_type == FileType.IMAGE)
        videos_count = sum(1 for m in all_media if m.file_type == FileType.VIDEO)
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الملف بنجاح',
            'remaining_media': {'images_count': images_count, 'videos_count': videos_count}
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting car inspection media {media_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حذف الملف'}), 500

@vehicle_api_v1.route('/requests/car-wash', methods=['GET'])
@token_required
def get_car_wash_requests(current_employee):
    """
    قائمة طلبات غسيل السيارات فقط مع فلترة
    """
    try:
        status = request.args.get('status')
        vehicle_id = request.args.get('vehicle_id', type=int)
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = EmployeeRequest.query.filter(
            EmployeeRequest.employee_id == current_employee.id,
            EmployeeRequest.request_type == RequestType.CAR_WASH
        )
        
        if status:
            try:
                status_enum = RequestStatus[status.upper()]
                query = query.filter(EmployeeRequest.status == status_enum)
            except KeyError:
                pass
        
        if from_date_str:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
            query = query.filter(EmployeeRequest.created_at >= from_date)
        
        if to_date_str:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
            query = query.filter(EmployeeRequest.created_at <= to_date)
        
        if vehicle_id:
            query = query.join(CarWashRequest).filter(CarWashRequest.vehicle_id == vehicle_id)
        
        query = query.order_by(EmployeeRequest.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        requests_list = []
        for emp_req in pagination.items:
            car_wash = CarWashRequest.query.filter_by(request_id=emp_req.id).first()
            if not car_wash:
                continue
            
            vehicle = Vehicle.query.get(car_wash.vehicle_id) if car_wash.vehicle_id else None
            media_count = CarWashMedia.query.filter_by(wash_request_id=car_wash.id).count()
            
            service_type_display = {
                'normal': 'غسيل عادي',
                'polish': 'تلميع وتنظيف',
                'full_clean': 'تنظيف شامل'
            }.get(car_wash.service_type, car_wash.service_type)
            
            status_display = {
                'PENDING': 'قيد الانتظار',
                'APPROVED': 'موافق عليه',
                'REJECTED': 'مرفوض',
                'COMPLETED': 'مكتمل',
                'CLOSED': 'مغلق'
            }.get(emp_req.status.value, emp_req.status.value)
            
            requests_list.append({
                'id': emp_req.id,
                'status': emp_req.status.value,
                'status_display': status_display,
                'employee': {
                    'id': current_employee.id,
                    'name': current_employee.name,
                    'job_number': current_employee.job_number
                },
                'vehicle': {
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model
                } if vehicle else None,
                'service_type': car_wash.service_type,
                'service_type_display': service_type_display,
                'scheduled_date': car_wash.scheduled_date.isoformat() if car_wash.scheduled_date else None,
                'media_count': media_count,
                'created_at': emp_req.created_at.isoformat(),
                'updated_at': emp_req.updated_at.isoformat() if emp_req.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'requests': requests_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching car wash requests: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء جلب الطلبات', 'error': str(e)}), 500

@vehicle_api_v1.route('/requests/car-inspection', methods=['GET'])
@token_required
def get_car_inspection_requests(current_employee):
    """
    قائمة طلبات فحص السيارات فقط مع فلترة
    """
    try:
        status = request.args.get('status')
        vehicle_id = request.args.get('vehicle_id', type=int)
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = EmployeeRequest.query.filter(
            EmployeeRequest.employee_id == current_employee.id,
            EmployeeRequest.request_type == RequestType.CAR_INSPECTION
        )
        
        if status:
            try:
                status_enum = RequestStatus[status.upper()]
                query = query.filter(EmployeeRequest.status == status_enum)
            except KeyError:
                pass
        
        if from_date_str:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
            query = query.filter(EmployeeRequest.created_at >= from_date)
        
        if to_date_str:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
            query = query.filter(EmployeeRequest.created_at <= to_date)
        
        if vehicle_id:
            query = query.join(CarInspectionRequest).filter(CarInspectionRequest.vehicle_id == vehicle_id)
        
        query = query.order_by(EmployeeRequest.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        requests_list = []
        for emp_req in pagination.items:
            inspection = CarInspectionRequest.query.filter_by(request_id=emp_req.id).first()
            if not inspection:
                continue
            
            vehicle = Vehicle.query.get(inspection.vehicle_id) if inspection.vehicle_id else None
            all_media = CarInspectionMedia.query.filter_by(inspection_request_id=inspection.id).all()
            images_count = sum(1 for m in all_media if m.file_type == FileType.IMAGE)
            videos_count = sum(1 for m in all_media if m.file_type == FileType.VIDEO)
            
            inspection_type_display = {
                'periodic': 'فحص دوري',
                'comprehensive': 'فحص شامل',
                'pre_sale': 'فحص قبل البيع'
            }.get(inspection.inspection_type, inspection.inspection_type)
            
            status_display = {
                'PENDING': 'قيد الانتظار',
                'APPROVED': 'موافق عليه',
                'REJECTED': 'مرفوض',
                'COMPLETED': 'مكتمل',
                'CLOSED': 'مغلق'
            }.get(emp_req.status.value, emp_req.status.value)
            
            requests_list.append({
                'id': emp_req.id,
                'status': emp_req.status.value,
                'status_display': status_display,
                'employee': {
                    'id': current_employee.id,
                    'name': current_employee.name,
                    'job_number': current_employee.job_number
                },
                'vehicle': {
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model
                } if vehicle else None,
                'inspection_type': inspection.inspection_type,
                'inspection_type_display': inspection_type_display,
                'inspection_date': inspection.inspection_date.isoformat() if inspection.inspection_date else None,
                'media': {
                    'images_count': images_count,
                    'videos_count': videos_count,
                    'total_count': len(all_media)
                },
                'created_at': emp_req.created_at.isoformat(),
                'updated_at': emp_req.updated_at.isoformat() if emp_req.updated_at else None,
                'reviewed_at': emp_req.reviewed_at.isoformat() if emp_req.reviewed_at else None
            })
        
        return jsonify({
            'success': True,
            'requests': requests_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching car inspection requests: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء جلب الطلبات', 'error': str(e)}), 500

@vehicle_api_v1.route('/requests/car-wash/<int:request_id>', methods=['GET'])
@token_required
def get_car_wash_details(current_employee, request_id):
    """
    تفاصيل طلب غسيل موسعة مع جميع الصور
    """
    try:
        emp_request = EmployeeRequest.query.filter_by(
            id=request_id,
            employee_id=current_employee.id,
            request_type=RequestType.CAR_WASH
        ).first()
        
        if not emp_request:
            return jsonify({'success': False, 'message': 'الطلب غير موجود أو ليس لديك صلاحية'}), 404
        
        car_wash = CarWashRequest.query.filter_by(request_id=request_id).first()
        if not car_wash:
            return jsonify({'success': False, 'message': 'بيانات الغسيل غير موجودة'}), 404
        
        vehicle = Vehicle.query.get(car_wash.vehicle_id) if car_wash.vehicle_id else None
        media_files = CarWashMedia.query.filter_by(wash_request_id=car_wash.id).all()
        
        reviewed_by_user = None
        if emp_request.reviewed_by:
            reviewer = Employee.query.get(emp_request.reviewed_by)
            if reviewer:
                reviewed_by_user = {'id': reviewer.id, 'name': reviewer.name, 'job_number': reviewer.job_number}
        
        media_list = []
        for media in media_files:
            media_type_display = {
                'PLATE': 'لوحة السيارة',
                'FRONT': 'صورة أمامية',
                'BACK': 'صورة خلفية',
                'RIGHT': 'جانب أيمن',
                'LEFT': 'جانب أيسر'
            }.get(media.media_type.value, media.media_type.value)
            
            media_list.append({
                'id': media.id,
                'media_type': media.media_type.value,
                'media_type_display': media_type_display,
                'local_path': f"/static/{media.local_path}" if media.local_path else None,
                'drive_view_url': media.drive_view_url,
                'file_size_kb': media.file_size // 1024 if media.file_size else 0,
                'uploaded_at': media.uploaded_at.isoformat() if media.uploaded_at else None
            })
        
        service_type_display = {
            'normal': 'غسيل عادي',
            'polish': 'تلميع وتنظيف',
            'full_clean': 'تنظيف شامل'
        }.get(car_wash.service_type, car_wash.service_type)
        
        status_display = {
            'PENDING': 'قيد الانتظار',
            'APPROVED': 'موافق عليه',
            'REJECTED': 'مرفوض',
            'COMPLETED': 'مكتمل',
            'CLOSED': 'مغلق'
        }.get(emp_request.status.value, emp_request.status.value)
        
        return jsonify({
            'success': True,
            'request': {
                'id': emp_request.id,
                'type': 'CAR_WASH',
                'status': emp_request.status.value,
                'status_display': status_display,
                'employee': {
                    'id': current_employee.id,
                    'name': current_employee.name,
                    'job_number': current_employee.job_number,
                    'department': current_employee.department.name if current_employee.department else None
                },
                'vehicle': {
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'year': vehicle.year,
                    'color': vehicle.color
                } if vehicle else None,
                'service_type': car_wash.service_type,
                'service_type_display': service_type_display,
                'scheduled_date': car_wash.scheduled_date.isoformat() if car_wash.scheduled_date else None,
                'notes': emp_request.description,
                'media_files': media_list,
                'created_at': emp_request.created_at.isoformat(),
                'updated_at': emp_request.updated_at.isoformat() if emp_request.updated_at else None,
                'reviewed_at': emp_request.reviewed_at.isoformat() if emp_request.reviewed_at else None,
                'reviewed_by': reviewed_by_user,
                'admin_notes': emp_request.admin_notes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching car wash details {request_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء جلب التفاصيل', 'error': str(e)}), 500
