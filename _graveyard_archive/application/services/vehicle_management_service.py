"""
خدمة إدارة المركبات — تحديث بيانات المركبة (تعديل السجل).
تُستخدم من: مسار vehicles.edit (POST).
المعاملات تُمرَّر من طبقة العرض؛ لا استخدام لـ request أو Flask globals.
"""
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from werkzeug.utils import secure_filename

from core.extensions import db
from modules.vehicles.domain.models import Vehicle
from models import ExternalAuthorization, OperationNotification, OperationRequest, User

from utils.vehicle_helpers import log_audit, allowed_file


def _safe_str(v: Any) -> str:
    """إرجاع قيمة آمنة كنص للتعامل مع form.data (قد يكون None أو غير نص)."""
    if v is None:
        return ""
    return str(v).strip()


def update_vehicle_record(
    vehicle_id: int,
    form_data: Dict[str, Any],
    files: Optional[Dict[str, Any]] = None,
    upload_base_path: Optional[str] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    يحدّث سجل المركبة بناءً على بيانات النموذج ورفع الملفات (إن وُجدت).

    Args:
        vehicle_id: معرف المركبة.
        form_data: قاموس حقول النموذج (مثل form.data بعد validate_on_submit):
            plate_number, make, model, year, color, status, notes,
            driver_name, project, owned_by, region, type_of_car.
        files: قاموس ملفات مرفوعة (مثل request.files)؛ اختياري.
        upload_base_path: المسار الأساسي لحفظ الملفات (مثل current_app.static_folder).
            إن وُجد، وحقل license_image في files، يتم حفظ الملف باستخدام secure_filename.

    Returns:
        (success, message, vehicle_id):
        - success: True إذا تم التحديث بنجاح، False عند فشل التحقق أو الاستثناء.
        - message: رسالة للمستخدم (للـ flash).
        - vehicle_id: معرف المركبة عند النجاح، None عند الفشل.
    """
    files = files or {}
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, "المركبة غير موجودة.", None

    plate_number = _safe_str(form_data.get("plate_number"))
    if not plate_number:
        return False, "رقم اللوحة مطلوب.", None

    existing = Vehicle.query.filter_by(plate_number=plate_number).first()
    if existing and existing.id != vehicle_id:
        return False, "يوجد سيارة أخرى مسجلة بنفس رقم اللوحة!", None

    try:
        vehicle.plate_number = plate_number
        vehicle.make = _safe_str(form_data.get("make"))
        vehicle.model = _safe_str(form_data.get("model"))
        try:
            y = form_data.get("year")
            vehicle.year = int(y) if y is not None else vehicle.year
        except (TypeError, ValueError):
            pass
        vehicle.color = _safe_str(form_data.get("color"))
        vehicle.status = _safe_str(form_data.get("status")) or vehicle.status
        vehicle.driver_name = _safe_str(form_data.get("driver_name")) or None
        vehicle.project = _safe_str(form_data.get("project")) or None
        vehicle.owned_by = _safe_str(form_data.get("owned_by")) or None
        vehicle.region = _safe_str(form_data.get("region")) or None
        vehicle.notes = _safe_str(form_data.get("notes")) or None
        vehicle.type_of_car = _safe_str(form_data.get("type_of_car")) or None
        vehicle.updated_at = datetime.utcnow()

        if upload_base_path:
            upload_dir = os.path.join(upload_base_path, "uploads", "vehicles")
            if "license_image" in files and files["license_image"] and getattr(files["license_image"], "filename", None):
                f = files["license_image"]
                if allowed_file(f.filename):
                    filename = secure_filename(f.filename)
                    if filename:
                        os.makedirs(upload_dir, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_name = f"license_{vehicle.plate_number}_{timestamp}_{filename}"
                        filepath = os.path.join(upload_dir, safe_name)
                        f.save(filepath)
                        vehicle.license_image = safe_name

        db.session.commit()
        log_audit(
            "update",
            "vehicle",
            vehicle.id,
            f"تم تعديل بيانات السيارة: {vehicle.plate_number}",
        )
        return True, "تم تعديل بيانات السيارة بنجاح!", vehicle.id
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء الحفظ: {str(e)}", None


def create_vehicle_record(
    form_data: Dict[str, Any],
    files: Optional[Dict[str, Any]] = None,
    upload_base_path: Optional[str] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    إنشاء سجل مركبة جديد. يتحقق من عدم تكرار رقم اللوحة، ينشئ المركبة،
    يربط المستخدمين المخولين، ويحفظ صورة الرخصة إن وُجدت.

    Args:
        form_data: قاموس حقول النموذج (plate_number, make, model, year, color, status,
            notes, driver_name, type_of_car, owned_by, region، واختياري authorized_users قائمة معرفات).
        files: قاموس ملفات مرفوعة (مثل request.files)؛ اختياري.
        upload_base_path: المسار الأساسي لحفظ الملفات؛ إن وُجد ورفعت صورة رخصة تُحفظ بـ secure_filename.

    Returns:
        (success, message, vehicle_id):
        - عند تكرار رقم اللوحة: (False, "رقم اللوحة مسجل مسبقاً في النظام", None).
        - عند النجاح: (True, رسالة نجاح, vehicle_id).
        - عند استثناء: (False, رسالة الخطأ, None).
    """
    files = files or {}
    plate_number = _safe_str(form_data.get("plate_number"))
    if not plate_number:
        return False, "رقم اللوحة مطلوب.", None

    if Vehicle.query.filter_by(plate_number=plate_number).first():
        return False, "رقم اللوحة مسجل مسبقاً في النظام", None

    try:
        year_val = form_data.get("year")
        try:
            year_int = int(year_val) if year_val is not None else 0
        except (TypeError, ValueError):
            year_int = 0

        vehicle = Vehicle(
            plate_number=plate_number,
            make=_safe_str(form_data.get("make")),
            model=_safe_str(form_data.get("model")),
            year=year_int,
            color=_safe_str(form_data.get("color")),
            status=_safe_str(form_data.get("status")) or "available",
            driver_name=_safe_str(form_data.get("driver_name")) or None,
            notes=_safe_str(form_data.get("notes")) or None,
            type_of_car=_safe_str(form_data.get("type_of_car")) or None,
            owned_by=_safe_str(form_data.get("owned_by")) or None,
            region=_safe_str(form_data.get("region")) or None,
        )
        db.session.add(vehicle)
        db.session.flush()

        authorized_user_ids = form_data.get("authorized_users")
        if authorized_user_ids:
            if isinstance(authorized_user_ids, (list, tuple)):
                ids = [int(x) for x in authorized_user_ids if x is not None and str(x).strip().isdigit()]
            else:
                ids = []
            if ids:
                users = User.query.filter(User.id.in_(ids)).all()
                for u in users:
                    vehicle.authorized_users.append(u)

        if upload_base_path:
            upload_dir = os.path.join(upload_base_path, "uploads", "vehicles")
            if "license_image" in files and files["license_image"] and getattr(files["license_image"], "filename", None):
                f = files["license_image"]
                if f.filename and allowed_file(f.filename):
                    filename = secure_filename(f.filename)
                    if filename:
                        os.makedirs(upload_dir, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_name = f"license_{vehicle.plate_number}_{timestamp}_{filename}"
                        filepath = os.path.join(upload_dir, safe_name)
                        f.save(filepath)
                        vehicle.license_image = safe_name

        db.session.commit()
        user_names = [u.name or u.username or u.email for u in vehicle.authorized_users]
        log_audit(
            "create",
            "vehicle",
            vehicle.id,
            f"تمت إضافة سيارة جديدة: {vehicle.plate_number}. المستخدمون المخولون: {', '.join(user_names) if user_names else 'لا يوجد'}",
        )
        return True, f"تمت إضافة السيارة بنجاح! المستخدمون المخولون: {len(vehicle.authorized_users)}", vehicle.id
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء الحفظ: {str(e)}", None


def delete_vehicle_record(
    vehicle_id: int,
    upload_base_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    حذف سجل المركبة والسجلات المرتبطة، مع حذف ملف صورة الرخصة من القرص إن وُجد.

    Args:
        vehicle_id: معرف المركبة.
        upload_base_path: المسار الأساسي للمرفقات (مثل current_app.static_folder).
            إن وُجد ومركبة لديها license_image، يُحذف الملف من uploads/vehicles/.

    Returns:
        (success, message) للاستخدام في flash والتحويل.
    """
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return False, "المركبة غير موجودة."

    plate_number = vehicle.plate_number
    license_filename = getattr(vehicle, "license_image", None)

    try:
        if upload_base_path and license_filename:
            upload_dir = os.path.join(upload_base_path, "uploads", "vehicles")
            file_path = os.path.join(upload_dir, license_filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        operation_requests = OperationRequest.query.filter_by(vehicle_id=vehicle_id).all()
        for op in operation_requests:
            for notif in OperationNotification.query.filter_by(operation_request_id=op.id).all():
                db.session.delete(notif)
            db.session.delete(op)
        for auth in ExternalAuthorization.query.filter_by(vehicle_id=vehicle_id).all():
            db.session.delete(auth)
        db.session.delete(vehicle)
        db.session.commit()
        log_audit("delete", "vehicle", vehicle_id, f"تم حذف السيارة: {plate_number}")
        return True, "تم حذف السيارة ومعلوماتها بنجاح!"
    except Exception as e:
        db.session.rollback()
        return False, f"حدث خطأ أثناء حذف السيارة: {str(e)}"
