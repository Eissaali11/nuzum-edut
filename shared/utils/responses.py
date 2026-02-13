"""
ردود JSON موحدة — ضمان ثبات الردود (Enterprise).
لا يتجاوز 400 سطر.
"""
from flask import jsonify
from typing import Any, Optional, Dict


def _body(
    success: bool,
    data: Optional[Any] = None,
    message: Optional[str] = None,
    code: Optional[str] = None,
    errors: Optional[list] = None,
    meta: Optional[Dict] = None,
) -> dict:
    out = {"success": success}
    if data is not None:
        out["data"] = data
    if message is not None:
        out["message"] = message
    if code is not None:
        out["code"] = code
    if errors is not None:
        out["errors"] = errors
    if meta is not None:
        out["meta"] = meta
    return out


def json_success(
    data: Any = None,
    message: Optional[str] = None,
    status: int = 200,
    meta: Optional[Dict] = None,
):
    """رد نجاح موحد."""
    body = _body(success=True, data=data, message=message, meta=meta)
    return jsonify(body), status


def json_error(
    message: str,
    code: Optional[str] = None,
    errors: Optional[list] = None,
    status: int = 400,
):
    """رد خطأ موحد."""
    body = _body(success=False, message=message, code=code, errors=errors)
    return jsonify(body), status


def json_created(data: Any = None, message: Optional[str] = None):
    """رد إنشاء (201)."""
    return json_success(data=data, message=message or "تم الإنشاء", status=201)


def json_not_found(message: str = "المورد غير موجود"):
    """رد 404."""
    return json_error(message=message, status=404)


def json_unauthorized(message: str = "غير مصرح"):
    """رد 401."""
    return json_error(message=message, status=401)


def json_forbidden(message: str = "ممنوع الوصول"):
    """رد 403."""
    return json_error(message=message, status=403)
