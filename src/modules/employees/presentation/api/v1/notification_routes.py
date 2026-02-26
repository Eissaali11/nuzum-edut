import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from src.core.extensions import db
from models import RequestNotification
from src.modules.employees.presentation.api.v1.auth_routes import token_required

logger = logging.getLogger(__name__)

notifications_api_v1 = Blueprint('notifications_api_v1', __name__, url_prefix='/api/v1')

@notifications_api_v1.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_employee):
    """
    الحصول على إشعارات الموظف
    
    Query Parameters:
    - unread_only: true/false (default: false)
    - page: رقم الصفحة (default: 1)
    - per_page: عدد العناصر (default: 20)
    
    Response:
    {
        "success": true,
        "notifications": [...],
        "unread_count": 5
    }
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = RequestNotification.query.filter_by(employee_id=current_employee.id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    pagination = query.order_by(RequestNotification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    notifications_list = []
    for notif in pagination.items:
        notifications_list.append({
            'id': notif.id,
            'request_id': notif.request_id if notif.request_id else None,
            'title': notif.title_ar if notif.title_ar else '',
            'message': notif.message_ar if notif.message_ar else '',
            'type': notif.notification_type if notif.notification_type else '',
            'is_read': notif.is_read if notif.is_read is not None else False,
            'created_at': notif.created_at.isoformat() if notif.created_at else datetime.utcnow().isoformat()
        })
    
    unread_count = RequestNotification.query.filter_by(
        employee_id=current_employee.id,
        is_read=False
    ).count()
    
    return jsonify({
        'success': True,
        'notifications': notifications_list,
        'unread_count': unread_count,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@notifications_api_v1.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_employee, notification_id):
    """
    تعليم إشعار كمقروء
    
    Response:
    {
        "success": true,
        "message": "تم تعليم الإشعار كمقروء"
    }
    """
    notification = RequestNotification.query.filter_by(
        id=notification_id,
        employee_id=current_employee.id
    ).first()
    
    if not notification:
        return jsonify({
            'success': False,
            'message': 'الإشعار غير موجود'
        }), 404
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'تم تعليم الإشعار كمقروء'
    }), 200


@notifications_api_v1.route('/notifications/mark-all-read', methods=['PUT'])
@token_required
def mark_all_notifications_read(current_employee):
    """
    تحديد جميع الإشعارات كمقروءة
    
    Response:
    {
        "success": true,
        "message": "تم تحديد جميع الإشعارات كمقروءة",
        "data": {
            "updated_count": 15
        }
    }
    """
    try:
        unread_notifications = RequestNotification.query.filter_by(
            employee_id=current_employee.id,
            is_read=False
        ).all()
        
        updated_count = len(unread_notifications)
        
        for notification in unread_notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديد جميع الإشعارات كمقروءة',
            'data': {
                'updated_count': updated_count,
                'unread_count': 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read for employee {current_employee.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء تحديث الإشعارات',
            'error': str(e)
        }), 500
