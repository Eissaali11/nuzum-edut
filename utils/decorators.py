from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user

# ملاحظة:
# لا نقوم باستيراد Module, UserRole من models هنا في أعلى الملف
# لتجنب مشكلة الاستيراد الدائري مع app.py و models.py.
# سيتم الاستيراد داخل الدوال عند الحاجة (lazy import).

def _resolve_module(module_arg):
    """
    Helper لتحويل اسم الوحدة (string) إلى Enum Module عند الحاجة.
    يدعم تمرير Module مباشرة أو اسمها كسلسلة نصية.
    """
    from models import Module  # استيراد متأخر

    if isinstance(module_arg, str):
        try:
            return Module[module_arg]
        except KeyError:
            # في حال لم يكن الاسم صالحاً، نعيده كما هو حتى يتعامل معه الكود الآخر
            return module_arg
    return module_arg


def module_access_required(module):
    """
    مصادقة للتحقق من أن المستخدم لديه الصلاحية للوصول إلى وحدة معينة.
    
    Args:
        module: الوحدة المطلوب التحقق من صلاحية الوصول إليها
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # استيراد متأخر لتجنب الاستيراد الدائري
            from models import UserRole

            resolved_module = _resolve_module(module)

            # التحقق من إذا كان المستخدم مسؤول (ADMIN)
            if current_user.role == UserRole.ADMIN:
                return f(*args, **kwargs)

            # التحقق من إذا كان للمستخدم صلاحية الوصول إلى الوحدة
            if not current_user.has_module_access(resolved_module):
                flash('ليس لديك صلاحية الوصول إلى هذه الصفحة', 'danger')
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(module, permission):
    """
    مصادقة للتحقق من أن المستخدم لديه صلاحية محددة على وحدة معينة.
    
    Args:
        module: الوحدة المطلوب التحقق من الصلاحية عليها
        permission: الصلاحية المطلوبة
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # استيراد متأخر لتجنب الاستيراد الدائري
            from models import UserRole

            resolved_module = _resolve_module(module)

            # التحقق من إذا كان المستخدم مسؤول (ADMIN)
            if current_user.role == UserRole.ADMIN:
                return f(*args, **kwargs)

            # التحقق من إذا كان للمستخدم صلاحية محددة على الوحدة
            if not current_user.has_permission(resolved_module, permission):
                flash('ليس لديك صلاحية كافية لتنفيذ هذا الإجراء', 'danger')
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator