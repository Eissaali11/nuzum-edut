---
title: Attendance v1 Technical Manual
---

# دليل تقني — Attendance v1

نبذة سريعة
- النسخة `v1` من وحدة الحضور تعتمد فصل واضح بين الطبقات: Controller → Service → Query (MVC مطبق مع لمسة DDD).
- تحولنا يهدف للحفاظ على تشغيل التطبيق بدون تراجع (compat-wrapper) مع تمييز صريح `X-Attendance-Handler: MODULAR_v1`.

1. MVC Flow (Controller → Service → Query)

- Controller (routes/attendance/v1/attendance_views.py): معالجات رقيقة (thin controllers) التي تستقبل الطلب، تتحقق من الصلاحيات وتستدعي الـ Service.
- Service (routes/attendance/v1/services/attendance_service.py): تحتوي على منطق العمل (business rules) مثل `calculate_late_minutes()` وأي تجميع/تصنيف للبيانات.
- Query / Models (routes/attendance/v1/models/attendance_queries.py): دوال الوصول للبيانات (SQL/SQLAlchemy) مركزة ومقروءة لإعادة استخدام الاستعلامات المعقدة.

2. Business rules — Late calculation

- قاعدة السماح الافتراضية: 15 دقيقة (grace period).
- دالة `calculate_late_minutes(check_in_time, shift_start_time, grace_period=15)` تُعيد عدد الدقائق المتأخرة فقط (≥1) وإرجاع `0` إن كان داخل فترة السماح.
- قواعد مهمة:
  - التأخير يُحسب كفرق الزمن (minutes) بين `check_in_time` و`shift_start_time` بعد خصم فترة السماح.
  - قيمة سالبة تُعامل كـ `0` (أي لا تأخير).

3. قواعد الأداء وقاعدة البيانات

- استعلام لوحة القيادة (dashboard) تم تحسينه ليستخدم تجميع واحد (GROUP BY) بدلاً من عدة استدعاءات متتالية.
- مؤشرات (indexes) المستخدمة/المتوقعة:
  - `idx_attendance_employee_date`
  - `idx_attendance_date`
- نتيجة قياسية من اختبارات المعيار: زمن تنفيذ تجميع الـ Dashboard ≲ 40ms على قاعدة بيانات محلية مع ~14k صف.

4. ملاحظات تركيبية وعملياتية

- تمييز النسخة: كل رد من نقاط الحضور في `v1` يحمل الهيدر `X-Attendance-Handler: MODULAR_v1` لتمييز مصدر المعالجة.
- التدرّج: الحزمة تستخدم متغير البيئة `ATTENDANCE_USE_MODULAR` للسيطرة على تفعيل الـ v1 مقابل العودة للوراثة التقليدية.
- الملفات الرئيسية:
  - Controller: routes/attendance/v1/attendance_views.py
  - Service: routes/attendance/v1/services/attendance_service.py
  - Queries: routes/attendance/v1/models/attendance_queries.py

5. تشغيل الـ Smoke & Benchmark

- تشغيل الاختبارات السريعة (باستخدام بيئة افتراضية):
  - `python scripts/test_attendance_smoke.py` (يستخدم Flask `test_client`)
  - لتشغيل وحدة الاختبار الخاصة بالحساب: `python scripts/run_attendance_unit_tests.py`
- لقياس الأداء المحلي استخدم: `python scripts/run_dashboard_benchmark.py`

6. لماذا هذا التصميم؟
- يسهل الفصل إلى Controller/Service/Query كتابة اختبارات وحدة دقيقة.
- يسهل استبدال/تحسين الاستعلامات دون تغيير منطق العمل.
- يوفّر درجة أمان أثناء الترحيل بفضل الـ compat-wrapper والـ env toggle.

---
ملاحظات أخيرة: إن أردت، أستطيع توليد رسم بياني بسيط يوضح تدفق الطلبات (Mermaid) وإضافة مثال استدعاء HTTP مع رؤوس الاستجابة.
