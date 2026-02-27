# Accounting Endpoint Mapping (Phase 0)

تاريخ الإصدار: 2026-02-27
الغرض: مرجع رسمي للتوافق الرجعي بين المسارات القديمة والمسارات القياسية.

| Legacy Endpoint | Canonical Endpoint | Legacy Rule | Methods | Critical |
|---|---|---|---|---|
| `salaries.index` | `payroll.process` | `/salaries/` | `GET` | نعم |
| `salaries.report` | `reports.salaries_report` | `/salaries/report` | `GET` | نعم |
| `salaries.create` | `payroll.process` | `/salaries/create` | `GET, POST` | نعم |
| `salaries.import_excel` | `payroll.process` | `/salaries/import` | `GET, POST` | نعم |
| `salaries.export_excel` | `reports.salaries_excel` | `/salaries/export` | `GET` | نعم |
| `salaries.report_pdf` | `reports.salaries_report_pdf` | `/salaries/report/pdf` | `GET` | نعم |
| `salaries.batch_salary_notifications` | `payroll.process` | `/salaries/notifications/batch` | `GET, POST` | نعم |
| `salaries.batch_deduction_notifications` | `payroll.process` | `/salaries/notifications/deduction/batch` | `GET, POST` | نعم |
| `salaries.edit` | `payroll.process` | `/salaries/<int:id>/edit` | `GET, POST` | نعم |
| `salaries.salary_notification_pdf` | `reports.salaries_pdf` | `/salaries/notification/<int:id>/pdf` | `GET` | نعم |
| `accounting.accounts` | `accounting_accounts.accounts` | `/accounting/accounts` | `GET` | نعم |
| `accounting.create_account` | `accounting_accounts.create_account` | `/accounting/accounts/create` | `GET, POST` | نعم |
| `accounting.edit_account` | `accounting_accounts.edit_account` | `/accounting/accounts/<int:account_id>/edit` | `GET, POST` | نعم |
| `accounting.confirm_delete_account` | `accounting_accounts.confirm_delete_account` | `/accounting/accounts/<int:account_id>/confirm-delete` | `GET, POST` | نعم |
| `accounting.chart_of_accounts` | `accounting_charts.chart_of_accounts` | `/accounting/chart-of-accounts` | `GET` | نعم |
| `accounting.create_default_accounts` | `accounting_charts.create_default_accounts` | `/accounting/create-default-accounts` | `POST` | نعم |
| `accounting.account_balance_page` | `accounting_charts.account_balance_page` | `/accounting/account/<int:account_id>/balance-page` | `GET` | نعم |
| `accounting.delete_account` | `accounting_charts.delete_account` | `/accounting/account/<int:account_id>/delete` | `POST` | نعم |
| `accounting.transactions` | `accounting_transactions.transactions` | `/accounting/transactions` | `GET` | نعم |
| `accounting.add_transaction` | `accounting_transactions.add_transaction` | `/accounting/transactions/new` | `GET, POST` | نعم |
| `accounting.create_journal_entry` | `accounting_transactions.add_transaction` | `/accounting/journal-entries/new` | `GET, POST` | نعم |
| `accounting.view_transaction` | `accounting_transactions.view_transaction` | `/accounting/transaction/<int:transaction_id>` | `GET` | نعم |
| `accounting.cost_centers` | `accounting_costcenters.cost_centers` | `/accounting/cost-centers` | `GET` | نعم |
| `accounting.create_cost_center` | `accounting_costcenters.create_cost_center` | `/accounting/cost-centers/create` | `GET, POST` | نعم |
| `accounting.view_cost_center` | `accounting_costcenters.view_cost_center` | `/accounting/cost-centers/<int:center_id>` | `GET` | نعم |
| `accounting.edit_cost_center` | `accounting_costcenters.edit_cost_center` | `/accounting/cost-centers/<int:center_id>/edit` | `GET, POST` | نعم |
| `accounting.analytics` | `analytics_simple.dashboard` | `/accounting/analytics` | `GET` | نعم |
| `accounting.trial_balance` | `accounting_ext.trial_balance` | `/accounting/trial-balance` | `GET` | نعم |
| `accounting.balance_sheet` | `accounting_ext.balance_sheet` | `/accounting/balance-sheet` | `GET` | نعم |
| `accounting.journal_entries` | `accounting_transactions.transactions` | `/accounting/journal-entries` | `GET` | نعم |
| `accounting.pending_transactions` | `accounting_transactions.transactions` | `/accounting/pending-transactions` | `GET` | نعم |
| `accounting.settings` | `accounting.dashboard` | `/accounting/settings` | `GET` | نعم |
| `accounting.fiscal_years` | `accounting.dashboard` | `/accounting/fiscal-years` | `GET` | نعم |
| `accounting.income_statement` | `accounting.dashboard` | `/accounting/income-statement` | `GET` | نعم |
| `accounting.customers` | `accounting.dashboard` | `/accounting/customers` | `GET` | نعم |
| `accounting.vendors` | `accounting.dashboard` | `/accounting/vendors` | `GET` | نعم |
| `accounting.edit_transaction` | `accounting_transactions.transactions` | `/accounting/transactions/<int:transaction_id>/edit` | `GET, POST` | نعم |

## ملاحظات تشغيلية
- المصدر البرمجي الرسمي لهذه الجدول هو: `routes/accounting/mapping_registry.py`.
- الـ aliases تُفعَّل فقط إذا كان endpoint القديم غير مسجل فعليًا، لتجنب أي تعارض.
- الهدف هنا حماية القوالب من BuildError أثناء الانتقال التدريجي إلى المسارات القياسية.
