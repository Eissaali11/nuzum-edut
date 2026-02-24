"""
Employee Requests REST API v2 (Refactored)

Modern REST API for mobile employee requests using service layer.
All business logic delegated to EmployeeRequestService.

Author: Refactored from api_employee_requests.py (3,403 lines → v2 API)
Date: 2026-02-20

Endpoints:
- POST /api/v2/employee-requests/auth/login - JWT authentication
- GET /api/v2/employee-requests/requests - List requests
- GET /api/v2/employee-requests/requests/<id> - Get request details
- POST /api/v2/employee-requests/requests - Create generic request
- POST /api/v2/employee-requests/requests/advance-payment - Create advance payment
- POST /api/v2/employee-requests/requests/invoice - Create invoice
- POST /api/v2/employee-requests/requests/car-wash - Create car wash
- POST /api/v2/employee-requests/requests/car-inspection - Create car inspection
- PUT /api/v2/employee-requests/requests/car-wash/<id> - Update car wash
- PUT /api/v2/employee-requests/requests/car-inspection/<id> - Update car inspection
- DELETE /api/v2/employee-requests/requests/<id> - Delete request
- POST /api/v2/employee-requests/requests/<id>/upload - Upload files
- DELETE /api/v2/employee-requests/requests/car-wash/<id>/media/<media_id> - Delete car wash media
- DELETE /api/v2/employee-requests/requests/car-inspection/<id>/media/<media_id> - Delete car inspection media
- POST /api/v2/employee-requests/requests/<id>/approve - Approve request (admin)
- POST /api/v2/employee-requests/requests/<id>/reject - Reject request (admin)
- GET /api/v2/employee-requests/requests/types - Get request types
- GET /api/v2/employee-requests/requests/statistics - Get statistics
- GET /api/v2/employee-requests/vehicles - Get vehicles
- GET /api/v2/employee-requests/notifications - Get notifications
- PUT /api/v2/employee-requests/notifications/<id>/read - Mark notification as read
- PUT /api/v2/employee-requests/notifications/mark-all-read - Mark all as read
- GET /api/v2/employee-requests/employee/profile - Get employee profile
- GET /api/v2/employee-requests/employee/liabilities - Get liabilities
- GET /api/v2/employee-requests/employee/financial-summary - Get financial summary
- GET /api/v2/employee-requests/health - Health check
"""

import logging
from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime

from services.employee_request_service import EmployeeRequestService
from models import Employee
from core.api_v2_security import issue_api_v2_token, validate_request_token, rate_limit

logger = logging.getLogger(__name__)

api_employee_requests_v2_bp = Blueprint(
    'api_employee_requests_v2', 
    __name__, 
    url_prefix='/api/v2/employee-requests'
)


# ==================== Authentication Decorator ====================

def token_required(f):
    """JWT token authentication decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        claims, error = validate_request_token(
            required_scopes=['api:v2:read', 'api:v2:write', 'employee_requests:read', 'employee_requests:write'],
            optional=False
        )
        if error:
            return error

        current_employee = Employee.query.get(int(claims.get('sub_id', 0)))
        if not current_employee:
            return jsonify({
                'success': False,
                'message': 'المستخدم المرتبط بالتوكن غير موجود'
            }), 401
        
        return f(current_employee, *args, **kwargs)
    
    return decorated


# ==================== Authentication ====================

@api_employee_requests_v2_bp.route('/auth/login', methods=['POST'])
@rate_limit("10 per minute")
def login():
    """
    Employee login with JWT token.
    
    Request Body:
    {
        "employee_id": "5216",
        "national_id": "1234567890"
    }
    
    Response:
    {
        "success": true,
        "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "employee": {
            "id": 1,
            "employee_id": "5216",
            "name": "أحمد محمد",
            "email": "ahmad@example.com"
        }
    }
    """
    data = request.get_json()
    
    if not data or not data.get('employee_id') or not data.get('national_id'):
        return jsonify({
            'success': False,
            'message': 'رقم الموظف ورقم الهوية مطلوبان'
        }), 400
    
    # Authenticate
    employee = EmployeeRequestService.authenticate_employee(
        employee_id=data['employee_id'],
        national_id=data['national_id']
    )
    
    if not employee:
        return jsonify({
            'success': False,
            'message': 'بيانات الدخول غير صحيحة أو الحساب غير نشط'
        }), 401
    
    # Generate scoped API v2 token
    token = issue_api_v2_token(
        subject_type='employee',
        subject_id=employee.id,
        scopes=['api:v2:read', 'api:v2:write', 'employee_requests:read', 'employee_requests:write'],
        expires_hours=24 * 30,
    )
    
    return jsonify({
        'success': True,
        'token': token,
        'employee': {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.name,
            'email': employee.email,
            'job_title': employee.job_title,
            'department': employee.department.name if employee.department else None,
            'profile_image': employee.profile_image,
            'mobile': employee.mobile,
            'status': employee.status
        }
    }), 200


# ==================== Request List & Details ====================

@api_employee_requests_v2_bp.route('/requests', methods=['GET'])
@token_required
def get_requests(current_employee):
    """
    Get paginated list of employee requests.
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    - status: Filter by status (PENDING, APPROVED, REJECTED, etc.)
    - type: Filter by type (INVOICE, CAR_WASH, CAR_INSPECTION, ADVANCE_PAYMENT)
    
    Response:
    {
        "success": true,
        "requests": [...],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 45,
            "pages": 3
        }
    }
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    
    try:
        requests_list, pagination_info = EmployeeRequestService.get_employee_requests(
            employee_id=current_employee.id,
            page=page,
            per_page=per_page,
            status_filter=status_filter if status_filter else None,
            type_filter=type_filter if type_filter else None
        )
        
        return jsonify({
            'success': True,
            'requests': requests_list,
            'pagination': pagination_info
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error getting requests: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء جلب الطلبات'
        }), 500


@api_employee_requests_v2_bp.route('/requests/<int:request_id>', methods=['GET'])
@token_required
def get_request_details(current_employee, request_id):
    """
    Get detailed information for a specific request.
    
    Response:
    {
        "success": true,
        "request": {
            "id": 1,
            "type": "INVOICE",
            "status": "PENDING",
            ...
            "details": {...}
        }
    }
    """
    emp_request = EmployeeRequestService.get_request_by_id(request_id, current_employee.id)
    
    if not emp_request:
        return jsonify({
            'success': False,
            'message': 'الطلب غير موجود'
        }), 404
    
    request_data = EmployeeRequestService.format_request_details(emp_request)
    
    return jsonify({
        'success': True,
        'request': request_data
    }), 200


@api_employee_requests_v2_bp.route('/public/requests/<int:request_id>', methods=['GET'])
def get_public_request_details(request_id):
    """
    Get request details without authentication (public endpoint).
    
    ⚠️ Warning: This endpoint is public and accessible without authentication.
    """
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request:
        return jsonify({
            'success': False,
            'message': 'الطلب غير موجود'
        }), 404
    
    request_data = EmployeeRequestService.format_request_details(emp_request)
    
    # Add employee info for public view
    request_data['employee'] = {
        'id': emp_request.employee.id,
        'name': emp_request.employee.name,
        'employee_id': emp_request.employee.employee_id
    } if emp_request.employee else None
    
    return jsonify({
        'success': True,
        'request': request_data
    }), 200


# ==================== Request Creation ====================

@api_employee_requests_v2_bp.route('/requests', methods=['POST'])
@token_required
def create_request(current_employee):
    """
    Create a generic request.
    
    Request Body:
    {
        "type": "INVOICE",
        "title": "عنوان الطلب",
        "description": "وصف الطلب",
        "amount": 1500.00,
        "details": {...}
    }
    """
    data = request.get_json()
    
    if not data or not data.get('type') or not data.get('title'):
        return jsonify({
            'success': False,
            'message': 'النوع والعنوان مطلوبان'
        }), 400
    
    try:
        new_request = EmployeeRequestService.create_generic_request(
            employee_id=current_employee.id,
            request_type=data['type'],
            title=data['title'],
            description=data.get('description'),
            amount=data.get('amount'),
            details=data.get('details', {})
        )
        
        return jsonify({
            'success': True,
            'request_id': new_request.id,
            'message': 'تم إنشاء الطلب بنجاح'
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating request: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء إنشاء الطلب'
        }), 500


@api_employee_requests_v2_bp.route('/requests/advance-payment', methods=['POST'])
@token_required
def create_advance_payment(current_employee):
    """
    Create an advance payment request.
    
    Request Body:
    {
        "requested_amount": 5000.00,
        "reason": "ظروف طارئة",
        "installments": 10,
        "description": "سلفة عاجلة"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('requested_amount') or not data.get('reason'):
        return jsonify({
            'success': False,
            'message': 'المبلغ والسبب مطلوبان'
        }), 400
    
    try:
        new_request = EmployeeRequestService.create_advance_payment_request(
            employee=current_employee,
            requested_amount=float(data['requested_amount']),
            reason=data['reason'],
            installments=data.get('installments'),
            description=data.get('description')
        )
        
        return jsonify({
            'success': True,
            'request_id': new_request.id,
            'message': 'تم إنشاء طلب السلفة بنجاح'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating advance payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


@api_employee_requests_v2_bp.route('/requests/invoice', methods=['POST'])
@token_required
def create_invoice(current_employee):
    """
    Create an invoice request.
    
    Request Body:
    {
        "vendor_name": "اسم المورد",
        "amount": 1500.00,
        "invoice_date": "2026-02-20",
        "description": "فاتورة شراء"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('vendor_name') or not data.get('amount'):
        return jsonify({
            'success': False,
            'message': 'اسم المورد والمبلغ مطلوبان'
        }), 400
    
    try:
        invoice_date = None
        if data.get('invoice_date'):
            invoice_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d')
        
        new_request = EmployeeRequestService.create_invoice_request(
            employee=current_employee,
            vendor_name=data['vendor_name'],
            amount=float(data['amount']),
            invoice_date=invoice_date,
            description=data.get('description')
        )
        
        return jsonify({
            'success': True,
            'request_id': new_request.id,
            'message': 'تم إنشاء طلب الفاتورة بنجاح'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


@api_employee_requests_v2_bp.route('/requests/car-wash', methods=['POST'])
@token_required
def create_car_wash(current_employee):
    """
    Create a car wash request.
    
    Request Body:
    {
        "vehicle_id": 123,
        "service_type": "غسيل عادي",
        "scheduled_date": "2026-02-25",
        "description": "غسيل السيارة"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('vehicle_id'):
        return jsonify({
            'success': False,
            'message': 'رقم المركبة مطلوب'
        }), 400
    
    try:
        scheduled_date = None
        if data.get('scheduled_date'):
            scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
        
        new_request = EmployeeRequestService.create_car_wash_request(
            employee=current_employee,
            vehicle_id=int(data['vehicle_id']),
            service_type=data.get('service_type', 'غسيل عادي'),
            scheduled_date=scheduled_date,
            description=data.get('description')
        )
        
        return jsonify({
            'success': True,
            'request_id': new_request.id,
            'message': 'تم إنشاء طلب غسيل السيارة بنجاح'
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating car wash: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


@api_employee_requests_v2_bp.route('/requests/car-inspection', methods=['POST'])
@token_required
def create_car_inspection(current_employee):
    """
    Create a car inspection request.
    
    Request Body:
    {
        "vehicle_id": 123,
        "inspection_type": "فحص دوري",
        "inspection_date": "2026-02-25",
        "description": "فحص السيارة"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('vehicle_id'):
        return jsonify({
            'success': False,
            'message': 'رقم المركبة مطلوب'
        }), 400
    
    try:
        inspection_date = None
        if data.get('inspection_date'):
            inspection_date = datetime.strptime(data['inspection_date'], '%Y-%m-%d')
        
        new_request = EmployeeRequestService.create_car_inspection_request(
            employee=current_employee,
            vehicle_id=int(data['vehicle_id']),
            inspection_type=data.get('inspection_type', 'فحص دوري'),
            inspection_date=inspection_date,
            description=data.get('description')
        )
        
        return jsonify({
            'success': True,
            'request_id': new_request.id,
            'message': 'تم إنشاء طلب فحص السيارة بنجاح'
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating car inspection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500


# ==================== Request Updates ====================

@api_employee_requests_v2_bp.route('/requests/car-wash/<int:request_id>', methods=['PUT'])
@token_required
def update_car_wash(current_employee, request_id):
    """
    Update a car wash request.
    
    Request Body:
    {
        "service_type": "غسيل متكامل",
        "scheduled_date": "2026-02-28",
        "notes": "ملاحظات إضافية"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'لا توجد بيانات للتحديث'
        }), 400
    
    success, message, updated_request = EmployeeRequestService.update_car_wash_request(
        request_id=request_id,
        employee_id=current_employee.id,
        service_type=data.get('service_type'),
        scheduled_date=data.get('scheduled_date'),
        notes=data.get('notes')
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'request': EmployeeRequestService.format_request_details(updated_request)
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@api_employee_requests_v2_bp.route('/requests/car-inspection/<int:request_id>', methods=['PUT'])
@token_required
def update_car_inspection(current_employee, request_id):
    """
    Update a car inspection request.
    
    Request Body:
    {
        "inspection_type": "فحص شامل",
        "inspection_date": "2026-02-28",
        "notes": "ملاحظات إضافية"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'لا توجد بيانات للتحديث'
        }), 400
    
    success, message, updated_request = EmployeeRequestService.update_car_inspection_request(
        request_id=request_id,
        employee_id=current_employee.id,
        inspection_type=data.get('inspection_type'),
        inspection_date=data.get('inspection_date'),
        notes=data.get('notes')
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'request': EmployeeRequestService.format_request_details(updated_request)
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


# ==================== Request Deletion ====================

@api_employee_requests_v2_bp.route('/requests/<int:request_id>', methods=['DELETE'])
@token_required
def delete_request(current_employee, request_id):
    """Delete a request."""
    success = EmployeeRequestService.delete_request(request_id, current_employee.id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'تم حذف الطلب بنجاح'
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'فشل حذف الطلب'
        }), 400


# ==================== File Upload ====================

@api_employee_requests_v2_bp.route('/requests/<int:request_id>/upload', methods=['POST'])
@token_required
def upload_files(current_employee, request_id):
    """
    Upload files (images or videos) for a request.
    
    Form Data:
    - files[]: Multiple files (up to 500MB each)
    
    Response:
    {
        "success": true,
        "uploaded_files": [...],
        "google_drive_folder_url": "https://drive.google.com/...",
        "message": "تم رفع 3 ملفات بنجاح"
    }
    """
    if 'files' not in request.files:
        return jsonify({
            'success': False,
            'message': 'لا يوجد ملفات مرفقة'
        }), 400
    
    files = request.files.getlist('files')
    
    if not files:
        return jsonify({
            'success': False,
            'message': 'لا يوجد ملفات مرفقة'
        }), 400
    
    success, message, uploaded_files = EmployeeRequestService.upload_request_files(
        request_id=request_id,
        employee_id=current_employee.id,
        files=files
    )
    
    if success:
        emp_request = EmployeeRequestService.get_request_by_id(request_id, current_employee.id)
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'google_drive_folder_url': emp_request.google_drive_folder_url if emp_request else None,
            'message': message
        }), 200
    else:
        status_code = 503 if 'غير متاحة' in message else 404
        return jsonify({
            'success': False,
            'message': message
        }), status_code


@api_employee_requests_v2_bp.route('/requests/<int:request_id>/upload-image', methods=['POST'])
@token_required
def upload_image_alias(current_employee, request_id):
    """Alias for upload_files endpoint (backward compatibility)."""
    return upload_files(current_employee, request_id)


@api_employee_requests_v2_bp.route('/requests/<int:request_id>/upload-inspection-image', methods=['POST'])
@token_required
def upload_inspection_image(current_employee, request_id):
    """Alias for upload_files endpoint (backward compatibility for inspection images)."""
    return upload_files(current_employee, request_id)


# ==================== Media Deletion ====================

@api_employee_requests_v2_bp.route('/requests/car-wash/<int:request_id>/media/<int:media_id>', methods=['DELETE'])
@token_required
def delete_car_wash_media(current_employee, request_id, media_id):
    """Delete a car wash media file."""
    success, message = EmployeeRequestService.delete_car_wash_media(
        request_id=request_id,
        media_id=media_id,
        employee_id=current_employee.id
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@api_employee_requests_v2_bp.route('/requests/car-inspection/<int:request_id>/media/<int:media_id>', methods=['DELETE'])
@token_required
def delete_car_inspection_media(current_employee, request_id, media_id):
    """Delete a car inspection media file."""
    success, message = EmployeeRequestService.delete_car_inspection_media(
        request_id=request_id,
        media_id=media_id,
        employee_id=current_employee.id
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


# ==================== Request Approval (Admin) ====================

@api_employee_requests_v2_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@token_required
def approve_request(current_employee, request_id):
    """
    Approve a request (admin only).
    
    Request Body:
    {
        "admin_notes": "موافقة (اختياري)"
    }
    """
    # TODO: Add admin check for current_employee
    
    data = request.get_json() or {}
    admin_notes = data.get('admin_notes', '')
    
    success, message = EmployeeRequestService.approve_request(
        request_id=request_id,
        approved_by_id=current_employee.id,
        admin_notes=admin_notes
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@api_employee_requests_v2_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@token_required
def reject_request(current_employee, request_id):
    """
    Reject a request (admin only).
    
    Request Body:
    {
        "rejection_reason": "سبب الرفض (مطلوب)"
    }
    """
    # TODO: Add admin check for current_employee
    
    data = request.get_json() or {}
    rejection_reason = data.get('rejection_reason', '')
    
    success, message = EmployeeRequestService.reject_request(
        request_id=request_id,
        approved_by_id=current_employee.id,
        rejection_reason=rejection_reason
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


# ==================== Statistics & Types ====================

@api_employee_requests_v2_bp.route('/requests/statistics', methods=['GET'])
@token_required
def get_statistics(current_employee):
    """Get request statistics for current employee."""
    stats = EmployeeRequestService.get_employee_statistics(current_employee.id)
    
    return jsonify({
        'success': True,
        'statistics': stats
    }), 200


@api_employee_requests_v2_bp.route('/requests/types', methods=['GET'])
def get_request_types():
    """Get list of available request types."""
    types = EmployeeRequestService.get_request_types()
    
    return jsonify({
        'success': True,
        'types': types
    }), 200


# ==================== Vehicles ====================

@api_employee_requests_v2_bp.route('/vehicles', methods=['GET'])
@token_required
def get_vehicles(current_employee):
    """Get vehicles assigned to employee."""
    vehicles = EmployeeRequestService.get_employee_vehicles(current_employee.id)
    
    return jsonify({
        'success': True,
        'vehicles': vehicles
    }), 200


# ==================== Notifications ====================

@api_employee_requests_v2_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_employee):
    """
    Get paginated notifications for employee.
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    notifications, pagination_info = EmployeeRequestService.get_employee_notifications(
        employee_id=current_employee.id,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        'success': True,
        'notifications': notifications,
        'pagination': pagination_info
    }), 200


@api_employee_requests_v2_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_employee, notification_id):
    """Mark a notification as read."""
    success, message = EmployeeRequestService.mark_notification_read(
        notification_id=notification_id,
        employee_id=current_employee.id
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 404


@api_employee_requests_v2_bp.route('/notifications/mark-all-read', methods=['PUT'])
@token_required
def mark_all_notifications_read(current_employee):
    """Mark all notifications as read for employee."""
    success, message, count = EmployeeRequestService.mark_all_notifications_read(
        employee_id=current_employee.id
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': count
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 500


# ==================== Employee Profile & Financial ====================

@api_employee_requests_v2_bp.route('/employee/profile', methods=['GET'])
@token_required
def get_employee_profile(current_employee):
    """Get complete employee profile."""
    profile = EmployeeRequestService.get_complete_employee_profile(current_employee.id)
    
    if profile:
        return jsonify({
            'success': True,
            'employee': profile
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'الملف الشخصي غير موجود'
        }), 404


@api_employee_requests_v2_bp.route('/employee/liabilities', methods=['GET'])
@token_required
def get_employee_liabilities(current_employee):
    """Get employee liabilities."""
    liabilities = EmployeeRequestService.get_employee_liabilities(current_employee.id)
    
    return jsonify({
        'success': True,
        'liabilities': liabilities
    }), 200


@api_employee_requests_v2_bp.route('/employee/financial-summary', methods=['GET'])
@token_required
def get_employee_financial_summary(current_employee):
    """Get financial summary for employee."""
    summary = EmployeeRequestService.get_employee_financial_summary(current_employee.id)
    
    return jsonify({
        'success': True,
        'summary': summary
    }), 200


# ==================== Utility Endpoints ====================

@api_employee_requests_v2_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'Employee Requests API v2',
        'version': '2.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
