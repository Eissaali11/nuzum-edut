"""
════════════════════════════════════════════════════════════════════════════
📋 إدارة الحسابات - Accounts Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: إدارة الحسابات والنماذج المحاسبية
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc

from src.core.extensions import db
from models import UserRole, Module
from models_accounting import Account, AccountType, Transaction, TransactionEntry, EntryType
from src.forms.accounting import AccountForm
from src.utils.helpers import log_activity

from .accounting_helpers import (
    check_accounting_access,
    validate_account_code_unique,
    search_accounts
)

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
    if not (current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.ACCOUNTING)):
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
    if not (current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.ACCOUNTING)):
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
    if not (current_user.role == UserRole.ADMIN or current_user.has_module_access(Module.ACCOUNTING)):
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
