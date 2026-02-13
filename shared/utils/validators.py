"""
محققون مشتركون (مدخلات، بريد، نصوص).
لا يتجاوز 400 سطر.
"""
import re
from typing import Optional


def is_valid_email(value: Optional[str]) -> bool:
    """التحقق من صيغة البريد الإلكتروني."""
    if not value or not value.strip():
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, value.strip()))


def normalize_string(value: Optional[str], max_len: Optional[int] = None) -> Optional[str]:
    """تطبيع نص: قص المسافات الزائدة واختياريًا الحد بالطول."""
    if value is None:
        return None
    s = value.strip()
    if max_len is not None and len(s) > max_len:
        s = s[:max_len]
    return s if s else None


def is_non_empty_string(value: Optional[str], min_len: int = 1) -> bool:
    """التحقق من أن القيمة نص غير فارغ."""
    if value is None:
        return False
    s = value.strip()
    return len(s) >= min_len
