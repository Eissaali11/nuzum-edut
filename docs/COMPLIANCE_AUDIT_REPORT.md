# تقرير مراجعة الإنجاز والمعايير (Compliance Audit)
## مشروع نُظم — وفق دستور المشروع (Enterprise Grade)

**المُعدّ بصفة:** Senior Software Architect  
**نوع التقرير:** استجواب تقني (Technical Audit)  
**المرجع:** دستور نُظم، SCAFFOLDING.md، ENTERPRISE_AUDIT_REPORT.md

---

## 1. هيكلة المجلدات (Architecture)

### ما تم إنجازه
- **المجلدات الإلزامية موجودة:** `core/`, `config/`, `infrastructure/`, `domain/`, `application/`, `presentation/web/`, `shared/`.
- **النواة (core):** `app_factory.py` (≈293 سطر)، `extensions.py`؛ تشغيل التطبيق عبر `wsgi:app` وتهيئة DB, Migrate, LoginManager, CORS.
- **العرض (presentation/web):** قوالب، static (css, fonts)، بلوبرينتات ويب وAPI ومصادقة.
- **المشترك (shared):** `utils/responses.py`, `utils/validators.py`.
- **البنية التحتية (infrastructure):** مجلدات `database/`, `redis/`, `storage/`, `cache/` كحواضن (stubs) جاهزة للربط.
- **النطاق (domain):** مجلدات `employees/`, `vehicles/`, `accounting/` كحواضن؛ لا تحتوي بعد على نماذج أو منطق منقول.

### الفجوة الحالية
- **النماذج (Models)** ما زالت في **ملف واحد في الجذر:** `models.py` (≈2,964 سطر)، مع ملفات إضافية مثل `models_accounting.py`. لم يُنقل أي نموذج إلى `domain/employees` أو `domain/vehicles` أو `domain/accounting`.
- **مسارات الوظائف (Routes)** ما زالت في **`routes/`** بالجذر؛ كل route يستورد من `models` و`app` (عبر stub). لا توجد طبقة **Application** (Use Cases / Services) تفصل المنطق عن الـ routes.
- **ضمان عدم تداخل موديول الموظفين والمركبات:** غير مضمون بعد. كلا الموديولين يعتمدان على نفس `models.py` ونفس الـ routes الضخمة؛ لا توجد **Bounded Contexts** واضحة (نماذج منفصلة، واجهات، خدمات لكل نطاق).

### التوصية لتفادي التداخل مستقبلاً
1. نقل نماذج الموظفين والأقسام والحضور إلى `domain/employees/` (أو `domain/` مع تقسيم داخلي واضح).
2. نقل نماذج المركبات والورشة والتسليم إلى `domain/vehicles/`.
3. إبقاء النماذج المشتركة (User, Module, Permission) في مكان مشترك (مثلاً `domain/shared/` أو `core/`).
4. إنشاء **Application Services** (مثلاً `application/employees/`, `application/vehicles/`) تستدعيها الـ routes فقط، دون استعلامات مباشرة من الـ route إلى النماذج.

---

## 2. قاعدة الـ 400 سطر

### الوضع الحالي
- **ملفات تتجاوز 400 سطر (عينة):**
  - **Python:** `models.py` (≈2,964)، `routes/vehicles.py` (≈6,724)، `routes/mobile.py` (≈7,427)، `routes/attendance.py` (≈4,562)، `routes/employees.py` (≈3,058)، `routes/api_employee_requests.py` (≈3,403)، `routes/external_safety.py` (≈2,549)، `routes/documents.py` (≈2,315)، `routes/operations.py` (≈2,378)، `routes/reports.py` (≈2,177)، `app.py` (≈804)، وملفات routes و utils أخرى.
  - **CSS:** `custom.css` (≈1,956) في الجذر وفي `presentation/web/static/css/`.
  - **قوالب:** `layout.html` (≈961)، `dashboard.html` (≈984)، وقوالب أخرى (employees, vehicles, mobile, attendance…) تتجاوز 400 سطر بكثير.

- **ملفات ملتزمة بالحد:** `core/app_factory.py` (≈293)، `shared/utils/responses.py` (≈71)، `presentation/web/static/css/theme.css` (≈149)، وملفات صغيرة في core و config و presentation.

### خطة التعامل مع ملفات الـ Routes القديمة (7,000+ سطر)
1. **عدم إعادة كتابة الملف بالكامل دفعة واحدة:** اختيار **موديول وظيفي واحد** (Feature) كبداية (مثلاً "عرض قائمة الموظفين" أو "إنشاء تسليم مركبة").
2. **تفكيك تدريجي:**
   - استخراج **استعلامات وقواعد البيانات** إلى **Repository** أو دوال في `infrastructure/database/` أو داخل النطاق.
   - استخراج **منطق الأعمال** (حسابات، تحققات، تسلسلات) إلى **Application Service** (دوال أو كلاسات في `application/`).
   - الإبقاء على الـ **Route** كطبقة رفيعة: استقبال الطلب، استدعاء Service، إرجاع JSON أو `render_template` مع بيانات جاهزة.
3. **تقسيم الملف الضخم إلى ملفات بحجم &lt;400 سطر:** مثلاً `vehicles/` ك package: `list.py`, `create_edit.py`, `handover.py`, `reports.py`, `api.py` مع تسجيل كل بلوبرينت فرعي في `app_factory`.
4. **نفس النهج لـ** `employees`, `attendance`, `mobile`, `documents` عند الدور عليها.

---

## 3. الهوية البصرية والـ CSS

### 3.1 خط beIN-Normal و @font-face
- **تم تثبيته وتعريفه بشكل صحيح:**
  - في **`presentation/web/static/css/theme.css`:** `@font-face` مع `url("../fonts/beIN-Normal.ttf")`.
  - في **`presentation/web/static/css/fonts.css`:** نفس التعريف لتحميل الخط من `presentation/web/static/fonts/beIN-Normal.ttf`.
  - الملف الفعلي موجود في `presentation/web/static/fonts/beIN-Normal.ttf`.
- **النطاق:** الخط مُطبَّق في theme.css و fonts.css على body والعناوين والعناصر الأساسية؛ القالب الرئيسي للمشروع الحالي (لوحة التحكم ومعظم الصفحات) هو **`templates/layout.html`** الذي يحمّل **custom.css** و **fonts.css** من presentation؛ custom.css يحدد أيضاً خط beIN-Normal للنص.

### 3.2 ألوان القائمة الجانبية وتحويلها إلى CSS Variables
- **في theme.css:** نعم. توجد في `:root` متغيرات مثل:
  - `--sidebar-bg`, `--sidebar-bg-start`, `--sidebar-bg-mid`, `--sidebar-bg-end`
  - `--sidebar-border`, `--sidebar-link`, `--sidebar-link-icon`, `--sidebar-link-hover`, `--sidebar-active-bg`, `--sidebar-active-border`, `--sidebar-navbar-bg`, `--sidebar-shadow`
  - `--body-bg`, `--font-default`, `--primary`, `--secondary`
- **في القالب الذي تستخدمه معظم الصفحات (layout.html):** القائمة الجانبية الفعلية تُنسَّق عبر **custom.css** وليس theme.css. في custom.css الألوان **ثابتة** (مثل `#29406A`, `#4C72B0`, `#5990D5`) وليست مرجعاً لمتغيرات theme.css، لأن layout.html لا يحمّل theme.css. لذا:
  - **عبر base.html و theme.css:** الهوية البصرية مع متغيرات CSS مُطبَّقة.
  - **عبر layout.html و custom.css:** الهوية مُطبقة بألوان ثابتة؛ لم يتم بعد توحيد مصدر الألوان عبر متغيرات theme.css لهذا المسار.

### 3.3 إزالة Inline Styles والاعتماد الكلي على base.html
- **base.html (presentation/web/templates/layout/base.html):** خالٍ من inline styles؛ يعتمد على Bootstrap و theme.css و block `extra_css`.
- **layout.html (القالب الرئيسي للمسارات الحالية):** يحتوي على **حوالي 16 موضعاً** لـ `style=` (مثلاً تنسيقات خاصة لبعض الروابط والشارات). لم يتم بعد نقل كل التنسيقات إلى ملفات CSS.
- **قوالب أخرى:** عشرات القوالب في templates/ (employees, vehicles, attendance, mobile, …) تحتوي على أنماط مضمنة أو `<style>` داخل الصفحة. الاعتماد الكلي على base.html لم يُطبَّق بعد على كل المشروع؛ جزء كبير من الصفحات ما زال يمتد من `layout.html` أو قوالب أخرى وليست base.html.

**الخلاصة:** الخط مُثبَّت وصحيح؛ المتغيرات موجودة في theme.css وتُستخدم في مسار base.html؛ لكن مسار layout.html وقوالب Legacy ما زالت تعتمد على custom.css وألوان ثابتة وع inline styles في أماكن متعددة.

---

## 4. استقرار الـ Backend

### 4.1 تهيئة app_factory.py
- **تم:** مصنع التطبيق يعمل عبر `create_app()` مع:
  - تحميل الإعدادات من config
  - ربط القوالب (ChoiceLoader: presentation ثم root templates)
  - ربط الملفات الثابتة من presentation/web/static
  - تهيئة الملحقات (SQLAlchemy, Migrate, LoginManager, CORS, CSRF عبر extensions)
  - تسجيل البلوبرينتات (ويب، API، مصادقة، ثم Legacy routes)
  - معالجات أخطاء 404/500
  - فلاتر قوالب و context processors (مع safe_url_for)
- **نقطة حرجة:** الـ static_folder مُوجَّه إلى **presentation/web/static** فقط؛ لذلك تم نسخ custom.css و logo.css و fonts.css إلى هناك لضمان تحميلها لصفحات layout.html.

### 4.2 الردود الموحدة (Standardized JSON Responses)
- **موجودة ومُعرَّفة:** `shared/utils/responses.py` يوفر:
  - `json_success()`, `json_error()`, `json_created()`, `json_not_found()`, `json_unauthorized()`, `json_forbidden()`
  - هيكل موحد: `{ "success", "data", "message", "code", "errors", "meta" }`
- **مدى الاستخدام:** حالياً **فقط** `presentation/web/api_routes.py` يستخدمها (مثلاً endpoint صحة الخدمة). مسارات API القديمة في `routes/` (وما يتبعها) لم تُحوَّل بعد إلى هذه الدوال.
- **كيف يخدم تحمّل ضغط الشركات الكبرى:**
  - توحيد شكل الردود يسهّل التعامل مع الـ API من الواجهات والجوال والشركاء.
  - يسهّل إضافة طبقة Caching (مثلاً Redis) على ردود موحدة.
  - يسهّل المراقبة والـ Logging (نفس البنية لكل استجابة).
  - التوصية: عند نقل أي endpoint من routes القديمة إلى طبقة API جديدة، استخدام `json_success` / `json_error` من `shared.utils.responses` وإرجاع رموز HTTP واضحة.

---

## 5. الخطوة القادمة — أول موديول وظيفي جاهز للبناء

### التوصية: موديول **"الإشعارات" (Notifications)** كأول Feature Module داخل الهيكل النظيف

**الأسباب:**
1. **نطاق محدود:** عرض قائمة، تحديد كمقروء، ربما حذف أو أرشفة؛ لا يتشعب إلى موظفين/مركبات/رواتب معقدة.
2. **يعتمد على بنية موجودة:** نموذج Notification وربطه بـ User موجودان في models؛ يمكن لاحقاً نقلهما إلى `domain/notifications/` أو نطاق مشترك دون كسر كل المسارات دفعة واحدة.
3. **مناسب لاختبار الطبقات:**
   - **Presentation:** صفحات تمتد من **base.html**، وتحمّل theme.css و fonts.css فقط؛ بدون inline styles.
   - **Application:** خدمة بسيطة من نوع `NotificationService.list_for_user()`, `mark_as_read()`.
   - **API:** endpoints تستخدم `json_success` / `json_error` من shared.
4. **لا يزعزع الاستقرار:** المسارات الحالية للإشعارات يمكن أن تبقى تعمل؛ الموديول الجديد يُضاف كمسارات جديدة (مثلاً تحت `/v2/notifications` أو تحت نفس المسار مع استبدال تدريجي للـ view).

**بديل:** إذا رُغب في موديول يظهر فوراً للمستخدم النهائي، يمكن اختيار **"عرض قائمة الموظفين (قراءة فقط)"** كشريحة رأسية: استعلام من طبقة خدمة، قالب واحد يمتد من base.html، جدول عبر ماكرو من `templates/macros/`، دون تعديل routes/employees.py الأصلي في البداية.

---

## ملخص تنفيذي

| المعيار | الحالة | ملاحظة |
|--------|--------|--------|
| هيكل المجلدات (core, config, presentation, shared, domain, infrastructure, application) | منشأة | domain/ و application/ و infrastructure/ ما زالت stubs؛ النماذج والمنطق في الجذر |
| فصل تام بين موديول الموظفين والمركبات | غير محقق | اعتماد مشترك على models.py و routes ضخمة |
| قاعدة 400 سطر | مخالفة واسعة | models، routes، custom.css، عشرات القوالب تتجاوز الحد؛ app_factory و responses و theme ملتزمة |
| خط beIN-Normal و @font-face | محقق | مُعرَّف في theme.css و fonts.css؛ الملف في presentation/web/static/fonts |
| ألوان القائمة كـ CSS Variables في theme.css | محقق في theme | غير موحّد لمسار layout.html (يعتمد custom.css بألوان ثابتة) |
| إزالة كافة Inline Styles والاعتماد الكلي على base.html | غير محقق | base.html نظيف؛ layout.html وقوالب أخرى ما زالت تحتوي inline وأنماط مبعثرة |
| تهيئة app_factory والردود الموحدة | محقق | المصنع يعمل؛ responses.py جاهز؛ الاستخدام محدود على API الجديد |
| أول موديول جاهز للبناء | مقترح | الإشعارات (أو قائمة الموظفين قراءة فقط) داخل الهيكل النظيف دون كسر التصميم الحالي |

---

*تم إعداد هذا التقرير لمراجعة الامتثال لدستور نُظم والمعايير المرجعية المذكورة أعلاه.*
