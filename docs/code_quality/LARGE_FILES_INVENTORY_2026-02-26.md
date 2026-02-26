# جرد الملفات الكبيرة وجودة الكود

تاريخ الجرد: 2026-02-26  
الأداة: `scripts/audit_large_files.py`

## معايير التقييم
- **الحجم (Bytes)**
- **عدد الأسطر**
- **أقصى طول سطر**
- **عدد الأسطر الطويلة (>120 حرف)**
- **نسبة التكرار (dup_ratio)**

> ملاحظة: الملفات الأرشيفية/النسخ الاحتياطية (`backups`, `package-lock`, docs) تم فصلها عن أولويات refactor الفعلي.

## أعلى ملفات كود تحتاج تنظيف (أولوية تقنية)

| الملف | الحجم | الأسطر | الأسطر الطويلة | التكرار | مستوى |
|---|---:|---:|---:|---:|---|
| `routes/legacy/_attendance_main.py` | 161148 | 3403 | 26 | 0.315 | Critical |
| `templates/mobile/partials/vehicle_details/_content.html` | 134197 | 3406 | 90 | 0.510 | Critical |
| `templates/vehicles/partials/view/_content.html` | 130227 | 1874 | 87 | 0.550 | Critical |
| `routes/integrations/external_safety.py` | 124739 | 2552 | 36 | 0.289 | High |
| `routes/legacy/operations_old.py` | 115755 | 2398 | 26 | 0.289 | High |
| `routes/reports_mgmt/reports_old.py` | 92299 | 2177 | 13 | 0.360 | High |
| `templates/geofences/view.html` | 80506 | 1829 | 50 | 0.463 | High |
| `templates/documents/create.html` | 60370 | 1319 | 8 | 0.459 | High |
| `templates/layout.html` | 63800 | 1087 | 71 | 0.435 | High |
| `services/employee_request_service.py` | 54331 | 1410 | 1 | 0.345 | Medium |

## ملفات متكررة/نسخ متشابهة (فرصة دمج)

- `templates/vehicles/partials/3view/_content.html`
- `modules/vehicles/presentation/templates/vehicles/views/partials/3view/_content.html`
- `templates/vehicles/partials/4view/_content.html`
- `templates/operations/partials/view/_content.html`
- `templates/mobile/partials/vehicle_checklist3/_content.html`

## ملفات كبيرة لكنها ليست هدف تنظيف كود مباشر

- `backups/nuzum.sql`
- `functions/package-lock.json`
- ملفات docs/arhive الضخمة

## خطة تنفيذ مقترحة (عملية)

### Phase 1 (أسرع أثر)
1. تفكيك `templates/layout.html` إلى partials (sidebar/header/alerts/scripts).
2. تفكيك `templates/documents/create.html` إلى `content + scripts + ajax-handlers`.
3. تقليص `templates/geofences/view.html` بفصل JS/CSS إلى ملفات static.

### Phase 2 (legacy routes)
1. تقسيم `routes/legacy/_attendance_main.py` إلى وحدات فرعية (`views`, `recording`, `crud`, `exports`).
2. تقسيم `routes/legacy/operations_old.py` على نمط core/workflow/export.
3. نقل/تجميد endpoints غير المستخدمة مع wrappers توافقية.

### Phase 3 (vehicles templates dedupe)
1. استخراج مكونات مشتركة من `3view/4view/view`.
2. توحيد partials المتكررة (cards/tables/actions/modals).
3. منع التكرار عبر include/macros.

## مخرجات الجرد المساعد
- سكربت الجرد: `scripts/audit_large_files.py`
- يمكن إعادة التشغيل بنفس الأمر:

```powershell
venv\Scripts\python scripts\audit_large_files.py
```

## تحديث نهائي بعد التنفيذ (2026-02-26)

### ملخص الحالة الحالية
- تم تنفيذ حملة dedupe تدريجية واسعة على القوالب/الأنماط/ملفات التوافق.
- نتيجة فحص التكرار للملفات النشطة عبر `scripts/find_exact_duplicates.py`: **DUPLICATE_GROUPS = 0**.
- تم حصر التكرارات المتبقية في مسارات غير تشغيلية (أرشيف/رسائل مولدة/ملفات فارغة) ثم استبعادها من تقييم الكود الفعلي.

### توحيد أدوات الجرد
- تم تحديث `scripts/find_exact_duplicates.py` لاستثناء:
	- `_graveyard_archive`
	- `emails_queue`
	- الملفات الفارغة (`size == 0`)
- تم تحديث `scripts/audit_large_files.py` لاستثناء:
	- `_graveyard_archive`
	- `emails_queue`
	- `docs`
	- `backups`
	- الملفات الفارغة (`size == 0`)

### نتيجة عملية
- تقرير الأحجام أصبح يركز على ملفات التطبيق الفعلية فقط.
- تقرير التكرار أصبح مؤشرًا دقيقًا لجودة الكود النشط بدل الضوضاء الأرشيفية.

### أوامر التحقق المعتمدة
```powershell
venv\Scripts\python scripts\find_exact_duplicates.py
venv\Scripts\python scripts\audit_large_files.py
```
