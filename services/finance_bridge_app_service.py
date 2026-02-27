"""
Application-level services for Finance Bridge UI/routes.

Keeps routes thin by isolating:
- settings persistence
- dashboard aggregations/pagination
- invoice preview math
"""

import json
import math
import os
from pathlib import Path
from urllib.parse import quote


def _escape_html(value):
    return (
        str(value or '')
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


class FinanceBridgeSettingsService:
    DEFAULT_INVOICE_PROFILE = {
        'company_name_en': 'RAS SAUDI COMPANY LTD',
        'company_name_ar': 'شركة راس السعودية المحدودة',
        'address_en': 'Olaya Street- Al Nimer Center#1-7TH Riyadh , Kingdom Of Saudi Arabia',
        'address_ar': 'حي العليا - مركز النمر - الرياض - المملكة العربية السعودية',
        'phone_en': '',
        'phone_ar': '',
        'fax_en': '',
        'fax_ar': '',
        'vat_no_en': '',
        'vat_no_ar': '',
        'logo_url': '',
        'customer_id_default': '',
        'customer_name_en_default': '',
        'customer_name_ar_default': '',
        'customer_vat_default': '',
        'customer_address_en_default': '',
        'customer_address_ar_default': '',
        'customer_ref_default': '',
        'delivery_term_default': '',
        'delivery_address_default': '',
        'payment_term_default': '15 Days Credit',
    }

    @staticmethod
    def _is_masked(value):
        return str(value or '').strip() == '********'

    @staticmethod
    def _settings_file_path():
        return Path('instance') / 'finance_bridge_settings.json'

    @staticmethod
    def load_settings():
        settings_file = FinanceBridgeSettingsService._settings_file_path()
        if not settings_file.exists():
            return {}

        try:
            settings = json.loads(settings_file.read_text(encoding='utf-8'))
            for key in ('ERPNEXT_API_KEY', 'ERPNEXT_API_SECRET'):
                if FinanceBridgeSettingsService._is_masked(settings.get(key)):
                    settings.pop(key, None)
            return settings
        except Exception:
            return {}

    @staticmethod
    def save_settings(settings_data):
        settings_file = FinanceBridgeSettingsService._settings_file_path()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps(settings_data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def apply_runtime_env(settings_data):
        for key in (
            'ERPNEXT_API_KEY',
            'ERPNEXT_API_SECRET',
            'ERPNEXT_BASE_URL',
            'ERPNEXT_VAT_ACCOUNT_HEAD',
            'ERPNEXT_PRINT_FORMAT',
            'ERPNEXT_PRINT_LANG',
            'ERPNEXT_LETTER_HEAD',
        ):
            value = settings_data.get(key)
            if value is not None and not FinanceBridgeSettingsService._is_masked(value):
                os.environ[key] = str(value)

    @staticmethod
    def get_invoice_profile(settings_data):
        profile = dict(FinanceBridgeSettingsService.DEFAULT_INVOICE_PROFILE)
        saved = settings_data.get('invoice_profile') or {}
        if isinstance(saved, dict):
            for key in profile.keys():
                if saved.get(key) is not None:
                    profile[key] = str(saved.get(key))
        return profile

    @staticmethod
    def _as_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

    @staticmethod
    def get_print_format(settings_data):
        return (
            settings_data.get('ERPNEXT_PRINT_FORMAT')
            or os.getenv('ERPNEXT_PRINT_FORMAT')
            or 'Standard'
        ).strip()

    @staticmethod
    def get_print_lang(settings_data):
        return (
            settings_data.get('ERPNEXT_PRINT_LANG')
            or os.getenv('ERPNEXT_PRINT_LANG')
            or 'ar'
        ).strip()

    @staticmethod
    def get_letter_head(settings_data):
        return (
            settings_data.get('ERPNEXT_LETTER_HEAD')
            or os.getenv('ERPNEXT_LETTER_HEAD')
            or 'NUZUM'
        ).strip()

    @staticmethod
    def format_sar(value):
        return f"{float(value or 0):,.2f} SAR"

    @staticmethod
    def get_base_url(settings_data):
        return (settings_data.get('ERPNEXT_BASE_URL') or os.getenv('ERPNEXT_BASE_URL', '')).rstrip('/')

    @staticmethod
    def build_invoice_pdf_url(settings_data, invoice_name):
        base_url = FinanceBridgeSettingsService.get_base_url(settings_data)
        if not base_url:
            return None

        encoded_name = quote(invoice_name, safe='')
        print_format = quote(FinanceBridgeSettingsService.get_print_format(settings_data), safe='')
        print_lang = quote(FinanceBridgeSettingsService.get_print_lang(settings_data), safe='')
        use_letterhead = FinanceBridgeSettingsService._as_bool(settings_data.get('ERPNEXT_APPLY_NUZUM_LOGO'), default=False)
        no_letterhead = '0' if use_letterhead else '1'
        pdf_url = (
            f"{base_url}/printview?doctype=Sales%20Invoice&name={encoded_name}"
            f"&format={print_format}&no_letterhead={no_letterhead}&_lang={print_lang}"
        )
        if use_letterhead:
            letter_head = FinanceBridgeSettingsService.get_letter_head(settings_data)
            if letter_head:
                pdf_url += f"&letterhead={quote(letter_head, safe='')}"
        return pdf_url

    @staticmethod
    def build_professional_invoice_html(invoice_profile):
        p = dict(FinanceBridgeSettingsService.DEFAULT_INVOICE_PROFILE)
        p.update(invoice_profile or {})

        c_name_en = _escape_html(p.get('company_name_en'))
        c_name_ar = _escape_html(p.get('company_name_ar'))
        address_en = _escape_html(p.get('address_en'))
        address_ar = _escape_html(p.get('address_ar'))
        phone_en = _escape_html(p.get('phone_en'))
        phone_ar = _escape_html(p.get('phone_ar'))
        fax_en = _escape_html(p.get('fax_en'))
        fax_ar = _escape_html(p.get('fax_ar'))
        vat_no_en = _escape_html(p.get('vat_no_en'))
        vat_no_ar = _escape_html(p.get('vat_no_ar'))
        logo_url = _escape_html(p.get('logo_url'))
        customer_id_default = _escape_html(p.get('customer_id_default'))
        customer_name_en_default = _escape_html(p.get('customer_name_en_default'))
        customer_name_ar_default = _escape_html(p.get('customer_name_ar_default'))
        customer_vat_default = _escape_html(p.get('customer_vat_default'))
        customer_address_en_default = _escape_html(p.get('customer_address_en_default'))
        customer_address_ar_default = _escape_html(p.get('customer_address_ar_default'))
        customer_ref_default = _escape_html(p.get('customer_ref_default'))
        delivery_term_default = _escape_html(p.get('delivery_term_default'))
        delivery_address_default = _escape_html(p.get('delivery_address_default'))
        payment_term_default = _escape_html(p.get('payment_term_default'))

        return f'''
<style>
    @page {{ size: A4; margin: 8mm; }}
    .inv {{ font-family: Arial, "Tajawal", sans-serif; font-size: 11px; color:#111; margin:0; padding:0; }}
    .top-grid {{ width:100%; border-collapse:collapse; table-layout:fixed; margin-top:2px; }}
    .top-grid td {{ vertical-align:top; }}
    .en {{ direction:ltr; text-align:left; }}
    .ar {{ direction:rtl; text-align:right; }}
    .hdr-lbl {{ font-weight:700; }}
    .hdr-line {{ margin:0 0 2px; line-height:1.15; font-size:12px; }}
    .logo-wrap {{ text-align:center; }}
    .logo-wrap img {{ max-height:72px; max-width:220px; object-fit:contain; }}
    .title {{ text-align:center; font-weight:700; font-size:44px; line-height:1; margin:8px 0 0; }}
    .sub-title {{ text-align:center; font-weight:700; font-size:22px; margin:0 0 8px; }}
    .b {{ border:1px solid #111; border-collapse:collapse; width:100%; }}
    .b td, .b th {{ border:1px solid #111; padding:3px 5px; }}
    .b th {{ background:#d0d0d0; font-weight:700; text-align:center; }}
    .gray {{ background:#efefef; }}
    .center {{ text-align:center; }}
    .right {{ text-align:right; }}
    .small {{ font-size:10px; }}
    .mt6 {{ margin-top:6px; }}
    .mt10 {{ margin-top:10px; }}
    .row {{ width:100%; display:table; table-layout:fixed; }}
    .cell {{ display:table-cell; vertical-align:top; }}
    .w40 {{ width:40%; }}
    .w60 {{ width:60%; }}
</style>

<div class="inv">
    <table class="top-grid">
        <tr>
            <td style="width:38%;" class="en">
                <div class="hdr-line"><span class="hdr-lbl">Company :</span> {c_name_en}</div>
                <div class="hdr-line"><span class="hdr-lbl">Address :</span> {address_en}</div>
                <div class="hdr-line"><span class="hdr-lbl">Phone :</span> {{{{ doc.company_phone_no or '{phone_en}' }}}}</div>
                <div class="hdr-line"><span class="hdr-lbl">Fax No :</span> {{{{ doc.company_fax or '{fax_en}' }}}}</div>
                <div class="hdr-line"><span class="hdr-lbl">VAT No :</span> {{{{ doc.company_tax_id or doc.tax_id or '{vat_no_en}' }}}}</div>
            </td>
            <td style="width:24%;" class="logo-wrap">
                {{% set _custom_logo = "{logo_url}" %}}
                {{% set _img = None %}}
                {{% if not _custom_logo and doc.letter_head %}}
                    {{% set _img = frappe.db.get_value('Letter Head', doc.letter_head, 'image') %}}
                {{% endif %}}
                {{% if _custom_logo %}}
                    <img src="{{{{ _custom_logo }}}}">
                {{% elif _img %}}
                    <img src="{{{{ _img }}}}">
                {{% else %}}
                    <div style="font-size:34px;font-weight:700;letter-spacing:1px;color:#555;margin-top:10px;">RASSCO</div>
                {{% endif %}}
            </td>
            <td style="width:38%;" class="ar">
                <table style="width:100%; border-collapse:collapse;">
                    <tr><td class="hdr-line" style="width:26%;">شركة</td><td class="hdr-line">: {c_name_ar}</td></tr>
                    <tr><td class="hdr-line">العنوان</td><td class="hdr-line">: {address_ar}</td></tr>
                    <tr><td class="hdr-line">هاتف</td><td class="hdr-line">: {{{{ doc.company_phone_no or '{phone_ar}' }}}}</td></tr>
                    <tr><td class="hdr-line">فاكس</td><td class="hdr-line">: {{{{ doc.company_fax or '{fax_ar}' }}}}</td></tr>
                    <tr><td class="hdr-line">رقم التسجيل الضريبي</td><td class="hdr-line">: {{{{ doc.company_tax_id or doc.tax_id or '{vat_no_ar}' }}}}</td></tr>
                </table>
            </td>
        </tr>
    </table>

    <div class="title">Tax Invoice</div>
    <div class="sub-title ar">فاتورة ضريبية</div>

    <table class="b mt6">
        <tr>
            <th style="width:50%;">Buyer Details</th>
            <th style="width:50%;">Seller Other Details</th>
        </tr>
        <tr>
            <td>
                <table class="b" style="width:100%; border:none;">
                    <tr><td class="gray" style="width:40%;">ID No.</td><td>{{{{ doc.customer or '{customer_id_default}' }}}}</td></tr>
                    <tr><td class="gray">Name</td><td>{{{{ doc.customer_name or doc.customer or '{customer_name_en_default}' }}}}{{% if not doc.customer_name and '{customer_name_ar_default}' %}}<br><span class="ar">{customer_name_ar_default}</span>{{% endif %}}</td></tr>
                    <tr><td class="gray">VAT No.</td><td>{{{{ doc.tax_id or '{customer_vat_default}' }}}}</td></tr>
                    <tr><td class="gray">Address</td><td>{{{{ doc.address_display or '{customer_address_en_default}' }}}}{{% if not doc.address_display and '{customer_address_ar_default}' %}}<br><span class="ar">{customer_address_ar_default}</span>{{% endif %}}</td></tr>
                </table>
            </td>
            <td>
                <table class="b" style="width:100%; border:none;">
                    <tr><td class="gray" style="width:40%;">Invoice No.</td><td>{{{{ doc.name }}}}</td></tr>
                    <tr><td class="gray">Invoice Date</td><td>{{{{ frappe.utils.formatdate(doc.posting_date) }}}}</td></tr>
                    <tr><td class="gray">Posting Date</td><td>{{{{ frappe.utils.formatdate(doc.posting_date) }}}}</td></tr>
                    <tr><td class="gray">Customer Ref.</td><td>{{{{ doc.po_no or '{customer_ref_default}' }}}}</td></tr>
                    <tr><td class="gray">Delivery Term</td><td>{{{{ doc.incoterm or '{delivery_term_default}' }}}}</td></tr>
                    <tr><td class="gray">Delivery Address</td><td>{{{{ doc.shipping_address_name or doc.address_display or '{delivery_address_default}' }}}}</td></tr>
                    <tr><td class="gray">Payment Term</td><td>{{{{ doc.payment_terms_template or '{payment_term_default}' }}}}</td></tr>
                    <tr><td class="gray">Currency</td><td>{{{{ doc.currency }}}}</td></tr>
                    <tr><td class="gray">Description</td><td>{{{{ doc.remarks or '' }}}}</td></tr>
                </table>
            </td>
        </tr>
    </table>

    <table class="b mt10">
        <tr>
            <th style="width:5%;">Serial<br>No.<br><span class="ar">الرقم التسلسلي</span></th>
            <th style="width:18%;">Nature of Goods or Service<br><span class="ar">طبيعة البضاعة أو الخدمة</span></th>
            <th style="width:30%;">DESCRIPTION<br><span class="ar">وصف</span></th>
            <th style="width:11%;">Taxable Amount<br><span class="ar">المبلغ الخاضع للضريبة</span></th>
            <th style="width:8%;">VAT Rate<br><span class="ar">قيمة الضريبة</span></th>
            <th style="width:12%;">VAT Amount<br><span class="ar">مبلغ الضريبة</span></th>
            <th style="width:16%;">Amount with VAT<br><span class="ar">المبلغ مع ضريبة القيمة المضافة</span></th>
        </tr>
        {{% for row in doc.items %}}
        {{% set vat_amount = ((row.amount or 0) * 0.15) %}}
        <tr>
            <td class="center">{{{{ loop.index }}}}</td>
            <td>{{{{ row.item_name or row.item_code }}}}</td>
            <td>{{{{ row.description or '' }}}}</td>
            <td class="right">{{{{ frappe.format_value(row.amount, {{'fieldtype':'Currency'}}) }}}}</td>
            <td class="center">15 %</td>
            <td class="right">{{{{ frappe.format_value(vat_amount, {{'fieldtype':'Currency'}}) }}}}</td>
            <td class="right">{{{{ frappe.format_value((row.amount or 0) + vat_amount, {{'fieldtype':'Currency'}}) }}}}</td>
        </tr>
        {{% endfor %}}
        <tr><td colspan="7" class="small">Count : ( {{{{ doc.items|length }}}} )</td></tr>
    </table>

    <div class="row mt10">
        <div class="cell w40 center" style="padding-right:8px;">
            <table class="b" style="height:180px;"><tr><td class="center" style="height:170px;">{{% set _qr = (doc.ksa_einv_qr or '')|trim %}}{{% if _qr %}}{{% if _qr.startswith('data:image') or _qr.startswith('http') %}}<img src="{{{{ _qr }}}}" style="width:150px; height:150px; object-fit:contain;">{{% else %}}<img src="data:image/png;base64,{{{{ _qr }}}}" style="width:150px; height:150px; object-fit:contain;">{{% endif %}}{{% else %}}<svg xmlns="http://www.w3.org/2000/svg" width="150" height="150" viewBox="0 0 150 150" style="border:1px solid #222;"><rect width="150" height="150" fill="#fff"/><rect x="8" y="8" width="30" height="30" fill="#000"/><rect x="14" y="14" width="18" height="18" fill="#fff"/><rect x="118" y="8" width="24" height="24" fill="#000"/><rect x="12" y="118" width="24" height="24" fill="#000"/><rect x="48" y="16" width="6" height="6" fill="#000"/><rect x="60" y="16" width="6" height="6" fill="#000"/><rect x="72" y="16" width="6" height="6" fill="#000"/><rect x="84" y="16" width="6" height="6" fill="#000"/><rect x="48" y="28" width="6" height="6" fill="#000"/><rect x="72" y="28" width="6" height="6" fill="#000"/><rect x="96" y="28" width="6" height="6" fill="#000"/><rect x="48" y="40" width="6" height="6" fill="#000"/><rect x="60" y="40" width="6" height="6" fill="#000"/><rect x="84" y="40" width="6" height="6" fill="#000"/><rect x="96" y="40" width="6" height="6" fill="#000"/><rect x="48" y="52" width="6" height="6" fill="#000"/><rect x="60" y="52" width="6" height="6" fill="#000"/><rect x="72" y="52" width="6" height="6" fill="#000"/><rect x="84" y="52" width="6" height="6" fill="#000"/><rect x="96" y="52" width="6" height="6" fill="#000"/><rect x="48" y="64" width="6" height="6" fill="#000"/><rect x="72" y="64" width="6" height="6" fill="#000"/><rect x="96" y="64" width="6" height="6" fill="#000"/><rect x="48" y="76" width="6" height="6" fill="#000"/><rect x="60" y="76" width="6" height="6" fill="#000"/><rect x="72" y="76" width="6" height="6" fill="#000"/><rect x="84" y="76" width="6" height="6" fill="#000"/><rect x="96" y="76" width="6" height="6" fill="#000"/><rect x="48" y="88" width="6" height="6" fill="#000"/><rect x="72" y="88" width="6" height="6" fill="#000"/><rect x="96" y="88" width="6" height="6" fill="#000"/><text x="75" y="136" font-size="9" text-anchor="middle" fill="#222">QR Pending</text></svg>{{% endif %}}</td></tr></table>
        </div>
        <div class="cell w60">
            <table class="b">
                <tr><td class="gray">Total Amount (Excluding VAT)</td><td class="right">{{{{ frappe.format_value(doc.net_total, {{'fieldtype':'Currency'}}) }}}}</td></tr>
                <tr><td class="gray">Discounts</td><td class="right">{{{{ frappe.format_value(doc.discount_amount or 0, {{'fieldtype':'Currency'}}) }}}}</td></tr>
                <tr><td class="gray">Total Taxable Amount (Excluding VAT)</td><td class="right">{{{{ frappe.format_value((doc.net_total or 0) - (doc.discount_amount or 0), {{'fieldtype':'Currency'}}) }}}}</td></tr>
                <tr><td class="gray">Total VAT</td><td class="right">{{{{ frappe.format_value(doc.total_taxes_and_charges, {{'fieldtype':'Currency'}}) }}}}</td></tr>
                <tr><td class="gray"><strong>Total Amount Due (Including VAT)</strong></td><td class="right"><strong>{{{{ frappe.format_value(doc.grand_total, {{'fieldtype':'Currency'}}) }}}}</strong></td></tr>
                <tr><td colspan="2" class="small">{{{{ doc.in_words or frappe.utils.money_in_words(doc.grand_total, doc.currency) }}}}</td></tr>
            </table>
        </div>
    </div>

    <div class="mt10 small">Prepared by :</div>
</div>
'''

    @staticmethod
    def upsert_print_format(client, format_name, html):
        payload = {
            'doctype': 'Print Format',
            'name': format_name,
            'doc_type': 'Sales Invoice',
            'print_format_type': 'Jinja',
            'module': 'Accounts',
            'disabled': 0,
            'custom_format': 1,
            'raw_printing': 0,
            'html': html,
        }
        existing = client.get_request(
            'Print Format',
            filters=[["Print Format", "name", "=", format_name]],
            fields=['name'],
            limit=1,
        )
        if existing:
            client._request('PUT', f"/api/resource/Print Format/{quote(format_name, safe='')}", payload=payload)
            return 'updated'
        client.post_request('Print Format', payload)
        return 'created'


class FinanceBridgeDashboardService:
    @staticmethod
    def _compute_monthly_revenue(invoices):
        monthly = {}
        for invoice in invoices:
            posting_date = invoice.get('posting_date') or ''
            if len(posting_date) < 7:
                continue
            month_key = posting_date[:7]
            monthly[month_key] = monthly.get(month_key, 0.0) + float(invoice.get('grand_total') or 0)

        labels = sorted(monthly.keys())
        values = [round(monthly[label], 2) for label in labels]
        return labels, values

    @staticmethod
    def build_dashboard_context(all_invoices, page=1, per_page=10):
        page = max(1, int(page or 1))

        total_invoiced = sum(float(item.get('grand_total') or 0) for item in all_invoices)
        pending_collection = sum(float(item.get('outstanding_amount') or 0) for item in all_invoices)
        tax_liabilities = total_invoiced * 0.15
        paid_total = total_invoiced - pending_collection
        profitability_index = (paid_total / total_invoiced * 100) if total_invoiced > 0 else 0

        total_pages = max(1, math.ceil((len(all_invoices) or 1) / per_page))
        if page > total_pages:
            page = total_pages

        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        invoices = all_invoices[start_index:end_index]

        chart_labels, chart_values = FinanceBridgeDashboardService._compute_monthly_revenue(all_invoices)

        return {
            'invoices': invoices,
            'total_invoiced': total_invoiced,
            'pending_collection': pending_collection,
            'tax_liabilities': tax_liabilities,
            'profitability_index': profitability_index,
            'chart_labels': chart_labels,
            'chart_values': chart_values,
            'page': page,
            'total_pages': total_pages,
        }


class FinanceBridgeInvoiceService:
    @staticmethod
    def build_preview_summary(billing_data, tax_rate=15, discount=0):
        subtotal = float(billing_data.get('total_amount') or 0)
        taxable = max(0.0, subtotal - max(0.0, float(discount or 0)))
        tax_amount = taxable * (max(0.0, float(tax_rate or 0)) / 100)
        grand_total = taxable + tax_amount

        return {
            'subtotal': round(subtotal, 2),
            'discount': round(max(0.0, float(discount or 0)), 2),
            'tax_rate': round(max(0.0, float(tax_rate or 0)), 2),
            'tax_amount': round(tax_amount, 2),
            'grand_total': round(grand_total, 2),
            'subtotal_formatted': FinanceBridgeSettingsService.format_sar(subtotal),
            'tax_amount_formatted': FinanceBridgeSettingsService.format_sar(tax_amount),
            'grand_total_formatted': FinanceBridgeSettingsService.format_sar(grand_total),
        }
