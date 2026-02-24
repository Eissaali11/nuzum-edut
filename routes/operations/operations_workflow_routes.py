"""
Operations workflow routes:
- Approve/reject/review operations
- Update operation status
- Create/manage notifications
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from core.extensions import db
from models import OperationRequest, OperationNotification, VehicleHandover, Vehicle, UserRole
from datetime import datetime
from utils.audit_logger import log_activity, log_audit

operations_workflow_bp = Blueprint('operations_workflow', __name__, url_prefix='/operations')


def create_operation_request(operation_type, related_record_id, vehicle_id, 
                           title, description, requested_by, priority='normal'):
    """إنشاء طلب عملية جديد"""
    from models import User, Notification
    from flask import url_for
    
    operation = OperationRequest()
    operation.operation_type = operation_type
    operation.related_record_id = related_record_id
    operation.vehicle_id = vehicle_id
    operation.title = title
    operation.description = description
    operation.requested_by = requested_by
    operation.requested_at = datetime.utcnow()
    operation.priority = priority
    operation.status = 'pending'
    
    try:
        db.session.add(operation)
        db.session.flush()  # للحصول على ID
        
        # إنشاء إشعارات للمديرين
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        for admin in admins:
            create_notification(
                operation_id=operation.id,
                user_id=admin.id,
                notification_type='new_operation',
                title=f'عملية جديدة تحتاج موافقة: {title}',
                message=f'عملية جديدة من نوع {get_operation_type_name(operation_type)} تحتاج للمراجعة والموافقة.'
            )
        
        # إنشاء إشعارات لجميع المستخدمين
        try:
            all_users = User.query.all()
            
            vehicle_info = ""
            if vehicle_id:
                vehicle = Vehicle.query.get(vehicle_id)
                if vehicle:
                    vehicle_info = f" - المركبة {vehicle.plate_number}"
            
            for user in all_users:
                try:
                    new_notification = Notification(
                        user_id=user.id,
                        notification_type='operations',
                        title=f'عملية جديدة{vehicle_info}',
                        description=description,
                        related_entity_type='operation',
                        related_entity_id=operation.id,
                        priority='high' if priority == 'urgent' else 'normal',
                        action_url=url_for('operations_core.view_operation', operation_id=operation.id)
                    )
                    db.session.add(new_notification)
                except Exception as e:
                    current_app.logger.error(f'خطأ في إنشاء إشعار للمستخدم {user.id}: {str(e)}')
        except Exception as e:
            current_app.logger.error(f'خطأ في إنشاء إشعارات العمليات الجديدة: {str(e)}')
        
        return operation
    except Exception as e:
        current_app.logger.error(f"خطأ في create_operation_request: {str(e)}")
        raise e


def create_notification(operation_id, user_id, notification_type, title, message):
    """إنشاء إشعار جديد"""
    
    notification = OperationNotification()
    notification.operation_request_id = operation_id
    notification.user_id = user_id
    notification.notification_type = notification_type
    notification.title = title
    notification.message = message
    
    db.session.add(notification)
    return notification


def get_operation_type_name(operation_type):
    """الحصول على اسم نوع العملية بالعربية"""
    
    type_names = {
        'handover': 'تسليم/استلام مركبة',
        'workshop': 'عملية ورشة',
        'workshop_record': 'سجل ورشة',
        'external_authorization': 'تفويض خارجي',
        'safety_inspection': 'فحص سلامة'
    }
    
    return type_names.get(operation_type, operation_type)


def get_pending_operations_count():
    """الحصول على عدد العمليات المعلقة"""
    return OperationRequest.query.filter_by(status='pending').count()


def get_unread_notifications_count(user_id):
    """الحصول على عدد الإشعارات غير المقروءة للمستخدم"""
    return OperationNotification.query.filter_by(
        user_id=user_id, 
        is_read=False
    ).count()


@operations_workflow_bp.route('/<int:operation_id>/approve', methods=['POST'])
@login_required
def approve_operation(operation_id):
    """الموافقة على العملية مع تفعيل السجل المرتبط"""
    
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'غير مسموح لك بالقيام بهذا الإجراء'})

    operation = OperationRequest.query.get_or_404(operation_id)
    review_notes = request.form.get('review_notes', '').strip()

    try:
        # تحديث حالة الطلب
        operation.status = 'approved'
        operation.reviewed_by = current_user.id
        operation.reviewed_at = datetime.utcnow()
        operation.review_notes = review_notes

        # معالجة حسب نوع العملية
        if operation.operation_type == 'handover':
            handover_record = VehicleHandover.query.get(operation.related_record_id)
            if handover_record:
                db.session.commit()

                # تحديث حالة السيارة
                if operation.vehicle_id:
                    from .operations_helpers import update_vehicle_state
                    update_vehicle_state(operation.vehicle_id)
                    log_audit(
                        'update', 'vehicle_state', operation.vehicle_id,
                        f'تم تحديث حالة السيارة والسائق بعد الموافقة على الطلب #{operation.id}'
                    )
            else:
                current_app.logger.warning(f"لم يتم العثور على سجل Handover رقم {operation.related_record_id}")

        # إنشاء إشعار للطالب
        create_notification(
            operation_id=operation.id,
            user_id=operation.requested_by,
            notification_type='status_change',
            title=f'✅ تمت الموافقة على طلبك: {operation.title}',
            message=f'تمت الموافقة على طلبك من قبل {current_user.username}.'
        )

        db.session.commit()

        log_activity(
            action='approve',
            entity_type='operation_request',
            entity_id=operation.id,
            details=f'تمت الموافقة على العملية: {operation.title}'
        )
        
        return jsonify({'success': True, 'message': 'تمت الموافقة بنجاح'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في الموافقة على العملية #{operation_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})


@operations_workflow_bp.route('/<int:operation_id>/reject', methods=['POST'])
@login_required
def reject_operation(operation_id):
    """رفض العملية"""
    
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'غير مسموح'})
    
    operation = OperationRequest.query.get_or_404(operation_id)
    review_notes = request.form.get('review_notes', '').strip()
    
    if not review_notes:
        return jsonify({'success': False, 'message': 'يجب إدخال سبب الرفض'})
    
    try:
        # تحديث حالة العملية
        operation.status = 'rejected'
        operation.reviewed_by = current_user.id
        operation.reviewed_at = datetime.utcnow()
        operation.review_notes = review_notes
        
        # إنشاء إشعار للطالب
        create_notification(
            operation_id=operation.id,
            user_id=operation.requested_by,
            notification_type='status_change',
            title=f'تم رفض العملية: {operation.title}',
            message=f'تم رفض العملية من قبل {current_user.username}.\nالسبب: {review_notes}'
        )

        # حذف السجل المرتبط إذا كان handover
        record_to_delete = None
        if operation.operation_type == 'handover':
            record_to_delete = VehicleHandover.query.get(operation.related_record_id)

        if record_to_delete:
            db.session.delete(record_to_delete)
            log_audit(
                'delete_on_rejection', 'VehicleHandover', record_to_delete.id,
                f"تم حذف سجل Handover بسبب رفض الطلب #{operation.id}"
            )
        else:
            if operation.operation_type == 'handover':
                current_app.logger.warning(f"لم يتم العثور على سجل Handover رقم {operation.related_record_id}")

        db.session.commit()
        
        log_audit(current_user.id, 'reject', 'operation_request', operation.id, 
                 f'تم رفض العملية: {operation.title} - السبب: {review_notes}')
        
        return jsonify({'success': True, 'message': 'تم رفض العملية'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})


@operations_workflow_bp.route('/<int:operation_id>/under-review', methods=['POST'])
@login_required  
def set_under_review(operation_id):
    """وضع العملية تحت المراجعة"""
    
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'غير مسموح'})
    
    operation = OperationRequest.query.get_or_404(operation_id)
    
    try:
        operation.status = 'under_review'
        operation.reviewed_by = current_user.id
        operation.reviewed_at = datetime.utcnow()
        
        # إنشاء إشعار للطالب
        create_notification(
            operation_id=operation.id,
            user_id=operation.requested_by,
            notification_type='status_change',
            title=f'العملية تحت المراجعة: {operation.title}',
            message=f'العملية قيد المراجعة من قبل {current_user.username}'
        )
        
        db.session.commit()
        
        log_audit(current_user.id, 'review', 'operation_request', operation.id, 
                 f'العملية تحت المراجعة: {operation.title}')
        
        return jsonify({'success': True, 'message': 'تم وضع العملية تحت المراجعة'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})


@operations_workflow_bp.route('/notifications')
@login_required
def notifications():
    """عرض الإشعارات"""
    from flask import render_template
    
    user_notifications = OperationNotification.query.filter_by(
        user_id=current_user.id
    ).order_by(OperationNotification.created_at.desc()).all()
    
    # تحديد الإشعارات كمقروءة
    OperationNotification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).update({'is_read': True, 'read_at': datetime.utcnow()})
    
    db.session.commit()
    
    return render_template('operations/notifications.html', 
                         notifications=user_notifications)


@operations_workflow_bp.route('/test-notifications', methods=['GET', 'POST'])
def test_operations_notifications():
    """اختبار إنشاء إشعارات العمليات"""
    from models import Notification, User
    from flask import url_for
    
    try:
        last_operation = OperationRequest.query.order_by(OperationRequest.id.desc()).first()
        
        if not last_operation:
            return jsonify({'success': False, 'message': 'لا توجد عمليات'}), 404
        
        all_users = User.query.all()
        
        vehicle_info = ""
        if last_operation.vehicle_id:
            vehicle = Vehicle.query.get(last_operation.vehicle_id)
            if vehicle:
                vehicle_info = f" - المركبة {vehicle.plate_number}"
        
        notification_count = 0
        for user in all_users:
            try:
                new_notification = Notification(
                    user_id=user.id,
                    notification_type='operations',
                    title=f'عملية جديدة{vehicle_info}',
                    description=last_operation.description or 'عملية تحتاج مراجعة',
                    related_entity_type='operation',
                    related_entity_id=last_operation.id,
                    priority='normal',
                    action_url=url_for('operations_core.view_operation', operation_id=last_operation.id)
                )
                db.session.add(new_notification)
                notification_count += 1
            except Exception as e:
                current_app.logger.error(f'خطأ في إنشاء إشعار للمستخدم {user.id}: {str(e)}')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء {notification_count} إشعار للعملية {last_operation.id}',
            'operation_id': last_operation.id,
            'users_count': len(all_users)
        })
    except Exception as e:
        current_app.logger.error(f'خطأ في اختبار الإشعارات: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@operations_workflow_bp.route('/api/count')
@login_required
def api_operations_count():
    """API للحصول على إحصائيات العمليات"""
    
    if current_user.role != UserRole.ADMIN:
        return jsonify({'error': 'غير مسموح'})
    
    pending_count = OperationRequest.query.filter_by(status='pending').count()
    under_review_count = OperationRequest.query.filter_by(status='under_review').count()
    
    return jsonify({
        'pending': pending_count,
        'under_review': under_review_count,
        'unread_notifications': get_unread_notifications_count(current_user.id)
    })
