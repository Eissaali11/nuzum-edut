"""Google login route for mobile blueprint."""

from flask import redirect, url_for


def register_google_routes(mobile_bp):
    @mobile_bp.route('/login/google')
    def google_login():
        """تسجيل الدخول باستخدام Google للنسخة المحمولة"""
        return redirect(url_for('auth.google_login', next=url_for('mobile.index')))
