import logging
import traceback
from flask import request, render_template, redirect, url_for, flash

logger = logging.getLogger(__name__)

def init_error_handlers(app):
    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error("Internal server error on %s", request.path)
        traceback.print_exc()
        return str(error), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """معالجة خطأ الطلب الكبير"""
        if request.endpoint and 'mobile' in request.endpoint:
            # للجوال: عرض رسالة خطأ مناسبة
            flash('حجم البيانات المرسلة كبير جداً. يرجى تقليل عدد الصور أو حجمها.', 'danger')
            return redirect(url_for('mobile.index'))
        else:
            # للويب: عرض صفحة خطأ
            return render_template('error.html',
                                 error_code=413,
                                 error_message='حجم الطلب كبير جداً. يرجى تقليل حجم البيانات المرسلة.'), 413
