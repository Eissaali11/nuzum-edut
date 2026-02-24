"""
╔════════════════════════════════════════════════════════════════════════════╗
║                   🚀 مرجع سريع لبنية المسارات الجديدة                    ║
║                    Quick Reference - Routes Organization                  ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ محتويات سريعة ────────────────────────────────────────────────────────┐
│ 1. الأقسام الـ 12 الرئيسية وأرقام المسارات
│ 2. أمثلة الاستيراد من كل قسم
│ 3. دوال مساعدة
│ 4. خريطة البحث السريع
└────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════
1️⃣ الأقسام الـ 12 الرئيسية - مرجع سريع
════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────┐
│ 🔐 core/
│ المسارات الأساسية
├─────────────────────────────────────┤
│ URL Prefix: /api/core/
│ Blueprints: auth_bp, users_bp
│ المسارات: ~15
│ الملفات: auth.py, users.py, dashboard.py
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.core import auth_bp, users_bp, core_blueprints
   for bp in core_blueprints:
       app.register_blueprint(bp)


┌─────────────────────────────────────┐
│ 👥 hr/
│ الموارد البشرية والموظفين
├─────────────────────────────────────┤
│ URL Prefix: /api/hr/
│ Blueprints: employees_bp, departments_bp
│ المسارات: ~25
│ الملفات: employees.py, departments.py, salaries.py
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.hr import hr_blueprints


┌─────────────────────────────────────┐
│ ✍️  attendance/
│ الحضور والإجازات والوقت
├─────────────────────────────────────┤
│ URL Prefix: /api/attendance/
│ Blueprints: mass_attendance_bp, leave_bp
│ المسارات: ~20
│ الملفات: 6 ملفات متخصصة
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.attendance import attendance_blueprints


┌─────────────────────────────────────┐
│ 📱 assets/
│ الأصول والجوالات والأجهزة
├─────────────────────────────────────┤
│ URL Prefix: /api/assets/
│ Blueprints: mobile_devices_bp, device_assignment_bp
│ المسارات: ~12
│ الملفات: mobile_devices.py, device_assignment.py
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.assets import assets_blueprints


┌─────────────────────────────────────┐
│ 📄 documents/
│ إدارة الوثائق والمستندات
├─────────────────────────────────────┤
│ URL Prefix: /api/documents/
│ Blueprints: documents_bp, documents_controller_bp
│ المسارات: ~8
│ الملفات: documents.py, documents_controller.py
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.documents import documents_blueprints


┌─────────────────────────────────────┐
│ 📋 requests/
│ الطلبات والشؤون الإدارية
├─────────────────────────────────────┤
│ URL Prefix: /api/requests/
│ Blueprints: employee_requests_bp
│ المسارات: ~16
│ الملفات: 3 ملفات (requests + controller + api)
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.requests import requests_blueprints


┌─────────────────────────────────────┐
│ 💰 accounting/
│ المحاسبة والفواتير والمالية
├─────────────────────────────────────┤
│ URL Prefix: /api/accounting/
│ Blueprints: accounting_bp, e_invoicing_bp
│ المسارات: ~20
│ الملفات: 5 ملفات متخصصة
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.accounting import accounting_blueprints


┌─────────────────────────────────────┐
│ 🔌 api/
│ واجهات API والخدمات الخارجية
├─────────────────────────────────────┤
│ URL Prefix: /api/
│ Blueprints: api_bp, api_external_bp
│ المسارات: ~30 🔴 الأكثر
│ الملفات: 7 ملفات متخصصة
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.api import api_blueprints


┌─────────────────────────────────────┐
│ 📧 communications/
│ الإخطارات والبريد الإلكتروني
├─────────────────────────────────────┤
│ URL Prefix: /api/notifications/
│ Blueprints: notifications_bp, email_queue_bp
│ المسارات: ~10
│ الملفات: notifications.py, email_queue.py
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.communications import communications_blueprints


┌─────────────────────────────────────┐
│ 🔗 integrations/
│ التكاملات مع الأنظمة الخارجية
├─────────────────────────────────────┤
│ URL Prefix: /api/integrations/
│ Blueprints: voicehub_bp, drive_bp, geofences_bp
│ المسارات: ~15
│ الملفات: 6 ملفات متخصصة
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.integrations import integrations_blueprints


┌─────────────────────────────────────┐
│ ⚙️  admin/
│ لوحات التحكم الإدارية
├─────────────────────────────────────┤
│ URL Prefix: /api/admin/
│ Blueprints: admin_dashboard_bp, payroll_bp
│ المسارات: ~18
│ الملفات: 3 ملفات متخصصة
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.admin import admin_blueprints


┌─────────────────────────────────────┐
│ 📊 analytics/
│ التقارير والتحليلات والبيانات
├─────────────────────────────────────┤
│ URL Prefix: /api/analytics/
│ Blueprints: analytics_bp, insights_bp, powerbi_bp
│ المسارات: ~25
│ الملفات: 7 ملفات + powerbi + reports
│ أنظمة: powerbi_dashboard/, reports_mgmt/
└─────────────────────────────────────┘

مثال الاستيراد:
   from routes.analytics import analytics_blueprints

════════════════════════════════════════════════════════════════════════════
2️⃣ أمثلة الاستيراد الشائعة
════════════════════════════════════════════════════════════════════════════

✅ الطريقة 1: استيراد جميع المسارات تلقائياً (الموصى به)
────────────────────────────────────────────────────────

from routes import register_routes

@app.before_first_request
def initialize():
    routes_count = register_routes(app)
    print(f"✅ تم تسجيل {routes_count} مسار")


✅ الطريقة 2: استيراد أقسام محددة
─────────────────────────────────────

from routes.core import core_blueprints
from routes.hr import hr_blueprints
from routes.analytics import analytics_blueprints

for bp in core_blueprints + hr_blueprints + analytics_blueprints:
    app.register_blueprint(bp)


✅ الطريقة 3: استيراد blueprint واحد
──────────────────────────────────────

from routes.operations import operations_bp
app.register_blueprint(operations_bp, url_prefix='/api/operations')


✅ الطريقة 4: استيراد انتقائي من قسم
──────────────────────────────────────

from routes.attendance import attendance_blueprints

# تسجيل فقط blueprints معينة
app.register_blueprint(attendance_blueprints[0])  # mass_attendance_bp
app.register_blueprint(attendance_blueprints[1])  # leave_management_bp


✅ الطريقة 5: الاستيراد من نظام متقدم
──────────────────────────────────────

from routes.operations import operations_bp
from routes.powerbi_dashboard import powerbi_bp
from routes.properties_mgmt import properties_bp

app.register_blueprint(operations_bp)


✅ الطريقة 6: في blueprint معقد - استيراد من قسم
──────────────────────────────────────────────────

def create_admin_panel():
    from routes.admin import admin_blueprints
    from routes.accounting import accounting_blueprints
    
    for bp in admin_blueprints + accounting_blueprints:
        # معالجة admin-specific
        pass

════════════════════════════════════════════════════════════════════════════
3️⃣ دوال مساعدة متاحة
════════════════════════════════════════════════════════════════════════════

من routes/__init__.py:

📌 get_all_blueprints()
   ├─ الغرض: جمع جميع blueprints من جميع الأقسام
   ├─ الإرجاع: قائمة بـ blueprints
   └─ مثال:
       blueprints = get_all_blueprints()
       for bp in blueprints:
           print(f"مسار: {bp.name}")


📌 register_routes(app)
   ├─ الغرض: تسجيل جميع المسارات تلقائياً
   ├─ المدخل: Flask app instance
   ├─ الإرجاع: عدد المسارات المسجلة
   └─ مثال:
       count = register_routes(app)
       app.logger.info(f"تم تسجيل {count} مسار")


📌 {section}_blueprints (في كل قسم)
   ├─ الغرض: قائمة blueprints البقسم
   ├─ الموقع: routes/{section}/__init__.py
   └─ مثال:
       from routes.core import core_blueprints
       for bp in core_blueprints:
           app.register_blueprint(bp)

════════════════════════════════════════════════════════════════════════════
4️⃣ خريطة البحث السريع
════════════════════════════════════════════════════════════════════════════

أبحث عن ملف متعلق بـ:

❓ المصادقة والتحقق من الهوية؟
   👉 routes/core/auth.py

❓ إدارة الموظفين؟
   👉 routes/hr/employees.py

❓ نظام الحضور؟
   👉 routes/attendance/ (6 ملفات)

❓ إدارة الهواتف الذكية؟
   👉 routes/assets/mobile_devices.py

❓ إدارة الوثائق؟
   👉 routes/documents/documents.py

❓ طلبات الموظفين؟
   👉 routes/requests/employee_requests.py

❓ الفواتير الإلكترونية؟
   👉 routes/accounting/e_invoicing.py

❓ واجهات API خارجية؟
   👉 routes/api/api_external.py

❓ نظام الإخطارات؟
   👉 routes/communications/notifications.py

❓ تكامل جوجل درايف؟
   👉 routes/integrations/google_drive_settings.py

❓ لوحات التحكم الإدارية؟
   👉 routes/admin/admin_dashboard.py

❓ التقارير والتحليلات؟
   👉 routes/analytics/ (7 ملفات)

❓ نظام العمليات المركب؟
   👉 routes/operations/ (7 ملفات متخصصة)

❓ لوحة Power BI؟
   👉 routes/powerbi_dashboard/ (4 ملفات)

════════════════════════════════════════════════════════════════════════════
5️⃣ ملفات الملفات والـ Helpers
════════════════════════════════════════════════════════════════════════════

كل نظام متقدم له ملف helpers:

routes/properties_mgmt/
   ├── properties_routes.py
   └── properties_helpers.py ← دوال مساعدة

routes/reports_mgmt/
   ├── reports_routes.py
   └── reports_helpers.py ← دوال مساعدة

routes/salaries_mgmt/
   ├── salaries_routes.py
   └── salaries_helpers.py ← دوال مساعدة

routes/sim_mgmt/
   ├── sim_routes.py
   └── sim_helpers.py ← دوال مساعدة

استيراد الدوال المساعدة:

from routes.operations.operations_helpers import format_operation_data
from routes.reports_mgmt.reports_helpers import generate_report_pdf

════════════════════════════════════════════════════════════════════════════
6️⃣ التحقق من المسارات
════════════════════════════════════════════════════════════════════════════

عرض جميع المسارات المسجلة:

python -c "
from app import app
for rule in app.url_map.iter_rules():
    print(f'{rule.rule} -> {rule.endpoint}')
"

أو في Flask shell:

flask shell
>>> from app import app
>>> [str(rule) for rule in app.url_map.iter_rules()]


عرض المسارات لقسم محدد:

python -c "
from app import app
from routes.core import core_blueprints
for rule in app.url_map.iter_rules():
    if 'core' in rule.endpoint:
        print(f'{rule.rule}')
"

════════════════════════════════════════════════════════════════════════════
7️⃣ معايير التسمية والاتساق
════════════════════════════════════════════════════════════════════════════

عند إضافة مسار جديد:

✅ الملف:
   - snake_case: my_feature.py
   - وضع في القسم المناسب: routes/{section}/

✅ Blueprint:
   - snake_case + _bp: my_feature_bp
   - إضافة في الملف: my_feature_bp = Blueprint(...)

✅ المسار (Route):
   - kebab-case: /api/section/feature-name
   - توثيق واضح: @bp.route('/feature-name', methods=['GET'])

✅ تحديث __init__.py:
   from .my_feature import my_feature_bp
   {section}_blueprints.append(my_feature_bp)

════════════════════════════════════════════════════════════════════════════
8️⃣ معالجة الأخطاء والتحذيرات
════════════════════════════════════════════════════════════════════════════

تحذير: المسار ليس في القسم الصحيح؟
   👉 تحقق من خريطة البحث السريع أعلاه

خطأ: ImportError عند الاستيراد؟
   👉 تأكد من وجود __init__.py في المجلد
   👉 تأكد من اسم blueprint في ملف {section}/__init__.py

مشكلة: مسار لا يعمل بعد التحديث؟
   👉 تحقق من الاستيرادات في app.py
   👉 تحقق من register_routes() واستدعاؤها

════════════════════════════════════════════════════════════════════════════
9️⃣ الإحصائيات السريعة
════════════════════════════════════════════════════════════════════════════

مجموع المسارات:       110+
أكثر قسم ملأ:        api (30 مسار)
أقل قسم ملأ:         documents (4 مسارات)
متوسط لكل قسم:       8-10 مسارات
أقسام رئيسية:        12 قسم
أنظمة متقدمة:        6 أنظمة
ملفات helpers:        4 ملفات
ملفات وrappers:       6 ملفات
ملفات في legacy:      16 ملف

════════════════════════════════════════════════════════════════════════════
🔟 الخطوات التالية
════════════════════════════════════════════════════════════════════════════

1️⃣ اختبر المسارات الحالية
   flask test

2️⃣ تحقق من الوثائق
   اقرأ ROUTES_ORGANIZATION_GUIDE.md

3️⃣ جرب إضافة مسار جديد
   أتبع معايير التسمية أعلاه

4️⃣ طبق الأفضليات
   استخدم register_routes() الموحدة

════════════════════════════════════════════════════════════════════════════
📚 موارد إضافية
════════════════════════════════════════════════════════════════════════════

📖 الملفات المهمة:
   - ROUTES_ORGANIZATION_GUIDE.md ← دليل شامل
   - ROUTES_ORGANIZATION_COMPLETE.md ← تقرير نهائي
   - routes/__init__.py ← مركز التوزيع الرئيسي

🔍 البحث السريع:
   grep -r "blueprint" routes/ ← جد جميع blueprints
   ls routes/*/  ← اعرض جميع الأقسام
   find routes/ -name "__init__.py" ← اعرض __init__.py

════════════════════════════════════════════════════════════════════════════
✨ الخلاصة
════════════════════════════════════════════════════════════════════════════

البنية الجديدة توفر:
✅ وضوح وتنظيم
✅ سهولة الصيانة
✅ سهولة التوسع
✅ توثيق شامل
✅ معايير موحدة

استخدم register_routes() للاستيراد الموحد!

════════════════════════════════════════════════════════════════════════════
© 2024 نُظم Nuzm - Quick Reference v1.0
════════════════════════════════════════════════════════════════════════════
"""
