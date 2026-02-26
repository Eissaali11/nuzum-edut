from markupsafe import Markup
from datetime import datetime
from src.utils.id_encoder import register_template_filters as register_id_encoder_filters

def init_filters(app):
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s:
            return Markup(s.replace('\n', '<br>'))
        return s

    @app.template_filter('format_date')
    def format_date_filter(date, format='%Y-%m-%d'):
        """
        فلتر آمن لتنسيق التواريخ مع التعامل مع القيم الفارغة
        """
        if date:
            return date.strftime(format)
        return ""

    @app.template_filter('display_date')
    def display_date_filter(date, format='%Y-%m-%d', default="غير محدد"):
        """
        عرض التاريخ بشكل منسق أو نص بديل إذا كان التاريخ فارغاً
        """
        if date:
            return date.strftime(format)
        return default

    @app.template_filter('days_remaining')
    def days_remaining_filter(date, from_date=None):
        """
        حساب عدد الأيام المتبقية من التاريخ المحدد حتى اليوم
        """
        if not date:
            return None

        if not from_date:
            from_date = datetime.now().date()
        elif hasattr(from_date, 'date'):
            from_date = from_date.date()

        if hasattr(date, 'date'):
            date = date.date()

        return (date - from_date).days

    @app.template_filter('bitwise_and')
    def bitwise_and_filter(value1, value2):
        """تنفيذ عملية bitwise AND بين قيمتين"""
        return value1 & value2

    @app.template_filter('check_module_access')
    def check_module_access_filter(user, module, permission=None):
        """
        مرشح للتحقق من صلاحيات المستخدم للوصول إلى وحدة معينة
        """
        from models import Permission
        from src.utils.user_helpers import check_module_access
        return check_module_access(user, module, permission or Permission.VIEW)

    # تسجيل فلاتر تشفير المعرفات للروابط الآمنة
    register_id_encoder_filters(app)
