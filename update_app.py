import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace logging config
logging_pattern = re.compile(r'# Set up structured logging \(JSON\).*?logger = logging\.getLogger\(__name__\)', re.DOTALL)
content = logging_pattern.sub(
    'from core.logging_config import init_logging\nlogger = init_logging()',
    content
)

# 2. Replace database config
db_config_pattern = re.compile(r'# Configure database connection with flexible support for different databases.*?app\.config\["SQLALCHEMY_ENGINE_OPTIONS"\]\["execution_options"\]\["isolation_level"\] = "READ COMMITTED"', re.DOTALL)
content = db_config_pattern.sub(
    'from core.database_config import init_db_config\ninit_db_config(app)',
    content
)

# 3. Replace error handlers
error_500_pattern = re.compile(r'@app\.errorhandler\(500\)\ndef handle_internal_error\(error\):\n    logger\.error\("Internal server error on %s", request\.path\)\n    traceback\.print_exc\(\)\n    return str\(error\), 500', re.DOTALL)
content = error_500_pattern.sub('', content)

error_413_pattern = re.compile(r'# معالج أخطاء الطلبات الكبيرة\n@app\.errorhandler\(413\)\ndef request_entity_too_large\(error\):.*?error_message=\'حجم الطلب كبير جداً\. يرجى تقليل حجم البيانات المرسلة\.\'\), 413', re.DOTALL)
content = error_413_pattern.sub('', content)

# Add init_error_handlers call after app creation
app_creation_pattern = re.compile(r'app = Flask\(__name__\)\napp\.secret_key = os\.environ\.get\("SESSION_SECRET", "employee_management_secret"\)\napp\.wsgi_app = ProxyFix\(app\.wsgi_app, x_proto=1, x_host=1\)  # needed for url_for to generate with https\ninit_rate_limiter\(app\)\nregister_api_v2_guard\(app\)')
content = app_creation_pattern.sub(
    'app = Flask(__name__)\napp.secret_key = os.environ.get("SESSION_SECRET", "employee_management_secret")\napp.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https\ninit_rate_limiter(app)\nregister_api_v2_guard(app)\n\nfrom core.error_handlers import init_error_handlers\ninit_error_handlers(app)',
    content
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py updated successfully.")
