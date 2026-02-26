"""
مساعدات مسارات المركبات — مشتركة بين routes/vehicles.py ووحدات العرض المستخرجة.
يُستورد منها: format_date_arabic, save_file, save_image, update_vehicle_state, check_vehicle_operation_restrictions.
"""
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from sqlalchemy import or_

# استيراد متأخر لتجنب التبعيات الدائرية عند تحميل routes.vehicles
def _get_db():
    from src.core.extensions import db
    return db

def _get_models():
    from models import (
        Vehicle, VehicleRental, VehicleWorkshop, VehicleHandover,
        OperationRequest, VehicleAccident, VehicleProject,
    )
    return (Vehicle, VehicleRental, VehicleWorkshop, VehicleHandover,
            OperationRequest, VehicleAccident, VehicleProject)


def format_date_arabic(date_obj):
    """تنسيق التاريخ باللغة العربية"""
    if date_obj is None:
        return ""
    months = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
        5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
        9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
    }
    return f"{date_obj.day} {months[date_obj.month]} {date_obj.year}"


def save_file(file, folder="vehicles"):
    """حفظ الملف (صورة أو PDF) في المجلد المحدد وإرجاع (المسار النسبي، نوع الملف)."""
    if not file or not getattr(file, "filename", None):
        return None, None
    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        upload_folder = os.path.join(current_app.static_folder, "uploads", folder)
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return None, None
        file_type = "pdf" if filename.lower().endswith(".pdf") else "image"
        return f"static/uploads/{folder}/{unique_filename}", file_type
    except Exception:
        return None, None


def save_image(file, folder="vehicles"):
    """توافق مع الكود القديم: إرجاع المسار فقط."""
    path, _ = save_file(file, folder)
    return path


def is_vehicle_operational(vehicle):
    """فحص إذا كانت السيارة قابلة للتشغيل أم خارج الخدمة."""
    return getattr(vehicle, "status", None) != "out_of_service"


def check_vehicle_operation_restrictions(vehicle):
    """فحص قيود التشغيل وإرجاع رسالة تحذير إذا كانت السيارة خارج الخدمة."""
    if not is_vehicle_operational(vehicle):
        return {
            "blocked": True,
            "message": f'❌ عذراً، السيارة "{vehicle.plate_number}" خارج الخدمة ولا يمكن تنفيذ أي عمليات عليها حالياً. يرجى تغيير حالة السيارة أولاً.',
            "status": "out_of_service",
        }
    return {"blocked": False}


def update_vehicle_state(vehicle_id):
    """
    الدالة المركزية لتحديد وتحديث الحالة النهائية للمركبة وسائقها.
    تعتمد على حالة OperationRequest المرتبط لتحديد السجلات الرسمية.
    """
    db = _get_db()
    (Vehicle, VehicleRental, VehicleWorkshop, VehicleHandover,
     OperationRequest, VehicleAccident, VehicleProject) = _get_models()
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            current_app.logger.warning("محاولة تحديث حالة لمركبة غير موجودة: ID=%s", vehicle_id)
            return
        if vehicle.status == "out_of_service":
            return
        active_accident = VehicleAccident.query.filter(
            VehicleAccident.vehicle_id == vehicle_id,
            VehicleAccident.accident_status != "مغلق",
        ).first()
        in_workshop = VehicleWorkshop.query.filter(
            VehicleWorkshop.vehicle_id == vehicle_id,
            VehicleWorkshop.exit_date.is_(None),
        ).first()
        is_critical_state = bool(active_accident or in_workshop)
        if active_accident:
            vehicle.status = "accident"
        elif in_workshop:
            vehicle.status = "in_workshop"
        active_rental = VehicleRental.query.filter_by(vehicle_id=vehicle_id, is_active=True).first()
        approved_handover_ids_subquery = db.session.query(OperationRequest.related_record_id).filter(
            OperationRequest.operation_type == "handover",
            OperationRequest.status == "approved",
            OperationRequest.vehicle_id == vehicle_id,
        ).subquery()
        all_handover_request_ids_subquery = db.session.query(OperationRequest.related_record_id).filter(
            OperationRequest.operation_type == "handover",
            OperationRequest.vehicle_id == vehicle_id,
        ).subquery()
        base_official_query = VehicleHandover.query.filter(
            VehicleHandover.vehicle_id == vehicle_id,
        ).filter(
            or_(
                VehicleHandover.id.in_(approved_handover_ids_subquery),
                ~VehicleHandover.id.in_(all_handover_request_ids_subquery),
            ),
        )
        latest_delivery = base_official_query.filter(
            VehicleHandover.handover_type.in_(["delivery", "تسليم"]),
        ).order_by(VehicleHandover.created_at.desc()).first()
        latest_return = base_official_query.filter(
            VehicleHandover.handover_type.in_(["return", "استلام", "receive"]),
        ).order_by(VehicleHandover.created_at.desc()).first()
        is_currently_handed_out = False
        if latest_delivery and (not latest_return or latest_delivery.created_at > latest_return.created_at):
            is_currently_handed_out = True
        if is_currently_handed_out:
            vehicle.driver_name = latest_delivery.person_name
            if not is_critical_state:
                vehicle.status = "rented" if active_rental else "in_project"
        else:
            vehicle.driver_name = None
            if not is_critical_state:
                vehicle.status = "rented" if active_rental else "available"
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("خطأ في دالة update_vehicle_state لـ vehicle_id %s: %s", vehicle_id, str(e))
