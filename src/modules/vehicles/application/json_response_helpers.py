"""
مساعدات استجابات JSON للموبايل — توحيد صيغ الاستجابات ومعالجة الأخطاء.
تُستخدم من: presentation/api/mobile/vehicle_routes.py
"""
from typing import Any, Dict, Optional, Tuple
from flask import jsonify, Response


def json_success(
    data: Any = None,
    message: str = "",
    status_code: int = 200
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON للنجاح.
    
    Args:
        data: البيانات المراد إرجاعها (dict, list, أو أي كائن قابل للتحويل).
        message: رسالة نجاح اختيارية.
        status_code: رمز الحالة HTTP (افتراضي 200).
    
    Returns:
        Tuple: (jsonify response, status_code)
    
    Examples:
        >>> return json_success({'vehicle': vehicle_dict}, "تم الحفظ بنجاح")
        >>> return json_success(vehicles_list)
    """
    response = {
        'success': True,
        'data': data,
    }
    if message:
        response['message'] = message
    
    return jsonify(response), status_code


def json_error(
    message: str,
    status_code: int = 400,
    errors: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON للخطأ.
    
    Args:
        message: رسالة الخطأ الرئيسية.
        status_code: رمز الحالة HTTP (افتراضي 400 Bad Request).
        errors: تفاصيل إضافية عن الأخطاء (اختياري).
    
    Returns:
        Tuple: (jsonify response, status_code)
    
    Examples:
        >>> return json_error("رقم اللوحة مطلوب", 400)
        >>> return json_error("المركبة غير موجودة", 404)
        >>> return json_error("خطأ في الخادم", 500, {'details': str(e)})
    """
    response = {
        'success': False,
        'message': message,
    }
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code


def json_created(
    data: Any = None,
    message: str = "تم الإنشاء بنجاح",
    resource_id: Optional[int] = None,
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON لعملية إنشاء ناجحة (201 Created).
    
    Args:
        data: البيانات المُنشأة.
        message: رسالة نجاح.
        resource_id: معرف المورد المُنشأ (اختياري).
    
    Returns:
        Tuple: (jsonify response, 201)
    """
    response = {
        'success': True,
        'message': message,
        'data': data,
    }
    if resource_id is not None:
        response['id'] = resource_id
    
    return jsonify(response), 201


def json_not_found(
    message: str = "المورد غير موجود",
    resource_type: str = "",
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON للمورد غير الموجود (404 Not Found).
    
    Args:
        message: رسالة الخطأ.
        resource_type: نوع المورد (مثل: "vehicle", "handover").
    
    Returns:
        Tuple: (jsonify response, 404)
    """
    if resource_type:
        message = f"{resource_type}: {message}"
    
    return json_error(message, 404)


def json_bad_request(
    message: str = "طلب غير صالح",
    errors: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON لطلب غير صالح (400 Bad Request).
    
    Args:
        message: رسالة الخطأ.
        errors: تفاصيل الأخطاء.
    
    Returns:
        Tuple: (jsonify response, 400)
    """
    return json_error(message, 400, errors)


def json_server_error(
    message: str = "حدث خطأ في الخادم",
    details: Optional[str] = None,
) -> Tuple[Response, int]:
    """
    إرجاع استجابة JSON لخطأ في الخادم (500 Internal Server Error).
    
    Args:
        message: رسالة الخطأ.
        details: تفاصيل الخطأ (للتسجيل أو التطوير).
    
    Returns:
        Tuple: (jsonify response, 500)
    """
    errors = {'details': details} if details else None
    return json_error(message, 500, errors)


def handle_service_result(
    result: Tuple[bool, str, Any],
    success_message: Optional[str] = None,
    error_status_code: int = 400,
) -> Tuple[Response, int]:
    """
    معالجة نتيجة من service layer وتحويلها إلى استجابة JSON.
    
    Args:
        result: Tuple من service method (success, message, data/id).
        success_message: رسالة نجاح بديلة (اختياري).
        error_status_code: رمز الحالة عند الفشل (افتراضي 400).
    
    Returns:
        Tuple: استجابة JSON مناسبة.
    
    Example:
        >>> success, msg, vehicle_id = create_vehicle_record(...)
        >>> return handle_service_result((success, msg, vehicle_id))
    """
    success, message, data = result
    
    if success:
        return json_success(
            data={'id': data} if isinstance(data, int) else data,
            message=success_message or message,
        )
    else:
        return json_error(message, error_status_code)


def serialize_vehicle(vehicle: Any) -> Dict[str, Any]:
    """
    تحويل كائن Vehicle إلى قاموس للـ JSON.
    
    Args:
        vehicle: كائن Vehicle من SQLAlchemy.
    
    Returns:
        Dict: تمثيل JSON-safe للمركبة.
    """
    return {
        'id': vehicle.id,
        'plate_number': vehicle.plate_number,
        'make': vehicle.make,
        'model': vehicle.model,
        'year': vehicle.year,
        'color': vehicle.color,
        'status': vehicle.status,
        'driver_name': vehicle.driver_name,
        'type_of_car': vehicle.type_of_car,
        'project': vehicle.project,
        'owned_by': vehicle.owned_by,
        'region': vehicle.region,
        'notes': vehicle.notes,
        'created_at': vehicle.created_at.isoformat() if vehicle.created_at else None,
        'updated_at': vehicle.updated_at.isoformat() if vehicle.updated_at else None,
    }


def serialize_vehicle_list(vehicles: list) -> list:
    """
    تحويل قائمة من المركبات إلى قوائم JSON.
    
    Args:
        vehicles: قائمة من كائنات Vehicle.
    
    Returns:
        list: قائمة من القواميس.
    """
    return [serialize_vehicle(v) for v in vehicles]
