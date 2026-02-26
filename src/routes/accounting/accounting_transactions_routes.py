"""
════════════════════════════════════════════════════════════════════════════
💳 المعاملات المالية - Transactions Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: إدارة المعاملات والقيود المحاسبية
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
from sqlalchemy import desc, or_
from sqlalchemy.orm import joinedload

from src.core.extensions import db
from models_accounting import (
    Transaction, TransactionEntry, FiscalYear, 
    AccountingSettings, AccountType, CostCenter,
    Vendor, Customer, TransactionType, EntryType, Account
)
from src.forms.accounting import TransactionForm
from src.utils.helpers import log_activity

from .accounting_helpers import (
    check_accounting_access,
    validate_transaction_balance,
    get_next_transaction_number,
    apply_changes_to_account_balance,
    search_accounts,
    search_transactions
)

# ────────────────────────────────────────────────────────────────────────────
# 🔧 إنشاء البلوبرينت
# ────────────────────────────────────────────────────────────────────────────

transactions_bp = Blueprint(
    'accounting_transactions',
    __name__,
    url_prefix='/accounting'
)


# ════════════════════════════════════════════════════════════════════════════
# 💳 قائمة وعرض المعاملات
# ════════════════════════════════════════════════════════════════════════════

@transactions_bp.route('/transaction/<int:transaction_id>')
@login_required
def view_transaction(transaction_id):
    """عرض تفاصيل معاملة مالية"""
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    transaction = Transaction.query.get_or_404(transaction_id)
    entries = TransactionEntry.query.filter_by(transaction_id=transaction_id).all()
    
    return render_template(
        'accounting/view_transaction.html',
        transaction=transaction,
        entries=entries
    )


@transactions_bp.route('/transactions')
@login_required
def transactions():
    """قائمة القيود المحاسبية"""
    
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        search_term = request.args.get('search', '')
        transaction_type_filter = request.args.get('type', '')
        status_filter = request.args.get('status', '')
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
        page = request.args.get('page', 1, type=int)
        
        query = Transaction.query.options(
            joinedload(Transaction.created_by)
        )
        
        if search_term:
            query = query.filter(or_(
                Transaction.description.ilike(f'%{search_term}%'),
                Transaction.reference_number.ilike(f'%{search_term}%'),
                Transaction.transaction_number.ilike(f'%{search_term}%')
            ))
        
        if transaction_type_filter:
            query = query.filter(
                Transaction.transaction_type == transaction_type_filter
            )
        
        if status_filter == 'pending':
            query = query.filter(Transaction.is_approved == False)
        elif status_filter == 'approved':
            query = query.filter(Transaction.is_approved == True)
        
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date <= to_date_obj)
        
        transactions_paginated = query.order_by(
            desc(Transaction.transaction_date),
            desc(Transaction.id)
        ).paginate(page=page, per_page=20, error_out=False)
        
        return render_template(
            'accounting/transactions/index.html',
            transactions=transactions_paginated,
            search_term=search_term,
            transaction_type_filter=transaction_type_filter,
            status_filter=status_filter,
            from_date=from_date,
            to_date=to_date
        )
        
    except Exception as e:
        flash(f'خطأ في تحميل المعاملات: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))


@transactions_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """إضافة قيد محاسبي جديد"""
    
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = TransactionForm()
    
    accounts = search_accounts(is_active=True)
    cost_centers = CostCenter.query.filter_by(is_active=True).all()
    vendors = Vendor.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    
    for entry_form in form.entries:
        entry_form.account_id.choices = [
            (acc.id, f"{acc.code} - {acc.name}") for acc in accounts
        ]
    
    form.cost_center_id.choices = [('', 'لا يوجد')] + [
        (cc.id, cc.name) for cc in cost_centers
    ]
    form.vendor_id.choices = [('', 'لا يوجد')] + [
        (v.id, v.name) for v in vendors
    ]
    form.customer_id.choices = [('', 'لا يوجد')] + [
        (c.id, c.name) for c in customers
    ]
    
    if request.method == 'POST':
        try:
            total_debits = sum(
                float(e.amount.data) for e in form.entries 
                if e.entry_type.data == 'debit' and e.amount.data
            )
            total_credits = sum(
                float(e.amount.data) for e in form.entries 
                if e.entry_type.data == 'credit' and e.amount.data
            )
            
            if not validate_transaction_balance(total_debits, total_credits):
                flash('خطأ: القيد غير متوازن. المدين يجب أن يساوي الدائن', 'danger')
                return render_template(
                    'accounting/transactions/form.html',
                    form=form, title='إضافة قيد جديد'
                )
            
            if not form.validate_on_submit() or total_debits == 0:
                flash('خطأ في البيانات المدخلة', 'danger')
                return render_template(
                    'accounting/transactions/form.html',
                    form=form, title='إضافة قيد جديد'
                )
            
            transaction_number = get_next_transaction_number()
            
            fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
            if not fiscal_year:
                flash('لا توجد سنة مالية نشطة', 'danger')
                return render_template(
                    'accounting/transactions/form.html',
                    form=form, title='إضافة قيد جديد'
                )
            
            transaction = Transaction(
                transaction_number=transaction_number,
                transaction_date=form.transaction_date.data,
                transaction_type=TransactionType(form.transaction_type.data),
                reference_number=form.reference_number.data,
                description=form.description.data,
                total_amount=Decimal(str(total_debits)),
                fiscal_year_id=fiscal_year.id,
                cost_center_id=form.cost_center_id.data or None,
                vendor_id=form.vendor_id.data or None,
                customer_id=form.customer_id.data or None,
                created_by_id=current_user.id
            )
            
            db.session.add(transaction)
            db.session.flush()
            
            for entry_form in form.entries:
                if entry_form.account_id.data and entry_form.amount.data:
                    entry = TransactionEntry(
                        transaction_id=transaction.id,
                        account_id=entry_form.account_id.data,
                        entry_type=EntryType(entry_form.entry_type.data),
                        amount=Decimal(str(entry_form.amount.data)),
                        description=entry_form.description.data
                    )
                    db.session.add(entry)
                    
                    apply_changes_to_account_balance(
                        account_id=entry_form.account_id.data,
                        amount=Decimal(str(entry_form.amount.data)),
                        entry_type=entry_form.entry_type.data
                    )
            
            db.session.commit()
            
            log_activity(f"إضافة قيد محاسبي: {transaction.transaction_number}")
            flash(f'تم إضافة القيد {transaction.transaction_number} بنجاح', 'success')
            return redirect(url_for('accounting_transactions.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في إضافة القيد: {str(e)}', 'danger')
    
    return render_template(
        'accounting/transactions/form.html',
        form=form,
        title='إضافة قيد محاسبي جديد'
    )
