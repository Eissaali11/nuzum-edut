# Accounting Unmapped Endpoint Triage (Phase 0)

تاريخ الإصدار: 2026-02-27
المصدر: tools/verify_templates.py
النطاق: accounting-only triage

## ملخص سريع
- المشكلة: عدد كبير من روابط القوالب ما يزال يستخدم legacy endpoints بصيغة `accounting.*`.
- الوضع الحالي: endpoint المحاسبة المسجّل فعليًا محدود (مثل `accounting.dashboard` + مجموعة `accounting_ext.*` + `profitability.*`).
- النتيجة: يجب تنفيذ طبقة توافق إضافية أو تحديث القوالب تدريجيًا إلى canonical endpoints.

## أعلى العناصر المحاسبية غير المربوطة (حسب التكرار)
| Legacy Endpoint | مرات الظهور | الأولوية |
|---|---:|---|
| accounting.cost_centers | 11 | P0 |
| accounting.accounts | 8 | P0 |
| accounting.transactions | 8 | P0 |
| accounting.chart_of_accounts | 7 | P0 |
| accounting.account_balance_page | 5 | P0 |
| accounting.view_cost_center | 4 | P1 |
| accounting.create_journal_entry | 3 | P1 |
| accounting.view_transaction | 3 | P1 |
| accounting.create_cost_center | 3 | P1 |
| accounting.add_transaction | 2 | P1 |
| accounting.create_account | 2 | P1 |
| accounting.edit_account | 2 | P1 |

## خطة التنفيذ الفوري
1. إضافة aliases توافقية لمجموعة P0 أولًا داخل `routes/accounting/mapping_registry.py`.
2. تشغيل verifier بنطاق المحاسبة: `.venv\Scripts\python tools/verify_templates.py --scope accounting`.
3. تحديث القوالب الأعلى استخدامًا تدريجيًا إلى canonical endpoints.
4. بعد استقرار BuildError = 0، البدء بإزالة aliases غير المستخدمة.

## ملاحظة
يفضّل أن تكون كل إضافة mapping مصحوبة بتوثيق في:
- docs/ACCOUNTING_ENDPOINT_MAPPING_2026-02-27.md
