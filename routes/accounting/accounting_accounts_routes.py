"""
════════════════════════════════════════════════════════════════════════════
📋 إدارة الحسابات - Accounts Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: إدارة الحسابات والنماذج المحاسبية
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, desc
from collections import defaultdict

from core.extensions import db
from models import UserRole, Module
from models_accounting import Account, AccountType, Budget, CostCenter, Transaction, TransactionEntry, EntryType
from forms.accounting import AccountForm
from services.finance_bridge import ERPNextClient, ERPNextBridgeError
from services.finance_bridge_app_service import FinanceBridgeSettingsService
from utils.helpers import log_activity

from .accounting_helpers import (
    check_accounting_access,
    validate_account_code_unique,
    search_accounts
)


def _is_descendant_account(parent_account, target_account_id):
    stack = list(parent_account.children or [])
    visited = set()
    while stack:
        node = stack.pop()
        if node.id in visited:
            continue
        visited.add(node.id)
        if int(node.id) == int(target_account_id):
            return True
        stack.extend(list(node.children or []))
    return False


def _build_local_accounting_health_report(limit=500):
    transactions = (
        Transaction.query.order_by(desc(Transaction.transaction_date), desc(Transaction.id)).limit(limit).all()
    )

    unbalanced_entries = []
    duplicate_buckets = defaultdict(list)
    group_accounts = []

    for tx in transactions:
        debit_total = Decimal('0.00')
        credit_total = Decimal('0.00')
        for entry in tx.entries:
            amount = Decimal(str(entry.amount or 0))
            if entry.entry_type == EntryType.DEBIT:
                debit_total += amount
            else:
                credit_total += amount

            has_children = Account.query.filter_by(parent_id=entry.account_id).count() > 0
            if has_children:
                group_accounts.append({
                    'account': entry.account.code,
                    'account_name': entry.account.name,
                    'disabled': not entry.account.is_active,
                    'sample_journal_entry': tx.transaction_number,
                })

        if debit_total != credit_total:
            unbalanced_entries.append({
                'name': tx.transaction_number,
                'posting_date': tx.transaction_date.isoformat() if tx.transaction_date else None,
                'total_debit': float(debit_total),
                'total_credit': float(credit_total),
                'difference': float(debit_total - credit_total),
            })

        reference_no = str(tx.reference_number or '').strip()
        if reference_no:
            duplicate_buckets[(tx.transaction_date, reference_no, float(tx.total_amount or 0))].append(tx)

    duplicate_references = []
    for (posting_date, reference_no, amount_value), rows in duplicate_buckets.items():
        if len(rows) > 1:
            duplicate_references.append({
                'posting_date': posting_date.isoformat() if posting_date else None,
                'reference_no': reference_no,
                'amount': amount_value,
                'entries': [row.transaction_number for row in rows],
                'count': len(rows),
            })

    unique_group_accounts = {}
    for item in group_accounts:
        unique_group_accounts[item['account']] = item

    issues_total = len(unbalanced_entries) + len(duplicate_references) + len(unique_group_accounts)
    scanned_count = max(1, len(transactions))
    cleanliness_score = max(0, int(round((1 - min(1.0, issues_total / scanned_count)) * 100)))

    return {
        'ok': True,
        'source': 'local',
        'scanned_journal_entries': len(transactions),
        'scanned_journal_lines': sum(len(tx.entries) for tx in transactions),
        'cleanliness_score': cleanliness_score,
        'issues_total': issues_total,
        'unbalanced_entries': unbalanced_entries,
        'duplicate_references': duplicate_references,
        'group_accounts_with_transactions': list(unique_group_accounts.values()),
        'generated_at': datetime.utcnow().isoformat(),
    }

# ────────────────────────────────────────────────────────────────────────────
# 🔧 إنشاء البلوبرينت
# ────────────────────────────────────────────────────────────────────────────

accounts_bp = Blueprint(
    'accounting_accounts',
    __name__,
    url_prefix='/accounting'
)


# ════════════════════════════════════════════════════════════════════════════
# 📋 قائمة الحسابات والعمليات الأساسية
# ════════════════════════════════════════════════════════════════════════════

@accounts_bp.route('/accounts')
@login_required
def accounts():
    """
    قائمة الحسابات
    
    تتضمن:
    ✓ البحث والتصفية المتقدمة
    ✓ ترتيب حسبالرمز
    ✓ تصفية حسب نوع الحساب
    ✓ عرض مرقع بـ 20 حساب لكل صفحة
    """
    
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        search_term = request.args.get('search', '')
        account_type_filter = request.args.get('type', '')
        page = request.args.get('page', 1, type=int)
        
        accounts_list = search_accounts(
            search_term=search_term,
            account_type=account_type_filter
        )
        
        accounts_paginated = accounts_list.order_by(Account.code).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template(
            'accounting/accounts/index.html',
            accounts=accounts_paginated,
            search_term=search_term,
            account_type_filter=account_type_filter
        )
        
    except Exception as e:
        flash(f'خطأ في تحميل الحسابات: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))


@accounts_bp.route('/accounts/add', methods=['POST'])
@login_required
def add_account():
    """إضافة حساب جديد من شجرة الحسابات"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        existing = Account.query.filter_by(code=request.form.get('code')).first()
        if existing:
            flash('رمز الحساب موجود مسبقاً', 'danger')
            return redirect(url_for('accounting_charts.chart_of_accounts'))
        
        account = Account(
            code=request.form.get('code'),
            name=request.form.get('name'),
            name_en=request.form.get('name_en', ''),
            account_type=AccountType(request.form.get('account_type')),
            parent_id=request.form.get('parent_id') if request.form.get('parent_id') else None,
            balance=float(request.form.get('balance', 0)),
            is_active=request.form.get('is_active') == 'on'
        )
        
        if account.parent_id:
            parent = Account.query.get(account.parent_id)
            account.level = parent.level + 1 if parent else 0
        else:
            account.level = 0
        
        db.session.add(account)
        db.session.commit()
        
        log_activity(f"إضافة حساب جديد: {account.name} ({account.code})")
        flash('تم إضافة الحساب بنجاح', 'success')
        return redirect(url_for('accounting_charts.chart_of_accounts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ في إضافة الحساب: {str(e)}', 'danger')
        return redirect(url_for('accounting_charts.chart_of_accounts'))


@accounts_bp.route('/accounts/create', methods=['GET', 'POST'])
@login_required
def create_account():
    """إضافة حساب جديد"""
    
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = AccountForm()
    
    parent_accounts = Account.query.filter_by(is_active=True).all()
    form.parent_id.choices = [('', 'لا يوجد')] + [
        (acc.id, f"{acc.code} - {acc.name}") for acc in parent_accounts
    ]
    
    if form.validate_on_submit():
        try:
            if not validate_account_code_unique(form.code.data):
                flash(f'رمز الحساب "{form.code.data}" موجود مسبقاً', 'danger')
                return render_template(
                    'accounting/accounts/form.html',
                    form=form,
                    title='إضافة حساب جديد'
                )
            
            account = Account(
                code=form.code.data,
                name=form.name.data,
                name_en=form.name_en.data,
                account_type=AccountType(form.account_type.data),
                parent_id=form.parent_id.data if form.parent_id.data else None,
                description=form.description.data,
                is_active=form.is_active.data
            )
            
            if account.parent_id:
                parent = Account.query.get(account.parent_id)
                account.level = parent.level + 1 if parent else 0
            else:
                account.level = 0
            
            db.session.add(account)
            db.session.commit()
            
            log_activity(f"إضافة حساب جديد: {account.name} ({account.code})")
            flash(f'تم إضافة الحساب "{account.name}" بنجاح', 'success')
            return redirect(url_for('accounting_accounts.accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في إضافة الحساب: {str(e)}', 'danger')
    
    return render_template(
        'accounting/accounts/form.html',
        form=form,
        title='إضافة حساب جديد'
    )


@accounts_bp.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    """تعديل حساب"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    account = Account.query.get_or_404(account_id)
    form = AccountForm(obj=account)
    
    parent_accounts = Account.query.filter(
        Account.is_active == True,
        Account.id != account.id
    ).all()
    form.parent_id.choices = [('', 'لا يوجد')] + [(acc.id, f"{acc.code} - {acc.name}") for acc in parent_accounts]
    
    if form.validate_on_submit():
        try:
            existing = Account.query.filter(
                Account.code == form.code.data,
                Account.id != account.id
            ).first()
            if existing:
                flash('رمز الحساب موجود مسبقاً', 'danger')
                return render_template('accounting/accounts/form.html', form=form, title='تعديل حساب', account=account)
            
            account.code = form.code.data
            account.name = form.name.data
            account.name_en = form.name_en.data
            account.account_type = AccountType(form.account_type.data)
            account.parent_id = form.parent_id.data if form.parent_id.data else None
            account.description = form.description.data
            account.is_active = form.is_active.data
            account.updated_at = datetime.utcnow()
            
            if account.parent_id:
                parent = Account.query.get(account.parent_id)
                account.level = parent.level + 1
            else:
                account.level = 0
            
            db.session.commit()
            
            log_activity(f"تعديل حساب: {account.name} ({account.code})")
            flash('تم تعديل الحساب بنجاح', 'success')
            return redirect(url_for('accounting_accounts.accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في تعديل الحساب: {str(e)}', 'danger')
    
    return render_template('accounting/accounts/form.html', form=form, title='تعديل حساب', account=account)


@accounts_bp.route('/accounts/<int:account_id>/confirm-delete', methods=['GET', 'POST'])
@login_required
def confirm_delete_account(account_id):
    """صفحة تأكيد حذف الحساب"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    account = Account.query.get_or_404(account_id)
    
    has_transactions = TransactionEntry.query.filter_by(account_id=account.id).count() > 0
    has_children = Account.query.filter_by(parent_id=account.id).count() > 0
    
    if request.method == 'POST':
        if has_transactions:
            flash('لا يمكن حذف الحساب لوجود معاملات مرتبطة به', 'danger')
            return redirect(url_for('accounting_accounts.accounts'))
        
        if has_children:
            flash('لا يمكن حذف الحساب لوجود حسابات فرعية تابعة له', 'danger')
            return redirect(url_for('accounting_accounts.accounts'))
        
        try:
            account_name = account.name
            account_code = account.code
            
            db.session.delete(account)
            db.session.commit()
            
            log_activity(f"حذف حساب: {account_name} ({account_code})")
            flash('تم حذف الحساب بنجاح', 'success')
            
            return redirect(url_for('accounting_accounts.accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في حذف الحساب: {str(e)}', 'danger')
    
    return render_template('accounting/accounts/confirm_delete.html', 
                         account=account,
                         has_transactions=has_transactions,
                         has_children=has_children)


@accounts_bp.route('/accounts/<int:account_id>/view')
@login_required
def view_account(account_id):
    """عرض تفاصيل الحساب"""
    
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        account = Account.query.get_or_404(account_id)
        
        recent_entries = TransactionEntry.query.filter_by(
            account_id=account.id
        ).join(
            Transaction
        ).filter(
            Transaction.is_approved == True
        ).order_by(
            desc(Transaction.transaction_date)
        ).limit(20).all()
        
        current_year = datetime.now().year
        monthly_balances = []
        
        for month in range(1, 13):
            month_start = date(current_year, month, 1)
            month_end = (
                date(current_year + 1, 1, 1) - timedelta(days=1)
                if month == 12
                else date(current_year, month + 1, 1) - timedelta(days=1)
            )
            
            debits = db.session.query(
                func.sum(TransactionEntry.amount)
            ).join(Transaction).filter(
                TransactionEntry.account_id == account.id,
                TransactionEntry.entry_type == EntryType.DEBIT,
                Transaction.transaction_date <= month_end,
                Transaction.is_approved == True
            ).scalar() or 0
            
            credits = db.session.query(
                func.sum(TransactionEntry.amount)
            ).join(Transaction).filter(
                TransactionEntry.account_id == account.id,
                TransactionEntry.entry_type == EntryType.CREDIT,
                Transaction.transaction_date <= month_end,
                Transaction.is_approved == True
            ).scalar() or 0
            
            balance = (
                debits - credits 
                if account.account_type in [AccountType.ASSETS, AccountType.EXPENSES]
                else credits - debits
            )
            monthly_balances.append(balance)
        
        return render_template(
            'accounting/accounts/view.html',
            account=account,
            recent_entries=recent_entries,
            monthly_balances=monthly_balances
        )
        
    except Exception as e:
        flash(f'خطأ في جلب بيانات الحساب: {str(e)}', 'danger')
        return redirect(url_for('accounting_accounts.accounts'))


@accounts_bp.route('/health-report')
@login_required
def accounting_health_report():
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    settings_data = FinanceBridgeSettingsService.load_settings()
    client = ERPNextClient(config_overrides=settings_data)
    requested_source = (request.args.get('source') or 'erp').strip().lower()
    if requested_source not in ('erp', 'local'):
        requested_source = 'erp'

    health_report = None
    report_error = None
    if requested_source == 'local':
        health_report = _build_local_accounting_health_report(limit=500)
    elif client.is_configured():
        try:
            health_report = client.get_accounting_health_report(limit=300)
            health_report['source'] = 'erp'
        except ERPNextBridgeError as exc:
            report_error = f"{exc} | تم التحويل تلقائياً إلى تقرير NUZUM المحلي"
            health_report = _build_local_accounting_health_report(limit=500)
    else:
        report_error = 'بيانات الربط مع ERPNext غير مكتملة. تم عرض تقرير NUZUM المحلي.'
        health_report = _build_local_accounting_health_report(limit=500)

    accounts_list = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    return render_template(
        'accounting/accounts/health_report.html',
        report=health_report,
        report_error=report_error,
        requested_source=requested_source,
        accounts=accounts_list,
    )


@accounts_bp.route('/merge-accounts', methods=['GET', 'POST'])
@login_required
def merge_accounts():
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        source_account_id = request.form.get('source_account_id', type=int)
        target_account_id = request.form.get('target_account_id', type=int)

        if not source_account_id or not target_account_id:
            flash('اختر الحساب القديم والحساب الهدف', 'danger')
            return redirect(url_for('accounting_accounts.accounting_health_report'))

        if source_account_id == target_account_id:
            flash('لا يمكن دمج الحساب في نفسه', 'danger')
            return redirect(url_for('accounting_accounts.accounting_health_report'))

        source_account = Account.query.get_or_404(source_account_id)
        target_account = Account.query.get_or_404(target_account_id)

        if _is_descendant_account(source_account, target_account.id):
            flash('لا يمكن دمج حساب أب داخل حساب فرعي له', 'danger')
            return redirect(url_for('accounting_accounts.accounting_health_report'))

        if not source_account.is_active:
            flash('الحساب القديم غير نشط بالفعل', 'warning')
            return redirect(url_for('accounting_accounts.accounting_health_report'))

        try:
            source_balance = Decimal(str(source_account.balance or 0))
            target_balance = Decimal(str(target_account.balance or 0))

            moved_entries = TransactionEntry.query.filter_by(account_id=source_account.id).update(
                {TransactionEntry.account_id: target_account.id},
                synchronize_session=False,
            )
            moved_budgets = Budget.query.filter_by(account_id=source_account.id).update(
                {Budget.account_id: target_account.id},
                synchronize_session=False,
            )
            moved_children = Account.query.filter_by(parent_id=source_account.id).update(
                {Account.parent_id: target_account.id},
                synchronize_session=False,
            )

            source_account.balance = Decimal('0.00')
            source_account.is_active = False
            source_account.updated_at = datetime.utcnow()
            target_account.balance = target_balance + source_balance
            target_account.updated_at = datetime.utcnow()

            erp_sync_note = 'ERP: لم يتم الربط'
            settings_data = FinanceBridgeSettingsService.load_settings()
            client = ERPNextClient(config_overrides=settings_data)
            if client.is_configured():
                try:
                    erp_result = client.disable_account_by_code_or_name(
                        account_code=source_account.code,
                        account_name=source_account.name,
                    )
                    if erp_result.get('disabled'):
                        erp_sync_note = f"ERP: تم تعطيل {erp_result.get('updated', 0)} حساب"
                    else:
                        erp_sync_note = 'ERP: الحساب غير موجود للتعطيل'
                except ERPNextBridgeError as exc:
                    erp_sync_note = f'ERP: فشل التعطيل ({exc})'

            db.session.commit()

            log_activity(
                f"دمج الحساب {source_account.code} -> {target_account.code} | "
                f"entries={moved_entries}, budgets={moved_budgets}, children={moved_children}"
            )
            flash(
                (
                    f'تم الدمج بنجاح: {source_account.code} -> {target_account.code} | '
                    f'القيود المنقولة: {moved_entries} | الميزانيات: {moved_budgets} | '
                    f'الحسابات الفرعية: {moved_children} | {erp_sync_note}'
                ),
                'success',
            )
        except Exception as exc:
            db.session.rollback()
            flash(f'فشل دمج الحسابات: {exc}', 'danger')

        return redirect(url_for('accounting_accounts.accounting_health_report'))

    return redirect(url_for('accounting_accounts.accounting_health_report'))


@accounts_bp.route('/bootstrap-accounting', methods=['POST'])
@login_required
def bootstrap_accounting():
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))

    try:
        today = date.today()
        fiscal_year = FiscalYear.query.filter_by(is_active=True, is_closed=False).first()
        if not fiscal_year:
            fiscal_year = FiscalYear(
                name=f"السنة المالية {today.year}",
                year=today.year,
                start_date=date(today.year, 1, 1),
                end_date=date(today.year, 12, 31),
                is_active=True,
                is_closed=False,
            )
            db.session.add(fiscal_year)

        settings = AccountingSettings.query.first()
        if not settings:
            settings = AccountingSettings(
                company_name='NUZUM',
                base_currency='SAR',
                decimal_places=2,
                transaction_prefix='JV',
                next_transaction_number=1,
                fiscal_year_start_month=1,
            )
            db.session.add(settings)

        defaults = [
            ('1001', 'الصندوق', 'Cash', AccountType.ASSETS),
            ('1101', 'البنك', 'Bank', AccountType.ASSETS),
            ('2101', 'ذمم دائنة', 'Accounts Payable', AccountType.LIABILITIES),
            ('3101', 'حقوق الملكية', 'Equity', AccountType.EQUITY),
            ('4101', 'مصروف الرواتب', 'Salary Expense', AccountType.EXPENSES),
            ('4201', 'مصروفات تشغيلية', 'Operating Expense', AccountType.EXPENSES),
            ('5101', 'إيرادات الخدمات', 'Service Revenue', AccountType.REVENUE),
        ]

        created_accounts = 0
        for code, name, name_en, account_type in defaults:
            existing = Account.query.filter_by(code=code).first()
            if existing:
                continue
            db.session.add(Account(
                code=code,
                name=name,
                name_en=name_en,
                account_type=account_type,
                level=0,
                is_active=True,
                balance=0,
            ))
            created_accounts += 1

        default_cost_center = CostCenter.query.filter_by(code='CC-001').first()
        if not default_cost_center:
            db.session.add(CostCenter(
                code='CC-001',
                name='المركز الرئيسي',
                name_en='Main Cost Center',
                description='مركز تكلفة افتراضي تم إنشاؤه تلقائياً',
                budget_amount=0,
                is_active=True,
            ))

        db.session.commit()
        flash(
            f'تمت التهيئة بنجاح: سنة مالية نشطة + إعدادات أساسية + {created_accounts} حساب افتراضي.',
            'success',
        )
    except Exception as exc:
        db.session.rollback()
        flash(f'فشلت التهيئة المحاسبية: {exc}', 'danger')

    return redirect(url_for('accounting_accounts.accounting_health_report', source='local'))
