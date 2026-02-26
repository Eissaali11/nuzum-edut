import os
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import request, jsonify, g

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:
    Limiter = None
    get_remote_address = None

_limiter = None


def init_rate_limiter(app):
    global _limiter
    if Limiter is None:
        app.logger.warning("Flask-Limiter not installed; rate limiting disabled")
        return None

    if _limiter is None:
        _limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["300 per hour"],
            storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        )
    _limiter.init_app(app)
    return _limiter


def rate_limit(limit_value: str):
    def passthrough(func):
        return func

    if _limiter is None:
        return passthrough
    return _limiter.limit(limit_value)


def _secret_key() -> str:
    return os.environ.get("SESSION_SECRET", "employee_management_secret")


def issue_api_v2_token(subject_type: str, subject_id: int, scopes=None, expires_hours: int = 24, extra=None) -> str:
    if scopes is None:
        scopes = ["api:v2:read"]
    if extra is None:
        extra = {}

    now = datetime.now(timezone.utc)
    payload = {
        "sub_type": subject_type,
        "sub_id": subject_id,
        "scopes": scopes,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
        "aud": "nuzm-api-v2",
    }
    payload.update(extra)
    return jwt.encode(payload, _secret_key(), algorithm="HS256")


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None
    return None


def _decode_token(token: str):
    return jwt.decode(token, _secret_key(), algorithms=["HS256"], options={"verify_aud": False})


def _token_has_scope(token_scopes, required_scopes) -> bool:
    if not required_scopes:
        return True
    token_scopes = set(token_scopes or [])
    if "api:v2:*" in token_scopes:
        return True
    for scope in required_scopes:
        if scope in token_scopes:
            return True
    return False


def validate_request_token(required_scopes=None, optional=False):
    token = _extract_bearer_token()

    if not token:
        if optional:
            return None, None
        return None, (jsonify({
            "success": False,
            "message": "Bearer token is required",
            "error": "TOKEN_REQUIRED",
        }), 401)

    try:
        claims = _decode_token(token)
    except jwt.ExpiredSignatureError:
        return None, (jsonify({
            "success": False,
            "message": "Token expired",
            "error": "TOKEN_EXPIRED",
        }), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({
            "success": False,
            "message": "Invalid token",
            "error": "INVALID_TOKEN",
        }), 401)

    if required_scopes and not _token_has_scope(claims.get("scopes", []), required_scopes):
        return None, (jsonify({
            "success": False,
            "message": "Insufficient token scope",
            "error": "INSUFFICIENT_SCOPE",
            "required_scopes": required_scopes,
        }), 403)

    g.api_v2_claims = claims
    return claims, None


def get_api_v2_claims():
    return getattr(g, "api_v2_claims", None)


def get_api_v2_actor():
    claims = get_api_v2_claims()
    if not claims:
        return None

    actor = getattr(g, "api_v2_actor", None)
    if actor is not None:
        return actor

    sub_type = claims.get("sub_type")
    sub_id = claims.get("sub_id")
    if not sub_id:
        return None

    try:
        if sub_type == "employee":
            from models import Employee
            actor = Employee.query.get(int(sub_id))
        else:
            from models import User
            actor = User.query.get(int(sub_id))
    except Exception:
        actor = None

    g.api_v2_actor = actor
    return actor


def v2_jwt_required(required_scopes=None, optional=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            claims, error = validate_request_token(required_scopes=required_scopes, optional=optional)
            if error:
                return error
            if claims is not None:
                g.api_v2_claims = claims
            return func(*args, **kwargs)

        return wrapper

    return decorator


def register_api_v2_guard(app):
    @app.before_request
    def _enforce_api_v2_guard():
        path = request.path or ""
        if not path.startswith("/api/v2/"):
            return None

        if path.endswith("/health") or path == "/api/v2/employee-requests/auth/login":
            return None

        method = request.method.upper()
        if method == "GET":
            scopes = ["api:v2:read"]
        else:
            scopes = ["api:v2:write"]

        if path.startswith("/api/v2/documents"):
            scopes.append("documents:read" if method == "GET" else "documents:write")
        elif path.startswith("/api/v2/attendance"):
            scopes.append("attendance:read" if method == "GET" else "attendance:write")
        elif path.startswith("/api/v2/employee-requests"):
            scopes.append("employee_requests:read" if method == "GET" else "employee_requests:write")
        elif path.startswith("/api/v2/safety-checks"):
            scopes.append("safety:read" if method == "GET" else "safety:write")

        _, error = validate_request_token(required_scopes=scopes, optional=False)
        if error:
            return error
        return None
