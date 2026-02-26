from flask import Blueprint, redirect, url_for, render_template, send_from_directory, abort, Response
import os
from src.utils.storage_helper import download_image

core_system_bp = Blueprint('core_system', __name__)

# إضافة route مختصر للتوافق مع الروابط القديمة
@core_system_bp.route('/login')
def login_redirect():
    """إعادة توجيه من /login إلى /auth/login للتوافق"""
    return redirect(url_for('auth.login'))

@core_system_bp.route('/leave/manager')
def legacy_leave_manager_redirect():
    """توافق مع الروابط القديمة: /leave/manager -> /leaves/manager"""
    return redirect(url_for('leaves.manager_dashboard'))

@core_system_bp.route('/leave/balances')
def legacy_leave_balances_redirect():
    """توافق مع الروابط القديمة: /leave/balances -> /leaves/balances"""
    return redirect(url_for('leaves.leave_balances'))

@core_system_bp.route('/leave/employee')
def legacy_leave_employee_redirect():
    """توافق مع الروابط القديمة: /leave/employee -> /leaves/employee"""
    return redirect(url_for('leaves.employee_view'))

@core_system_bp.route('/payroll_management/dashboard')
@core_system_bp.route('/payroll-management/dashboard')
def legacy_payroll_dashboard_redirect():
    """توافق مع الروابط القديمة: payroll_management -> /payroll/dashboard"""
    return redirect(url_for('payroll.dashboard'))

# Google Search Console verification route
@core_system_bp.route('/googleab59b7c3bfbdd81d.html')
def google_verification():
    """عرض ملف التحقق من Google Search Console"""
    return Response('google-site-verification: googleab59b7c3bfbdd81d.html', mimetype='text/html')

@core_system_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # البحث أولاً في uploads
    file_path = os.path.join("uploads", filename)
    if os.path.exists(file_path):
        dir_parts = filename.split("/")
        if len(dir_parts) > 1:
            subdir = "/".join(dir_parts[:-1])
            file_name = dir_parts[-1]
            return send_from_directory(f"uploads/{subdir}", file_name)
        else:
            return send_from_directory("uploads", filename)

    # البحث في static/uploads كنسخة احتياطية
    static_file_path = os.path.join("static", "uploads", filename)
    if os.path.exists(static_file_path):
        dir_parts = filename.split("/")
        if len(dir_parts) > 1:
            subdir = "/".join(dir_parts[:-1])
            file_name = dir_parts[-1]
            return send_from_directory(f"static/uploads/{subdir}", file_name)
        else:
            return send_from_directory("static/uploads", filename)

    # البحث في Object Storage
    image_data = download_image(filename)
    if image_data:
        ext = filename.lower().rsplit('.', 1)[-1]
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'webp': 'image/webp', 'svg': 'image/svg+xml'
        }
        content_type = content_types.get(ext, 'image/jpeg')
        return Response(image_data, mimetype=content_type)

    # في حالة عدم وجود الصورة، إرجاع صورة بديلة
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return send_from_directory('static/images', 'image-not-found.svg')

    abort(404)

@core_system_bp.route('/static/uploads/<path:filename>')
def static_uploaded_file(filename):
    # البحث في static/uploads
    file_path = os.path.join('static', 'uploads', filename)
    if os.path.exists(file_path):
        dir_parts = filename.split('/')
        if len(dir_parts) > 1:
            subdir = '/'.join(dir_parts[:-1])
            file_name = dir_parts[-1]
            return send_from_directory(f'static/uploads/{subdir}', file_name)
        else:
            return send_from_directory('static/uploads', filename)

    # البحث في Object Storage
    image_data = download_image(filename)
    if image_data:
        ext = filename.lower().rsplit('.', 1)[-1]
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'webp': 'image/webp', 'svg': 'image/svg+xml'
        }
        content_type = content_types.get(ext, 'image/jpeg')
        return Response(image_data, mimetype=content_type)

    # في حالة عدم وجود الصورة، إرجاع صورة بديلة
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return send_from_directory('static/images', 'image-not-found.svg')
    
    abort(404)

# ================== صفحات المعلومات الثابتة ==================

@core_system_bp.route('/about')
def about():
    """صفحة من نحن - لتوضيح طبيعة النظام لمحركات البحث"""
    return render_template('about.html')

@core_system_bp.route('/privacy')
def privacy():
    """صفحة سياسة الخصوصية - لتوضيح استخدام البيانات"""
    return render_template('privacy.html')

@core_system_bp.route('/contact')
def contact():
    """صفحة اتصل بنا - معلومات الشركة"""
    return render_template('contact.html')

# ================== نهاية صفحات المعلومات الثابتة ==================
