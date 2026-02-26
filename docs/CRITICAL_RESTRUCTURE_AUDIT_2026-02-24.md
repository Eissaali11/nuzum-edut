# فحص شامل للملفات الحرجة — 2026-02-24

## ملخص سريع
- إجمالي الملفات المفحوصة: 2743
- إجمالي أسطر الكود (py/html/js/css): 439,766
- الامتدادات الأعلى: HTML (1251)، Python (650)

## أخطر المخاطر البنيوية (الأولوية القصوى)

### 1) ازدواج المسارات (Routes Duplication)
- [modules/vehicles/presentation/web/handover_routes.py](modules/vehicles/presentation/web/handover_routes.py)
- [presentation/web/vehicles/handover_routes.py](presentation/web/vehicles/handover_routes.py)
- التشابه الآلي: 0.955
- الأثر: أي إصلاح في ملف لا ينعكس دائمًا في الملف الآخر، وهذا سبب مباشر لتكرار أخطاء CSRF وتباين السلوك.

- [modules/vehicles/presentation/web/vehicle_routes.py](modules/vehicles/presentation/web/vehicle_routes.py)
- [presentation/web/vehicle_routes.py](presentation/web/vehicle_routes.py)
- التشابه الآلي: 0.994
- الأثر: ازدواج شبه كامل لمسارات حيوية (عرض/تعديل المركبة) واحتمال تضارب مسار التنفيذ.

### 2) ازدواج القوالب (Templates Duplication)
- [modules/vehicles/presentation/templates/vehicles/handovers/partials/handover_create/_content.html](modules/vehicles/presentation/templates/vehicles/handovers/partials/handover_create/_content.html)
- [templates/vehicles/partials/handover_create/_content.html](templates/vehicles/partials/handover_create/_content.html)
- التشابه الآلي: 0.984
- الأثر: إصلاحات الواجهة (حقل ملاحظة/CSRF) تظهر في نسخة ولا تظهر في الأخرى.

### 3) مصنع التطبيق يخلط طبقتين قديمة/جديدة
- [core/app_factory.py](core/app_factory.py)
- الأثر: تسجيل Blueprints متعددة المصدر يسبب التباسًا حول أي route/template هو الفعلي.

## ملفات حرجة تحتاج إعادة هيكلة فورية (Hotspot Files)

### Routes / Controllers
- [modules/vehicles/presentation/web/handover_routes.py](modules/vehicles/presentation/web/handover_routes.py)
- [presentation/web/vehicles/handover_routes.py](presentation/web/vehicles/handover_routes.py)
- [modules/vehicles/presentation/web/vehicle_routes.py](modules/vehicles/presentation/web/vehicle_routes.py)
- [presentation/web/vehicle_routes.py](presentation/web/vehicle_routes.py)
- [modules/employees/presentation/web/routes.py](modules/employees/presentation/web/routes.py)
- [routes/hr/employees.py](routes/hr/employees.py)

### Services (منطق أعمال متضخم)
- [modules/vehicles/application/vehicle_service.py](modules/vehicles/application/vehicle_service.py) (882 سطر)
- [modules/employees/application/core/employee_service.py](modules/employees/application/core/employee_service.py) (1071 سطر)

### Templates (واجهات متضخمة/مكررة)
- [templates/vehicles/partials/view/_content.html](templates/vehicles/partials/view/_content.html) (1874 سطر)
- [templates/vehicles/partials/handover_create/_scripts.html](templates/vehicles/partials/handover_create/_scripts.html) (1028 سطر)
- [modules/vehicles/presentation/templates/vehicles/handovers/partials/handover_create/_scripts.html](modules/vehicles/presentation/templates/vehicles/handovers/partials/handover_create/_scripts.html) (875 سطر)
- [templates/layout.html](templates/layout.html) (1087 سطر)

## ملفات كبيرة جدًا تحتاج تفكيك (Refactor Candidates)
- [routes/legacy/_attendance_main.py](routes/legacy/_attendance_main.py) (3403)
- [routes/requests/api_employee_requests.py](routes/requests/api_employee_requests.py) (3404)
- [utils/excel.py](utils/excel.py) (3140)
- [routes/integrations/external_safety.py](routes/integrations/external_safety.py) (2552)
- [routes/legacy/operations_old.py](routes/legacy/operations_old.py) (2398)
- [models_old.py](models_old.py) (2179)

## تشخيص جذري
- السبب المركزي للمشكلات الأخيرة ليس خطأ واحدًا، بل ازدواج بنيوي في routes + templates.
- النظام يحتوي نسخًا متعددة لنفس الميزة (modules / presentation / templates / vehicles11 / routes legacy).
- أي تعديل سريع بدون توحيد المصدر يسبب رجوع نفس الأعطال (CSRF، اختفاء حقول، اختلاف صفحة التنفيذ).

## خطة إعادة هيكلة مقترحة (مختصرة)
1. اعتماد مصدر وحيد للمركبات: modules/vehicles فقط.
2. إيقاف استدعاء النسخ الموازية في presentation/web/vehicles تدريجيًا عبر redirects واضحة.
3. توحيد قوالب handover في مسار واحد وحذف النسخ المكررة بعد المقارنة.
4. تقسيم vehicle_service و employee_service إلى use-cases صغيرة (read/update/report).
5. فصل JavaScript الضخم من قوالب HTML إلى ملفات static/js منظمة لكل feature.

## الأولوية التنفيذية
- P0 (عاجل): توحيد handover routes + handover templates.
- P1: توحيد vehicle view routes/templates.
- P2: تفكيك services المتضخمة.
- P3: تنظيف legacy files الكبيرة ونقلها إلى archive مع توثيق.
