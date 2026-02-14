"""
خدمة إدارة المركبات — تحديث بيانات المركبة (تعديل السجل).
تُستخدم من: مسار vehicles.edit (POST).
المعاملات تُمرَّر من طبقة العرض؛ لا استخدام لـ request أو Flask globals.
"""
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List

from werkzeug.utils import secure_filename

from core.extensions import db
from sqlalchemy import func

from modules.vehicles.domain.models import Vehicle, VehicleHandover, VehicleWorkshop
from models import (
    ExternalAuthorization,
    OperationNotification,
    OperationRequest,
    User,
    Employee,
    Department,
    VehicleExternalSafetyCheck,
    VehicleMaintenance,
    employee_departments,
)

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


def build_vehicle_operations_context(
    current_user: Any,
    vehicle_filter: str = "",
    operation_type: str = "",
    date_from: str = "",
    date_to: str = "",
    employee_filter: str = "",
    department_filter: str = "",
) -> Dict[str, Any]:
    """
    بناء سياق عمليات المركبات لصفحة العرض.
    يعكس نفس منطق routes/vehicle_operations.py دون تغيير.
    """
    operations: List[Dict[str, Any]] = []

    # فلترة العمليات حسب القسم المحدد للمستخدم الحالي
    department_filter_ids = None
    if getattr(current_user, "assigned_department_id", None):
        dept_employee_ids = db.session.query(Employee.id).join(
            employee_departments
        ).join(Department).filter(
            Department.id == current_user.assigned_department_id
        ).all()
        department_filter_ids = [emp.id for emp in dept_employee_ids]

    # جلب عمليات التسليم والاستلام
    if not operation_type or operation_type == 'handover':
        handover_query = VehicleHandover.query.join(Vehicle, VehicleHandover.vehicle_id == Vehicle.id)

        if department_filter_ids:
            handover_query = handover_query.filter(VehicleHandover.employee_id.in_(department_filter_ids))

        if vehicle_filter:
            handover_query = handover_query.filter(Vehicle.plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                handover_query = handover_query.filter(VehicleHandover.handover_date >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                handover_query = handover_query.filter(VehicleHandover.handover_date <= date_to_obj)
            except ValueError:
                pass

        if employee_filter:
            handover_query = handover_query.filter(VehicleHandover.person_name.ilike(f'%{employee_filter}%'))

        handovers = handover_query.all()

        for handover in handovers:
            operations.append({
                'id': handover.id,
                'type': 'handover',
                'type_ar': 'تسليم/استلام',
                'vehicle_plate': handover.vehicle.plate_number if handover.vehicle else 'غير محدد',
                'operation_date': handover.handover_date,
                'person_name': handover.person_name,
                'details': f"{handover.handover_type or 'تسليم/استلام'} - الوقود: {handover.fuel_level or 'غير محدد'}",
                'status': 'مكتمل',
                'department': handover.driver_employee.departments[0].name if handover.driver_employee and handover.driver_employee.departments else 'غير محدد'
            })

    # جلب عمليات الورشة
    if not operation_type or operation_type == 'workshop':
        workshop_query = VehicleWorkshop.query.join(Vehicle, VehicleWorkshop.vehicle_id == Vehicle.id)

        if vehicle_filter:
            workshop_query = workshop_query.filter(Vehicle.plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                workshop_query = workshop_query.filter(VehicleWorkshop.entry_date >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                workshop_query = workshop_query.filter(VehicleWorkshop.entry_date <= date_to_obj)
            except ValueError:
                pass

        if department_filter_ids:
            dept_vehicle_ids = db.session.query(VehicleHandover.vehicle_id).filter(
                VehicleHandover.handover_type == 'delivery',
                VehicleHandover.employee_id.in_(department_filter_ids)
            ).distinct().all()
            dept_vehicle_ids = [v.vehicle_id for v in dept_vehicle_ids]
            if dept_vehicle_ids:
                workshop_query = workshop_query.filter(Vehicle.id.in_(dept_vehicle_ids))
            else:
                workshop_query = workshop_query.filter(Vehicle.id == -1)

        workshops = workshop_query.all()

        for workshop in workshops:
            operations.append({
                'id': workshop.id,
                'type': 'workshop',
                'type_ar': 'ورشة',
                'vehicle_plate': workshop.vehicle.plate_number if workshop.vehicle else 'غير محدد',
                'operation_date': workshop.entry_date,
                'person_name': workshop.technician_name or 'غير محدد',
                'details': f"الورشة: {workshop.workshop_name or 'غير محدد'} - الحالة: {workshop.repair_status or 'غير محدد'}",
                'status': workshop.repair_status or 'غير محدد',
                'department': 'الصيانة'
            })

    # جلب فحوصات السلامة الخارجية
    if not operation_type or operation_type == 'safety_check':
        safety_query = VehicleExternalSafetyCheck.query

        if vehicle_filter:
            safety_query = safety_query.filter(VehicleExternalSafetyCheck.vehicle_plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                safety_query = safety_query.filter(func.date(VehicleExternalSafetyCheck.created_at) >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                safety_query = safety_query.filter(func.date(VehicleExternalSafetyCheck.created_at) <= date_to_obj)
            except ValueError:
                pass

        if employee_filter:
            safety_query = safety_query.filter(VehicleExternalSafetyCheck.driver_name.ilike(f'%{employee_filter}%'))

        if department_filter_ids:
            dept_vehicle_plates = db.session.query(Vehicle.plate_number).join(
                VehicleHandover, Vehicle.id == VehicleHandover.vehicle_id
            ).filter(
                VehicleHandover.handover_type == 'delivery',
                VehicleHandover.employee_id.in_(department_filter_ids)
            ).distinct().all()
            dept_vehicle_plates = [v.plate_number for v in dept_vehicle_plates]
            if dept_vehicle_plates:
                safety_query = safety_query.filter(VehicleExternalSafetyCheck.vehicle_plate_number.in_(dept_vehicle_plates))
            else:
                safety_query = safety_query.filter(VehicleExternalSafetyCheck.id == -1)

        safety_checks = safety_query.all()

        for safety in safety_checks:
            status_ar = {
                'pending': 'قيد المراجعة',
                'approved': 'معتمد',
                'rejected': 'مرفوض'
            }.get(safety.approval_status, 'غير محدد')

            operations.append({
                'id': safety.id,
                'type': 'safety_check',
                'type_ar': 'فحص سلامة',
                'vehicle_plate': safety.vehicle_plate_number,
                'operation_date': safety.created_at.date() if safety.created_at else None,
                'person_name': safety.driver_name or 'غير محدد',
                'details': f"فحص سلامة خارجي - السائق: {safety.driver_name or 'غير محدد'}",
                'status': status_ar,
                'department': safety.driver_department or 'غير محدد'
            })

    # جلب عمليات الصيانة (إذا كانت موجودة)
    if not operation_type or operation_type == 'maintenance':
        try:
            maintenance_query = VehicleMaintenance.query.join(Vehicle, VehicleMaintenance.vehicle_id == Vehicle.id)

            if vehicle_filter:
                maintenance_query = maintenance_query.filter(Vehicle.plate_number.ilike(f'%{vehicle_filter}%'))

            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    maintenance_query = maintenance_query.filter(VehicleMaintenance.date >= date_from_obj)
                except ValueError:
                    pass

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                    maintenance_query = maintenance_query.filter(VehicleMaintenance.date <= date_to_obj)
                except ValueError:
                    pass

            maintenances = maintenance_query.all()

            for maintenance in maintenances:
                operations.append({
                    'id': maintenance.id,
                    'type': 'maintenance',
                    'type_ar': 'صيانة',
                    'vehicle_plate': maintenance.vehicle.plate_number if maintenance.vehicle else 'غير محدد',
                    'operation_date': maintenance.date,
                    'person_name': maintenance.technician or 'غير محدد',
                    'details': f"صيانة: {maintenance.type or 'غير محدد'} - التكلفة: {maintenance.cost or 0} ريال",
                    'status': maintenance.status or 'مكتمل',
                    'department': 'الصيانة'
                })
        except Exception:
            pass

    if department_filter:
        operations = [op for op in operations if department_filter.lower() in op['department'].lower()]

    def get_sort_date(operation: Dict[str, Any]):
        date_val = operation['operation_date']
        if date_val is None:
            return datetime.min.date()
        if isinstance(date_val, datetime):
            return date_val.date()
        return date_val

    operations.sort(key=get_sort_date, reverse=True)

    vehicles = Vehicle.query.all()
    departments = Department.query.all()

    total_operations = len(operations)
    handover_count = len([op for op in operations if op['type'] == 'handover'])
    workshop_count = len([op for op in operations if op['type'] == 'workshop'])
    safety_count = len([op for op in operations if op['type'] == 'safety_check'])
    maintenance_count = len([op for op in operations if op['type'] == 'maintenance'])

    return {
        'operations': operations,
        'vehicles': vehicles,
        'departments': departments,
        'vehicle_filter': vehicle_filter,
        'operation_type': operation_type,
        'date_from': date_from,
        'date_to': date_to,
        'employee_filter': employee_filter,
        'department_filter': department_filter,
        'total_operations': total_operations,
        'handover_count': handover_count,
        'workshop_count': workshop_count,
        'safety_count': safety_count,
        'maintenance_count': maintenance_count,
    }


def build_vehicle_operations_export_operations(
    vehicle_filter: str = "",
    operation_type: str = "",
    date_from: str = "",
    date_to: str = "",
    employee_filter: str = "",
    department_filter: str = "",
) -> List[Dict[str, Any]]:
    """بناء بيانات عمليات المركبات للتصدير (Excel)."""
    operations: List[Dict[str, Any]] = []

    if not operation_type or operation_type == 'handover':
        handover_query = VehicleHandover.query.join(Vehicle, VehicleHandover.vehicle_id == Vehicle.id)

        if vehicle_filter:
            handover_query = handover_query.filter(Vehicle.plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                handover_query = handover_query.filter(func.date(VehicleHandover.handover_date) >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                handover_query = handover_query.filter(func.date(VehicleHandover.handover_date) <= date_to_obj)
            except ValueError:
                pass

        handovers = handover_query.all()

        for handover in handovers:
            operations.append({
                'vehicle_plate': handover.vehicle.plate_number if handover.vehicle else 'غير محدد',
                'type_ar': 'تسليم/استلام',
                'operation_date': handover.handover_date,
                'person_name': handover.person_name,
                'details': f"{handover.handover_type or 'تسليم/استلام'} - الوقود: {handover.fuel_level or 'غير محدد'}",
                'status': 'مكتمل',
                'department': handover.driver_employee.departments[0].name if handover.driver_employee and handover.driver_employee.departments else 'غير محدد'
            })

    if not operation_type or operation_type == 'workshop':
        workshop_query = VehicleWorkshop.query.join(Vehicle, VehicleWorkshop.vehicle_id == Vehicle.id)

        if vehicle_filter:
            workshop_query = workshop_query.filter(Vehicle.plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                workshop_query = workshop_query.filter(VehicleWorkshop.entry_date >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                workshop_query = workshop_query.filter(VehicleWorkshop.entry_date <= date_to_obj)
            except ValueError:
                pass

        workshops = workshop_query.all()

        for workshop in workshops:
            operations.append({
                'vehicle_plate': workshop.vehicle.plate_number if workshop.vehicle else 'غير محدد',
                'type_ar': 'ورشة',
                'operation_date': workshop.entry_date,
                'person_name': workshop.technician_name or 'غير محدد',
                'details': f"الورشة: {workshop.workshop_name or 'غير محدد'} - الحالة: {workshop.repair_status or 'غير محدد'}",
                'status': workshop.repair_status or 'غير محدد',
                'department': 'الصيانة'
            })

    if not operation_type or operation_type == 'safety_check':
        safety_query = VehicleExternalSafetyCheck.query

        if vehicle_filter:
            safety_query = safety_query.filter(VehicleExternalSafetyCheck.vehicle_plate_number.ilike(f'%{vehicle_filter}%'))

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                safety_query = safety_query.filter(func.date(VehicleExternalSafetyCheck.created_at) >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                safety_query = safety_query.filter(func.date(VehicleExternalSafetyCheck.created_at) <= date_to_obj)
            except ValueError:
                pass

        if employee_filter:
            safety_query = safety_query.filter(VehicleExternalSafetyCheck.driver_name.ilike(f'%{employee_filter}%'))

        safety_checks = safety_query.all()

        for safety in safety_checks:
            status_ar = {
                'pending': 'قيد المراجعة',
                'approved': 'معتمد',
                'rejected': 'مرفوض'
            }.get(safety.approval_status, 'غير محدد')

            operations.append({
                'vehicle_plate': safety.vehicle_plate_number,
                'type_ar': 'فحص سلامة',
                'operation_date': safety.created_at.date() if safety.created_at else None,
                'person_name': safety.driver_name or 'غير محدد',
                'details': f"فحص سلامة خارجي - السائق: {safety.driver_name or 'غير محدد'}",
                'status': status_ar,
                'department': safety.driver_department or 'غير محدد'
            })

    if department_filter:
        operations = [op for op in operations if department_filter.lower() in op['department'].lower()]

    def get_sort_date(operation: Dict[str, Any]):
        date_val = operation['operation_date']
        if date_val is None:
            return datetime.min.date()
        if isinstance(date_val, datetime):
            return date_val.date()
        return date_val

    operations.sort(key=get_sort_date, reverse=True)

    return operations
