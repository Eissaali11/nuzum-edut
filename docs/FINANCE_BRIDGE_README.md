# NUZUM Finance Bridge (ERPNext) — Quick Test Guide

## 1) Environment Variables
Add these values to `.env` (or your secrets manager):

- `ERPNEXT_BASE_URL`
- `ERPNEXT_API_KEY`
- `ERPNEXT_API_SECRET`
- `ERPNEXT_TIMEOUT=20` (optional)
- `ERPNEXT_DEFAULT_COMPANY` (optional)
- `ERPNEXT_DEFAULT_ITEM_CODE=NUZUM-SERVICE` (optional)
- `ERPNEXT_DEFAULT_ITEM_GROUP=Services` (optional)
- `ERPNEXT_DEFAULT_UOM=Nos` (optional)
- `ERPNEXT_VAT_ACCOUNT_HEAD` (optional but recommended)

## 2) What was added
- Service client: `services/finance_bridge.py`
  - `ERPNextClient.post_request(doctype, data)`
  - `ERPNextClient.get_request(doctype, filters, fields, limit)`
  - Connection test + customer sync + invoice push + invoice list
- Routes: `routes/accounting/finance_bridge_routes.py`
  - `GET /accounting/finance-bridge/`
   - `GET|POST /accounting/finance-bridge/settings`
  - `POST /accounting/finance-bridge/test-connection`
   - `POST /accounting/finance-bridge/contracts/<contract_id>/invoice-preview`
  - `POST /accounting/finance-bridge/contracts/<contract_id>/generate-zatca-invoice`
   - `POST /accounting/finance-bridge/invoices/<invoice_name>/sync-status`
- UI:
   - Dashboard: `templates/accounting/erp_dashboard.html`
   - Settings: `templates/accounting/erp_settings.html`
   - Invoicing Modal: `templates/accounting/partials/_invoice_modal.html`
  - Contract action button in `templates/accounting/contracts/resources.html`

## 3) First live connection test
1. Start app using project method:
   - `python startup.py`
2. Open:
   - `/accounting/finance-bridge/`
3. Click:
   - `Test Connection`
4. Expected:
   - Badge changes to `Connected 🟢`
   - Recent ERPNext Sales Invoices appear in the table

## 4) First invoice sync test
1. Ensure at least one contract has active resources with billing rates.
2. Open contract resources page.
3. Click `Generate ZATCA Invoice`.
4. Expected:
   - Customer is created/synced in ERPNext if missing.
   - Sales Invoice is created with 15% VAT in ERPNext.
   - Success flash includes invoice name and PDF link.

## 5) Billing logic used
For a selected contract and month/year:
- Fetch active contract resources.
- Count attendance days from `attendance` table (statuses: `present`, `late`, `early_leave`).
- Calculate line amount:
  - Daily billing: `days_worked * daily_rate`
  - Monthly billing: fixed monthly rate
- Push Sales Invoice in `SAR` with two-decimal formatting.

## 6) Troubleshooting
- **401/403**: Check key/secret and role permissions in ERPNext.
- **Timeout**: Increase `ERPNEXT_TIMEOUT`.
- **Item missing**: Bridge auto-creates default item (`ERPNEXT_DEFAULT_ITEM_CODE`).
- **No invoice lines**: Ensure attendance records exist and billing rates are > 0.
- **VAT account issues**: Set `ERPNEXT_VAT_ACCOUNT_HEAD` for your ERP chart of accounts.
