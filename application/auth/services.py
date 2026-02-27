"""
خدمات المصادقة — منطق تسجيل الدخول والتحقق من كلمة المرور وجلسة المستخدم.
مشترك بين الويب (routes/auth) والجوال (presentation/api/mobile).
لا يتجاوز 400 سطر.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, Any

from core.extensions import db

logger = logging.getLogger(__name__)


def get_user_by_identifier(identifier: str) -> Optional[Any]:
    """
    جلب المستخدم بالبريد الإلكتروني أو اسم المستخدم.
    identifier: البريد الإلكتروني أو اسم المستخدم (للجوال والويب).
    """
    if not identifier or not str(identifier).strip():
        return None
    from models import User
    ident = str(identifier).strip()
    user = User.query.filter(
        (User.username == ident) | (User.email == ident)
    ).first()
    if not user:
        total_users = User.query.count()
        logger.warning(f"Login attempt: user not found for identifier '{ident}'. Total users in DB: {total_users}")
    return user


def verify_credentials(identifier: str, password: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    التحقق من بيانات الدخول.
    يُرجع (user, None) عند النجاح، أو (None, error_message) عند الفشل.
    error_message بالعربية لاستخدامه في flash أو JSON (مع الحفاظ على الخط إن وُجد).
    """
    user = get_user_by_identifier(identifier)
    if not user:
        return None, "اسم المستخدم أو كلمة المرور غير صحيحة"
    if not user.check_password(password):
        logger.warning(f"Login attempt: password mismatch for user id={user.id} email={user.email}")
        return None, "اسم المستخدم أو كلمة المرور غير صحيحة"
    if not getattr(user, "is_active", True):
        return None, "الحساب غير مفعّل"
    logger.info(f"Login successful for user id={user.id} email={user.email}")
    return user, None


def record_login(user: Any) -> None:
    """
    تسجيل آخر دخول للمستخدم (تحديث last_login والحفظ).
    يُستدعى بعد login_user في طبقة العرض.
    """
    user.last_login = datetime.utcnow()
    db.session.commit()
