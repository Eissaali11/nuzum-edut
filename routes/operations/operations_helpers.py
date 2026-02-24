"""
Operations helper utilities:
Shared functions used across operations modules
"""

from core.extensions import db
from models import OperationRequest, VehicleHandover, VehicleWorkshop, VehicleRental, Vehicle, ExternalAuthorization
from datetime import datetime
from flask import current_app


def update_vehicle_state(vehicle_id):
    """
    الدالة المركزية الذكية لتحديد وتحديث الحالة النهائية للمركبة وسائقها.
    تعتمد على حالة OperationRequest المرتبط لتحديد السجلات الرسمية.
    """
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            current_app.logger.warning(f"محاولة تحديث حالة لمركبة غير موجودة: ID={vehicle_id}")
            return

        # 1. فحص الحالات ذات الأولوية القصوى
        if vehicle.status == 'out_of_service':
            return

        # التحقق من الحوادث الفعالة والورشة
        from models import VehicleAccident
        from sqlalchemy import and_
        
        active_accident = VehicleAccident.query.filter(
            and_(
                VehicleAccident.vehicle_id == vehicle_id, 
                VehicleAccident.accident_status != 'مغلق'
            )
        ).first()
        
        in_workshop = VehicleWorkshop.query.filter(
            and_(
                VehicleWorkshop.vehicle_id == vehicle_id, 
                VehicleWorkshop.exit_date.is_(None)
            )
        ).first()

        is_critical_state = bool(active_accident or in_workshop)

        if active_accident:
            vehicle.status = 'accident'
        elif in_workshop:
            vehicle.status = 'in_workshop'

        # 2. التحقق من الإيجار النشط
        active_rental = VehicleRental.query.filter_by(
            vehicle_id=vehicle_id, 
            is_active=True
        ).first()

        # 3. استعلام السجلات الرسمية للتسليم
        from sqlalchemy import or_
        
        approved_handover_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.status == 'approved',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()

        all_handover_request_ids_subquery = db.session.query(
            OperationRequest.related_record_id
        ).filter(
            OperationRequest.operation_type == 'handover',
            OperationRequest.vehicle_id == vehicle_id
        ).subquery()

        base_official_query = VehicleHandover.query.filter(
            VehicleHandover.vehicle_id == vehicle_id
        ).filter(
            or_(
                VehicleHandover.id.in_(approved_handover_ids_subquery),
                ~VehicleHandover.id.in_(all_handover_request_ids_subquery)
            )
        )

        # 4. الحصول على آخر عملية تسليم واستلام
        latest_delivery = base_official_query.filter(
            VehicleHandover.handover_type.in_(['delivery', 'تسليم'])
        ).order_by(VehicleHandover.created_at.desc()).first()

        latest_return = base_official_query.filter(
            VehicleHandover.handover_type.in_(['return', 'استلام', 'receive'])
        ).order_by(VehicleHandover.created_at.desc()).first()

        # 5. تطبيق التحديثات
        is_currently_handed_out = False
        if latest_delivery:
            if not latest_return or latest_delivery.created_at > latest_return.created_at:
                is_currently_handed_out = True

        if is_currently_handed_out:
            vehicle.driver_name = latest_delivery.person_name
            if not is_critical_state:
                vehicle.status = 'rented' if active_rental else 'in_project'
        else:
            vehicle.driver_name = None
            if not is_critical_state:
                vehicle.status = 'rented' if active_rental else 'available'

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في update_vehicle_state {vehicle_id}: {str(e)}")


def get_operation_type_name_arabic(operation_type):
    """تحويل نوع العملية إلى النص العربي"""
    type_names = {
        'handover': 'تسليم/استلام مركبة',
        'workshop': 'عملية ورشة',
        'workshop_record': 'سجل ورشة',
        'external_authorization': 'تفويض خارجي',
        'safety_inspection': 'فحص سلامة'
    }
    return type_names.get(operation_type, operation_type)


def get_status_name_arabic(status):
    """تحويل الحالة إلى النص العربي"""
    status_names = {
        'pending': 'معلقة',
        'under_review': 'تحت المراجعة',
        'approved': 'موافق عليها',
        'rejected': 'مرفوضة'
    }
    return status_names.get(status, status)


def get_priority_name_arabic(priority):
    """تحويل الأولوية إلى النص العربي"""
    priority_names = {
        'urgent': 'عاجل',
        'high': 'عالي',
        'normal': 'عادي',
        'low': 'منخفض'
    }
    return priority_names.get(priority, priority)
