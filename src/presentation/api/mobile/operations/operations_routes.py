"""Mobile operations routes extracted from routes/mobile.py."""

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, text

from src.core.extensions import db
from models import OperationNotification, OperationRequest, UserRole, Vehicle


def _admin_only_or_redirect():
    if current_user.role != UserRole.ADMIN:
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('mobile.dashboard'))
    return None


def register_operations_routes(mobile_bp):
    @mobile_bp.route('/operations')
    @login_required
    def operations_dashboard():
        """لوحة إدارة العمليات الرئيسية للنسخة المحمولة"""
        denied = _admin_only_or_redirect()
        if denied:
            return denied

        search_plate = request.args.get('search_plate', '').strip()

        pending_query = OperationRequest.query.filter_by(status='pending')

        if search_plate:
            pending_query = pending_query.join(Vehicle).filter(Vehicle.plate_number.ilike(f"%{search_plate}%"))

        pending_requests = pending_query.order_by(
            OperationRequest.priority.desc(),
            OperationRequest.requested_at.desc(),
        ).limit(10).all()

        stats = {
            'pending': OperationRequest.query.filter_by(status='pending').count(),
            'under_review': OperationRequest.query.filter_by(status='under_review').count(),
            'approved': OperationRequest.query.filter_by(status='approved').count(),
            'rejected': OperationRequest.query.filter_by(status='rejected').count(),
            'unread_notifications': OperationNotification.query.filter_by(user_id=current_user.id, is_read=False).count() if hasattr(current_user, 'id') else 0,
        }

        return render_template('mobile/operations.html', stats=stats, pending_requests=pending_requests)

    @mobile_bp.route('/operations/list')
    @login_required
    def operations_list():
        """قائمة جميع العمليات مع فلترة للنسخة المحمولة"""
        denied = _admin_only_or_redirect()
        if denied:
            return denied

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

        if vehicle_search:
            query = query.filter(
                or_(
                    OperationRequest.title.contains(vehicle_search),
                    OperationRequest.description.contains(vehicle_search),
                )
            )

        operations = query.order_by(
            OperationRequest.priority.desc(),
            OperationRequest.requested_at.desc(),
        ).all()

        return render_template(
            'mobile/operations_list.html',
            operations=operations,
            status_filter=status_filter,
            operation_type_filter=operation_type_filter,
            priority_filter=priority_filter,
            vehicle_search=vehicle_search,
        )

    @mobile_bp.route('/operations/<int:operation_id>')
    @login_required
    def operation_details(operation_id):
        """عرض تفاصيل العملية للنسخة المحمولة"""
        denied = _admin_only_or_redirect()
        if denied:
            return denied

        operation = OperationRequest.query.get_or_404(operation_id)
        related_record = operation.get_related_record()

        workshop_images = []
        if operation.operation_type == 'workshop_record' and related_record:
            try:
                result = db.session.execute(
                    text(
                        "SELECT id, image_type, image_path, notes, uploaded_at "
                        "FROM vehicle_workshop_images "
                        "WHERE workshop_record_id = :workshop_id "
                        "ORDER BY uploaded_at DESC"
                    ),
                    {'workshop_id': related_record.id},
                )
                workshop_images = [
                    {
                        'id': row[0],
                        'image_type': row[1],
                        'image_path': row[2],
                        'notes': row[3],
                        'uploaded_at': row[4],
                    }
                    for row in result
                ]
            except Exception as e:
                current_app.logger.error(f"خطأ في جلب صور الورشة: {str(e)}")

        return render_template(
            'mobile/operation_details.html',
            operation=operation,
            related_record=related_record,
            workshop_images=workshop_images,
        )

    @mobile_bp.route('/operations/notifications')
    @login_required
    def operations_notifications():
        """صفحة الإشعارات للنسخة المحمولة"""
        denied = _admin_only_or_redirect()
        if denied:
            return denied

        notifications = OperationNotification.query.filter_by(
            user_id=current_user.id
        ).order_by(
            OperationNotification.is_read.asc(),
            OperationNotification.created_at.desc(),
        ).limit(50).all()

        unread_count = OperationNotification.query.filter_by(
            user_id=current_user.id,
            is_read=False,
        ).count()

        return render_template(
            'mobile/operations_notifications.html',
            notifications=notifications,
            unread_count=unread_count,
        )
