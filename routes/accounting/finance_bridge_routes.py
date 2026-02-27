"""
Finance bridge routes: NUZUM ↔ ERPNext integration.
"""

import os
import time
import uuid
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from services.finance_bridge import ERPNextClient, ERPNextBridgeError
from services.finance_bridge_app_service import (
    FinanceBridgeSettingsService,
    FinanceBridgeDashboardService,
    FinanceBridgeInvoiceService,
)
from routes.accounting.accounting_helpers import check_accounting_access
from modules.accounting.domain.profitability_models import ProjectContract
from models_accounting import CostCenter


finance_bridge_bp = Blueprint('finance_bridge', __name__, url_prefix='/accounting/finance-bridge')

_invoice_jobs = {}
_invoice_jobs_lock = threading.Lock()
_invoice_jobs_ttl_seconds = 3600


def _cleanup_invoice_jobs():
    now = time.time()
    with _invoice_jobs_lock:
        expired = [
            job_id
            for job_id, job in _invoice_jobs.items()
            if now - float(job.get('updated_at', now)) > _invoice_jobs_ttl_seconds
        ]
        for job_id in expired:
            _invoice_jobs.pop(job_id, None)


def _set_invoice_job(job_id, **updates):
    with _invoice_jobs_lock:
        job = _invoice_jobs.get(job_id, {})
        job.update(updates)
        job['updated_at'] = time.time()
        _invoice_jobs[job_id] = job
        return dict(job)


def _get_invoice_job(job_id):
    with _invoice_jobs_lock:
        job = _invoice_jobs.get(job_id)
        return dict(job) if job else None


def _run_invoice_generation_job(app, job_id, contract_id, payload):
    with app.app_context():
        try:
            _set_invoice_job(job_id, status='running', progress=20, stage='collecting', message='جاري حصر ساعات العمل القابلة للفوترة...')
            settings_data = FinanceBridgeSettingsService.load_settings()
            client = ERPNextClient(config_overrides=settings_data)
            if not client.is_configured():
                _set_invoice_job(job_id, status='failed', progress=100, stage='failed', message='ERPNext env variables are missing')
                return

            _set_invoice_job(job_id, status='running', progress=65, stage='erp_sync', message='جاري الاتصال بـ ERPNext وإنشاء الفاتورة...')
            result = client.create_sales_invoice_for_contract(
                contract_id=contract_id,
                month=payload['month'],
                year=payload['year'],
                tax_rate=payload['tax_rate'],
                discount=payload['discount'],
                payment_terms=payload['payment_terms'],
                manual_ot_hours=payload.get('manual_ot_hours', 0),
            )

            _set_invoice_job(
                job_id,
                status='done',
                progress=100,
                stage='completed',
                message=f"تم إنشاء الفاتورة {result.get('invoice_name')} بنجاح",
                result=result,
            )
        except ERPNextBridgeError as exc:
            _set_invoice_job(job_id, status='failed', progress=100, stage='failed', message=str(exc))
        except Exception as exc:
            _set_invoice_job(job_id, status='failed', progress=100, stage='failed', message=f'Unexpected error: {exc}')


def _start_invoice_job(contract_id, payload, user_id):
    _cleanup_invoice_jobs()
    job_id = uuid.uuid4().hex
    _set_invoice_job(
        job_id,
        id=job_id,
        contract_id=contract_id,
        owner_id=user_id,
        status='queued',
        progress=5,
        stage='queued',
        message='تم استلام الطلب، جارٍ بدء المعالجة...',
        created_at=time.time(),
    )
    app_obj = current_app._get_current_object()
    worker = threading.Thread(
        target=_run_invoice_generation_job,
        args=(app_obj, job_id, contract_id, payload),
        daemon=True,
        name=f'invoice-job-{job_id[:8]}',
    )
    worker.start()
    return job_id


def _wants_json_response():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    return request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html


@finance_bridge_bp.route('/')
@login_required
def dashboard():
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    settings_data = FinanceBridgeSettingsService.load_settings()
    client = ERPNextClient(config_overrides=settings_data)
    connection_ok = False
    connection_message = 'Disconnected'
    all_invoices = []
    page = max(1, request.args.get('page', 1, type=int))

    if client.is_configured():
        try:
            status = client.test_connection()
            connection_ok = bool(status.get('ok'))
            connection_message = f"Connected as {status.get('user', 'ERP user')}" if connection_ok else 'Disconnected'
            all_invoices = client.list_sales_invoices(limit=100)
        except ERPNextBridgeError as exc:
            connection_message = str(exc)
    else:
        connection_message = 'ERPNext env variables are not configured.'

    dashboard_context = FinanceBridgeDashboardService.build_dashboard_context(
        all_invoices=all_invoices,
        page=page,
        per_page=10,
    )

    contracts = ProjectContract.query.order_by(ProjectContract.created_at.desc()).limit(20).all()

    return render_template(
        'accounting/erp_dashboard.html',
        connection_ok=connection_ok,
        connection_message=connection_message,
        contracts=contracts,
        now=datetime.now(),
        format_sar=FinanceBridgeSettingsService.format_sar,
        settings=settings_data,
        **dashboard_context,
    )


@finance_bridge_bp.route('/test-connection', methods=['POST'])
@login_required
def test_connection():
    if not check_accounting_access(current_user):
        if _wants_json_response():
            return jsonify({'ok': False, 'message': 'Unauthorized'}), 403
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    if not client.is_configured():
        message = 'ERPNext env variables are missing'
        if _wants_json_response():
            return jsonify({'ok': False, 'message': message}), 400
        flash('متغيرات ربط ERPNext غير مكتملة', 'danger')
        return redirect(url_for('finance_bridge.dashboard'))

    try:
        status = client.test_connection()
        message = f"Connected as {status.get('user', 'ERP user')}"
        if _wants_json_response():
            return jsonify({'ok': True, 'message': message})
        flash(message, 'success')
        return redirect(url_for('finance_bridge.dashboard'))
    except ERPNextBridgeError as exc:
        message = str(exc)
        if _wants_json_response():
            return jsonify({'ok': False, 'message': message}), 502
        flash(message, 'danger')
        return redirect(url_for('finance_bridge.dashboard'))


@finance_bridge_bp.route('/api/test-erp-connection', methods=['GET'])
@login_required
def test_erp_connection_api():
    if not check_accounting_access(current_user):
        return jsonify({
            'ok': False,
            'status': 'error',
            'message': 'غير مصرح بالوصول',
            'color': '#ff4136',
        }), 403

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    if not client.is_configured():
        return jsonify({
            'ok': False,
            'status': 'error',
            'message': 'بيانات الربط غير مكتملة (Base URL / API Key / API Secret)',
            'color': '#ff4136',
        }), 400

    try:
        status = client.test_connection()
        user_email = status.get('user', 'ERP user')
        return jsonify({
            'ok': True,
            'status': 'success',
            'message': f'متصل بنجاح كـ {user_email}',
            'color': '#39cccc',
        })
    except ERPNextBridgeError as exc:
        return jsonify({
            'ok': False,
            'status': 'error',
            'message': f'فشل الاتصال: {exc}',
            'color': '#ff4136',
        }), 502


@finance_bridge_bp.route('/contracts/<int:contract_id>/invoice-preview', methods=['POST'])
@login_required
def preview_contract_invoice(contract_id):
    if not check_accounting_access(current_user):
        return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

    payload = request.get_json(silent=True) or {}
    month = int(payload.get('month') or datetime.now().month)
    year = int(payload.get('year') or datetime.now().year)
    tax_rate = float(payload.get('tax_rate') or 15)
    discount = float(payload.get('discount') or 0)
    manual_ot_hours = float(payload.get('manual_ot_hours') or 0)

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    try:
        billing = client.build_contract_invoice_data(
            contract_id=contract_id,
            month=month,
            year=year,
            manual_ot_hours=manual_ot_hours,
        )
    except ERPNextBridgeError as exc:
        return jsonify({'ok': False, 'message': str(exc)}), 400

    summary = FinanceBridgeInvoiceService.build_preview_summary(
        billing_data=billing,
        tax_rate=tax_rate,
        discount=discount,
    )

    return jsonify({
        'ok': True,
        'contract_id': contract_id,
        'period': f"{month:02d}/{year}",
        'lines': billing.get('lines', []),
        **summary,
    })


@finance_bridge_bp.route('/contracts/<int:contract_id>/generate-zatca-invoice', methods=['POST'])
@login_required
def generate_contract_invoice(contract_id):
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    payload = request.get_json(silent=True) or {}
    month = request.form.get('month', type=int) or int(payload.get('month') or datetime.now().month)
    year = request.form.get('year', type=int) or int(payload.get('year') or datetime.now().year)
    tax_rate = request.form.get('tax_rate', type=float)
    if tax_rate is None:
        tax_rate = float(payload.get('tax_rate') or 15)
    discount = request.form.get('discount', type=float)
    if discount is None:
        discount = float(payload.get('discount') or 0)
    payment_terms = request.form.get('payment_terms') or payload.get('payment_terms') or ''
    manual_ot_hours = request.form.get('manual_ot_hours', type=float)
    if manual_ot_hours is None:
        manual_ot_hours = float(payload.get('manual_ot_hours') or 0)
    run_async = bool(payload.get('async', False)) and _wants_json_response()

    request_payload = {
        'month': month,
        'year': year,
        'tax_rate': tax_rate,
        'discount': discount,
        'payment_terms': payment_terms,
        'manual_ot_hours': manual_ot_hours,
    }

    if run_async:
        job_id = _start_invoice_job(contract_id=contract_id, payload=request_payload, user_id=current_user.id)
        return jsonify({
            'ok': True,
            'queued': True,
            'job_id': job_id,
            'message': 'تم إرسال الطلب للمعالجة الخلفية',
        }), 202

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    if not client.is_configured():
        if _wants_json_response():
            return jsonify({'ok': False, 'message': 'ERPNext env variables are missing'}), 400
        flash('بيانات ربط ERPNext غير مكتملة في متغيرات البيئة', 'danger')
        return redirect(request.referrer or url_for('finance_bridge.dashboard'))

    try:
        result = client.create_sales_invoice_for_contract(
            contract_id=contract_id,
            month=month,
            year=year,
            tax_rate=tax_rate,
            discount=discount,
            payment_terms=payment_terms,
            manual_ot_hours=manual_ot_hours,
        )
        if _wants_json_response():
            return jsonify({'ok': True, 'message': f"تم إنشاء الفاتورة {result.get('invoice_name')} بنجاح", 'result': result})
        flash(
            f"تم إنشاء الفاتورة {result.get('invoice_name')} بقيمة {result.get('total_amount')}.",
            'success',
        )
        if result.get('pdf_url'):
            flash(f"رابط PDF: {result.get('pdf_url')}", 'info')
    except ERPNextBridgeError as exc:
        if _wants_json_response():
            return jsonify({'ok': False, 'message': str(exc)}), 400
        flash(f'فشل إنشاء الفاتورة: {exc}', 'danger')

    return redirect(request.referrer or url_for('finance_bridge.dashboard'))


@finance_bridge_bp.route('/invoice-jobs/<job_id>', methods=['GET'])
@login_required
def invoice_job_status(job_id):
    if not check_accounting_access(current_user):
        return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

    job = _get_invoice_job(job_id)
    if not job:
        return jsonify({'ok': False, 'message': 'Job not found'}), 404
    if int(job.get('owner_id') or 0) != int(current_user.id):
        return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

    return jsonify({
        'ok': True,
        'job': {
            'id': job.get('id'),
            'status': job.get('status'),
            'progress': job.get('progress', 0),
            'stage': job.get('stage'),
            'message': job.get('message'),
            'result': job.get('result') if job.get('status') == 'done' else None,
        },
    })


@finance_bridge_bp.route('/contracts/<int:contract_id>/sync-customer', methods=['POST'])
@login_required
def sync_contract_customer(contract_id):
    if not check_accounting_access(current_user):
        return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    if not client.is_configured():
        return jsonify({'ok': False, 'message': 'ERPNext env variables are missing'}), 400

    try:
        result = client.sync_contract_customer(contract_id=contract_id)
        if result.get('created'):
            message = f"تم إنشاء العميل {result.get('customer_name')} في ERPNext بنجاح"
        else:
            message = f"العميل {result.get('customer_name')} موجود مسبقاً في ERPNext"
        return jsonify({'ok': True, 'message': message, 'result': result})
    except ERPNextBridgeError as exc:
        return jsonify({'ok': False, 'message': str(exc)}), 400


@finance_bridge_bp.route('/invoices/<invoice_name>/sync-status', methods=['POST'])
@login_required
def sync_invoice_status(invoice_name):
    if not check_accounting_access(current_user):
        return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

    client = ERPNextClient(config_overrides=FinanceBridgeSettingsService.load_settings())
    if not client.is_configured():
        return jsonify({'ok': False, 'message': 'ERPNext env variables are missing'}), 400

    try:
        docs = client.get_request(
            'Sales Invoice',
            filters=[["Sales Invoice", "name", "=", invoice_name]],
            fields=['name', 'status', 'outstanding_amount', 'grand_total', 'posting_date'],
            limit=1,
        )
        if not docs:
            return jsonify({'ok': False, 'message': 'Invoice not found in ERPNext'}), 404

        invoice = docs[0]
        return jsonify({'ok': True, 'invoice': invoice, 'message': f"Status: {invoice.get('status', 'Unknown')}"})
    except ERPNextBridgeError as exc:
        return jsonify({'ok': False, 'message': str(exc)}), 400


@finance_bridge_bp.route('/invoices/<invoice_name>/pdf', methods=['GET'])
@login_required
def invoice_pdf(invoice_name):
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    settings_data = FinanceBridgeSettingsService.load_settings()
    pdf_url = FinanceBridgeSettingsService.build_invoice_pdf_url(settings_data, invoice_name)
    if not pdf_url:
        if _wants_json_response():
            return jsonify({'ok': False, 'message': 'ERPNext base URL is not configured'}), 400
        flash('رابط ERPNext الأساسي غير مهيأ في إعدادات الربط', 'danger')
        return redirect(url_for('finance_bridge.dashboard'))
    return redirect(pdf_url)


@finance_bridge_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def integration_settings():
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    settings_data = FinanceBridgeSettingsService.load_settings()

    if request.method == 'POST':
        api_key = (request.form.get('api_key') or '').strip()
        api_secret = (request.form.get('api_secret') or '').strip()
        vat_account_head = (request.form.get('vat_account_head') or '').strip()
        base_url = (request.form.get('base_url') or '').strip()
        print_format = (request.form.get('print_format') or '').strip()
        print_lang = (request.form.get('print_lang') or '').strip()
        letter_head_name = (request.form.get('letter_head_name') or '').strip()
        apply_logo_sync = request.form.get('apply_logo_sync') == 'on'

        if api_key and api_key != '********':
            settings_data['ERPNEXT_API_KEY'] = api_key
            os.environ['ERPNEXT_API_KEY'] = api_key
        if api_secret and api_secret != '********':
            settings_data['ERPNEXT_API_SECRET'] = api_secret
            os.environ['ERPNEXT_API_SECRET'] = api_secret
        if base_url:
            settings_data['ERPNEXT_BASE_URL'] = base_url
            os.environ['ERPNEXT_BASE_URL'] = base_url

        settings_data['ERPNEXT_VAT_ACCOUNT_HEAD'] = vat_account_head
        settings_data['ERPNEXT_PRINT_FORMAT'] = print_format or settings_data.get('ERPNEXT_PRINT_FORMAT', 'Standard')
        settings_data['ERPNEXT_PRINT_LANG'] = print_lang or settings_data.get('ERPNEXT_PRINT_LANG', 'ar')
        settings_data['ERPNEXT_LETTER_HEAD'] = letter_head_name or settings_data.get('ERPNEXT_LETTER_HEAD', 'NUZUM')
        settings_data['ERPNEXT_APPLY_NUZUM_LOGO'] = apply_logo_sync
        os.environ['ERPNEXT_VAT_ACCOUNT_HEAD'] = vat_account_head
        os.environ['ERPNEXT_PRINT_FORMAT'] = settings_data['ERPNEXT_PRINT_FORMAT']
        os.environ['ERPNEXT_PRINT_LANG'] = settings_data['ERPNEXT_PRINT_LANG']
        os.environ['ERPNEXT_LETTER_HEAD'] = settings_data['ERPNEXT_LETTER_HEAD']

        mapping = {}
        for key, value in request.form.items():
            if key.startswith('mapping_'):
                cost_center_code = key.replace('mapping_', '', 1)
                mapping[cost_center_code] = value
        settings_data['cost_center_mapping'] = mapping

        FinanceBridgeSettingsService.save_settings(settings_data)
        FinanceBridgeSettingsService.apply_runtime_env(settings_data)
        flash('تم حفظ إعدادات الربط بنجاح', 'success')
        return redirect(url_for('finance_bridge.integration_settings'))

    client = ERPNextClient(config_overrides=settings_data)
    account_options = []
    if client.is_configured():
        try:
            accounts = client.get_request('Account', fields=['name', 'account_name'], limit=200)
            account_options = [f"{item.get('name')} - {item.get('account_name', '')}" for item in accounts]
        except ERPNextBridgeError:
            account_options = []

    cost_centers = CostCenter.query.order_by(CostCenter.code).all()
    masked_key = '********' if settings_data.get('ERPNEXT_API_KEY') else ''
    masked_secret = '********' if settings_data.get('ERPNEXT_API_SECRET') else ''

    return render_template(
        'accounting/erp_settings.html',
        settings=settings_data,
        account_options=account_options,
        cost_centers=cost_centers,
        masked_key=masked_key,
        masked_secret=masked_secret,
        default_base_url=FinanceBridgeSettingsService.get_base_url(settings_data),
    )


@finance_bridge_bp.route('/invoice-settings', methods=['GET', 'POST'])
@login_required
def invoice_data_settings():
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    settings_data = FinanceBridgeSettingsService.load_settings()
    profile = FinanceBridgeSettingsService.get_invoice_profile(settings_data)

    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()

        if action == 'autofill_latest':
            client = ERPNextClient(config_overrides=settings_data)
            if not client.is_configured():
                flash('تعذر التعبئة التلقائية: بيانات ربط ERPNext غير مكتملة', 'warning')
                return redirect(url_for('finance_bridge.invoice_data_settings'))

            try:
                latest_invoices = client.list_sales_invoices(limit=1)
                if not latest_invoices:
                    flash('لا توجد فواتير في ERPNext للتعبئة التلقائية', 'warning')
                    return redirect(url_for('finance_bridge.invoice_data_settings'))

                invoice_name = latest_invoices[0].get('name')
                docs = client.get_request(
                    'Sales Invoice',
                    filters=[["Sales Invoice", "name", "=", invoice_name]],
                    fields=[
                        'name',
                        'customer',
                        'customer_name',
                        'tax_id',
                        'address_display',
                        'po_no',
                        'incoterm',
                        'shipping_address_name',
                        'payment_terms_template',
                    ],
                    limit=1,
                )
                if not docs:
                    flash('تعذر قراءة بيانات آخر فاتورة للتعبئة التلقائية', 'warning')
                    return redirect(url_for('finance_bridge.invoice_data_settings'))

                latest = docs[0]
                profile['customer_id_default'] = (latest.get('customer') or profile.get('customer_id_default') or '').strip()
                profile['customer_name_en_default'] = (latest.get('customer_name') or profile.get('customer_name_en_default') or '').strip()
                profile['customer_vat_default'] = (latest.get('tax_id') or profile.get('customer_vat_default') or '').strip()
                profile['customer_address_en_default'] = (latest.get('address_display') or profile.get('customer_address_en_default') or '').strip()
                profile['customer_ref_default'] = (latest.get('po_no') or profile.get('customer_ref_default') or '').strip()
                profile['delivery_term_default'] = (latest.get('incoterm') or profile.get('delivery_term_default') or '').strip()
                profile['delivery_address_default'] = (latest.get('shipping_address_name') or profile.get('delivery_address_default') or '').strip()
                profile['payment_term_default'] = (latest.get('payment_terms_template') or profile.get('payment_term_default') or '').strip()

                settings_data['invoice_profile'] = profile
                FinanceBridgeSettingsService.save_settings(settings_data)

                format_name = (settings_data.get('ERPNEXT_PRINT_FORMAT') or 'NUZUM Professional Invoice').strip()
                html = FinanceBridgeSettingsService.build_professional_invoice_html(profile)
                action_result = FinanceBridgeSettingsService.upsert_print_format(client, format_name, html)
                flash(f'تمت التعبئة التلقائية من الفاتورة {invoice_name} وتحديث القالب ({action_result})', 'success')
            except ERPNextBridgeError as exc:
                flash(f'فشل التعبئة التلقائية: {exc}', 'warning')

            return redirect(url_for('finance_bridge.invoice_data_settings'))

        profile = {
            'company_name_en': (request.form.get('company_name_en') or '').strip(),
            'company_name_ar': (request.form.get('company_name_ar') or '').strip(),
            'address_en': (request.form.get('address_en') or '').strip(),
            'address_ar': (request.form.get('address_ar') or '').strip(),
            'phone_en': (request.form.get('phone_en') or '').strip(),
            'phone_ar': (request.form.get('phone_ar') or '').strip(),
            'fax_en': (request.form.get('fax_en') or '').strip(),
            'fax_ar': (request.form.get('fax_ar') or '').strip(),
            'vat_no_en': (request.form.get('vat_no_en') or '').strip(),
            'vat_no_ar': (request.form.get('vat_no_ar') or '').strip(),
            'logo_url': (request.form.get('logo_url') or '').strip(),
            'customer_id_default': (request.form.get('customer_id_default') or '').strip(),
            'customer_name_en_default': (request.form.get('customer_name_en_default') or '').strip(),
            'customer_name_ar_default': (request.form.get('customer_name_ar_default') or '').strip(),
            'customer_vat_default': (request.form.get('customer_vat_default') or '').strip(),
            'customer_address_en_default': (request.form.get('customer_address_en_default') or '').strip(),
            'customer_address_ar_default': (request.form.get('customer_address_ar_default') or '').strip(),
            'customer_ref_default': (request.form.get('customer_ref_default') or '').strip(),
            'delivery_term_default': (request.form.get('delivery_term_default') or '').strip(),
            'delivery_address_default': (request.form.get('delivery_address_default') or '').strip(),
            'payment_term_default': (request.form.get('payment_term_default') or '').strip(),
        }
        settings_data['invoice_profile'] = profile

        format_name = (settings_data.get('ERPNEXT_PRINT_FORMAT') or 'NUZUM Professional Invoice').strip()
        settings_data['ERPNEXT_PRINT_FORMAT'] = format_name

        FinanceBridgeSettingsService.save_settings(settings_data)
        FinanceBridgeSettingsService.apply_runtime_env(settings_data)

        client = ERPNextClient(config_overrides=settings_data)
        if client.is_configured():
            try:
                html = FinanceBridgeSettingsService.build_professional_invoice_html(profile)
                action = FinanceBridgeSettingsService.upsert_print_format(client, format_name, html)
                flash(f'تم حفظ بيانات الفاتورة وتحديث قالب الطباعة ({action}) بنجاح', 'success')
            except ERPNextBridgeError as exc:
                flash(f'تم حفظ البيانات محلياً لكن فشل تحديث قالب ERP: {exc}', 'warning')
        else:
            flash('تم حفظ البيانات محلياً. أكمل إعدادات الربط لتحديث قالب ERP تلقائياً.', 'info')

        return redirect(url_for('finance_bridge.invoice_data_settings'))

    return render_template(
        'accounting/erp_invoice_settings.html',
        settings=settings_data,
        profile=profile,
        print_format_name=settings_data.get('ERPNEXT_PRINT_FORMAT', 'NUZUM Professional Invoice'),
    )
