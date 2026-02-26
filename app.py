import os
import sys
import json
import logging
import sqlite3
import traceback
import shutil
import importlib.util
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime, timezone

from flask import Flask, session, redirect, url_for, render_template, request, g, current_app
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate  # أضف هذا الاستيراد في الأعلى
from flask_compress import Compress  # Gzip compression

# استيراد مكتبة dotenv لقراءة ملف .env
from dotenv import load_dotenv
load_dotenv()  # تحميل المتغيرات البيئية من ملف .env

# عند تشغيل الملف مباشرة باستخدام `python app.py` يكون اسم الموديول `__main__`
# بينما يقوم models.py بالاستيراد باستخدام `from core.extensions import db`
# السطر التالي يضمن أن اسم الموديول `app` يشير إلى نفس الكائن لتفادي
# مشكلة الاستيراد الدائري الجزئي (partially initialized module).
if __name__ == "__main__":
    app_pkg_spec = importlib.util.find_spec("app")
    if app_pkg_spec is None:
        sys.modules.setdefault("app", sys.modules[__name__])


# app.py
from whatsapp_client import WhatsAppWrapper
from core.api_v2_security import init_rate_limiter, register_api_v2_guard
# ... استيراد مكتبات أخرى ...

from core.logging_config import init_logging
logger = init_logging()

# إنشاء كائن واتساب واحد عند بدء تشغيل التطبيق
# سيقوم الكلاس تلقائياً بقراءة المتغيرات من ملف .env
# محمي بـ try-except لتجنب الأخطاء إذا لم تكن المتغيرات موجودة
whatsapp_service = None
try:
    whatsapp_service = WhatsAppWrapper()
    logger.info("WhatsApp service initialized successfully")
except (ValueError, Exception) as e:
    logger.warning(f"WhatsApp service not initialized: {e}")
    logger.info("You can set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env to enable WhatsApp features")

# ... بقية كود التطبيق الخاص بك ...


# في ملف manage.py أو app.py


# إعدادات اللغة العربية
ARABIC_CONFIG = {
    'language': 'Arabic',
    'delete_harakat': True,
    'delete_tatweel': False,
    'support_zwj': True,
    'support_ligatures': True
}

# استيراد مكتبة SQLAlchemy للتعامل مع MySQL
import pymysql
pymysql.install_as_MySQLdb()  # استخدام PyMySQL كبديل لـ MySQLdb

# استخدام db من core.extensions لتفادي الاستيراد الدائري مع models
from core.extensions import db

# Import database backup blueprint (moved outside app_context for proper registration)
from routes.database_backup import database_backup_bp
from routes.documents_controller import documents_refactored_bp
from routes.api_documents_v2 import api_documents_v2_bp

# Initialize Flask-Login
login_manager = LoginManager()




# Initialize CSRF Protection
csrf = CSRFProtect()

# Create the Flask application
app = Flask(__name__)
_secret = os.environ.get("SESSION_SECRET")
if not _secret:
    raise RuntimeError("CRITICAL: SESSION_SECRET environment variable is not set. Application cannot start without it.")
app.secret_key = _secret
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https
init_rate_limiter(app)
register_api_v2_guard(app)

from core.error_handlers import init_error_handlers
init_error_handlers(app)




# Prefer module templates over global templates
vehicles_templates_path = os.path.join(
    os.path.dirname(__file__),
    "modules",
    "vehicles",
    "presentation",
    "templates",
)
employees_templates_path = os.path.join(
    os.path.dirname(__file__),
    "modules",
    "employees",
    "templates",
)
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(vehicles_templates_path),
    FileSystemLoader(employees_templates_path),
    app.jinja_loader,
])

# إعفاء بعض المسارات من حماية CSRF
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # تعطيل التحقق التلقائي من CSRF

from core.database_config import init_db_config
init_db_config(app)

# Provide default values for uploads and other configurations
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB - لدعم رفع عدد كبير من الصور
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'warning'

# التعامل بشكل مخصص مع المسارات المحمولة عند عدم تسجيل الدخول
@login_manager.unauthorized_handler
def unauthorized_handler():
    if request.path.startswith('/mobile'):
        # إعادة توجيه المستخدم إلى صفحة تسجيل الدخول المحمولة
        return redirect(url_for('mobile.login', next=request.path))
    # استخدام المسار الافتراضي لتسجيل الدخول
    return redirect(url_for('auth.login', next=request.path))

# Initialize CSRF Protection
csrf.init_app(app)

# Initialize Gzip Compression
Compress(app)

# Initialize Extensions & Utilities
from core.jinja_filters import init_filters
from core.context_processors import init_context_processors
from core.scheduler import init_scheduler

init_filters(app)
init_context_processors(app, csrf)
init_scheduler(app)


# تكوين Gzip Compression
app.config['COMPRESS_LEVEL'] = 6  # مستوى الضغط (1-9، 6 متوازن)
app.config['COMPRESS_MIN_SIZE'] = 1024  # ضغط الملفات > 1KB
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'text/xml',
    'text/plain',
    'text/javascript',
    'application/json',
    'application/javascript'
]

# ... بعد تعريف db = SQLAlchemy(app)
migrate = Migrate(app, db)

# إعداد Firebase
app.config['FIREBASE_API_KEY'] = os.environ.get('FIREBASE_API_KEY')
app.config['FIREBASE_PROJECT_ID'] = os.environ.get('FIREBASE_PROJECT_ID')
app.config['FIREBASE_APP_ID'] = os.environ.get('FIREBASE_APP_ID')

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))



# مسار الجذر الرئيسي للتطبيق مع توجيه تلقائي حسب نوع الجهاز
@app.route('/')
def root():
    from flask import request
    from models import Module, UserRole 

    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_devices = ['android', 'iphone', 'ipad', 'mobile']

    # التحقق مما إذا كان الطلب يتضمن معلمة m=1 للوصول المباشر إلى نسخة الجوال
    mobile_param = request.args.get('m', '0')

    # إذا كان المستخدم يستخدم جهازاً محمولاً أو طلب نسخة الجوال صراحةً
    if any(device in user_agent for device in mobile_devices) or mobile_param == '1':
        if current_user.is_authenticated:
            return redirect(url_for('mobile.index'))
        else:
            return redirect(url_for('mobile.login'))

    # إذا كان المستخدم يستخدم جهاز كمبيوتر
    if current_user.is_authenticated:
        # التحقق من صلاحيات المستخدم للوصول إلى لوحة التحكم
        if current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.DASHBOARD):
            return redirect(url_for('dashboard.index'))

        # توجيه المستخدم إلى أول وحدة مصرح له بالوصول إليها
        if current_user.has_module_access(Module.EMPLOYEES):
            return redirect(url_for('employees.index'))
        elif current_user.has_module_access(Module.DEPARTMENTS):
            return redirect(url_for('departments.index'))
        elif current_user.has_module_access(Module.ATTENDANCE):
            return redirect(url_for('attendance.index'))
        elif current_user.has_module_access(Module.SALARIES):
            return redirect(url_for('salaries.index'))
        elif current_user.has_module_access(Module.DOCUMENTS):
            return redirect(url_for('documents.index'))
        elif current_user.has_module_access(Module.VEHICLES):
            return redirect(url_for('vehicles.index'))
        elif current_user.has_module_access(Module.REPORTS):
            return redirect(url_for('reports.index'))
        elif current_user.has_module_access(Module.FEES):
            return redirect(url_for('fees_costs.index'))
        elif current_user.has_module_access(Module.USERS):
            return redirect(url_for('users.index'))
        else:
            # إذا لم يكن له أي صلاحية، عرض الصفحة المقيدة
            return render_template('restricted.html')
    else:
        return redirect(url_for('auth.login'))







# تعطيل استخدام WeasyPrint مؤقتاً
WEASYPRINT_ENABLED = False

# Register blueprints for different modules
with app.app_context():
    # Import models before creating tables
    import models  # noqa: F401
    import models_accounting  # noqa: F401

    # Register all blueprints
    from routes.blueprint_registry import register_all_blueprints
    register_all_blueprints(app, csrf)
    



    @app.route('/static/uploads/<path:filename>')
    def static_uploaded_file(filename):
        from flask import send_from_directory, abort, Response
        from werkzeug.security import safe_join
        from utils.storage_helper import download_image
        import os

        uploads_root = app.config.get("UPLOAD_FOLDER", os.path.join(app.root_path, "static", "uploads"))

        safe_path = safe_join(uploads_root, filename)
        if safe_path is None:
            abort(404)

        resolved = os.path.realpath(safe_path)
        if not resolved.startswith(os.path.realpath(uploads_root) + os.sep):
            abort(404)

        if os.path.isfile(resolved):
            return send_from_directory(os.path.dirname(resolved), os.path.basename(resolved))

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

        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 'image-not-found.svg')

        abort(404)

    # إضافة دوال مساعدة لقوالب Jinja
    from utils.user_helpers import get_role_display_name, get_module_display_name, format_permissions, check_module_access
    
    # تسجيل فلاتر تشفير المعرفات للروابط الآمنة
    from utils.id_encoder import register_template_filters
    register_template_filters(app)

    # إضافة مرشح bitwise_and لاستخدامه في قوالب Jinja2
    @app.template_filter('bitwise_and')
    def bitwise_and_filter(value1, value2):
        """تنفيذ عملية bitwise AND بين قيمتين"""
        return value1 & value2

    # إضافة مرشح للتحقق من صلاحيات المستخدم
    @app.template_filter('check_module_access')
    def check_module_access_filter(user, module, permission=None):
        """
        مرشح للتحقق من صلاحيات المستخدم للوصول إلى وحدة معينة

        :param user: كائن المستخدم
        :param module: الوحدة المطلوب التحقق منها
        :param permission: الصلاحية المطلوبة (اختياري)
        :return: True إذا كان المستخدم لديه الصلاحية، False غير ذلك
        """
        from models import Permission
        return check_module_access(user, module, permission or Permission.VIEW)

    @app.context_processor
    def inject_global_template_vars():
        from models import Module, UserRole, Permission
        return {
            'get_role_display_name': get_role_display_name,
            'get_module_display_name': get_module_display_name,
            'format_permissions': format_permissions,
            'Module': Module,
            'UserRole': UserRole,
            'Permission': Permission
        }

    # ملاحظة: تم دمج هذا الكود مع مسار الجذر الرئيسي

    # Create database tables if they don't exist
    logger.info("Creating database tables...")
    try:
        db.create_all()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.info(f"Database tables already exist: {str(e)}")

# Register database backup blueprint OUTSIDE app_context to avoid Flask reloader issues
app.register_blueprint(database_backup_bp, url_prefix='/backup')
logger.info("Database backup blueprint registered successfully at /backup")

@app.before_request
def before_request():
    # تعيين اللغة الافتراضية للعربية
    g.language = 'ar'
    g.rtl = True
    g.arabic_config = ARABIC_CONFIG


@app.after_request
def after_request(response):
    return response








# في ملف manage.py أو app.py

from models import User, UserRole # استيراد النماذج اللازمة
import click

@app.cli.command("make-all-admins")
def make_all_users_admins_command():
    """
    يقوم بتحويل دور كل المستخدمين المسجلين في النظام إلى مدير (ADMIN).
    """
    try:
        # 1. جلب كل المستخدمين من قاعدة البيانات
        users_to_update = User.query.all()

        if not users_to_update:
            print("لا يوجد مستخدمين في قاعدة البيانات لتحديثهم.")
            return

        count = 0
        # 2. المرور على كل مستخدم وتغيير دوره
        for user in users_to_update:
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                count += 1

        # 3. حفظ كل التغييرات في قاعدة البيانات دفعة واحدة
        db.session.commit()

        print(f"نجاح! تم تحديث دور {count} مستخدم إلى 'admin'.")
        print(f"إجمالي عدد المستخدمين الآن: {len(users_to_update)}.")

    except Exception as e:
        db.session.rollback()
        print(f"حدث خطأ أثناء تحديث الأدوار: {e}")
        print("تم التراجع عن كل التغييرات.")
    """
    يقوم بتحويل دور كل المستخدمين المسجلين في النظام إلى مدير (ADMIN).
    """
    try:
        # 1. جلب كل المستخدمين من قاعدة البيانات
        users_to_update = User.query.all()

        if not users_to_update:
            print("لا يوجد مستخدمين في قاعدة البيانات لتحديثهم.")
            return

        count = 0
        # 2. المرور على كل مستخدم وتغيير دوره
        for user in users_to_update:
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                count += 1

        # 3. حفظ كل التغييرات في قاعدة البيانات دفعة واحدة
        db.session.commit()

        print(f"نجاح! تم تحديث دور {count} مستخدم إلى 'admin'.")
        print(f"إجمالي عدد المستخدمين الآن: {len(users_to_update)}.")

    except Exception as e:
        db.session.rollback()
        print(f"حدث خطأ أثناء تحديث الأدوار: {e}")
        print("تم التراجع عن كل التغييرات.")







# تشغيل خادم Flask عند تنفيذ الملف مباشرة
if __name__ == "__main__":
    default_port = 5000
    run_port = int(os.environ.get("APP_PORT", os.environ.get("PORT", default_port)))
    app.run(
        host="0.0.0.0",
        port=run_port,
        debug=os.environ.get("FLASK_DEBUG", "False").lower() == "true",
        threaded=os.environ.get("APP_THREADED", "true").lower() == "true",
    )
