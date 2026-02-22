"""
Employee Request Service Layer

This module contains all business logic for employee requests.
It provides a clean separation between database operations and HTTP handling.

Author: Refactored from api_employee_requests.py (3,403 lines → Service Layer)
Date: 2026-02-20
"""

import os
import jwt
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import shutil

from core.extensions import db
from models import (
    User, Employee, EmployeeRequest, InvoiceRequest, AdvancePaymentRequest,
    CarWashRequest, CarInspectionRequest, CarWashMedia, CarInspectionMedia,
    RequestNotification, RequestStatus, RequestType, Vehicle, MediaType, 
    FileType, EmployeeLiability, LiabilityStatus, Department
)
from utils.employee_requests_drive_uploader import EmployeeRequestsDriveUploader
from sqlalchemy import desc, or_, and_, func, text
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class EmployeeRequestService:
    """
    Service layer for Employee Requests business logic.
    
    All methods are static for easy testability and reusability.
    """
    
    # ==================== Configuration ====================
    
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'mp4', 'mov', 'avi', 'pdf'}
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    # Type and status translations
    TYPE_NAMES_AR = {
        'INVOICE': 'فاتورة',
        'CAR_WASH': 'غسيل سيارة',
        'CAR_INSPECTION': 'فحص وتوثيق',
        'ADVANCE_PAYMENT': 'سلفة مالية'
    }
    
    STATUS_NAMES_AR = {
        'PENDING': 'قيد الانتظار',
        'APPROVED': 'موافق عليها',
        'REJECTED': 'مرفوضة',
        'IN_REVIEW': 'قيد المراجعة',
        'CANCELLED': 'ملغية'
    }
    
    # ==================== Helper Methods ====================
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        if not filename or not isinstance(filename, str):
            return False
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in EmployeeRequestService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_type_display(request_type: RequestType) -> str:
        """Get Arabic display name for request type."""
        return EmployeeRequestService.TYPE_NAMES_AR.get(request_type.name, request_type.name)
    
    @staticmethod
    def get_status_display(status: RequestStatus) -> str:
        """Get Arabic display name for request status."""
        return EmployeeRequestService.STATUS_NAMES_AR.get(status.name, status.name)
    
    @staticmethod
    def format_request_data(emp_request: EmployeeRequest, include_employee: bool = False) -> Dict:
        """Format employee request data for API response."""
        data = {
            'id': emp_request.id,
            'type': emp_request.request_type.name,
            'type_display': EmployeeRequestService.get_type_display(emp_request.request_type),
            'status': emp_request.status.name,
            'status_display': EmployeeRequestService.get_status_display(emp_request.status),
            'title': emp_request.title,
            'description': emp_request.description,
            'amount': float(emp_request.amount) if emp_request.amount else None,
            'created_at': emp_request.created_at.isoformat(),
            'updated_at': emp_request.updated_at.isoformat() if emp_request.updated_at else None,
            'reviewed_at': emp_request.reviewed_at.isoformat() if emp_request.reviewed_at else None,
            'admin_notes': emp_request.admin_notes,
            'google_drive_folder_url': emp_request.google_drive_folder_url
        }
        
        if include_employee and emp_request.employee:
            data['employee'] = {
                'id': emp_request.employee.id,
                'name': emp_request.employee.name,
                'employee_id': emp_request.employee.employee_id
            }
        
        return data
    
    @staticmethod
    def format_request_details(emp_request: EmployeeRequest) -> Dict:
        """Format request with type-specific details."""
        data = EmployeeRequestService.format_request_data(emp_request)
        
        # Add type-specific details
        if emp_request.request_type == RequestType.INVOICE and emp_request.invoice_data:
            invoice = emp_request.invoice_data
            data['details'] = {
                'vendor_name': invoice.vendor_name,
                'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                'drive_view_url': invoice.drive_view_url,
                'drive_file_id': invoice.drive_file_id,
                'file_size': invoice.file_size,
                'local_file_path': invoice.local_image_path
            }
        
        elif emp_request.request_type == RequestType.ADVANCE_PAYMENT and emp_request.advance_data:
            advance = emp_request.advance_data
            data['details'] = {
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
            
            data['details'] = {
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
            
            data['details'] = {
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
        
        return data
    
    # ==================== Authentication ====================
    
    @staticmethod
    def authenticate_employee(employee_id: str, national_id: str) -> Optional[Employee]:
        """
        Authenticate employee using employee_id and national_id.
        
        Args:
            employee_id: Employee ID
            national_id: National ID/Iqama number
            
        Returns:
            Employee object if authentication successful, None otherwise
        """
        try:
            result = db.session.execute(text("""
                SELECT id FROM employee 
                WHERE national_id::text = :national_id 
                AND employee_id::text = :employee_id
                AND status = 'active'
                LIMIT 1
            """), {
                'national_id': national_id,
                'employee_id': employee_id
            }).fetchone()
            
            if result:
                return Employee.query.get(result[0])
            return None
            
        except Exception as e:
            logger.error(f"Database error during authentication: {str(e)}")
            return None
    
    @staticmethod
    def generate_jwt_token(employee: Employee, expiry_days: int = 30) -> str:
        """
        Generate JWT token for employee.
        
        Args:
            employee: Employee object
            expiry_days: Token expiry in days
            
        Returns:
            JWT token string
        """
        if not EmployeeRequestService.SECRET_KEY:
            raise RuntimeError("SESSION_SECRET environment variable is required")
        
        token = jwt.encode({
            'employee_id': employee.employee_id,
            'exp': datetime.utcnow() + timedelta(days=expiry_days)
        }, EmployeeRequestService.SECRET_KEY, algorithm='HS256')
        
        return token
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[Employee]:
        """
        Verify JWT token and return employee.
        
        Args:
            token: JWT token string
            
        Returns:
            Employee object if token is valid, None otherwise
        """
        try:
            data = jwt.decode(token, EmployeeRequestService.SECRET_KEY, algorithms=['HS256'])
            employee = Employee.query.filter_by(employee_id=data['employee_id']).first()
            return employee
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
    
    # ==================== Request CRUD Operations ====================
    
    @staticmethod
    def get_employee_requests(
        employee_id: int,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Get paginated list of employee requests.
        
        Args:
            employee_id: Employee ID
            page: Page number
            per_page: Items per page
            status_filter: Filter by status (PENDING, APPROVED, etc.)
            type_filter: Filter by type (INVOICE, CAR_WASH, etc.)
            
        Returns:
            Tuple of (requests_list, pagination_info)
        """
        query = EmployeeRequest.query.filter_by(employee_id=employee_id)
        
        if status_filter:
            try:
                query = query.filter_by(status=RequestStatus[status_filter])
            except KeyError:
                raise ValueError(f'حالة غير صحيحة: {status_filter}')
        
        if type_filter:
            try:
                query = query.filter_by(request_type=RequestType[type_filter])
            except KeyError:
                raise ValueError(f'نوع غير صحيح: {type_filter}')
        
        pagination = query.order_by(EmployeeRequest.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        requests_list = [
            EmployeeRequestService.format_request_data(req)
            for req in pagination.items
        ]
        
        pagination_info = {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
        
        return requests_list, pagination_info
    
    @staticmethod
    def get_request_by_id(request_id: int, employee_id: Optional[int] = None) -> Optional[EmployeeRequest]:
        """
        Get request by ID, optionally filtered by employee.
        
        Args:
            request_id: Request ID
            employee_id: Employee ID (optional - for security check)
            
        Returns:
            EmployeeRequest object or None
        """
        query = EmployeeRequest.query.filter_by(id=request_id)
        
        if employee_id is not None:
            query = query.filter_by(employee_id=employee_id)
        
        return query.first()
    
    @staticmethod
    def create_generic_request(
        employee_id: int,
        request_type: str,
        title: str,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        details: Optional[Dict] = None
    ) -> EmployeeRequest:
        """
        Create a generic employee request.
        
        Args:
            employee_id: Employee ID
            request_type: Type of request (INVOICE, CAR_WASH, etc.)
            title: Request title
            description: Request description
            amount: Request amount
            details: Type-specific details
            
        Returns:
            Created EmployeeRequest object
        """
        try:
            req_type = RequestType[request_type]
        except KeyError:
            raise ValueError(f'نوع طلب غير صحيح: {request_type}')
        
        new_request = EmployeeRequest()
        new_request.employee_id = employee_id
        new_request.request_type = req_type
        new_request.title = title
        new_request.description = description
        new_request.amount = amount
        new_request.status = RequestStatus.PENDING
        
        db.session.add(new_request)
        db.session.flush()
        
        # Create type-specific data if details provided
        if details:
            EmployeeRequestService._create_request_details(new_request, req_type, details)
        
        db.session.commit()
        return new_request
    
    @staticmethod
    def _create_request_details(request: EmployeeRequest, req_type: RequestType, details: Dict):
        """Helper to create type-specific request details."""
        employee = request.employee
        
        if req_type == RequestType.INVOICE:
            invoice = InvoiceRequest()
            invoice.request_id = request.id
            invoice.vendor_name = details.get('vendor_name', '')
            if details.get('invoice_date'):
                invoice.invoice_date = datetime.strptime(details['invoice_date'], '%Y-%m-%d').date()
            db.session.add(invoice)
        
        elif req_type == RequestType.ADVANCE_PAYMENT:
            advance = AdvancePaymentRequest()
            advance.request_id = request.id
            advance.employee_name = employee.name
            advance.employee_number = employee.employee_id
            advance.national_id = employee.national_id or ''
            advance.job_title = employee.job_title or ''
            advance.department_name = employee.department.name if employee.department else ''
            advance.requested_amount = details.get('requested_amount', 0)
            advance.reason = details.get('reason')
            advance.installments = details.get('installments')
            advance.installment_amount = details.get('installment_amount')
            db.session.add(advance)
        
        elif req_type == RequestType.CAR_WASH:
            wash = CarWashRequest()
            wash.request_id = request.id
            wash.vehicle_id = details.get('vehicle_id')
            wash.service_type = details.get('service_type', 'غسيل عادي')
            if details.get('scheduled_date'):
                wash.scheduled_date = datetime.strptime(details['scheduled_date'], '%Y-%m-%d').date()
            db.session.add(wash)
        
        elif req_type == RequestType.CAR_INSPECTION:
            inspection = CarInspectionRequest()
            inspection.request_id = request.id
            inspection.vehicle_id = details.get('vehicle_id')
            inspection.inspection_type = details.get('inspection_type', 'فحص دوري')
            if details.get('inspection_date'):
                inspection.inspection_date = datetime.strptime(details['inspection_date'], '%Y-%m-%d').date()
            else:
                inspection.inspection_date = datetime.now().date()
            db.session.add(inspection)
    
    @staticmethod
    def delete_request(request_id: int, employee_id: Optional[int] = None) -> bool:
        """
        Delete a request.
        
        Args:
            request_id: Request ID
            employee_id: Employee ID (optional - for security check)
            
        Returns:
            True if deleted, False otherwise
        """
        request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not request:
            return False
        
        try:
            db.session.delete(request)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting request {request_id}: {str(e)}")
            return False
    
    @staticmethod
    def approve_request(
        request_id: int,
        approved_by_id: int,
        admin_notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Approve a request and send notification.
        
        Args:
            request_id: Request ID
            approved_by_id: ID of admin approving
            admin_notes: Optional admin notes
            
        Returns:
            Tuple of (success, message)
        """
        request = EmployeeRequestService.get_request_by_id(request_id)
        
        if not request:
            return False, 'الطلب غير موجود'
        
        if request.status != RequestStatus.PENDING:
            return False, 'هذا الطلب تمت معالجته مسبقاً'
        
        request.status = RequestStatus.APPROVED
        request.approved_by_id = approved_by_id
        request.approved_at = datetime.utcnow()
        
        if admin_notes:
            request.admin_notes = admin_notes
        
        # Create notification
        type_display = EmployeeRequestService.get_type_display(request.request_type)
        notification = RequestNotification()
        notification.request_id = request_id
        notification.employee_id = request.employee_id
        notification.title_ar = 'تمت الموافقة على طلبك'
        notification.message_ar = f'تمت الموافقة على طلب {type_display}'
        notification.notification_type = 'APPROVED'
        db.session.add(notification)
        
        try:
            db.session.commit()
            return True, 'تمت الموافقة على الطلب بنجاح'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving request {request_id}: {str(e)}")
            return False, f'حدث خطأ: {str(e)}'
    
    @staticmethod
    def reject_request(
        request_id: int,
        approved_by_id: int,
        rejection_reason: str
    ) -> Tuple[bool, str]:
        """
        Reject a request and send notification.
        
        Args:
            request_id: Request ID
            approved_by_id: ID of admin rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            Tuple of (success, message)
        """
        if not rejection_reason:
            return False, 'يجب إدخال سبب الرفض'
        
        request = EmployeeRequestService.get_request_by_id(request_id)
        
        if not request:
            return False, 'الطلب غير موجود'
        
        if request.status != RequestStatus.PENDING:
            return False, 'هذا الطلب تمت معالجته مسبقاً'
        
        request.status = RequestStatus.REJECTED
        request.approved_by_id = approved_by_id
        request.approved_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
        
        # Create notification
        type_display = EmployeeRequestService.get_type_display(request.request_type)
        notification = RequestNotification()
        notification.request_id = request_id
        notification.employee_id = request.employee_id
        notification.title_ar = 'تم رفض طلبك'
        notification.message_ar = f'تم رفض طلب {type_display}: {rejection_reason}'
        notification.notification_type = 'REJECTED'
        db.session.add(notification)
        
        try:
            db.session.commit()
            return True, 'تم رفض الطلب'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rejecting request {request_id}: {str(e)}")
            return False, f'حدث خطأ: {str(e)}'
    
    # ==================== Type-Specific Request Creation ====================
    
    @staticmethod
    def create_advance_payment_request(
        employee: Employee,
        requested_amount: float,
        reason: str,
        installments: Optional[int] = None,
        description: Optional[str] = None
    ) -> EmployeeRequest:
        """Create an advance payment request."""
        request = EmployeeRequest()
        request.employee_id = employee.id
        request.request_type = RequestType.ADVANCE_PAYMENT
        request.title = f'طلب سلفة مالية - {requested_amount} ريال'
        request.description = description or reason
        request.amount = requested_amount
        request.status = RequestStatus.PENDING
        
        db.session.add(request)
        db.session.flush()
        
        advance = AdvancePaymentRequest()
        advance.request_id = request.id
        advance.employee_name = employee.name
        advance.employee_number = employee.employee_id
        advance.national_id = employee.national_id or ''
        advance.job_title = employee.job_title or ''
        advance.department_name = employee.department.name if employee.department else ''
        advance.requested_amount = requested_amount
        advance.reason = reason
        advance.installments = installments
        
        if installments and installments > 0:
            advance.installment_amount = requested_amount / installments
        
        db.session.add(advance)
        db.session.commit()
        
        return request
    
    @staticmethod
    def create_invoice_request(
        employee: Employee,
        vendor_name: str,
        amount: float,
        invoice_date: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> EmployeeRequest:
        """Create an invoice request."""
        request = EmployeeRequest()
        request.employee_id = employee.id
        request.request_type = RequestType.INVOICE
        request.title = f'فاتورة - {vendor_name}'
        request.description = description
        request.amount = amount
        request.status = RequestStatus.PENDING
        
        db.session.add(request)
        db.session.flush()
        
        invoice = InvoiceRequest()
        invoice.request_id = request.id
        invoice.vendor_name = vendor_name
        invoice.invoice_date = invoice_date or datetime.now().date()
        
        db.session.add(invoice)
        db.session.commit()
        
        return request
    
    @staticmethod
    def create_car_wash_request(
        employee: Employee,
        vehicle_id: int,
        service_type: str = 'غسيل عادي',
        scheduled_date: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> EmployeeRequest:
        """Create a car wash request."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            raise ValueError('المركبة غير موجودة')
        
        request = EmployeeRequest()
        request.employee_id = employee.id
        request.request_type = RequestType.CAR_WASH
        request.title = f'طلب غسيل سيارة - {vehicle.plate_number}'
        request.description = description or f'{service_type} - {vehicle.plate_number}'
        request.status = RequestStatus.PENDING
        
        db.session.add(request)
        db.session.flush()
        
        wash = CarWashRequest()
        wash.request_id = request.id
        wash.vehicle_id = vehicle_id
        wash.service_type = service_type
        wash.scheduled_date = scheduled_date or datetime.now().date()
        
        db.session.add(wash)
        db.session.commit()
        
        return request
    
    @staticmethod
    def create_car_inspection_request(
        employee: Employee,
        vehicle_id: int,
        inspection_type: str = 'فحص دوري',
        inspection_date: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> EmployeeRequest:
        """Create a car inspection request."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            raise ValueError('المركبة غير موجودة')
        
        request = EmployeeRequest()
        request.employee_id = employee.id
        request.request_type = RequestType.CAR_INSPECTION
        request.title = f'طلب فحص وتوثيق - {vehicle.plate_number}'
        request.description = description or f'{inspection_type} - {vehicle.plate_number}'
        request.status = RequestStatus.PENDING
        
        db.session.add(request)
        db.session.flush()
        
        inspection = CarInspectionRequest()
        inspection.request_id = request.id
        inspection.vehicle_id = vehicle_id
        inspection.inspection_type = inspection_type
        inspection.inspection_date = inspection_date or datetime.now().date()
        
        db.session.add(inspection)
        db.session.commit()
        
        return request
    
    # ==================== Type-Specific Request Updates ====================
    
    @staticmethod
    def update_car_wash_request(
        request_id: int,
        employee_id: int,
        service_type: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[EmployeeRequest]]:
        """Update a car wash request."""
        emp_request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not emp_request:
            return False, 'الطلب غير موجود', None
        
        if emp_request.request_type != RequestType.CAR_WASH:
            return False, 'هذا الطلب ليس طلب غسيل سيارة', None
        
        if emp_request.status != RequestStatus.PENDING:
            return False, 'لا يمكن تعديل طلب تمت معالجته', None
        
        wash = emp_request.car_wash_data
        if not wash:
            return False, 'بيانات الطلب غير موجودة', None
        
        if service_type:
            wash.service_type = service_type
        
        if scheduled_date:
            try:
                wash.scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            except ValueError:
                return False, 'تاريخ غير صحيح', None
        
        if notes:
            emp_request.description = notes
        
        emp_request.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return True, 'تم تحديث الطلب بنجاح', emp_request
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating car wash request: {str(e)}")
            return False, f'حدث خطأ: {str(e)}', None
    
    @staticmethod
    def update_car_inspection_request(
        request_id: int,
        employee_id: int,
        inspection_type: Optional[str] = None,
        inspection_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[EmployeeRequest]]:
        """Update a car inspection request."""
        emp_request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not emp_request:
            return False, 'الطلب غير موجود', None
        
        if emp_request.request_type != RequestType.CAR_INSPECTION:
            return False, 'هذا الطلب ليس طلب فحص وتوثيق', None
        
        if emp_request.status != RequestStatus.PENDING:
            return False, 'لا يمكن تعديل طلب تمت معالجته', None
        
        inspection = emp_request.inspection_data
        if not inspection:
            return False, 'بيانات الطلب غير موجودة', None
        
        if inspection_type:
            inspection.inspection_type = inspection_type
        
        if inspection_date:
            try:
                inspection.inspection_date = datetime.strptime(inspection_date, '%Y-%m-%d').date()
            except ValueError:
                return False, 'تاريخ غير صحيح', None
        
        if notes:
            emp_request.description = notes
        
        emp_request.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return True, 'تم تحديث الطلب بنجاح', emp_request
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating car inspection request: {str(e)}")
            return False, f'حدث خطأ: {str(e)}', None
    
    # ==================== File Upload Operations ====================
    
    @staticmethod
    def upload_request_files(
        request_id: int,
        employee_id: int,
        files: List[FileStorage]
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Upload files for a request to Google Drive.
        
        Args:
            request_id: Request ID
            employee_id: Employee ID
            files: List of file objects
            
        Returns:
            Tuple of (success, message, uploaded_files_list)
        """
        emp_request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not emp_request:
            return False, 'الطلب غير موجود', []
        
        if not files:
            return False, 'لا يوجد ملفات مرفقة', []
        
        drive_uploader = EmployeeRequestsDriveUploader()
        
        if not drive_uploader.is_available():
            return False, 'خدمة Google Drive غير متاحة حالياً', []
        
        # Create folder structure
        type_map = {
            RequestType.INVOICE: 'invoice',
            RequestType.CAR_WASH: 'car_wash',
            RequestType.CAR_INSPECTION: 'car_inspection',
            RequestType.ADVANCE_PAYMENT: 'advance_payment'
        }
        
        vehicle_number = EmployeeRequestService._get_request_vehicle_number(emp_request)
        
        folder_result = drive_uploader.create_request_folder(
            request_type=type_map.get(emp_request.request_type, 'other'),
            request_id=emp_request.id,
            employee_name=emp_request.employee.name,
            vehicle_number=vehicle_number or ''
        )
        
        if not folder_result:
            return False, 'فشل إنشاء مجلد على Google Drive', []
        
        emp_request.google_drive_folder_id = folder_result['folder_id']
        emp_request.google_drive_folder_url = folder_result['folder_url']
        db.session.commit()
        
        # Upload files
        uploaded_files = []
        
        for file in files:
            if not file.filename or file.filename == '':
                continue
            
            if not EmployeeRequestService.allowed_file(file.filename):
                continue
            
            result = EmployeeRequestService._upload_single_file(
                file, emp_request, folder_result['folder_id'], drive_uploader
            )
            
            if result:
                uploaded_files.append(result)
        
        db.session.commit()
        
        return True, f'تم رفع {len(uploaded_files)} ملف بنجاح إلى Google Drive', uploaded_files
    
    @staticmethod
    def _get_request_vehicle_number(request: EmployeeRequest) -> Optional[str]:
        """Helper to get vehicle number from request."""
        if request.request_type == RequestType.CAR_WASH and request.car_wash_data and request.car_wash_data.vehicle:
            return request.car_wash_data.vehicle.plate_number
        elif request.request_type == RequestType.CAR_INSPECTION and request.inspection_data and request.inspection_data.vehicle:
            return request.inspection_data.vehicle.plate_number
        return None
    
    @staticmethod
    def _upload_single_file(
        file: FileStorage,
        request: EmployeeRequest,
        folder_id: str,
        drive_uploader: EmployeeRequestsDriveUploader
    ) -> Optional[Dict]:
        """Helper to upload a single file based on request type."""
        temp_path = None
        try:
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            if request.request_type == RequestType.INVOICE:
                return EmployeeRequestService._upload_invoice_file(
                    temp_path, file.filename, request, folder_id, drive_uploader
                )
            elif request.request_type == RequestType.CAR_WASH:
                return EmployeeRequestService._upload_car_wash_file(
                    temp_path, request, folder_id, drive_uploader
                )
            elif request.request_type == RequestType.CAR_INSPECTION:
                return EmployeeRequestService._upload_inspection_file(
                    temp_path, file.filename, file_ext, request, folder_id, drive_uploader
                )
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        return None
    
    @staticmethod
    def _upload_invoice_file(
        temp_path: str,
        filename: str,
        request: EmployeeRequest,
        folder_id: str,
        drive_uploader: EmployeeRequestsDriveUploader
    ) -> Optional[Dict]:
        """Upload invoice file."""
        # Save locally
        safe_filename = secure_filename(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{safe_filename}"
        local_path = os.path.join('uploads', 'invoices', unique_filename)
        full_path = os.path.join('static', local_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        shutil.copy(temp_path, full_path)
        
        # Upload to Drive
        result = drive_uploader.upload_invoice_image(
            file_path=temp_path,
            folder_id=folder_id,
            custom_name=filename
        )
        
        if result:
            invoice = request.invoice_data
            if invoice:
                invoice.local_image_path = local_path
                invoice.drive_file_id = result['file_id']
                invoice.drive_view_url = result['view_url']
                invoice.drive_download_url = result.get('download_url')
                invoice.file_size = result.get('file_size')
            
            return {
                'filename': filename,
                'drive_url': result['view_url'],
                'file_id': result['file_id']
            }
        
        return None
    
    @staticmethod
    def _upload_car_wash_file(
        temp_path: str,
        request: EmployeeRequest,
        folder_id: str,
        drive_uploader: EmployeeRequestsDriveUploader
    ) -> Optional[Dict]:
        """Upload car wash media file."""
        if not request.car_wash_data:
            return None
        
        existing_count = len(request.car_wash_data.media_files)
        media_types_order = [MediaType.PLATE, MediaType.FRONT, MediaType.BACK, MediaType.RIGHT, MediaType.LEFT]
        
        if existing_count >= 5:
            return None
        
        media_type = media_types_order[existing_count]
        images_dict = {media_type.value: temp_path}
        
        results = drive_uploader.upload_car_wash_images(
            images_dict=images_dict,
            folder_id=folder_id
        )
        
        result = results.get(media_type.value)
        
        if result:
            media = CarWashMedia()
            media.wash_request_id = request.car_wash_data.id
            media.media_type = media_type
            media.drive_file_id = result['file_id']
            media.drive_view_url = result['view_url']
            media.file_size = result.get('file_size')
            db.session.add(media)
            
            return {
                'filename': media_type.value,
                'drive_url': result['view_url'],
                'file_id': result['file_id']
            }
        
        return None
    
    @staticmethod
    def _upload_inspection_file(
        temp_path: str,
        filename: str,
        file_ext: str,
        request: EmployeeRequest,
        folder_id: str,
        drive_uploader: EmployeeRequestsDriveUploader
    ) -> Optional[Dict]:
        """Upload car inspection media file."""
        if not request.inspection_data:
            return None
        
        is_video = file_ext in ['mp4', 'mov', 'avi']
        inspection_file_type = FileType.VIDEO if is_video else FileType.IMAGE
        
        if is_video:
            result = drive_uploader.upload_large_video_resumable(
                file_path=temp_path,
                folder_id=folder_id,
                filename=filename
            )
        else:
            results = drive_uploader.upload_inspection_images_batch(
                images_list=[temp_path],
                folder_id=folder_id
            )
            result = results[0] if results else None
        
        if result:
            media = CarInspectionMedia()
            media.inspection_request_id = request.inspection_data.id
            media.file_type = inspection_file_type
            media.drive_file_id = result['file_id']
            media.drive_view_url = result['view_url']
            media.drive_download_url = result.get('download_url')
            media.original_filename = filename
            media.file_size = result.get('file_size')
            media.upload_status = 'completed'
            media.upload_progress = 100
            db.session.add(media)
            
            return {
                'filename': filename,
                'drive_url': result['view_url'],
                'file_id': result['file_id']
            }
        
        return None
    
    @staticmethod
    def delete_car_wash_media(
        request_id: int,
        media_id: int,
        employee_id: int
    ) -> Tuple[bool, str]:
        """Delete car wash media file."""
        emp_request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not emp_request or emp_request.request_type != RequestType.CAR_WASH:
            return False, 'الطلب غير موجود'
        
        if emp_request.status != RequestStatus.PENDING:
            return False, 'لا يمكن حذف ملفات طلب تمت معالجته'
        
        media = CarWashMedia.query.filter_by(
            id=media_id,
            wash_request_id=emp_request.car_wash_data.id
        ).first()
        
        if not media:
            return False, 'الملف غير موجود'
        
        try:
            db.session.delete(media)
            db.session.commit()
            return True, 'تم حذف الملف بنجاح'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting car wash media: {str(e)}")
            return False, f'حدث خطأ: {str(e)}'
    
    @staticmethod
    def delete_car_inspection_media(
        request_id: int,
        media_id: int,
        employee_id: int
    ) -> Tuple[bool, str]:
        """Delete car inspection media file."""
        emp_request = EmployeeRequestService.get_request_by_id(request_id, employee_id)
        
        if not emp_request or emp_request.request_type != RequestType.CAR_INSPECTION:
            return False, 'الطلب غير موجود'
        
        if emp_request.status != RequestStatus.PENDING:
            return False, 'لا يمكن حذف ملفات طلب تمت معالجته'
        
        media = CarInspectionMedia.query.filter_by(
            id=media_id,
            inspection_request_id=emp_request.inspection_data.id
        ).first()
        
        if not media:
            return False, 'الملف غير موجود'
        
        try:
            db.session.delete(media)
            db.session.commit()
            return True, 'تم حذف الملف بنجاح'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting car inspection media: {str(e)}")
            return False, f'حدث خطأ: {str(e)}'
    
    # ==================== Statistics & Analytics ====================
    
    @staticmethod
    def get_employee_statistics(employee_id: int) -> Dict:
        """Get request statistics for employee."""
        stats = {
            'total': EmployeeRequest.query.filter_by(employee_id=employee_id).count(),
            'pending': EmployeeRequest.query.filter_by(
                employee_id=employee_id,
                status=RequestStatus.PENDING
            ).count(),
            'approved': EmployeeRequest.query.filter_by(
                employee_id=employee_id,
                status=RequestStatus.APPROVED
            ).count(),
            'rejected': EmployeeRequest.query.filter_by(
                employee_id=employee_id,
                status=RequestStatus.REJECTED
            ).count()
        }
        
        # Get counts by type
        for req_type in RequestType:
            type_count = EmployeeRequest.query.filter_by(
                employee_id=employee_id,
                request_type=req_type
            ).count()
            stats[f'{req_type.name.lower()}_count'] = type_count
        
        return stats
    
    @staticmethod
    def get_admin_statistics() -> Dict:
        """Get overall request statistics for admin."""
        stats = {
            'total': EmployeeRequest.query.count(),
            'pending': EmployeeRequest.query.filter_by(status=RequestStatus.PENDING).count(),
            'approved': EmployeeRequest.query.filter_by(status=RequestStatus.APPROVED).count(),
            'rejected': EmployeeRequest.query.filter_by(status=RequestStatus.REJECTED).count()
        }
        
        # Get counts by type
        for req_type in RequestType:
            type_count = EmployeeRequest.query.filter_by(request_type=req_type).count()
            stats[f'{req_type.name.lower()}_count'] = type_count
        
        return stats
    
    @staticmethod
    def get_request_types() -> List[Dict]:
        """Get list of available request types."""
        types = []
        for req_type in RequestType:
            types.append({
                'value': req_type.name,
                'label_ar': EmployeeRequestService.get_type_display(req_type),
                'label_en': req_type.name.replace('_', ' ').title()
            })
        return types
    
    # ==================== Notifications ====================
    
    @staticmethod
    def get_employee_notifications(employee_id: int, page: int = 1, per_page: int = 20) -> Tuple[List[Dict], Dict]:
        """Get paginated notifications for employee."""
        query = RequestNotification.query.filter_by(employee_id=employee_id)
        
        pagination = query.order_by(RequestNotification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        notifications = []
        for notif in pagination.items:
            notifications.append({
                'id': notif.id,
                'request_id': notif.request_id,
                'title': notif.title_ar,
                'message': notif.message_ar,
                'type': notif.notification_type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat()
            })
        
        pagination_info = {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'unread_count': RequestNotification.query.filter_by(
                employee_id=employee_id,
                is_read=False
            ).count()
        }
        
        return notifications, pagination_info
    
    @staticmethod
    def mark_notification_read(notification_id: int, employee_id: int) -> Tuple[bool, str]:
        """Mark a notification as read."""
        notification = RequestNotification.query.filter_by(
            id=notification_id,
            employee_id=employee_id
        ).first()
        
        if not notification:
            return False, 'الإشعار غير موجود'
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return True, 'تم تحديث حالة الإشعار'
        except Exception as e:
            db.session.rollback()
            return False, f'حدث خطأ: {str(e)}'
    
    @staticmethod
    def mark_all_notifications_read(employee_id: int) -> Tuple[bool, str, int]:
        """Mark all notifications as read for employee."""
        try:
            updated = RequestNotification.query.filter_by(
                employee_id=employee_id,
                is_read=False
            ).update({
                'is_read': True,
                'read_at': datetime.utcnow()
            })
            
            db.session.commit()
            return True, f'تم تحديث {updated} إشعار', updated
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return False, f'حدث خطأ: {str(e)}', 0
    
    @staticmethod
    def create_notification(
        employee_id: int,
        request_id: int,
        title: str,
        message: str,
        notification_type: str = 'INFO'
    ) -> RequestNotification:
        """Create a new notification."""
        notification = RequestNotification()
        notification.employee_id = employee_id
        notification.request_id = request_id
        notification.title_ar = title
        notification.message_ar = message
        notification.notification_type = notification_type
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
    
    # ==================== Financial ====================
    
    @staticmethod
    def get_employee_liabilities(employee_id: int) -> List[Dict]:
        """Get employee liabilities."""
        liabilities = EmployeeLiability.query.filter_by(employee_id=employee_id).all()
        
        result = []
        for liability in liabilities:
            result.append({
                'id': liability.id,
                'amount': float(liability.amount),
                'remaining_amount': float(liability.remaining_amount),
                'description': liability.description,
                'status': liability.status.value if liability.status else None,
                'created_at': liability.created_at.isoformat() if liability.created_at else None
            })
        
        return result
    
    @staticmethod
    def get_employee_financial_summary(employee_id: int) -> Dict:
        """Get financial summary for employee."""
        # Get active liabilities
        active_liabilities = EmployeeLiability.query.filter_by(
            employee_id=employee_id,
            status=LiabilityStatus.ACTIVE
        ).all()
        
        total_liabilities = sum(float(l.remaining_amount) for l in active_liabilities)
        
        # Get approved advance payments
        approved_advances = EmployeeRequest.query.filter_by(
            employee_id=employee_id,
            request_type=RequestType.ADVANCE_PAYMENT,
            status=RequestStatus.APPROVED
        ).all()
        
        total_advances = sum(
            float(r.advance_data.requested_amount) 
            for r in approved_advances 
            if r.advance_data
        )
        
        # Get pending requests
        pending_count = EmployeeRequest.query.filter_by(
            employee_id=employee_id,
            status=RequestStatus.PENDING
        ).count()
        
        return {
            'total_liabilities': total_liabilities,
            'active_liabilities_count': len(active_liabilities),
            'total_approved_advances': total_advances,
            'approved_advances_count': len(approved_advances),
            'pending_requests_count': pending_count
        }
    
    # ==================== Vehicles ====================
    
    @staticmethod
    def get_employee_vehicles(employee_id: int) -> List[Dict]:
        """Get vehicles assigned to employee."""
        # This is a simplified version - adjust based on your vehicle assignment logic
        vehicles = Vehicle.query.filter_by(driver_id=employee_id).all()
        
        result = []
        for vehicle in vehicles:
            result.append({
                'id': vehicle.id,
                'plate_number': vehicle.plate_number,
                'make': vehicle.make,
                'model': vehicle.model,
                'year': vehicle.year,
                'status': vehicle.status
            })
        
        return result
    
    # ==================== Employee Profile ====================
    
    @staticmethod
    def get_complete_employee_profile(employee_id: int) -> Optional[Dict]:
        """Get complete employee profile with all related data."""
        employee = Employee.query.options(
            joinedload(Employee.department),
            joinedload(Employee.nationality_rel)
        ).get(employee_id)
        
        if not employee:
            return None
        
        return {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.name,
            'email': employee.email,
            'mobile': employee.mobile,
            'job_title': employee.job_title,
            'national_id': employee.national_id,
            'status': employee.status,
            'profile_image': employee.profile_image,
            'department': {
                'id': employee.department.id,
                'name': employee.department.name
            } if employee.department else None,
            'nationality': {
                'id': employee.nationality_rel.id,
                'name': employee.nationality_rel.name
            } if employee.nationality_rel else None,
            'hire_date': employee.hire_date.isoformat() if employee.hire_date else None
        }
    
    @staticmethod
    def get_all_employees_data() -> List[Dict]:
        """Get simplified data for all active employees."""
        employees = Employee.query.filter_by(status='active').all()
        
        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'name': emp.name,
                'email': emp.email,
                'mobile': emp.mobile,
                'department': emp.department.name if emp.department else None
            })
        
        return result
