"""
Core operations routes:
- Dashboard & list views
- View operation details
- Delete operations
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from core.extensions import db
from models import OperationRequest, OperationNotification, VehicleHandover, VehicleWorkshop, Vehicle, UserRole, Employee, MobileDevice
from datetime import datetime
from utils.audit_logger import log_activity, log_audit

operations_core_bp = Blueprint('operations_core', __name__, url_prefix='/operations')


@operations_core_bp.route('/')
@login_required
def operations_dashboard():
    """لوحة إدارة العمليات الرئيسية مع إمكانية البحث"""

    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    # 1. استلام قيمة البحث من رابط URL
    search_plate = request.args.get('search_plate', '').strip()

    # 2. بناء استعلام العمليات المعلقة
    pending_query = OperationRequest.query.filter_by(status='pending')

    # 3. تطبيق فلتر البحث (إذا تم إدخال قيمة)
    if search_plate:
        pending_query = pending_query.join(Vehicle).filter(Vehicle.plate_number.ilike(f"%{search_plate}%"))

    # 4. تنفيذ الاستعلام النهائي
    pending_requests = pending_query.order_by(
        OperationRequest.priority.desc(),
        OperationRequest.requested_at.desc()
    ).limit(10).all()

    # إحصائيات العمليات
    stats = {
        'pending': OperationRequest.query.filter_by(status='pending').count(),
        'under_review': OperationRequest.query.filter_by(status='under_review').count(),
        'approved': OperationRequest.query.filter_by(status='approved').count(),
        'rejected': OperationRequest.query.filter_by(status='rejected').count(),
        'unread_notifications': OperationNotification.query.filter_by(user_id=current_user.id, is_read=False).count(),
    }

    return render_template('operations/dashboard.html', 
                         stats=stats, 
                         pending_requests=pending_requests)


@operations_core_bp.route('/list')
@login_required
def operations_list():
    """قائمة جميع العمليات مع فلترة"""
    
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # فلترة العمليات
    status_filter = request.args.get('status', 'all')
    operation_type_filter = request.args.get('operation_type', 'all')
    priority_filter = request.args.get('priority', 'all')
    vehicle_search = request.args.get('vehicle_search', '').strip()
    
    query = OperationRequest.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if operation_type_filter != 'all':
        query = query.filter_by(operation_type=operation_type_filter)
    
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    # البحث حسب السيارة
    if vehicle_search:
        query = query.filter(
            OperationRequest.title.contains(vehicle_search) |
            OperationRequest.description.contains(vehicle_search)
        )
    
    # ترتيب العمليات
    operations = query.order_by(
        OperationRequest.priority.desc(),
        OperationRequest.requested_at.desc()
    ).all()
    
    return render_template('operations/list.html', 
                         operations=operations,
                         status_filter=status_filter,
                         operation_type_filter=operation_type_filter,
                         priority_filter=priority_filter,
                         vehicle_search=vehicle_search)


@operations_core_bp.route('/<int:operation_id>')
@login_required
def view_operation(operation_id):
    """عرض تفاصيل العملية"""
    
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    operation = OperationRequest.query.get_or_404(operation_id)
    related_record = operation.get_related_record()
    
    # توجيه عمليات الورشة إلى صفحة منفصلة
    if operation.operation_type == 'workshop_record':
        # جلب معلومات السائق الحالي من آخر تسليم
        driver_employee = None
        current_driver_info = None
        
        # البحث عن آخر تسليم للمركبة للحصول على السائق الحالي
        last_handover = VehicleHandover.query.filter_by(
            vehicle_id=operation.vehicle_id,
            handover_type='delivery'
        ).order_by(VehicleHandover.handover_date.desc()).first()
        
        if last_handover:
            current_driver_info = {
                'name': last_handover.person_name,
                'phone': last_handover.driver_phone_number,
                'residency_number': last_handover.driver_residency_number
            }
            
            # محاولة العثور على بيانات الموظف في النظام
            if last_handover.driver_residency_number:
                driver_employee = Employee.query.filter_by(
                    national_id=last_handover.driver_residency_number
                ).first()
            
            if not driver_employee and last_handover.person_name:
                driver_employee = Employee.query.filter_by(
                    name=last_handover.person_name
                ).first()
        
        # جلب الصور من قاعدة البيانات مباشرة
        from sqlalchemy import text
        workshop_images = []
        if related_record and hasattr(related_record, 'id'):
            try:
                result = db.session.execute(
                    text("SELECT id, image_type, image_path, notes, uploaded_at FROM vehicle_workshop_images WHERE workshop_record_id = :workshop_id ORDER BY uploaded_at DESC"),
                    {'workshop_id': related_record.id}
                )
                workshop_images = [
                    {
                        'id': row[0],
                        'image_type': row[1], 
                        'image_path': row[2],
                        'notes': row[3],
                        'uploaded_at': row[4]
                    } 
                    for row in result
                ]
            except Exception as e:
                current_app.logger.error(f"خطأ في جلب صور الورشة: {str(e)}")
        
        return render_template('operations/view_workshop.html', 
                             operation=operation,
                             related_record=related_record,
                             workshop_images=workshop_images,
                             driver_employee=driver_employee,
                             current_driver_info=current_driver_info)
    
    # جلب بيانات الموظف إذا كانت متاحة
    employee = None
    if related_record:
        if hasattr(related_record, 'driver_residency_number') and related_record.driver_residency_number:
            employee = Employee.query.filter_by(national_id=related_record.driver_residency_number).first()
        if not employee and hasattr(related_record, 'person_name') and related_record.person_name:
            employee = Employee.query.filter_by(name=related_record.person_name).first()
        if not employee and hasattr(related_record, 'driver_name') and related_record.driver_name:
            employee = Employee.query.filter_by(name=related_record.driver_name).first()
    
    # تحميل معلومات إضافية للطالب إذا كان موظفاً
    if operation.requester and hasattr(operation.requester, 'id'):
        try:
            requester_employee = Employee.query.options(db.joinedload(Employee.departments)).get(operation.requester.id)
            if requester_employee:
                operation.requester = requester_employee
        except Exception as e:
            print(f"خطأ في تحميل بيانات الموظف الطالب: {e}")
    
    # البحث عن جهاز الجوال المخصص للمستخدم
    mobile_device = MobileDevice.query.filter_by(employee_id=operation.requester.id).first()
    
    return render_template('operations/view.html', 
                         operation=operation,
                         related_record=related_record,
                         employee=employee,
                         mobile_device=mobile_device)


@operations_core_bp.route('/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete_operation(id):
    """حذف العملية"""
    
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بحذف العمليات', 'error')
        return redirect(url_for('operations_core.operations_list'))
    
    operation = OperationRequest.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('operations/delete.html', operation=operation)
    
    # معالجة الحذف عند POST
    try:
        operation_title = operation.title
        operation_type = operation.operation_type
        
        # حذف الإشعارات المرتبطة بالعملية أولاً
        OperationNotification.query.filter_by(operation_request_id=id).delete()
        
        # حذف العملية
        db.session.delete(operation)
        db.session.commit()
        
        # تسجيل عملية الحذف
        log_audit(current_user.id, 'delete', 'operation_request', id, f'تم حذف العملية: {operation_title} من النوع {operation_type}')
        
        flash('تم حذف العملية بنجاح', 'success')
        return redirect(url_for('operations_core.operations_list'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في حذف العملية #{id}: {str(e)}")
        flash(f'حدث خطأ أثناء حذف العملية: {str(e)}', 'error')
        return redirect(url_for('operations_core.view_operation', operation_id=id))
