"""
════════════════════════════════════════════════════════════════════════════
📂 مجلد المسارات - Routes Package Hub
════════════════════════════════════════════════════════════════════════════

نقطة المدخل المركزية لجميع مسارات (Routes) تطبيق نُظم الشامل.

📊 البنية التنظيمية:
════════════════════════════════════════════════════════════════════════════

12 قسم رئيسي:
├── 🔐 core          - مسارات أساسية (auth, users, dashboard)
├── 👥 hr            - الموارد البشرية (employees, departments)
├── ✍️  attendance   - الحضور والإجازات
├── 📱 assets        - الأصول والجوالات
├── 📄 documents     - إدارة الوثائق
├── 📋 requests      - الطلبات الإدارية
├── 💰 accounting    - المحاسبة والفواتير
├── 🔌 api           - واجهات API
├── 📧 communications- الإخطارات والبريد
├── 🔗 integrations  - التكاملات الخارجية
├── ⚙️  admin        - لوحات التحكم
└── 📊 analytics     - التقارير والتحليلات

6 أنظمة متقدمة (Advanced Packages):
├── operations       - العمليات المركبة (7 modules)
├── powerbi_dashboard- لوحة Power BI (4 modules)
├── properties_mgmt  - إدارة العقارات (+ helpers)
├── reports_mgmt     - إدارة التقارير (+ helpers)
├── salaries_mgmt    - إدارة الرواتب (+ helpers)
└── sim_mgmt         - إدارة بطاقات SIM (+ helpers)

أرشيف:
└── legacy           - ملفات قديمة وملفات احتياطية

════════════════════════════════════════════════════════════════════════════

📈 الإحصائيات:
- أقسام رئيسية: 12
- أنظمة متقدمة: 6
- ملفات منظمة: 54+ ملف
- مسارات API: 110+ مسار
- حجم الملفات المنظمة: ~200 كيلوبايت

════════════════════════════════════════════════════════════════════════════

🚀 طريقة الاستخدام من app.py:

```python
# استيراد الأقسام الرئيسية
from routes.core import core_blueprints
from routes.hr import hr_blueprints
from routes.attendance import attendance_blueprints
from routes.analytics import analytics_blueprints

# تسجيل المسارات
def register_blueprints(app):
    for bp in core_blueprints:
        app.register_blueprint(bp)
    for bp in hr_blueprints:
        app.register_blueprint(bp)
    # ... والمزيد
```

════════════════════════════════════════════════════════════════════════════

🎯 مبادئ الترتيب:
✅ التصنيف المنطقي حسب المسؤولية الوظيفية
✅ سهولة الملاحة والصيانة
✅ استقلالية الأقسام مع إمكانية التكامل
✅ تسمية واضحة وفهم برمجي سليم
✅ سهولة التوسع والإضافة

════════════════════════════════════════════════════════════════════════════

📝 ملاحظة مهمة:
هذا الملف بمثابة "مركز توزيع" للمسارات. كل قسم لديه __init__.py خاص به
يجمع blueprints المسارات المتعلقة به ليسهل استيرادها من نقطة مركزية.

════════════════════════════════════════════════════════════════════════════
"""


def get_all_blueprints():
    """جمع جميع blueprints من جميع الأقسام."""
    all_blueprints = []
    
    sections = [
        'core', 'hr', 'attendance', 'assets', 'documents',
        'requests', 'accounting', 'api', 'communications',
        'integrations', 'admin', 'analytics'
    ]
    
    for section in sections:
        try:
            module = __import__(f'routes.{section}', fromlist=[f'{section}_blueprints'])
            if hasattr(module, f'{section}_blueprints'):
                blueprints = getattr(module, f'{section}_blueprints')
                if isinstance(blueprints, list):
                    all_blueprints.extend(blueprints)
        except (ImportError, AttributeError) as e:
            print(f"⚠️ تحذير: عند تحميل {section}: {e}")
    
    # إضافة الأنظمة المتقدمة
    advanced_systems = [
        'operations',
        'powerbi_dashboard',
        'properties_mgmt',
        'reports_mgmt',
        'salaries_mgmt',
        'sim_mgmt'
    ]
    
    for system in advanced_systems:
        try:
            module = __import__(f'routes.{system}', fromlist=['*'])
            # البحث عن أي blueprint في النظام
            for attr_name in dir(module):
                if attr_name.endswith('_bp') or attr_name.endswith('_blueprint'):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, 'register'):  # تحقق من أنه blueprint
                        all_blueprints.append(attr)
        except ImportError as e:
            print(f"⚠️ تحذير: عند تحميل النظام {system}: {e}")
    
    return all_blueprints


def register_routes(app):
    """تسجيل جميع المسارات في التطبيق."""
    blueprints = get_all_blueprints()
    for bp in blueprints:
        try:
            if bp.name in app.blueprints:
                continue
            app.register_blueprint(bp)
            print(f"✅ تم تسجيل: {bp.name}")
        except Exception as e:
            print(f"❌ خطأ عند تسجيل {bp.name}: {e}")
    return len(blueprints)


__version__ = "2.0"
__author__ = "نُظم Nuzm System"
__all__ = [
    'get_all_blueprints',
    'register_routes',
    'core',
    'hr',
    'attendance',
    'assets',
    'documents',
    'requests',
    'accounting',
    'api',
    'communications',
    'integrations',
    'admin',
    'analytics',
    'operations',
    'powerbi_dashboard',
    'properties_mgmt',
    'reports_mgmt',
    'salaries_mgmt',
    'sim_mgmt',
    'legacy'
]
