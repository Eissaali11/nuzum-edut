"""
NUZUM ↔ ERPNext finance bridge service.
"""

import json
import os
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from urllib.parse import quote

import requests

from core.extensions import db
from models import Attendance, Salary
from models_accounting import Account, FiscalYear
from modules.accounting.domain.profitability_models import ProjectContract


class ERPNextBridgeError(Exception):
    """Custom bridge exception for ERPNext integration errors."""


def _to_decimal(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _resolve_entry_date(entry_date=None, month=None, year=None):
    if entry_date:
        if isinstance(entry_date, datetime):
            return entry_date.date()
        return entry_date
    if month and year:
        return date(int(year), int(month), 1)
    return date.today()


def validate_accounting_payload(entries=None, entry_date=None, month=None, year=None, require_entries=True):
    entries = entries or []
    resolved_date = _resolve_entry_date(entry_date=entry_date, month=month, year=year)

    fiscal_year = FiscalYear.query.filter(
        FiscalYear.is_active == True,
        FiscalYear.is_closed == False,
        FiscalYear.start_date <= resolved_date,
        FiscalYear.end_date >= resolved_date,
    ).first()
    if not fiscal_year:
        raise ERPNextBridgeError('لا يمكن الترحيل: لا توجد فترة مالية مفتوحة لهذا التاريخ.')

    if require_entries and not entries:
        raise ERPNextBridgeError('لا يمكن الترحيل بدون بنود قيد.')

    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')

    for entry in entries:
        entry_type = str(entry.get('entry_type') or '').strip().lower()
        amount_value = _to_decimal(entry.get('amount'))
        debit_value = _to_decimal(entry.get('debit'))
        credit_value = _to_decimal(entry.get('credit'))

        if amount_value > 0:
            if entry_type == 'debit':
                debit_value = amount_value
            elif entry_type == 'credit':
                credit_value = amount_value

        total_debit += debit_value
        total_credit += credit_value

        account_id = entry.get('account_id')
        if not account_id:
            raise ERPNextBridgeError('لا يمكن الترحيل: يوجد بند بدون حساب محاسبي.')

        account = Account.query.get(int(account_id))
        if not account or not account.is_active:
            raise ERPNextBridgeError('لا يمكن الترحيل: الحساب غير موجود أو غير نشط.')

        has_children = Account.query.filter_by(parent_id=account.id).count() > 0
        if has_children:
            raise ERPNextBridgeError(f'لا يمكن الترحيل على حساب تجميعي: {account.code} - {account.name}')

    if entries and total_debit != total_credit:
        raise ERPNextBridgeError(
            f'القيد غير متوازن: المدين {total_debit} لا يساوي الدائن {total_credit}'
        )

    return {
        'entry_date': resolved_date.isoformat(),
        'fiscal_year_id': fiscal_year.id,
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
    }


def validate_accounting_entry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        entries = kwargs.get('entries')
        validation_meta = validate_accounting_payload(
            entries=entries,
            entry_date=kwargs.get('entry_date') or kwargs.get('posting_date'),
            month=kwargs.get('month'),
            year=kwargs.get('year'),
            require_entries=False,
        )
        kwargs.setdefault('validation_meta', validation_meta)
        return func(*args, **kwargs)

    return wrapper


class ERPNextClient:
    @staticmethod
    def _as_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

    def __init__(self, config_overrides=None):
        config_overrides = config_overrides or {}

        self.base_url = (config_overrides.get('ERPNEXT_BASE_URL') or os.getenv('ERPNEXT_BASE_URL') or '').rstrip('/')
        self.api_key = (config_overrides.get('ERPNEXT_API_KEY') or os.getenv('ERPNEXT_API_KEY') or '').strip()
        self.api_secret = (config_overrides.get('ERPNEXT_API_SECRET') or os.getenv('ERPNEXT_API_SECRET') or '').strip()
        self.api_token = (config_overrides.get('ERPNEXT_API_TOKEN') or os.getenv('ERPNEXT_API_TOKEN') or '').strip()
        self._auth_header_value = None
        self._normalize_auth_credentials()
        self.timeout = int(config_overrides.get('ERPNEXT_TIMEOUT') or os.getenv('ERPNEXT_TIMEOUT', '20'))

        self.default_company = (config_overrides.get('ERPNEXT_DEFAULT_COMPANY') or os.getenv('ERPNEXT_DEFAULT_COMPANY', '')).strip() or None
        self.default_item_code = (config_overrides.get('ERPNEXT_DEFAULT_ITEM_CODE') or os.getenv('ERPNEXT_DEFAULT_ITEM_CODE', 'NUZUM-SERVICE')).strip()
        self.default_item_group = (config_overrides.get('ERPNEXT_DEFAULT_ITEM_GROUP') or os.getenv('ERPNEXT_DEFAULT_ITEM_GROUP', 'Services')).strip()
        self.default_uom = (config_overrides.get('ERPNEXT_DEFAULT_UOM') or os.getenv('ERPNEXT_DEFAULT_UOM', 'Nos')).strip()
        self.vat_account_head = (config_overrides.get('ERPNEXT_VAT_ACCOUNT_HEAD') or os.getenv('ERPNEXT_VAT_ACCOUNT_HEAD', '')).strip() or None
        self.apply_nuzum_logo = ERPNextClient._as_bool(
            config_overrides.get('ERPNEXT_APPLY_NUZUM_LOGO', os.getenv('ERPNEXT_APPLY_NUZUM_LOGO', False)),
            default=False,
        )
        self.print_format = (config_overrides.get('ERPNEXT_PRINT_FORMAT') or os.getenv('ERPNEXT_PRINT_FORMAT', 'Standard')).strip()
        self.print_lang = (config_overrides.get('ERPNEXT_PRINT_LANG') or os.getenv('ERPNEXT_PRINT_LANG', 'ar')).strip()
        self.letter_head_name = (config_overrides.get('ERPNEXT_LETTER_HEAD') or os.getenv('ERPNEXT_LETTER_HEAD', 'NUZUM')).strip()

    def _normalize_auth_credentials(self):
        token = str(self.api_token or '').strip()
        if token:
            if token.lower().startswith('bearer ') or token.lower().startswith('token '):
                self._auth_header_value = token
                self.api_key = ''
                self.api_secret = ''
                return
            if ':' in token:
                parsed_key, parsed_secret = token.split(':', 1)
                self.api_key = parsed_key.strip()
                self.api_secret = parsed_secret.strip()
                return

        key = str(self.api_key or '').strip()
        secret = str(self.api_secret or '').strip()

        combined = key or secret
        lower_combined = combined.lower()

        if lower_combined.startswith('bearer '):
            self._auth_header_value = combined
            self.api_key = ''
            self.api_secret = ''
            return

        token_value = None
        if lower_combined.startswith('token '):
            token_value = combined[6:].strip()
        elif key.lower().startswith('token '):
            token_value = key[6:].strip()
        elif secret.lower().startswith('token '):
            token_value = secret[6:].strip()

        if token_value and ':' in token_value:
            parsed_key, parsed_secret = token_value.split(':', 1)
            self.api_key = parsed_key.strip()
            self.api_secret = parsed_secret.strip()
            return

        if key and ':' in key and not secret:
            parsed_key, parsed_secret = key.split(':', 1)
            self.api_key = parsed_key.strip()
            self.api_secret = parsed_secret.strip()
            return

        if secret and ':' in secret and not key:
            parsed_key, parsed_secret = secret.split(':', 1)
            self.api_key = parsed_key.strip()
            self.api_secret = parsed_secret.strip()
            return

        self.api_key = key
        self.api_secret = secret

    def is_configured(self):
        has_token = bool(self.api_key and self.api_secret)
        has_auth_header = bool(self._auth_header_value)
        return bool(self.base_url and (has_token or has_auth_header))

    def _headers(self):
        if not self.is_configured():
            raise ERPNextBridgeError('ERPNext configuration is missing in environment variables.')

        auth_value = self._auth_header_value or f'token {self.api_key}:{self.api_secret}'
        return {
            'Authorization': auth_value,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _url(self, path):
        return f'{self.base_url}{path}'

    def _request(self, method, path, params=None, payload=None):
        try:
            response = requests.request(
                method=method,
                url=self._url(path),
                headers=self._headers(),
                params=params,
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise ERPNextBridgeError('ERPNext request timed out.') from exc
        except requests.RequestException as exc:
            raise ERPNextBridgeError(f'ERPNext connectivity error: {exc}') from exc

        if response.status_code in (401, 403):
            raise ERPNextBridgeError(
                'ERPNext authentication failed (401/403). '
                'تحقق من Base URL ومفاتيح API Key/API Secret أو استخدم ERPNEXT_API_TOKEN بصيغة token key:secret.'
            )

        if response.status_code >= 400:
            message = response.text
            try:
                message = response.json()
            except Exception:
                pass
            raise ERPNextBridgeError(f'ERPNext API error ({response.status_code}): {message}')

        try:
            return response.json()
        except ValueError as exc:
            raise ERPNextBridgeError('ERPNext returned non-JSON response.') from exc

    def test_connection(self):
        result = self._request('GET', '/api/method/frappe.auth.get_logged_user')
        return {'ok': True, 'user': result.get('message')}

    def get_request(self, doctype, filters=None, fields=None, limit=20):
        params = {
            'limit_page_length': limit,
        }
        if fields:
            params['fields'] = json.dumps(fields)
        if filters:
            params['filters'] = json.dumps(filters)

        result = self._request('GET', f'/api/resource/{doctype}', params=params)
        return result.get('data', [])

    def post_request(self, doctype, data):
        result = self._request('POST', f'/api/resource/{doctype}', payload=data)
        return result.get('data', result)

    def ensure_customer(self, customer_name, customer_data=None):
        customer_data = customer_data or {}
        existing = self.get_request(
            'Customer',
            filters=[["Customer", "customer_name", "=", customer_name]],
            fields=['name', 'customer_name'],
            limit=1,
        )
        if existing:
            return existing[0]['name']

        payload = {
            'customer_name': customer_name,
            'customer_type': customer_data.get('customer_type', 'Company'),
            'customer_group': customer_data.get('customer_group', 'All Customer Groups'),
            'territory': customer_data.get('territory', 'Saudi Arabia'),
        }

        tax_id = customer_data.get('tax_id')
        if tax_id:
            payload['tax_id'] = tax_id

        created = self.post_request('Customer', payload)
        return created.get('name')

    def ensure_service_item(self):
        existing = self.get_request(
            'Item',
            filters=[["Item", "item_code", "=", self.default_item_code]],
            fields=['name', 'item_code'],
            limit=1,
        )
        if existing:
            return existing[0]['item_code']

        payload = {
            'item_code': self.default_item_code,
            'item_name': self.default_item_code,
            'is_stock_item': 0,
            'item_group': self.default_item_group,
            'stock_uom': self.default_uom,
        }
        created = self.post_request('Item', payload)
        return created.get('item_code', self.default_item_code)

    def _resolve_payment_terms_template(self, payment_terms):
        template_name = str(payment_terms or '').strip()
        if not template_name:
            return None

        existing = self.get_request(
            'Payment Terms Template',
            filters=[["Payment Terms Template", "name", "=", template_name]],
            fields=['name'],
            limit=1,
        )
        if existing:
            return existing[0].get('name')
        return None

    def disable_account_by_code_or_name(self, account_code, account_name):
        candidates = []
        for filters in (
            [["Account", "account_number", "=", str(account_code or '').strip()]],
            [["Account", "name", "=", str(account_code or '').strip()]],
            [["Account", "account_name", "=", str(account_name or '').strip()]],
        ):
            docs = self.get_request('Account', filters=filters, fields=['name', 'disabled'], limit=5)
            for doc in docs:
                doc_name = doc.get('name')
                if doc_name and doc_name not in candidates:
                    candidates.append(doc_name)

        if not candidates:
            return {'disabled': False, 'updated': 0, 'message': 'account_not_found_in_erp'}

        updated = 0
        for account_doc_name in candidates:
            self._request(
                'PUT',
                f"/api/resource/Account/{quote(account_doc_name, safe='')}",
                payload={'disabled': 1},
            )
            updated += 1

        return {'disabled': True, 'updated': updated, 'accounts': candidates}

    def get_accounting_health_report(self, limit=200):
        journal_entries = self.get_request(
            'Journal Entry',
            fields=['name', 'posting_date', 'total_debit', 'total_credit', 'cheque_no', 'title'],
            limit=limit,
        )

        unbalanced_entries = []
        duplicate_buckets = defaultdict(list)

        for entry in journal_entries:
            total_debit = float(entry.get('total_debit') or 0)
            total_credit = float(entry.get('total_credit') or 0)
            if round(total_debit - total_credit, 2) != 0:
                unbalanced_entries.append({
                    'name': entry.get('name'),
                    'posting_date': entry.get('posting_date'),
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'difference': round(total_debit - total_credit, 2),
                })

            reference_no = str(entry.get('cheque_no') or entry.get('title') or '').strip()
            if reference_no:
                dup_key = (entry.get('posting_date'), reference_no, round(total_debit, 2))
                duplicate_buckets[dup_key].append(entry)

        duplicate_references = []
        for (posting_date, reference_no, amount_value), rows in duplicate_buckets.items():
            if len(rows) > 1:
                duplicate_references.append({
                    'posting_date': posting_date,
                    'reference_no': reference_no,
                    'amount': amount_value,
                    'entries': [row.get('name') for row in rows],
                    'count': len(rows),
                })

        journal_accounts = self.get_request(
            'Journal Entry Account',
            fields=['parent', 'account', 'debit_in_account_currency', 'credit_in_account_currency'],
            limit=max(500, limit * 4),
        )
        touched_accounts = sorted({row.get('account') for row in journal_accounts if row.get('account')})

        group_accounts_with_transactions = []
        for account_name in touched_accounts[:400]:
            account_docs = self.get_request(
                'Account',
                filters=[["Account", "name", "=", account_name]],
                fields=['name', 'account_name', 'is_group', 'disabled'],
                limit=1,
            )
            if not account_docs:
                continue
            account_doc = account_docs[0]
            is_group = int(account_doc.get('is_group') or 0) == 1
            if not is_group:
                continue

            sample_row = next((row for row in journal_accounts if row.get('account') == account_name), None)
            group_accounts_with_transactions.append({
                'account': account_doc.get('name'),
                'account_name': account_doc.get('account_name') or account_doc.get('name'),
                'disabled': int(account_doc.get('disabled') or 0) == 1,
                'sample_journal_entry': sample_row.get('parent') if sample_row else None,
            })

        issue_count = len(unbalanced_entries) + len(duplicate_references) + len(group_accounts_with_transactions)
        scanned_count = max(1, len(journal_entries))
        issue_ratio = min(1.0, issue_count / scanned_count)
        cleanliness_score = max(0, int(round((1.0 - issue_ratio) * 100)))

        return {
            'ok': True,
            'scanned_journal_entries': len(journal_entries),
            'scanned_journal_lines': len(journal_accounts),
            'cleanliness_score': cleanliness_score,
            'issues_total': issue_count,
            'unbalanced_entries': unbalanced_entries,
            'duplicate_references': duplicate_references,
            'group_accounts_with_transactions': group_accounts_with_transactions,
            'generated_at': datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _month_bounds(month, year):
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        return start_date, end_date

    def build_contract_invoice_data(self, contract_id, month, year, manual_ot_hours=0.0):
        contract = ProjectContract.query.get_or_404(contract_id)
        resources = contract.resources.filter_by(is_active=True).all()

        period_start, period_end = self._month_bounds(month, year)
        status_billable = ['present', 'late', 'early_leave']

        lines = []
        total_amount = Decimal('0')
        resource_rates = []

        for resource in resources:
            attendance_days = Attendance.query.filter(
                Attendance.employee_id == resource.employee_id,
                Attendance.date >= period_start,
                Attendance.date < period_end,
                Attendance.status.in_(status_billable),
            ).count()

            rate = Decimal(str(resource.billing_rate or 0))
            if rate > 0:
                resource_rates.append(float(rate))
            if resource.billing_type == 'daily':
                amount = Decimal(attendance_days) * rate
                qty = float(attendance_days)
                line_desc = f"{resource.employee.name} — {attendance_days} أيام × {rate:.2f} SAR"
            else:
                amount = rate
                qty = 1.0
                line_desc = f"{resource.employee.name} — تعاقد شهري"

            amount = amount.quantize(Decimal('0.01'))
            if amount <= 0:
                continue

            lines.append({
                'employee_id': resource.employee_id,
                'employee_name': resource.employee.name,
                'billing_type': resource.billing_type,
                'resource_notes': resource.notes,
                'is_overtime': False,
                'days_worked': attendance_days,
                'daily_rate': float(rate),
                'qty': qty,
                'rate': float(rate),
                'amount': float(amount),
                'description': line_desc,
            })
            total_amount += amount

            salary_row = Salary.query.filter_by(
                employee_id=resource.employee_id,
                month=month,
                year=year,
            ).order_by(Salary.updated_at.desc()).first()
            overtime_hours = float(getattr(salary_row, 'overtime_hours', 0) or 0)
            if overtime_hours > 0:
                ot_amount = (Decimal(str(overtime_hours)) * rate).quantize(Decimal('0.01'))
                lines.append({
                    'employee_id': resource.employee_id,
                    'employee_name': resource.employee.name,
                    'billing_type': 'hourly_ot',
                    'resource_notes': (resource.notes or '') + ' OT',
                    'is_overtime': True,
                    'days_worked': attendance_days,
                    'daily_rate': float(rate),
                    'qty': overtime_hours,
                    'rate': float(rate),
                    'amount': float(ot_amount),
                    'description': f"Labor O.T ({rate:.2f} SAR * {overtime_hours:.2f} H)",
                })
                total_amount += ot_amount

        manual_ot_hours_value = float(manual_ot_hours or 0)
        if manual_ot_hours_value > 0:
            manual_ot_rate = float(resource_rates[0]) if resource_rates else 0.0
            if manual_ot_rate <= 0:
                raise ERPNextBridgeError('Manual OT hours were provided but no valid contract billing rate was found.')

            manual_ot_amount = (Decimal(str(manual_ot_hours_value)) * Decimal(str(manual_ot_rate))).quantize(Decimal('0.01'))
            lines.append({
                'employee_id': None,
                'employee_name': 'Manual Overtime',
                'billing_type': 'hourly_ot',
                'resource_notes': 'Manual OT',
                'is_overtime': True,
                'days_worked': 0,
                'daily_rate': manual_ot_rate,
                'qty': manual_ot_hours_value,
                'rate': manual_ot_rate,
                'amount': float(manual_ot_amount),
                'description': f"Labor O.T ({manual_ot_rate:.2f} SAR * {manual_ot_hours_value:.2f} H)",
            })
            total_amount += manual_ot_amount

        return {
            'contract': contract,
            'lines': lines,
            'total_amount': float(total_amount.quantize(Decimal('0.01'))),
            'month': month,
            'year': year,
        }

    @validate_accounting_entry
    def create_sales_invoice_for_contract(self, contract_id, month, year, tax_rate=15.0, discount=0.0, payment_terms='', manual_ot_hours=0.0, entries=None, validation_meta=None):
        billing = self.build_contract_invoice_data(contract_id, month, year, manual_ot_hours=manual_ot_hours)
        contract = billing['contract']
        lines = billing['lines']

        if not lines:
            raise ERPNextBridgeError('No billable attendance records found for this contract and period.')

        customer_name = contract.client_name.strip()
        customer = self.ensure_customer(customer_name)
        item_code = self.ensure_service_item()

        def _is_ot_line(line_data):
            if bool(line_data.get('is_overtime')):
                return True
            note_text = str(line_data.get('resource_notes') or '').strip().lower()
            return any(keyword in note_text for keyword in ('ot', 'o.t', 'overtime', 'اضافي', 'إضافي'))

        def _service_name(line_data):
            return 'Labor O.T' if _is_ot_line(line_data) else 'Labor'

        def _qty_label(line_data, qty_value):
            if _is_ot_line(line_data):
                return f"{int(qty_value)} H"
            if str(line_data.get('billing_type') or '').strip().lower() == 'daily':
                return f"{int(qty_value)} Days"
            return f"{int(qty_value)} Days"

        posting_date = date(year, month, 1).isoformat()
        due_date = date.today().isoformat()

        grouped_items = {}
        for line in lines:
            service_name = _service_name(line)
            rate_value = float(line.get('rate') or 0)
            group_key = (service_name, rate_value)

            if group_key not in grouped_items:
                grouped_items[group_key] = {
                    'service_name': service_name,
                    'rate': rate_value,
                    'qty': 0.0,
                    'amount': 0.0,
                }

            grouped_items[group_key]['qty'] += float(line.get('qty') or 0)
            grouped_items[group_key]['amount'] += float(line.get('amount') or 0)

        items = []
        for (_, _), entry in grouped_items.items():
            qty = round(float(entry['qty']), 2)
            rate_value = float(entry['rate'])
            amount_value = round(float(entry['amount']), 2)
            source_line = next((line for line in lines if _service_name(line) == entry['service_name'] and float(line.get('rate') or 0) == rate_value), None)
            qty_label = _qty_label(source_line or {}, qty)
            description = f"{entry['service_name']} ({rate_value:.2f} SAR * {qty_label})"

            items.append({
                'item_code': item_code,
                'item_name': entry['service_name'],
                'description': description,
                'qty': qty,
                'rate': rate_value,
                'amount': amount_value,
            })

        invoice_payload = {
            'doctype': 'Sales Invoice',
            'customer': customer,
            'posting_date': posting_date,
            'due_date': due_date,
            'currency': 'SAR',
            'items': items,
            'taxes': [
                {
                    'charge_type': 'On Net Total',
                    'description': 'VAT 15%',
                    'rate': float(tax_rate or 0),
                }
            ],
            'remarks': f"NUZUM Auto Invoice for contract #{contract.id} ({month}/{year})",
        }

        discount_value = max(0.0, float(discount or 0))
        if discount_value > 0:
            invoice_payload['apply_discount_on'] = 'Grand Total'
            invoice_payload['discount_amount'] = discount_value

        payment_terms_template = self._resolve_payment_terms_template(payment_terms)
        if payment_terms_template:
            invoice_payload['payment_terms_template'] = payment_terms_template

        if self.apply_nuzum_logo and self.letter_head_name:
            invoice_payload['letter_head'] = self.letter_head_name

        if self.default_company:
            invoice_payload['company'] = self.default_company
        if self.vat_account_head:
            invoice_payload['taxes'][0]['account_head'] = self.vat_account_head

        created = self.post_request('Sales Invoice', invoice_payload)
        invoice_name = created.get('name')

        pdf_url = None
        if invoice_name:
            encoded_name = quote(invoice_name, safe='')
            encoded_format = quote(self.print_format or 'Standard', safe='')
            encoded_lang = quote(self.print_lang or 'ar', safe='')
            no_letterhead = '0' if self.apply_nuzum_logo else '1'
            pdf_url = (
                f"{self.base_url}/printview?doctype=Sales%20Invoice&name={encoded_name}"
                f"&format={encoded_format}&no_letterhead={no_letterhead}&_lang={encoded_lang}"
            )
            if self.apply_nuzum_logo and self.letter_head_name:
                pdf_url += f"&letterhead={quote(self.letter_head_name, safe='')}"

        return {
            'invoice_name': invoice_name,
            'pdf_url': pdf_url,
            'customer': customer,
            'total_amount': f"{billing['total_amount']:.2f} SAR",
            'discount': f"{discount_value:.2f} SAR",
            'tax_rate': float(tax_rate or 0),
            'lines_count': len(lines),
            'period': f"{month:02d}/{year}",
        }

    def list_sales_invoices(self, limit=20):
        fields = ['name', 'customer', 'grand_total', 'outstanding_amount', 'status', 'posting_date', 'currency']
        invoices = self.get_request('Sales Invoice', fields=fields, limit=limit)

        for invoice in invoices:
            grand_total = float(invoice.get('grand_total') or 0)
            invoice['grand_total_formatted'] = f"{grand_total:,.2f} SAR"
            invoice['currency'] = invoice.get('currency') or 'SAR'

        return invoices

    def sync_contract_customer(self, contract_id):
        contract = ProjectContract.query.get_or_404(contract_id)
        customer_name = (contract.client_name or '').strip()
        if not customer_name:
            raise ERPNextBridgeError('Contract client name is empty and cannot be synced.')

        existing = self.get_request(
            'Customer',
            filters=[["Customer", "customer_name", "=", customer_name]],
            fields=['name', 'customer_name'],
            limit=1,
        )
        if existing:
            return {
                'created': False,
                'customer': existing[0].get('name'),
                'customer_name': customer_name,
                'contract_id': contract.id,
            }

        created_customer = self.ensure_customer(customer_name)
        return {
            'created': True,
            'customer': created_customer,
            'customer_name': customer_name,
            'contract_id': contract.id,
        }
