"""
طبقة التطبيق للمصادقة — خدمات مشتركة بين الويب والجوال.
"""
from .services import (
    get_user_by_identifier,
    verify_credentials,
    record_login,
)

__all__ = [
    "get_user_by_identifier",
    "verify_credentials",
    "record_login",
]
