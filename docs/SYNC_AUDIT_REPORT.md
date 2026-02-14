# تقرير مزامنة النواة — نُظم (Enterprise Constitution Audit)

**المراجع:** Lead Architect  
**التاريخ:** مراجعة ما بعد هجرة البنية التحتية ونطاق المركبات  
**الغرض:** التحقق من التزام المشروع بـ "الدستور المؤسسي" بعد التعديلات الأخيرة.

---

## 1. Infrastructure Connectivity

### 1.1 Redis and Celery in `core/app_factory.py`

| البند | الحالة | التفاصيل |
|-------|--------|----------|
| تهيئة Redis | ✅ مؤكد | `_init_redis(app)` يُستدعى بعد `_init_extensions(app)` في `create_app()`. |
| مصدر الإعداد | ✅ | `REDIS_URL` يُقرأ من `app.config.get("REDIS_URL")` (يأتي من `config/base.py` أو البيئة). |
| ربط العميل | ✅ | عند توفر الحزمة `redis` يُعيَّن `app.redis = redis_lib.from_url(redis_url)`؛ وإلا `app.redis = None`. |
| تهيئة Celery | ✅ مؤكد | `_init_celery(app)` يُستدعى بعد `_init_redis(app)`. |
| تعامل مع عدم تثبيت Celery | ✅ | في حال `ImportError` يُعيَّن `app.celery = None` دون إسقاط التطبيق. |

**الخلاصة:** Redis و Celery مربوطان في `app_factory`؛ Redis اختياري عند غياب الحزمة، وCelery لا يعطل التشغيل عند عدم التثبيت.

### 1.2 Flask app_context مع مهام Celery

| البند | الحالة | التفاصيل |
|-------|--------|----------|
| ContextTask | ✅ مؤكد | في `core/celery_app.py` الصنف `ContextTask(_celery_app.Task)` يغلف تنفيذ المهمة. |
| دفع السياق | ✅ | `def __call__(self, *args, **kwargs): with _get_flask_app().app_context(): return self.run(*args, **kwargs)`. |
| مصدر التطبيق | ✅ | `_get_flask_app()` يستدعي `create_app()` من `core.app_factory`، فيحصل الـ worker على سياق كامل (DB، config، إلخ). |

**الخلاصة:** كل مهمة Celery تُنفَّذ داخل `app_context()`، مما يقلل أخطاء الاتصال بقاعدة البيانات أو الوصول إلى `current_app`.

**توصية:** توثيق تشغيل الـ worker: `celery -A core.celery_app worker --loglevel=info` في README أو دليل النشر.

---

## 2. Vehicle Domain Integrity

### 2.1 استبدال التعريفات في `models.py` الجذر

| المكون | الموقع الحالي | في الجذر `models.py` |
|--------|----------------|----------------------|
| `vehicle_user_access` | `domain/vehicles/models.py` | ❌ لا يوجد تعريف — استيراد فقط من `domain.vehicles.models` |
| `Vehicle` | `domain/vehicles/models.py` | ❌ استيراد فقط |
| `VehicleRental` | `domain/vehicles/models.py` | ❌ استيراد فقط |
| `VehicleWorkshop` | `domain/vehicles/models.py` | ❌ استيراد فقط |
| `VehicleWorkshopImage` | `domain/vehicles/models.py` | ❌ استيراد فقط |
| `VehicleProject` | `domain/vehicles/models.py` | ❌ استيراد فقط |
| `VehicleHandover` | `domain/vehicles/handover_models.py` (مُصدَّر عبر `models.py`) | ❌ استيراد فقط |
| `VehicleHandoverImage` | `domain/vehicles/handover_models.py` | ❌ استيراد فقط |

تم التحقق: لا يوجد في الجذر أي `class Vehicle(`, `class VehicleHandover(`, أو `vehicle_user_access = db.Table(` — التعريفات الوحيدة لهذه الكيانات هي في النطاق.

**الخلاصة:** نطاق المركبات استبدل التعريفات بالكامل في الجذر؛ الجذر يعيد فقط التصدير من `domain.vehicles.models`.

### 2.2 استيرادات المسارات القديمة ودوران الاستيراد

| المصدر | الاستيراد | دائرة؟ |
|--------|-----------|--------|
| `routes/vehicles.py` | `from models import Vehicle, VehicleRental, VehicleWorkshop, …` | ❌ لا |
| `models.py` | `from domain.vehicles.models import …` | — |
| `domain/vehicles/models.py` | `from domain.vehicles.handover_models import …` (في نهاية الملف) | ❌ لا |
| `domain/vehicles/handover_models.py` | لا يستورد من `models` ولا من `routes` | — |

**ترتيب التحميل:**  
`routes/vehicles` → `models` → `domain.vehicles.models` → `domain.vehicles.handover_models`. لا يوجد استيراد من النطاق أو من الجذر داخل `handover_models`؛ العلاقات تستخدم أسماء نصية (مثل `"Vehicle"`, `"Employee"`) يحلها SQLAlchemy لاحقاً.

**الخلاصة:** لا توجد دوائر استيراد ناتجة عن بقاء المسارات القديمة مع `from models import …`؛ النماذج تُحمَّل مرة واحدة عبر الجذر.

---

## 3. UI & Design System Consistency

### 3.1 صفحة القائمة `/app/vehicles/` ومتغيرات `theme.css`

| العنصر | الصنف / الاستخدام | متغير CSS في theme.css |
|--------|---------------------|-------------------------|
| عنوان الصفحة | `theme-page-title` | `font-family: var(--font-default)`؛ `color: var(--primary-color)` |
| البطاقات | `theme-card` | `background: var(--card-bg)`؛ `border: var(--card-border)` |
| رأس البطاقة | `.theme-card .card-header` | `background: var(--card-header-bg)`؛ `color` و`border` من المتغيرات |
| جدول المركبات | `theme-vehicles-table-wrap` | `background: var(--card-bg)` |
| جدول المركبات | `theme-vehicles-table`, `theme-vehicles-thead`, `theme-vehicles-row` | `font-family: var(--font-default)`؛ `color: var(--sidebar-text)`؛ `background: var(--card-header-bg)` للـ thead؛ `border: var(--card-border)` |
| شارة الحالة | `theme-badge-secondary` | `background: var(--sidebar-brand)` |
| زر العرض | `theme-btn-info` | لون ثابت (متناسق مع الهوية) |

النموذج (التصفية) يستخدم `form-control`, `form-select`, `btn btn-primary` من Bootstrap؛ زر "تطبيق" يمكن استبداله لاحقاً بـ `theme-btn-primary` لتحقيق اتساق كامل مع المتغيرات.

**الخلاصة:** عناصر الواجهة الجديدة في الصفحة (العنوان، البطاقات، الجدول، الشارات، زر العرض) تعتمد على أصناف theme التي تستخدم متغيرات `theme.css`؛ التصميم متسق مع الدستور البصري.

### 3.2 خط beIN-Normal

| البند | الحالة |
|-------|--------|
| تعريف الخط في theme.css | ✅ `@font-face { font-family: "beIN-Normal"; src: url("../fonts/beIN-Normal.ttf"); }` |
| المتغير العام | ✅ `:root { --font-default: "beIN-Normal", "Cairo", system-ui, sans-serif; }` |
| تطبيق على body | ✅ `body { font-family: var(--font-default); }` (في theme.css) |
| تطبيق على العناوين والعناصر | ✅ `h1..h6, .theme-sidebar-brand, .theme-navbar .navbar-brand, .theme-sidebar-link` و`.theme-page-title` و`.theme-vehicles-*` تستخدم `var(--font-default)` |
| تحميل theme.css في القالب | ✅ `layout/base.html` يربط `css/theme.css` بعد Bootstrap لضمان الأولوية |

**الخلاصة:** beIN-Normal مُعرَّف ومُطبَّق عبر المتغيرات؛ الـ fallback إلى Cairo ثم system-ui يحدث فقط عند فشل تحميل الملف. لا توجد أنماط inline تتعارض مع الخط.

### 3.3 ربط زر "عرض" بقائمة Clean Architecture وعرض التفاصيل Legacy

| البند | الحالة |
|-------|--------|
| القالب | `presentation/web/templates/vehicles/list.html` |
| الرابط | `url_for('vehicles.view', id=vehicle.id)` |
| الـ Blueprint Legacy | `vehicles_bp` مسجّل ببادئة `/vehicles` في `_register_legacy_blueprints` |
| المسار الناتج | `/vehicles/<id>` — عرض تفاصيل المركبة (القديم) |

**الخلاصة:** زر "عرض" يربط القائمة الجديدة (الـ slice) بعرض التفاصيل القديم بشكل صحيح؛ لا كسر في التدفق.

---

## 4. Technical Debt & Compliance

### 4.1 أكبر ملف منتفخ في `routes/` بعد الهجرة الجزئية

| الملف | عدد الأسطر (تقريبي) | ملاحظة |
|-------|----------------------|--------|
| **mobile.py** | **~7,427** | الأكبر — لم يُهاجَر بعد |
| **vehicles.py** | **~6,724** | ثاني أكبر — قائمة المركبات فقط انتقلت إلى slice؛ التفاصيل، الورشة، التسليم، التقارير ما زالت هنا |
| operations.py | ~2,378 | |
| employees.py | كبير (لم يُحسب بالضبط) | |
| ... | | |

**الخلاصة:** أكبر ملف "منتفخ" في المسارات القديمة هو **`routes/mobile.py`** (~7.4k سطر)، يليه **`routes/vehicles.py`** (~6.7k سطر). كلاهما مرشحان لتقسيم أو هجرة تدريجية حسب الدستور.

### 4.2 قاعدة 400 سطر — الملفات الجديدة في هذه الجلسة

| الملف | عدد الأسطر | ضمن 400؟ |
|-------|------------|----------|
| domain/vehicles/models.py | 169 | ✅ |
| domain/vehicles/handover_models.py | 191 | ✅ |
| application/vehicles/services.py | 157 | ✅ |
| presentation/web/vehicles/routes.py | 42 | ✅ |
| presentation/web/templates/vehicles/list.html | 121 | ✅ (قالب) |
| core/celery_app.py | 53 | ✅ |
| core/app_factory.py | (لم يُعدّ في التقرير) | يُفترض الالتزام حسب قاعدة المشروع |

**الخلاصة:** جميع الملفات الجديدة التي أُنشئت أو وُسِّعت في هذه الجلسة تلتزم بقاعدة 400 سطر.

---

## 5. Readiness for the Next Slice: Vehicle Handover

### 5.1 هل يمكن نقل "منطق تسليم المركبة" إلى `application/vehicles/services.py` الآن؟

**الإجابة المختصرة:** يمكن البدء بنقل **أجزاء** المنطق (استعلامات، تحقق من الحالة، بناء كائن التسليم)، لكن **لا** نقل كامل دون فك تبعيات في المسار القديم.

### 5.2 التبعيات الحالية في `routes/vehicles.py` (create_handover وما يتصل بها)

| التبعية | الاستخدام في create_handover / عرض التسليم |
|---------|--------------------------------------------|
| **OperationRequest** | تحديد السجلات "الرسمية" (المُعتمدة) vs المعلقة؛ استعلامات فرعية لـ approved_handover_ids و all_handover_request_ids. |
| **Employee, Department** | قوائم للقائمة المنسدلة (موظفون، أقسام). |
| **Vehicle, VehicleHandover** | جلب المركبة، إنشاء سجل التسليم، استعلام آخر تسليم/استلام. |
| **db, request, redirect, url_for, flash** | سياق Flask. |
| **دوال مساعدة** | مثل `save_base64_image`, `save_uploaded_file` (تواقيع، شعارات، رسم الأضرار) — معرفة في نفس الملف أو مستوردة. |
| **قوالب** | `vehicles/handover_create.html` مع متغيرات كثيرة. |

### 5.3 ما الذي يمكن نقله إلى الخدمة دون تغيير كبير؟

- **استعلام "آخر تسليم / آخر استلام"** (مع أو بدون OperationRequest): دالة مثل `get_latest_handover_state(vehicle_id)` أو `get_handover_create_context(vehicle_id)` تُرجع `force_mode`, `current_driver_info`, `info_message`.
- **التحقق من حالة المركبة** (غير مناسبة للتسليم): دالة مثل `check_vehicle_handover_eligibility(vehicle)` تُرجع `(allowed: bool, redirect_to, message)`.
- **بناء كائن VehicleHandover من بيانات النموذج** (بدون حفظ): دالة مثل `build_handover_from_form(vehicle, form_data)` تُرجع كائناً غير مُلصق أو قاموساً؛ الحفظ يبقى في المسار أو في خدمة أخرى بعد إضافة الملفات والتواقيع.

### 5.4 ما الذي يجب حله أولاً؟

1. **OperationRequest و"الرسمي vs المعلّق"** — المنطق معقد ومُدمج في الاستعلامات؛ يفضّل استخراجه إلى خدمة (مثلاً `application/operations/` أو داخل `application/vehicles/`) ثم استدعاؤها من المسار والخدمة معاً.
2. **حفظ الملفات والتواقيع** — `save_base64_image`, `save_uploaded_file` يجب أن تصبحا وحدتين قابلة لإعادة الاستخدام (مثلاً في `utils/` أو `infrastructure/storage/`) وتُستدعيان من الخدمة أو من مسار رفيع.
3. **إنشاء طلب عملية (OperationRequest)** — إن كان إنشاء التسليم يخلق أو يربط بـ OperationRequest، فهذا الجزء يجب أن يكون واضحاً في الخدمة أو في تنسيق (orchestration) بين خدمة المركبات وخدمة العمليات.

### 5.5 التوصية

- **جاهزية جزئية:** نعم — يمكن فوراً إضافة دوال في `application/vehicles/services.py` لـ "قراءة فقط": حالة التسليم الحالية، التحقق من الأهلية، وربما بناء كائن التسليم من بيانات نقية.
- **نقل كامل create_handover:** لا يُنصح به قبل:
  - استخراج منطق OperationRequest (والسجلات الرسمية) إلى خدمة/وحدة واضحة،
  - توحيد حفظ الملفات/التواقيع في طبقة مشتركة،
  - ثم نقل خطوة POST (إنشاء السجل + ربط الطلبات + رفع الملفات) إلى خدمة مركبات أو خدمة تسليم، مع بقاء المسار رفيعاً (استدعاء الخدمة وعرض القوالب فقط).

---

## ملخص تنفيذي

| المحور | الحالة | ملاحظة |
|--------|--------|--------|
| 1. البنية التحتية (Redis/Celery) | ✅ متوافقة | الربط في app_factory؛ سياق التطبيق متاح لمهام Celery. |
| 2. نطاق المركبات | ✅ سليم | التعريفات في النطاق؛ الجذر يعيد التصدير فقط؛ لا دوائر استيراد. |
| 3. واجهة قائمة المركبات | ✅ متسقة | استخدام متغيرات theme، خط beIN-Normal، وربط صحيح مع عرض التفاصيل القديم. |
| 4. الديون التقنية والالتزام | ⚠️ جزئي | الملفات الجديدة &lt;400 سطر؛ أكبر ملف legacy: `mobile.py` ثم `vehicles.py`. |
| 5. الجاهزية لتسليم المركبة (Slice التالي) | ⚠️ جزئية | نقل القراءة والتحقق ممكن؛ نقل كامل create_handover يتطلب فك تبعيات OperationRequest وحفظ الملفات. |

تم إعداد هذا التقرير ليكون مرجعاً لمراجعات المزامنة والتخطيط للشرائح التالية.
