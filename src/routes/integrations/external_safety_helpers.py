from flask import current_app, url_for
from PIL import Image
from sqlalchemy import func, select

from src.core.extensions import db
from models import VehicleHandover

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}


def create_safety_check_notification(user_id, vehicle_plate, supervisor_name, check_status, check_id):
    from models import Notification

    status_labels = {
        'pending': 'قيد الانتظار',
        'under_review': 'قيد المراجعة',
        'approved': 'موافق عليه',
        'rejected': 'مرفوض'
    }

    priority_map = {
        'pending': 'high',
        'under_review': 'normal',
        'approved': 'normal',
        'rejected': 'critical'
    }

    status_label = status_labels.get(check_status, check_status)

    notification = Notification(
        user_id=user_id,
        notification_type='safety_check',
        title=f'فحص السلامة - السيارة {vehicle_plate}',
        description=f'طلب فحص السلامة الخارجية للسيارة {vehicle_plate} من قبل {supervisor_name} - الحالة: {status_label}',
        related_entity_type='safety_check',
        related_entity_id=check_id,
        priority=priority_map.get(check_status, 'normal'),
        action_url=url_for('external_safety.admin_external_safety_checks')
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def create_safety_check_review_notification(user_id, vehicle_plate, action, reviewer_name, check_id):
    from models import Notification

    action_labels = {
        'approved': 'تمت الموافقة على',
        'rejected': 'تم رفض',
        'under_review': 'قيد المراجعة'
    }

    priority = 'high' if action in ['rejected'] else 'normal'
    action_label = action_labels.get(action, action)

    notification = Notification(
        user_id=user_id,
        notification_type='safety_check_review',
        title=f'{action_label} فحص السلامة - {vehicle_plate}',
        description=f'تمت مراجعة فحص السلامة للسيارة {vehicle_plate} بواسطة {reviewer_name}: {action_label}',
        related_entity_type='safety_check',
        related_entity_id=check_id,
        priority=priority,
        action_url=url_for('external_safety.admin_external_safety_checks')
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def get_all_current_drivers_with_email():
    delivery_handover_types = ['delivery', 'تسليم', 'handover']

    subq = select(
        VehicleHandover.id,
        func.row_number().over(
            partition_by=VehicleHandover.vehicle_id,
            order_by=VehicleHandover.handover_date.desc()
        ).label('row_num')
    ).where(
        VehicleHandover.handover_type.in_(delivery_handover_types)
    ).subquery()

    stmt = select(VehicleHandover).join(
        subq, VehicleHandover.id == subq.c.id
    ).where(subq.c.row_num == 1)

    latest_handovers_with_drivers = db.session.execute(stmt).scalars().all()

    current_drivers_map = {
        record.vehicle_id: {
            'name': record.driver_employee.name,
            'email': record.driver_employee.email,
            'mobile': record.driver_employee.mobile,
            'phone': record.driver_employee.mobile,
            'national_id': record.driver_employee.national_id
        }
        for record in latest_handovers_with_drivers if record.driver_employee
    }

    return current_drivers_map


def get_all_current_drivers():
    delivery_handover_types = ['delivery', 'تسليم', 'handover']

    subq = select(
        VehicleHandover.id,
        func.row_number().over(
            partition_by=VehicleHandover.vehicle_id,
            order_by=VehicleHandover.handover_date.desc()
        ).label('row_num')
    ).where(
        VehicleHandover.handover_type.in_(delivery_handover_types)
    ).subquery()

    stmt = select(VehicleHandover).join(
        subq, VehicleHandover.id == subq.c.id
    ).where(subq.c.row_num == 1)

    latest_handovers = db.session.execute(stmt).scalars().all()
    return {record.vehicle_id: record.person_name for record in latest_handovers}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_image(image_path, max_size=1200, quality=85):
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            if img.mode != 'RGB':
                img = img.convert('RGB')

            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            img.save(image_path, 'JPEG', quality=quality, optimize=True)
            return True
    except Exception as error:
        current_app.logger.error(f"خطأ في ضغط الصورة: {str(error)}")
        return False
