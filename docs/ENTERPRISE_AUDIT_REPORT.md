# تقرير التحليل المعماري للنظام (Enterprise Audit Report)

**المُعدّ بصفة:** Senior Software Architect  
**الهدف:** التحضير لإعادة بناء النظام بمعايير Enterprise Grade  
**تاريخ التحليل:** 2025

---

## 1. تقييم تضخم الملفات (File Bloat Audit)

### 1.1 الملفات التي تتجاوز المعايير القياسية

| الملف | عدد الأسطر | المعيار المقترح | التصنيف |
|-------|------------|-----------------|---------|
| `routes/mobile.py` | **7,427** | 300–500 | حرج |
| `routes/vehicles.py` | **6,724** | 300–500 | حرج |
| `routes/mobile_backup.py` | 5,909 | — | ملف احتياطي ضخم |
| `routes/vehicles_backup.py` | 5,610 | — | ملف احتياطي ضخم |
| `routes/vehicles_backup2.py` | 5,629 | — | ملف احتياطي ضخم |
| `routes/attendance.py` | **4,562** | 300–500 | حرج |
| `routes/api_employee_requests.py` | **3,403** | 300–500 | حرج |
| `routes/employees.py` | **3,058** | 300–500 | حرج |
| `models.py` | **2,964** | 200–400 لكل نطاق | حرج |
| `utils/excel.py` | **3,140** | 300–500 | حرج |
| `routes/external_safety.py` | 2,549 | 300–500 | عالي |
| `routes/documents.py` | 2,315 | 300–500 | عالي |
| `routes/operations.py` | 2,378 | 300–500 | عالي |
| `routes/reports.py` | 2,177 | 300–500 | عالي |
| `routes/salaries.py` | 1,889 | 300–500 | عالي |
| `routes/properties.py` | 1,844 | 300–500 | عالي |
| `routes/powerbi_dashboard.py` | 1,842 | 300–500 | عالي |
| `routes/geofences.py` | 1,544 | 300–500 | عالي |
| `utils/fpdf_arabic_report.py` | 1,252 | 300–500 | عالي |
| `app.py` | 804 | 150–250 | متوسط |

### 1.2 لماذا يسبب التضخم انهياراً في الأداء وتداخلاً في التصميم؟

- **أداء IDE والـ Refactoring:** ملفات بأكثر من 5,000 سطر تبطئ التحليل الثابت والتنقل والبحث، وتزيد احتمال تعارضات الدمج (merge conflicts).
- **مسؤولية واحدة (SRP):** ملف واحد يجمع عشرات الـ endpoints ومنطق واجهة وتصدير PDF/Excel واستعلامات ثقيلة؛ أي تغيير صغير يتطلب فهم كتلة ضخمة.
- **اختبار الوحدة:** صعب عزل دوال قابلة للاختبار دون استيراد سلسلة طويلة من التبعيات.
- **تحميل الذاكرة:** تحميل موديول واحد (مثل `vehicles.py`) يسحب عشرات الاستيرادات (models, utils, forms) مما يزيد زمن بدء التشغيل واستهلاك الذاكرة.
- **تداخل المنطق:** في نفس الملف يختلط: عرض القوائم، إنشاء/تعديل السجلات، تصدير PDF/Excel، استدعاء واتساب، رفع ملفات، وتحقق صلاحيات؛ مما يزيد الـ coupling ويصعّب إعادة الاستخدام.

---

## 2. تحليل تداخل المسؤوليات (Coupling Analysis)

### 2.1 خلط منطق قاعدة البيانات مع الـ Routes

- **الـ Routes تستدعي مباشرة:** `Model.query.filter_by(...).all()` و `db.session.add/commit` وبناء استعلامات معقدة (`sqlalchemy.func`, `or_`, `and_`, `joinedload`).
- **مثال من `routes/vehicles.py`:** دوال مثل `update_vehicle_driver` تحتوي على منطق استعلام وتسلسل (delivery → employee → driver_name) داخل الـ route؛ الأفضل نقله إلى **Service** أو **Repository**.
- **مثال من `routes/employees.py`:** تحميل الموظف مع الأقسام والمستندات والصلاحيات داخل الـ view؛ لا يوجد طبقة **Use Case** أو **Application Service** تفصل "طلب العرض" عن "جلب البيانات".

### 2.2 خلط منطق الأعمال مع الواجهات (HTML/عرض)

- **منطق في القوالب:** في `layout.html` توجد شروط صلاحيات معقدة (`current_user.role == UserRole.ADMIN or current_user|check_module_access(Module.EMPLOYEES, Permission.VIEW)`) مما يكرر منطق التحقق ويصعب تغيير السياسات من مكان واحد.
- **بيانات مُعدّة في الـ Route:** كثير من الـ routes تعدّ قوائم وقواميس ومعادلات (مثل حسابات الراتب أو الإحصائيات) ثم تمررها إلى `render_template(...)`؛ هذا منطق أعمال يجب أن يكون في **Application/ Domain Layer** وليس في طبقة العرض.
- **تصدير PDF/Excel داخل الـ Route:** إنشاء التقارير (مثل `export_vehicle_pdf`, `generate_employee_comprehensive_pdf`) يُستدعى من داخل الـ route مع تمرير `request` و `response`؛ الأفضل: **Command/Service** يُستدعى من الـ route فقط بمعاملات واضحة.

### 2.3 تبعيات متشابكة بين الموديولات

- **استيراد تقاطعي:** `routes/vehicles.py` يستورد من `routes/operations` (`create_operation_request`)؛ و`routes/attendance.py` يستورد نماذج وإشعارات من أماكن متعددة.
- **موديل واحد عملاق:** `models.py` يجمع الموظفين، المركبات، الحضور، المستخدمين، الإشعارات، الدوائر الجغرافية، المحاسبة (جزئياً عبر `models_accounting`)، مما يمنع فصل نطاقات (Bounded Contexts) واضح.
- **Utils كـ "مستودع مشترك":** عشرات الملفات في `utils/` (أكثر من 80 ملفاً) تخدم موظفين ومركبات ومحاسبة وورشة ورواتب؛ لا يوجد تجميع حسب النطاق (employees, vehicles, accounting).

### 2.4 ملخص التداخل

| المنطقة | الوضع الحالي | المشكلة |
|--------|--------------|---------|
| DB ↔ Routes | استعلامات وـ session داخل الـ routes | لا توجد طبقة Repository/Data Access موحدة |
| Business ↔ UI | حسابات وشروط في routes وقوالب | لا توجد طبقة Application/Domain واضحة |
| PDF/Excel | داخل routes و utils مبعثرة | لا يوجد Report Service موحد يُستدعى من طبقة واحدة |
| Models | ملف واحد ضخم + models_accounting | صعوبة فصل الموظفين عن المركبات عن المحاسبة |

---

## 3. فحص سلامة الواجهات والـ CSS (UI/UX Integrity)

### 3.1 كيف يتم استدعاء التنسيقات (CSS)

- **قالب أساسي واحد:** `templates/layout.html` يحمّل:
  - Bootstrap RTL من CDN
  - Font Awesome من CDN
  - DataTables، Select2، Select2 Bootstrap theme من CDN
  - `static/css/custom.css`
  - `static/css/logo.css?v={{ now.timestamp()|int }}`
  - ثم `{% block styles %}` و `{% block extra_css %}`

- **صفحات فردية:** كثير من القوالب تضيف:
  - روابط CDN إضافية (Leaflet، خطوط مختلفة، نسخ مختلفة من Bootstrap/Font Awesome).
  - ملفات مثل `vehicle_documents.css`, `handover.css`, `attendance.css`, `permissions_v1.css` حتى `permissions_v4.css`.
  - أنماط مضمنة (inline) داخل القالب أو داخل `<style>` في الصفحة (مثلاً في `workshop_details.html`, `vehicle_details.html`, `mobile_devices/edit.html`).

### 3.2 لماذا يحدث تداخل مدمّر عند أي تعديل بسيط؟

- **تضارب التحديثات:** نسخ متعددة من Bootstrap (5.2.3 في layout، 5.3.0 في بعض صفحات المركبات) ونسخ مختلفة من Font Awesome (6.0, 6.1.1, 6.4.0, 6.5.1) تؤدي إلى اختلاف المظهر وسلوك المكونات.
- **ترتيب التحميل:** الصفحات التي تحمّل `custom.css` ثم تضيف في `{% block styles %}` قواعد أكثر تحديداً (specificity) أو `!important` تلغي تنسيقات القالب أو العكس؛ وتعديل بسيط في `custom.css` يكسر صفحات لم تُختبر.
- **تعدد نسخ الـ permissions:** وجود `permissions_v1.css` … `permissions_v4.css` يدل على تعديلات تراكمية بدون توحيد؛ أي تغيير في سياسة الصلاحيات يتطلب مراجعة أربعة ملفات.
- **أنماط مضمنة في قوالب ضخمة:** في قوابل بحجم 2,000+ سطر (مثل `view.html`, `vehicle_details.html`) توجد مئات الأسطر من الـ CSS داخل الصفحة؛ إعادة استخدام التصميم شبه مستحيل وتعديل المظهر يتطلب فتح قوالب ضخمة.
- **غياب تصميم نظام (Design System):** لا توجد متغيرات CSS مركزية (مثل ألوان العلامة التجارية، المسافات، الأنماط المشتركة) موثقة ومستخدَمة في كل الصفحات؛ كل صفحة "تُخترع" تنسيقاتها.

### 3.3 خلاصة UI/UX

- **توصية:** اعتماد Design System (متغيرات + مكونات)، تحميل نسخة واحدة من Bootstrap و Font Awesome من القالب الأساسي فقط، وإزالة الـ CSS المضمن من القوالب ونقله إلى ملفات CSS scope حسب الصفحة أو المكون، مع إلغاء النسخ المكررة (مثل permissions_v1–v4).

---

## 4. تقييم الأداء والتحمل (Scalability Review)

### 4.1 هل الكود الحالي قادر على معالجة 10,000 مستخدم متزامن؟

**الإجابة المختصرة: لا، دون تغييرات جذرية.**

### 4.2 الاستعلامات الثقيلة وغياب التحسين

- **استعلامات بدون eager loading:** في routes مثل `vehicles` و `employees` و `attendance` يتم جلب كيانات رئيسية ثم الوصول إلى علاقات (مثل `vehicle.handovers`, `employee.departments`) مما يسبب **N+1 queries** عند عرض القوائم.
- **تجمعات ثقيلة في الذاكرة:** حسابات إحصائية (مثل `func.sum(Account.balance)`) أو تجميع حضور/رواتب على فترات طويلة تُنفّذ في الـ route دون pagination أو تحسين استعلام؛ مع نمو البيانات سيزيد زمن الاستجابة واستهلاك الذاكرة.
- **عدم استخدام الفهارس بشكل منهجي:** لا يظهر من التحليل السريع توثيق لسياسة فهارس (indexes) على الأعمدة المستخدمة في `filter` و `order_by` و `join`؛ جداول كبيرة (attendance, locations, workshop records) معرضة لاستعلامات بطيئة.

### 4.3 غياب أنظمة التخزين المؤقت (Caching)

- **لا يوجد Redis أو Memcached:** لا يوجد تكوين لـ cache خارجي في التطبيق.
- **استثناءات محدودة جداً:**
  - `utils/permissions_service.py`: cache صلاحيات المستخدم في `g._user_permissions_cache` (عمرها طلب واحد فقط).
  - `utils/id_encoder.py`: `@lru_cache` للتشفير/فك التشفير.
  - `routes/api_external.py`: "location cache" في الذاكرة لتحديث الموقع دون حفظ فوري في DB.
- **ما يُفقد:** لا cache لصفحات القراءة الثقيلة (لوحات التحكم، التقارير)، ولا cache لنتائج استعلامات تكرارية (مثل قوائم الأقسام، السنوات المالية)، ولا session store خارجي؛ مع 10,000 مستخدم متزامن سيزيد الحمل على قاعدة البيانات ووقت الاستجابة.

### 4.4 نقاط أخرى تؤثر على التحمل

- **رفع الملفات والتقارير:** إنشاء PDF/Excel داخل عملية الطلب (request) يربط زمن الاستجابة بزمن التوليد؛ الأفضل قائمة مهام (Task Queue) وتوليد التقارير في الخلفية.
- **اتصالات خارجية:** واتساب، إيميل، Google Drive تُستدعى أحياناً بشكل متزامن داخل الطلب؛ أي تأخر من الطرف الثالث يبطئ الاستجابة للمستخدم.
- **حالة الجلسة:** استخدام جلسة Flask الافتراضية (على الأرجح cookie-based أو filesystem) لا يتناسب مع توزيع الحمل على عدة instances؛ يلزم Session Store مركزي (مثل Redis).

### 4.5 خلاصة الأداء والتحمل

- **الوضع الحالي:** مناسب لتشغيل داخلي أو عدد محدود من المستخدمين المتزامنين.
- **لبلوغ 10,000 مستخدم متزامن يلزم:** إدخال cache (Redis)، فصل التقارير والعمليات الثقيلة إلى Queue (Celery/RQ)، تحسين الاستعلامات (eager loading، فهارس، تجميع في DB)، واستخدام Session Store مركزي وربما قراءة/كتابة منفصلة لقاعدة البيانات (read replicas).

---

## 5. المخرج المطلوب

### 5.1 خريطة طريق (Roadmap) لتفكيك الكود وتحويله إلى Clean Architecture

#### المرحلة 0: استقرار وتنظيف (4–6 أسابيع)

1. **إيقاف التضخم:** وضع حد أقصى لعدد الأسطر لكل ملف (مثلاً 500) ورفض دمج ملفات routes/models تتجاوزه دون خطة تفكيك.
2. **إزالة الملفات الاحتياطية من المسار النشط:** نقل `*_backup*.py` و `*.backup` إلى مجلد أرشيف أو حذفها بعد التأكد من عدم الحاجة.
3. **توحيد الواجهات:** اختيار نسخة واحدة من Bootstrap و Font Awesome، وتحميلها من `layout.html` فقط؛ بداية توحيد ملفات permissions وتقليل الـ inline CSS.

#### المرحلة 1: فصل النطاقات (Bounded Contexts) (8–12 أسبوع)

1. **تقسيم `models.py`:** فصل إلى نطاقات على الأقل:
   - `domain/employees/` (موظفون، أقسام، حضور، رواتب، طلبات موظفين، مستندات مرتبطة).
   - `domain/vehicles/` (مركبات، ورشة، تسليم، حوادث، فحص سلامة).
   - `domain/accounting/` (دمج مع `models_accounting` إن أمكن أو الإبقاء على حزمة منفصلة).
   - `domain/identity/` (مستخدمون، صلاحيات، إشعارات، دوائر جغرافية، أجهزة).
2. **استخراج Repositories:** لكل نطاق تعريف واجهات (Interfaces) لجلب وحفظ الكيانات؛ التنفيذ الأولي يمكن أن يلتف حول استعلامات SQLAlchemy الحالية داخل طبقة Data.
3. **استخراج Application Services (Use Cases):** نقل منطق "عرض قائمة مركبات"، "إنشاء سجل ورشة"، "حساب راتب شهر" من الـ routes إلى خدمات تُستدعى من الـ routes بمعاملات بسيطة.

#### المرحلة 2: تفكيك الملفات الضخمة (8–10 أسابيع)

1. **`routes/vehicles.py` و `routes/mobile.py`:** تقسيم إلى:
   - routes رفيعة (فقط استقبال طلب، استدعاء خدمة، إرجاع response).
   - خدمات (VehicleListService, WorkshopRecordService, VehicleExportService, …).
   - تكرار نفس النهج لـ `attendance`, `employees`, `api_employee_requests`.
2. **`utils/`:** تجميع الملفات حسب النطاق (مثلاً `employees/reports.py`, `vehicles/export.py`, `accounting/chart_of_accounts.py`) ونقل التبعيات تدريجياً إلى الطبقة الجديدة.

#### المرحلة 3: البنية النظيفة (Clean Architecture) (10–14 أسبوع)

1. **طبقات واضحة:**
   - **Domain:** كيانات وقواعد أعمال فقط (بدون Flask، بدون SQL).
   - **Application (Use Cases):** أوامر واستعلامات تستخدم واجهات Repositories و Services.
   - **Infrastructure:** تنفيذ Repositories (SQLAlchemy)، إرسال إيميل، واتساب، تخزين ملفات.
   - **Presentation:** Flask Blueprints، قوالب، تحويل الطلبات إلى أوامر/استعلامات واستدعاء Use Cases.
2. **اعتماد CQRS حيث يناسب:** فصل استعلامات القراءة (تقارير، لوحات) عن أوامر الكتابة لتمكين تحسين الاستعلامات والـ cache بشكل مستقل.
3. **إدخال Queue للعمليات الثقيلة:** توليد PDF/Excel وإرسال إشعارات خارجية عبر قائمة مهام (مثل Celery) مع تخزين حالة المهمة وعرضها للمستخدم.

#### المرحلة 4: الأداء والتحمل (6–8 أسابيع)

1. **إدخال Redis:** للـ cache (صفحات، استعلامات متكررة) و Session Store.
2. **تحسين الاستعلامات:** مراجعة كل قائمة وتقرير: eager loading، فهارس، تجميع في DB، pagination إلزامي.
3. **تقارير وقراءة ثقيلة:** نقلها إلى قراءة من Replica إن وُجدت، و/أو cache مع invalidation واضح.

---

### 5.2 هيكل مجلدات جديد مقترح (Modular Structure)

الهدف: فصل موديول الموظفين عن المركبات عن المحاسبة تماماً مع إبقاء مشروع واحد (Monolith) منظم، قابل لاحقاً لفصل إلى خدمات إذا لزم.

```
nuzm/
├── app.py                          # إنشاء التطبيق وتسجيل Blueprints فقط
├── config/
│   ├── __init__.py
│   ├── base.py
│   ├── development.py
│   └── production.py
├── core/
│   ├── __init__.py
│   ├── extensions.py               # db, login_manager, csrf, migrate
│   └── cli.py                      # أوامر flask إن وجدت
│
├── domain/                         # النطاقات (Bounded Contexts)
│   ├── employees/
│   │   ├── __init__.py
│   │   ├── models.py               # Employee, Department, Attendance, Salary, ...
│   │   ├── repositories.py         # واجهات/تنفيذ جلب وحفظ الموظفين والحضور
│   │   └── services.py             # منطق أعمال (حساب راتب، قواعد حضور)
│   ├── vehicles/
│   │   ├── __init__.py
│   │   ├── models.py               # Vehicle, Workshop, Handover, Accident, ...
│   │   ├── repositories.py
│   │   └── services.py
│   ├── accounting/
│   │   ├── __init__.py
│   │   ├── models.py               # من models_accounting + تكامل مع النظام
│   │   ├── repositories.py
│   │   └── services.py
│   └── identity/
│       ├── __init__.py
│       ├── models.py               # User, Permission, Module, Notification, Geofence, ...
│       ├── repositories.py
│       └── services.py
│
├── application/                    # طبقة التطبيق (Use Cases) اختياري في مرحلة لاحقة
│   ├── employees/
│   │   ├── commands.py            # إنشاء موظف، تحديث حضور، ...
│   │   └── queries.py             # قائمة موظفين، تقرير حضور، ...
│   ├── vehicles/
│   ├── accounting/
│   └── identity/
│
├── infrastructure/                 # تنفيذ التقنيات الخارجية
│   ├── persistence/               # تنفيذ Repositories بـ SQLAlchemy
│   ├── email/
│   ├── whatsapp/
│   ├── storage/                   # Google Drive, local files
│   └── cache/                     # Redis wrapper
│
├── presentation/                   # واجهة المستخدم (Web)
│   ├── web/
│   │   ├── __init__.py
│   │   ├── layout.html
│   │   ├── static/
│   │   │   ├── css/               # design system + صفحات حسب الموديول
│   │   │   └── js/
│   │   ├── employees/             # Blueprint + routes + templates فرعية
│   │   │   ├── routes.py
│   │   │   ├── forms.py
│   │   │   └── templates/
│   │   ├── vehicles/
│   │   ├── accounting/
│   │   ├── attendance/
│   │   ├── auth/
│   │   └── ...
│   └── api/                        # REST/JSON للجوال والعملاء الخارجيين
│       ├── v1/
│       │   ├── employees.py
│       │   ├── vehicles.py
│       │   └── ...
│       └── ...
│
├── shared/                         # مشترك بين النطاقات (بحذر)
│   ├── utils/                     # تحويل تواريخ، ترميز، تحقق صحة
│   ├── reporting/                 # قاعدة تصدير PDF/Excel إذا كانت مشتركة
│   └── permissions.py            # تحقق صلاحيات يعتمد على identity
│
├── tasks/                          # مهام غير متزامنة (Celery/RQ)
│   ├── reports.py
│   ├── notifications.py
│   └── ...
├── docs/
│   └── ENTERPRISE_AUDIT_REPORT.md
├── tests/
│   ├── domain/
│   ├── application/
│   └── presentation/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── .env.example
```

### 5.3 ضمان الفصل بين الموديولات

- **موظفون (employees):** لا يستورد من `presentation/web/vehicles` أو من `domain/vehicles` إلا عبر واجهات محددة (مثلاً "الحصول على مركبات موظف" عبر خدمة مشتركة أو حدث).
- **مركبات (vehicles):** لا يحتوي على منطق رواتب أو حضور؛ يستخدم فقط هوية المستخدم والصلاحيات من `identity`.
- **محاسبة (accounting):** يقرأ من الموظفين/المركبات فقط عبر أرقام أو مراجع (مثل employee_id، vehicle_id) أو عبر أحداث/واجهات محددة؛ لا يستورد نماذج الموظفين الكاملة إن أمكن.
- **الهوية (identity):** يوفر المستخدمين والصلاحيات والدوائر الجغرافية؛ باقي الموديولات تعتمد عليه دون العكس.

---

## 6. ملخص تنفيذي

| المحور | الحالة الحالية | التوصية الرئيسية |
|--------|----------------|-------------------|
| تضخم الملفات | ملفات routes/models/utils تتجاوز 3,000–7,000 سطر | حد أقصى ~500 سطر، تفكيك فوري لـ mobile.py و vehicles.py و attendance.py |
| التداخل | DB وعرض وأعمال وPDF مخلوطة في الـ routes | إدخال Repositories و Application Services وفصل الطبقات |
| الواجهات والـ CSS | CDN متعددة، inline، permissions_v1–v4 | Design System واحد، إزالة تكرار، تحميل مركزي من layout |
| التحمل | لا cache، N+1، تقارير داخل الطلب، جلسة غير موزعة | Redis للـ cache والجلسة، Queue للتقارير، تحسين استعلامات وفهارس |
| الهيكل | موديل واحد ضخم، utils مبعثرة، 50+ blueprint في app.py | هيكل مجلدات حسب النطاق (employees / vehicles / accounting / identity) وطبقات واضحة |

التحول إلى المعمارية المقترحة يتطلب التزاماً زمنياً (تقريباً 6–9 أشهر لفريق صغير) وإدارة مخاطر (ترحيل البيانات، عدم كسر الوظائف الحالية). يُفضّل البدء بمرحلة 0 ومرحلة 1 (فصل النطاقات وتقسيم models) ثم تفكيك ملفين حرجين (مثلاً vehicles و attendance) كنموذج قبل تعميم النهج على بقية النظام.
