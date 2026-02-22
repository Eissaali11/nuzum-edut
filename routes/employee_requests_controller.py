"""
Employee Requests Web Controller (Refactored)

Slim controller for admin web interface to manage employee requests.
All business logic delegated to EmployeeRequestService.

Author: Refactored from employee_requests.py (760 lines → Slim Controller)
Date: 2026-02-20
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from core.extensions import db
from models import (
    EmployeeRequest, InvoiceRequest, AdvancePaymentRequest,
    CarWashRequest, CarInspectionRequest, EmployeeLiability,
    RequestNotification, Employee, RequestStatus, RequestType,
    UserRole, Module, Vehicle, LiabilityStatus, CarWashMedia, CarInspectionMedia
)
from services.employee_request_service import EmployeeRequestService
from datetime import datetime
from sqlalchemy import desc, or_, and_
import os
import logging

logger = logging.getLogger(__name__)

employee_requests_refactored_bp = Blueprint(
    'employee_requests_refactored', 
    __name__, 
    url_prefix='/employee-requests-new'
)


def check_access():
    """Check if current user has admin access."""
    if current_user.role != UserRole.ADMIN:
        return False
    return True


# ==================== List & View Routes ====================

@employee_requests_refactored_bp.route('/')
@login_required
def index():
    """List all employee requests with filters."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    employee_filter = request.args.get('employee_id', '')
    
    # Build query
    query = EmployeeRequest.query
    
    if status_filter:
        query = query.filter_by(status=RequestStatus[status_filter])
    
    if type_filter:
        query = query.filter_by(request_type=RequestType[type_filter])
    
    if employee_filter:
        query = query.filter_by(employee_id=int(employee_filter))
    
    requests_pagination = query.order_by(desc(EmployeeRequest.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get employees list
    from sqlalchemy.orm import joinedload
    employees = Employee.query.options(
        joinedload(Employee.departments),
        joinedload(Employee.nationality_rel)
    ).all()
    
    # Get statistics using service
    stats = EmployeeRequestService.get_admin_statistics()
    
    return render_template('employee_requests/index.html',
                         requests=requests_pagination.items,
                         pagination=requests_pagination,
                         employees=employees,
                         stats=stats,
                         RequestStatus=RequestStatus,
                         RequestType=RequestType)


@employee_requests_refactored_bp.route('/<int:request_id>')
@login_required
def view_request(request_id):
    """View request details."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request:
        flash('الطلب غير موجود', 'error')
        return redirect(url_for('employee_requests_refactored.index'))
    
    # Get type-specific data
    specific_request = None
    if emp_request.request_type == RequestType.INVOICE:
        specific_request = InvoiceRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.CAR_WASH:
        specific_request = CarWashRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.CAR_INSPECTION:
        specific_request = CarInspectionRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.ADVANCE_PAYMENT:
        specific_request = AdvancePaymentRequest.query.filter_by(request_id=request_id).first()
    
    return render_template('employee_requests/view.html',
                         emp_request=emp_request,
                         specific_request=specific_request,
                         RequestType=RequestType,
                         RequestStatus=RequestStatus)


# ==================== Edit Routes ====================

@employee_requests_refactored_bp.route('/<int:request_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    """Edit request (basic info only)."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request:
        flash('الطلب غير موجود', 'error')
        return redirect(url_for('employee_requests_refactored.index'))
    
    if request.method == 'POST':
        emp_request.title = request.form.get('title')
        emp_request.description = request.form.get('description')
        emp_request.amount = float(request.form.get('amount', 0))
        
        if emp_request.request_type == RequestType.INVOICE:
            invoice = emp_request.invoice_data
            if invoice:
                invoice.vendor_name = request.form.get('vendor_name')
        
        try:
            db.session.commit()
            flash('تم تحديث الطلب بنجاح', 'success')
            return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء التحديث: {str(e)}', 'error')
    
    # Get type-specific data for form
    specific_request = None
    if emp_request.request_type == RequestType.INVOICE:
        specific_request = InvoiceRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.CAR_WASH:
        specific_request = CarWashRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.CAR_INSPECTION:
        specific_request = CarInspectionRequest.query.filter_by(request_id=request_id).first()
    elif emp_request.request_type == RequestType.ADVANCE_PAYMENT:
        specific_request = AdvancePaymentRequest.query.filter_by(request_id=request_id).first()
    
    return render_template('employee_requests/edit.html',
                         emp_request=emp_request,
                         specific_request=specific_request,
                         RequestType=RequestType,
                         RequestStatus=RequestStatus)


@employee_requests_refactored_bp.route('/<int:request_id>/edit-advance-payment', methods=['POST'])
@login_required
def edit_advance_payment(request_id):
    """Edit advance payment request details."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request or emp_request.request_type != RequestType.ADVANCE_PAYMENT:
        flash('الطلب غير صحيح', 'error')
        return redirect(url_for('employee_requests_refactored.index'))
    
    if emp_request.status != RequestStatus.PENDING:
        flash('لا يمكن تعديل طلب تمت معالجته', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
    
    advance_data = AdvancePaymentRequest.query.filter_by(request_id=request_id).first()
    if not advance_data:
        flash('بيانات السلفة غير موجودة', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
    
    try:
        # Update amount
        requested_amount = request.form.get('requested_amount')
        if requested_amount:
            requested_amount = float(requested_amount)
            if requested_amount <= 0:
                raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
            advance_data.requested_amount = requested_amount
            advance_data.remaining_amount = requested_amount
            emp_request.amount = requested_amount
            emp_request.title = f"طلب سلفة - {requested_amount} ريال"
        
        # Update installments
        installments = request.form.get('installments')
        if installments:
            installments_int = int(installments)
            if installments_int > 0:
                advance_data.installments = installments_int
                advance_data.installment_amount = advance_data.requested_amount / installments_int
            else:
                advance_data.installments = None
                advance_data.installment_amount = None
        
        # Update reason
        reason = request.form.get('reason', '')
        advance_data.reason = reason
        emp_request.description = reason
        
        db.session.commit()
        flash('تم تحديث بيانات السلفة بنجاح', 'success')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing advance payment {request_id}: {str(e)}")
        flash('حدث خطأ أثناء تحديث البيانات', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))


@employee_requests_refactored_bp.route('/<int:request_id>/edit-car-wash', methods=['POST'])
@login_required
def edit_car_wash(request_id):
    """Edit car wash request details."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request or emp_request.request_type != RequestType.CAR_WASH:
        flash('الطلب غير صحيح', 'error')
        return redirect(url_for('employee_requests_refactored.index'))
    
    if emp_request.status != RequestStatus.PENDING:
        flash('لا يمكن تعديل طلب تمت معالجته', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
    
    car_wash_data = CarWashRequest.query.filter_by(request_id=request_id).first()
    if not car_wash_data:
        flash('بيانات غسيل السيارة غير موجودة', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
    
    try:
        # Update service type
        service_type = request.form.get('service_type')
        if service_type:
            car_wash_data.service_type = service_type
        
        # Update scheduled date
        scheduled_date_str = request.form.get('scheduled_date')
        if scheduled_date_str:
            car_wash_data.scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
        
        # Delete selected media
        delete_media_ids = request.form.getlist('delete_media')
        for media_id in delete_media_ids:
            media = CarWashMedia.query.get(media_id)
            if media and media.wash_request_id == car_wash_data.id:
                db.session.delete(media)
        
        db.session.commit()
        flash('تم تحديث بيانات طلب غسيل السيارة بنجاح', 'success')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing car wash {request_id}: {str(e)}")
        flash('حدث خطأ أثناء تحديث البيانات', 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))


# ==================== Approve/Reject Routes ====================

@employee_requests_refactored_bp.route('/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    """Approve a request."""
    if not check_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    admin_notes = request.form.get('admin_notes', '')
    
    success, message = EmployeeRequestService.approve_request(
        request_id=request_id,
        approved_by_id=current_user.id,
        admin_notes=admin_notes
    )
    
    if success:
        flash(message, 'success')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))
    else:
        flash(message, 'error')
        return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))


@employee_requests_refactored_bp.route('/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    """Reject a request."""
    if not check_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    rejection_reason = request.form.get('rejection_reason', '')
    
    success, message = EmployeeRequestService.reject_request(
        request_id=request_id,
        approved_by_id=current_user.id,
        rejection_reason=rejection_reason
    )
    
    if success:
        flash(message, 'warning')
    else:
        flash(message, 'error')
    
    return redirect(url_for('employee_requests_refactored.view_request', request_id=request_id))


# ==================== Delete Route ====================

@employee_requests_refactored_bp.route('/delete/<int:request_id>', methods=['POST'])
@login_required
def delete_request(request_id):
    """Delete a request."""
    if not check_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    success = EmployeeRequestService.delete_request(request_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if success:
            return jsonify({'success': True, 'message': 'تم حذف الطلب بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'فشل حذف الطلب'}), 500
    else:
        if success:
            flash('تم حذف الطلب بنجاح', 'success')
        else:
            flash('فشل حذف الطلب', 'error')
        return redirect(url_for('employee_requests_refactored.index'))


# ==================== Type-Specific Lists ====================

@employee_requests_refactored_bp.route('/advance-payments')
@login_required
def advance_payments():
    """List advance payment requests."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', '')
    
    query = EmployeeRequest.query.filter_by(request_type=RequestType.ADVANCE_PAYMENT)
    
    if status_filter:
        query = query.filter_by(status=RequestStatus[status_filter])
    
    requests_pagination = query.order_by(desc(EmployeeRequest.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    total_pending = EmployeeRequest.query.filter_by(
        request_type=RequestType.ADVANCE_PAYMENT,
        status=RequestStatus.PENDING
    ).count()
    
    total_approved = EmployeeRequest.query.filter_by(
        request_type=RequestType.ADVANCE_PAYMENT,
        status=RequestStatus.APPROVED
    ).count()
    
    return render_template('employee_requests/advance_payments.html',
                         requests=requests_pagination.items,
                         pagination=requests_pagination,
                         total_pending=total_pending,
                         total_approved=total_approved,
                         RequestStatus=RequestStatus)


@employee_requests_refactored_bp.route('/invoices')
@login_required
def invoices():
    """List invoice requests."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', '')
    
    query = EmployeeRequest.query.filter_by(request_type=RequestType.INVOICE)
    
    if status_filter:
        query = query.filter_by(status=RequestStatus[status_filter])
    
    requests_pagination = query.order_by(desc(EmployeeRequest.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('employee_requests/invoices.html',
                         requests=requests_pagination.items,
                         pagination=requests_pagination,
                         RequestStatus=RequestStatus)


@employee_requests_refactored_bp.route('/liabilities')
@login_required
def liabilities():
    """List employee liabilities."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    liability_type = request.args.get('type', '')
    status_filter = request.args.get('status', '')
    
    query = EmployeeLiability.query
    
    if liability_type:
        query = query.filter_by(liability_type=liability_type)
    
    if status_filter:
        if status_filter == 'ACTIVE':
            query = query.filter_by(status=LiabilityStatus.ACTIVE)
        elif status_filter == 'PAID':
            query = query.filter_by(status=LiabilityStatus.PAID)
    
    liabilities_pagination = query.order_by(desc(EmployeeLiability.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    total_unpaid = EmployeeLiability.query.filter_by(status=LiabilityStatus.ACTIVE).count()
    total_amount = db.session.query(db.func.sum(EmployeeLiability.amount)).filter_by(status=LiabilityStatus.ACTIVE).scalar() or 0
    
    return render_template('employee_requests/liabilities.html',
                         liabilities=liabilities_pagination.items,
                         pagination=liabilities_pagination,
                         total_unpaid=total_unpaid,
                         total_amount=total_amount)


# ==================== Utility Routes ====================

@employee_requests_refactored_bp.route('/<int:request_id>/upload-to-drive', methods=['POST'])
@login_required
def upload_to_drive(request_id):
    """Manually upload request files to Google Drive."""
    if not check_access():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    from utils.employee_requests_drive_uploader import EmployeeRequestsDriveUploader
    
    emp_request = EmployeeRequestService.get_request_by_id(request_id)
    
    if not emp_request:
        return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404
    
    if emp_request.google_drive_folder_id:
        return jsonify({
            'success': False,
            'message': 'هذا الطلب مرفوع بالفعل على Google Drive',
            'folder_url': emp_request.google_drive_folder_url
        }), 400
    
    drive_uploader = EmployeeRequestsDriveUploader()
    
    if not drive_uploader.is_available():
        return jsonify({
            'success': False,
            'message': 'خدمة Google Drive غير متاحة حالياً'
        }), 503
    
    # Create folder
    type_map = {
        RequestType.INVOICE: 'invoice',
        RequestType.CAR_WASH: 'car_wash',
        RequestType.CAR_INSPECTION: 'car_inspection',
        RequestType.ADVANCE_PAYMENT: 'advance_payment'
    }
    
    vehicle_number = None
    if emp_request.request_type == RequestType.CAR_WASH and emp_request.car_wash_data:
        vehicle = emp_request.car_wash_data.vehicle
        vehicle_number = vehicle.plate_number if vehicle else None
    elif emp_request.request_type == RequestType.CAR_INSPECTION and emp_request.inspection_data:
        vehicle = emp_request.inspection_data.vehicle
        vehicle_number = vehicle.plate_number if vehicle else None
    
    folder_result = drive_uploader.create_request_folder(
        request_type=type_map.get(emp_request.request_type, 'other'),
        request_id=request_id,
        employee_name=emp_request.employee.name if emp_request.employee else "Unknown",
        vehicle_number=str(vehicle_number) if vehicle_number else '',
        date=emp_request.created_at
    )
    
    if not folder_result:
        return jsonify({
            'success': False,
            'message': 'فشل إنشاء المجلد في Google Drive'
        }), 500
    
    # Save folder info
    emp_request.google_drive_folder_id = folder_result['folder_id']
    emp_request.google_drive_folder_url = folder_result['folder_url']
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'تم إنشاء مجلد Google Drive بنجاح',
        'folder_url': folder_result['folder_url']
    }), 200


@employee_requests_refactored_bp.route('/stats')
@login_required
def stats():
    """Get statistics dashboard."""
    if not check_access():
        flash('ليس لديك صلاحية الوصول إلى هذا القسم', 'error')
        return redirect(url_for('dashboard'))
    
    stats = EmployeeRequestService.get_admin_statistics()
    
    return render_template('employee_requests/stats.html', stats=stats)
