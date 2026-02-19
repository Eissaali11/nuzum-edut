"""Authorization management service for external vehicle authorizations."""

import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from werkzeug.utils import secure_filename

from core.extensions import db
from modules.vehicles.domain.models import Vehicle, ExternalAuthorization
from domain.employees.models import Employee, Department
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions


ALLOWED_AUTH_FILE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
MAX_AUTH_FILE_SIZE_BYTES = 10 * 1024 * 1024


def _parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    if not date_str:
        return None
    return datetime.strptime(date_str, '%Y-%m-%d').date()


def _validate_dates(form_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    try:
        start_date = _parse_date(form_data.get('start_date'))
        end_date = _parse_date(form_data.get('end_date'))
    except (ValueError, TypeError):
        return False, 'تاريخ غير صالح. يرجى إدخال تاريخ بصيغة صحيحة.'

    if start_date and end_date and end_date < start_date:
        return False, 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية.'

    return True, None


def _get_file_size(file) -> Optional[int]:
    if not file:
        return None
    if getattr(file, 'content_length', None):
        return file.content_length
    try:
        pos = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(pos)
        return size
    except Exception:
        return None


def _validate_attachment(file) -> Tuple[bool, Optional[str]]:
    if not file or not file.filename:
        return True, None

    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    if ext not in ALLOWED_AUTH_FILE_EXTENSIONS:
        return False, 'نوع الملف غير مدعوم. الرجاء رفع PDF أو صورة أو Word.'

    size = _get_file_size(file)
    if size and size > MAX_AUTH_FILE_SIZE_BYTES:
        return False, 'حجم الملف كبير جداً. الحد الأقصى 10 MB.'

    return True, None


def _save_authorization_file(file, upload_dir: str, store_prefix: str) -> str:
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"

    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    return f"{store_prefix}/{filename}"


def get_external_authorization_view_context(vehicle_id: int, auth_id: int) -> Optional[Dict[str, Any]]:
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None

    authorization = ExternalAuthorization.query.get(auth_id)
    if not authorization:
        return None

    return {
        'vehicle': vehicle,
        'authorization': authorization,
    }


def get_external_authorization_form_context(vehicle_id: int) -> Optional[Dict[str, Any]]:
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None

    employees = Employee.query.all()
    departments = Department.query.all()

    return {
        'vehicle': vehicle,
        'employees': employees,
        'departments': departments,
    }


def get_external_authorization_edit_context(vehicle_id: int, auth_id: int) -> Optional[Dict[str, Any]]:
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return None

    authorization = ExternalAuthorization.query.get(auth_id)
    if not authorization:
        return None

    employees = Employee.query.all()
    departments = Department.query.all()

    return {
        'vehicle': vehicle,
        'authorization': authorization,
        'employees': employees,
        'departments': departments,
    }


def create_external_authorization_record(
    vehicle_id: int,
    form_data: Dict[str, Any],
    file,
    static_folder: str,
) -> Tuple[bool, str, Optional[int]]:
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False, 'المركبة غير موجودة', None

        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            return False, restrictions['message'], None

        valid_dates, date_error = _validate_dates(form_data)
        if not valid_dates:
            return False, date_error, None

        valid_file, file_error = _validate_attachment(file)
        if not valid_file:
            return False, file_error, None

        authorization = ExternalAuthorization(
            vehicle_id=vehicle_id,
            employee_id=form_data.get('employee_id'),
            authorization_type=form_data.get('authorization_type'),
            project_name=form_data.get('project_name'),
            city=form_data.get('city'),
            external_link=form_data.get('external_link'),
            notes=form_data.get('notes'),
            status='pending',
        )

        if file and file.filename:
            upload_dir = os.path.join('static', 'uploads', 'authorizations')
            authorization.file_path = _save_authorization_file(
                file,
                upload_dir,
                'static/uploads/authorizations',
            )

        db.session.add(authorization)
        db.session.commit()

        return True, 'تم إنشاء التفويض بنجاح', authorization.id

    except Exception as exc:
        db.session.rollback()
        return False, f'خطأ في إنشاء التفويض: {str(exc)}', None


def update_external_authorization_record(
    auth_id: int,
    form_data: Dict[str, Any],
    file,
    static_folder: str,
) -> Tuple[bool, str, Optional[int]]:
    try:
        authorization = ExternalAuthorization.query.get(auth_id)
        if not authorization:
            return False, 'التفويض غير موجود', None

        valid_dates, date_error = _validate_dates(form_data)
        if not valid_dates:
            return False, date_error, authorization.vehicle_id

        valid_file, file_error = _validate_attachment(file)
        if not valid_file:
            return False, file_error, authorization.vehicle_id

        authorization.employee_id = form_data.get('employee_id')
        authorization.project_name = form_data.get('project_name')
        authorization.authorization_type = form_data.get('authorization_type')
        authorization.city = form_data.get('city')
        authorization.external_link = form_data.get('form_link')
        authorization.notes = form_data.get('notes')

        if file and file.filename:
            upload_dir = os.path.join(static_folder, 'uploads', 'authorizations')
            authorization.file_path = _save_authorization_file(
                file,
                upload_dir,
                'uploads/authorizations',
            )

        db.session.commit()

        return True, 'تم تحديث التفويض بنجاح', authorization.vehicle_id

    except Exception as exc:
        db.session.rollback()
        return False, f'حدث خطأ أثناء تحديث التفويض: {str(exc)}', None


def delete_external_authorization_record(auth_id: int) -> Tuple[bool, str, Optional[int]]:
    try:
        authorization = ExternalAuthorization.query.get(auth_id)
        if not authorization:
            return False, 'التفويض غير موجود', None

        vehicle_id = authorization.vehicle_id
        db.session.delete(authorization)
        db.session.commit()

        return True, 'تم حذف التفويض بنجاح', vehicle_id

    except Exception as exc:
        db.session.rollback()
        return False, f'حدث خطأ أثناء حذف التفويض: {str(exc)}', None


def approve_external_authorization_record(vehicle_id: int, auth_id: int) -> Tuple[bool, str, Optional[int]]:
    try:
        authorization = ExternalAuthorization.query.filter_by(
            id=auth_id,
            vehicle_id=vehicle_id,
        ).first()

        if not authorization:
            return False, 'التفويض غير موجود', vehicle_id

        authorization.status = 'approved'
        authorization.updated_at = datetime.utcnow()
        db.session.commit()

        return True, 'تم الموافقة على التفويض بنجاح', vehicle_id

    except Exception as exc:
        db.session.rollback()
        return False, f'خطأ في موافقة التفويض: {str(exc)}', vehicle_id


def reject_external_authorization_record(vehicle_id: int, auth_id: int) -> Tuple[bool, str, Optional[int]]:
    try:
        authorization = ExternalAuthorization.query.filter_by(
            id=auth_id,
            vehicle_id=vehicle_id,
        ).first()

        if not authorization:
            return False, 'التفويض غير موجود', vehicle_id

        authorization.status = 'rejected'
        authorization.updated_at = datetime.utcnow()
        db.session.commit()

        return True, 'تم رفض التفويض', vehicle_id

    except Exception as exc:
        db.session.rollback()
        return False, f'خطأ في رفض التفويض: {str(exc)}', vehicle_id
