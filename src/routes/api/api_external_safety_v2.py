"""
External Safety Check API Routes
================================
RESTful API endpoints for mobile apps and external integrations

Authentication:
- Uses Flask-Login for web sessions
- Can be extended with JWT tokens for mobile apps

Response Format:
- All responses return JSON
- Success: {'success': true, 'data': {...}, 'message': '...'}
- Error: {'success': false, 'error': '...', 'code': 'ERROR_CODE'}

Endpoints:
----------
1. Safety Checks CRUD:
   - POST   /api/v2/safety-checks          Create new check
   - GET    /api/v2/safety-checks          List all checks (with filters)
   - GET    /api/v2/safety-checks/<id>     Get specific check
   - PUT    /api/v2/safety-checks/<id>     Update check
   - DELETE /api/v2/safety-checks/<id>     Delete check

2. Check Actions:
   - POST   /api/v2/safety-checks/<id>/approve   Approve check
   - POST   /api/v2/safety-checks/<id>/reject    Reject check
   - POST   /api/v2/safety-checks/<id>/images    Upload images
   - DELETE /api/v2/safety-checks/<id>/images    Delete images

3. Utilities:
   - GET    /api/v2/vehicles                     List vehicles
   - GET    /api/v2/employees/<national_id>      Verify employee
   - POST   /api/v2/notifications/whatsapp       Send WhatsApp
   - POST   /api/v2/notifications/email          Send Email

4. Statistics:
   - GET    /api/v2/statistics/safety-checks     Get statistics
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from datetime import datetime
from functools import wraps
from src.core.api_v2_security import validate_request_token, get_api_v2_actor, rate_limit

# Import Service Layer
from src.services.external_safety_service import ExternalSafetyService

# Import Models (for basic queries only)
from models import Vehicle, VehicleExternalSafetyCheck

# Blueprint Definition
api_external_safety_bp = Blueprint('api_external_safety_v2', __name__, url_prefix='/api/v2')


# ===============================
# Decorators
# ===============================

def json_response(func):
    """
    Decorator to standardize JSON responses
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            current_app.logger.error(f"API Error in {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }), 500
    return wrapper


def require_api_auth(func):
    """
    Decorator for API authentication
    Currently uses Flask-Login, can be extended with JWT
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        _, error = validate_request_token(
            required_scopes=['api:v2:read', 'api:v2:write', 'safety:read', 'safety:write'],
            optional=False,
        )
        if error:
            return error
        return func(*args, **kwargs)
    return wrapper


def _api_user():
    return get_api_v2_actor() or current_user


# ===============================
# Safety Checks CRUD
# ===============================

@api_external_safety_bp.route('/safety-checks', methods=['POST'])
@rate_limit("30 per minute")
@json_response
def create_safety_check():
    """
    إنشاء فحص سلامة جديد
    
    Request Body:
    {
        "vehicle_id": 123,
        "driver_name": "أحمد محمد",
        "driver_national_id": "1234567890",
        "driver_department": "قسم النقل",
        "driver_city": "الرياض",
        "tires_ok": true,
        "lights_ok": true,
        "mirrors_ok": true,
        "body_ok": true,
        "cleanliness_ok": true,
        "notes": "ملاحظات",
        "latitude": 24.7136,
        "longitude": 46.6753
    }
    
    Response:
    {
        "success": true,
        "data": {
            "check_id": 456,
            "status": "pending",
            "created_at": "2024-01-01T10:00:00"
        },
        "message": "تم إنشاء الفحص بنجاح"
    }
    """
    data = request.get_json()
    
    # Validation
    required_fields = ['vehicle_id', 'driver_name', 'driver_national_id', 'driver_department', 'driver_city']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return jsonify({
            'success': False,
            'error': f'حقول مطلوبة مفقودة: {", ".join(missing_fields)}',
            'code': 'MISSING_FIELDS'
        }), 400
    
    # Get vehicle info
    vehicle = Vehicle.query.get(data['vehicle_id'])
    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'المركبة غير موجودة',
            'code': 'VEHICLE_NOT_FOUND'
        }), 404
    
    # Build check data
    check_data = {
        'vehicle_id': data['vehicle_id'],
        'vehicle_plate_number': data.get('vehicle_plate_number', vehicle.plate_number),
        'driver_name': data['driver_name'],
        'driver_national_id': data['driver_national_id'],
        'driver_department': data['driver_department'],
        'driver_city': data['driver_city'],
        'tires_ok': data.get('tires_ok', False),
        'lights_ok': data.get('lights_ok', False),
        'mirrors_ok': data.get('mirrors_ok', False),
        'body_ok': data.get('body_ok', False),
        'cleanliness_ok': data.get('cleanliness_ok', False),
        'notes': data.get('notes', ''),
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    }
    
    # Create via service
    api_user = _api_user()
    current_user_id = api_user.id if api_user else None
    result = ExternalSafetyService.create_safety_check(check_data, current_user_id)
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'CREATE_FAILED'
        }), 400
    
    check = result['check']
    
    # Send notifications (async recommended)
    try:
        ExternalSafetyService.send_supervisor_notification_email(check)
    except Exception as e:
        current_app.logger.error(f"فشل إرسال البريد: {str(e)}")
    
    return jsonify({
        'success': True,
        'data': {
            'check_id': check.id,
            'status': check.approval_status,
            'created_at': check.check_date.isoformat() if check.check_date else None
        },
        'message': 'تم إنشاء الفحص بنجاح'
    }), 201


@api_external_safety_bp.route('/safety-checks', methods=['GET'])
@json_response
def list_safety_checks():
    """
    استرجاع قائمة فحوصات السلامة مع الفلاتر
    
    Query Parameters:
    - status: pending|approved|rejected
    - vehicle_id: int
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - driver_name: string
    - limit: int (default: 50)
    - offset: int (default: 0)
    
    Response:
    {
        "success": true,
        "data": {
            "checks": [...],
            "total": 100,
            "limit": 50,
            "offset": 0
        }
    }
    """
    # Extract filters
    filters = {}
    
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    
    if request.args.get('vehicle_id'):
        filters['vehicle_id'] = int(request.args.get('vehicle_id'))
    
    if request.args.get('start_date'):
        try:
            filters['start_date'] = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'تنسيق start_date غير صحيح (استخدم YYYY-MM-DD)',
                'code': 'INVALID_DATE_FORMAT'
            }), 400
    
    if request.args.get('end_date'):
        try:
            filters['end_date'] = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'تنسيق end_date غير صحيح (استخدم YYYY-MM-DD)',
                'code': 'INVALID_DATE_FORMAT'
            }), 400
    
    if request.args.get('driver_name'):
        filters['driver_name'] = request.args.get('driver_name')
    
    # Pagination
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    # Get checks from service
    all_checks = ExternalSafetyService.get_safety_checks_with_filters(filters)
    total = len(all_checks)
    
    # Apply pagination
    checks = all_checks[offset:offset + limit]
    
    # Serialize
    checks_data = []
    for check in checks:
        checks_data.append({
            'id': check.id,
            'vehicle_id': check.vehicle_id,
            'vehicle_plate': check.vehicle_plate_number,
            'driver_name': check.driver_name,
            'driver_national_id': check.driver_national_id,
            'check_date': check.check_date.isoformat() if check.check_date else None,
            'approval_status': check.approval_status,
            'tires_ok': check.tires_ok,
            'lights_ok': check.lights_ok,
            'mirrors_ok': check.mirrors_ok,
            'body_ok': check.body_ok,
            'cleanliness_ok': check.cleanliness_ok,
            'notes': check.notes,
            'image_count': len(check.images) if hasattr(check, 'images') else 0
        })
    
    return jsonify({
        'success': True,
        'data': {
            'checks': checks_data,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>', methods=['GET'])
@json_response
def get_safety_check(check_id):
    """
    استرجاع تفاصيل فحص سلامة محدد
    
    Response:
    {
        "success": true,
        "data": {
            "check": {...},
            "images": [...]
        }
    }
    """
    try:
        check = ExternalSafetyService.get_safety_check_by_id(check_id)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'الفحص غير موجود',
            'code': 'CHECK_NOT_FOUND'
        }), 404
    
    # Serialize check
    check_data = {
        'id': check.id,
        'vehicle_id': check.vehicle_id,
        'vehicle_plate': check.vehicle_plate_number,
        'driver_name': check.driver_name,
        'driver_national_id': check.driver_national_id,
        'driver_department': check.driver_department,
        'driver_city': check.driver_city,
        'check_date': check.check_date.isoformat() if check.check_date else None,
        'approval_status': check.approval_status,
        'tires_ok': check.tires_ok,
        'lights_ok': check.lights_ok,
        'mirrors_ok': check.mirrors_ok,
        'body_ok': check.body_ok,
        'cleanliness_ok': check.cleanliness_ok,
        'notes': check.notes,
        'reviewed_by': check.reviewed_by_user_id,
        'review_date': check.review_date.isoformat() if check.review_date else None,
        'review_notes': check.review_notes,
        'latitude': check.latitude,
        'longitude': check.longitude
    }
    
    # Serialize images
    images_data = []
    if hasattr(check, 'images'):
        for img in check.images:
            images_data.append({
                'id': img.id,
                'url': img.image_url if hasattr(img, 'image_url') else img.image_path,
                'description': img.image_description if hasattr(img, 'image_description') else None
            })
    
    return jsonify({
        'success': True,
        'data': {
            'check': check_data,
            'images': images_data
        }
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>', methods=['PUT'])
@require_api_auth
@json_response
def update_safety_check(check_id):
    """
    تحديث فحص سلامة
    
    Request Body:
    {
        "driver_name": "...",
        "notes": "...",
        "tires_ok": true,
        ...
    }
    """
    data = request.get_json()
    
    api_user = _api_user()
    result = ExternalSafetyService.update_safety_check(
        check_id=check_id,
        data=data,
        current_user_id=api_user.id
    )
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'UPDATE_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'تم تحديث الفحص بنجاح'
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>', methods=['DELETE'])
@require_api_auth
@json_response
def delete_safety_check(check_id):
    """
    حذف فحص سلامة
    """
    api_user = _api_user()
    result = ExternalSafetyService.delete_safety_check(
        check_id=check_id,
        user_id=api_user.id
    )
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'DELETE_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'تم حذف الفحص بنجاح'
    })


# ===============================
# Check Actions
# ===============================

@api_external_safety_bp.route('/safety-checks/<int:check_id>/approve', methods=['POST'])
@require_api_auth
@json_response
def approve_check(check_id):
    """
    الموافقة على فحص السلامة
    
    Request Body:
    {
        "notes": "ملاحظات اختيارية"
    }
    """
    api_user = _api_user()
    result = ExternalSafetyService.approve_safety_check(
        check_id=check_id,
        reviewer_id=api_user.id,
        reviewer_name=getattr(api_user, 'username', getattr(api_user, 'name', 'api-user'))
    )
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'APPROVE_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'تم اعتماد الفحص بنجاح'
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>/reject', methods=['POST'])
@require_api_auth
@json_response
def reject_check(check_id):
    """
    رفض فحص السلامة
    
    Request Body:
    {
        "rejection_reason": "سبب الرفض (مطلوب)"
    }
    """
    data = request.get_json()
    rejection_reason = data.get('rejection_reason', '').strip()
    
    if not rejection_reason:
        return jsonify({
            'success': False,
            'error': 'سبب الرفض مطلوب',
            'code': 'MISSING_REASON'
        }), 400
    
    api_user = _api_user()
    result = ExternalSafetyService.reject_safety_check(
        check_id=check_id,
        reviewer_id=api_user.id,
        reviewer_name=getattr(api_user, 'username', getattr(api_user, 'name', 'api-user')),
        rejection_reason=rejection_reason
    )
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'REJECT_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'تم رفض الفحص'
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>/images', methods=['POST'])
@require_api_auth
@json_response
def upload_check_images(check_id):
    """
    رفع صور إضافية لفحص السلامة
    
    Content-Type: multipart/form-data
    Files: images[]
    """
    # Verify check exists
    try:
        ExternalSafetyService.get_safety_check_by_id(check_id)
    except:
        return jsonify({
            'success': False,
            'error': 'الفحص غير موجود',
            'code': 'CHECK_NOT_FOUND'
        }), 404
    
    uploaded_files = request.files.getlist('images[]')
    
    if not uploaded_files or not uploaded_files[0].filename:
        return jsonify({
            'success': False,
            'error': 'لم يتم اختيار ملفات',
            'code': 'NO_FILES'
        }), 400
    
    result = ExternalSafetyService.process_uploaded_images(uploaded_files, check_id)
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': 'فشل رفع الصور',
            'code': 'UPLOAD_FAILED',
            'details': result['errors']
        }), 400
    
    return jsonify({
        'success': True,
        'data': {
            'uploaded_count': result['uploaded_count']
        },
        'message': f'تم رفع {result["uploaded_count"]} صورة بنجاح'
    })


@api_external_safety_bp.route('/safety-checks/<int:check_id>/images', methods=['DELETE'])
@require_api_auth
@json_response
def delete_check_images(check_id):
    """
    حذف صور من فحص السلامة
    
    Request Body:
    {
        "image_ids": [1, 2, 3]
    }
    """
    data = request.get_json()
    image_ids = data.get('image_ids', [])
    
    if not image_ids:
        return jsonify({
            'success': False,
            'error': 'لم يتم تحديد صور للحذف',
            'code': 'NO_IMAGES'
        }), 400
    
    result = ExternalSafetyService.delete_safety_check_images(check_id, image_ids)
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'DELETE_FAILED'
        }), 400
    
    return jsonify({
        'success': True,
        'data': {
            'deleted_count': result['deleted_count']
        },
        'message': result['message']
    })


# ===============================
# Utilities
# ===============================

@api_external_safety_bp.route('/vehicles', methods=['GET'])
@json_response
def list_vehicles():
    """
    استرجاع قائمة المركبات
    
    Query Parameters:
    - status: active|inactive
    - make: string
    - search: string (للبحث في رقم اللوحة)
    - limit: int
    - offset: int
    """
    query = Vehicle.query
    
    # Filters
    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))
    
    if request.args.get('make'):
        query = query.filter_by(make=request.args.get('make'))
    
    if request.args.get('search'):
        search = request.args.get('search')
        query = query.filter(Vehicle.plate_number.ilike(f'%{search}%'))
    
    # Pagination
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    total = query.count()
    vehicles = query.offset(offset).limit(limit).all()
    
    # Serialize
    vehicles_data = []
    for vehicle in vehicles:
        vehicles_data.append({
            'id': vehicle.id,
            'plate_number': vehicle.plate_number,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.year,
            'status': vehicle.status
        })
    
    return jsonify({
        'success': True,
        'data': {
            'vehicles': vehicles_data,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    })


@api_external_safety_bp.route('/employees/<national_id>', methods=['GET'])
@json_response
def verify_employee(national_id):
    """
    التحقق من وجود موظف بواسطة رقم الهوية
    
    Response:
    {
        "success": true,
        "data": {
            "exists": true,
            "name": "أحمد محمد علي"
        }
    }
    """
    result = ExternalSafetyService.verify_employee_by_national_id(national_id)
    
    return jsonify({
        'success': True,
        'data': {
            'exists': result['exists'],
            'name': result['name']
        }
    })


@api_external_safety_bp.route('/notifications/whatsapp', methods=['POST'])
@json_response
def send_whatsapp():
    """
    إرسال إشعار WhatsApp
    
    Request Body:
    {
        "phone_number": "+966xxxxxxxxx",
        "vehicle_plate": "ABC-1234",
        "check_url": "https://..."
    }
    """
    data = request.get_json()
    
    required = ['phone_number', 'vehicle_plate', 'check_url']
    if not all(data.get(field) for field in required):
        return jsonify({
            'success': False,
            'error': 'بيانات ناقصة',
            'code': 'MISSING_FIELDS'
        }), 400
    
    result = ExternalSafetyService.send_whatsapp_notification(
        phone_number=data['phone_number'],
        vehicle_plate=data['vehicle_plate'],
        check_url=data['check_url']
    )
    
    if not result['success']:
        return jsonify({
            'success': False,
            'error': result['message'],
            'code': 'WHATSAPP_FAILED'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'تم إرسال الرسالة بنجاح'
    })


@api_external_safety_bp.route('/notifications/email', methods=['POST'])
@json_response
def send_email():
    """
    إرسال بريد إلكتروني
    
    Request Body:
    {
        "email": "user@example.com",
        "subject": "...",
        "body": "..."
    }
    """
    # TODO: Implement email sending via service
    return jsonify({
        'success': False,
        'error': 'الميزة غير متاحة حالياً',
        'code': 'NOT_IMPLEMENTED'
    }), 501


# ===============================
# Statistics
# ===============================

@api_external_safety_bp.route('/statistics/safety-checks', methods=['GET'])
@json_response
def get_statistics():
    """
    استرجاع احصائيات فحوصات السلامة
    
    Query Parameters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    
    Response:
    {
        "success": true,
        "data": {
            "total_checks": 100,
            "pending": 20,
            "approved": 70,
            "rejected": 10,
            "approval_rate": 87.5
        }
    }
    """
    start_date = None
    end_date = None
    
    if request.args.get('start_date'):
        try:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
        except ValueError:
            pass
    
    if request.args.get('end_date'):
        try:
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
        except ValueError:
            pass
    
    stats = ExternalSafetyService.get_safety_check_statistics(start_date, end_date)
    
    return jsonify({
        'success': True,
        'data': stats
    })


# ===============================
# Health Check
# ===============================

@api_external_safety_bp.route('/health', methods=['GET'])
def health_check():
    """
    API صحة النظام
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'version': 'v2.0',
        'timestamp': datetime.utcnow().isoformat()
    })
