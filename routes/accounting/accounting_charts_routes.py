"""
════════════════════════════════════════════════════════════════════════════
🌳 شجرة الحسابات - Chart of Accounts Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: إدارة شجرة الحسابات والأرصدة
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from core.extensions import db
from models import UserRole, Module
from models_accounting import Account, TransactionEntry, Transaction
from utils.helpers import log_activity
from utils.chart_of_accounts import (
    create_default_chart_of_accounts,
    get_accounts_tree,
    get_account_hierarchy,
    calculate_account_balance
)

# ────────────────────────────────────────────────────────────────────────────
# 🔧 إنشاء البلوبرينت
# ────────────────────────────────────────────────────────────────────────────

charts_bp = Blueprint(
    'accounting_charts',
    __name__,
    url_prefix='/accounting'
)


# ════════════════════════════════════════════════════════════════════════════
# 🌳 شجرة الحسابات والعروض
# ════════════════════════════════════════════════════════════════════════════

@charts_bp.route('/chart-of-accounts')
@login_required
def chart_of_accounts():
    """عرض شجرة الحسابات"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    accounts_tree = get_accounts_tree()
    
    total_accounts = Account.query.filter_by(is_active=True).count()
    main_accounts = Account.query.filter_by(level=1, is_active=True).count()
    sub_accounts = Account.query.filter_by(level=2, is_active=True).count()
    detail_accounts = Account.query.filter_by(level=3, is_active=True).count()
    
    return render_template('accounting/chart_of_accounts.html',
                         accounts_tree=accounts_tree,
                         total_accounts=total_accounts,
                         main_accounts=main_accounts,
                         sub_accounts=sub_accounts,
                         detail_accounts=detail_accounts)


@charts_bp.route('/create-default-accounts', methods=['POST'])
@login_required
def create_default_accounts():
    """إنشاء الحسابات الافتراضية"""
    if not current_user._is_admin_role():
        flash('غير مسموح لك بتنفيذ هذا الإجراء', 'danger')
        return redirect(url_for('accounting_charts.chart_of_accounts'))
    
    try:
        success, message = create_default_chart_of_accounts()
        if success:
            log_activity("إنشاء شجرة الحسابات الافتراضية")
            flash(message, 'success')
        else:
            flash(message, 'warning')
    except Exception as e:
        flash(f'خطأ في إنشاء الحسابات: {str(e)}', 'danger')
    
    return redirect(url_for('accounting_charts.chart_of_accounts'))


@charts_bp.route('/account/<int:account_id>/balance')
@login_required
def account_balance(account_id):
    """عرض رصيد حساب مع التفاصيل"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        return jsonify({'error': 'غير مسموح'}), 403
    
    try:
        account = Account.query.get_or_404(account_id)
        
        total_balance = calculate_account_balance(account_id, True)
        account_balance_only = account.balance
        
        hierarchy = get_account_hierarchy(account_id)
        
        children = Account.query.filter_by(parent_id=account_id, is_active=True).all()
        
        return jsonify({
            'account': {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'name_en': account.name_en,
                'type': account.account_type.value,
                'level': account.level
            },
            'balances': {
                'account_only': float(account_balance_only),
                'with_children': float(total_balance)
            },
            'hierarchy': [{'code': acc.code, 'name': acc.name} for acc in hierarchy],
            'children': [{'id': child.id, 'code': child.code, 'name': child.name, 'balance': float(child.balance)} for child in children]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@charts_bp.route('/account/<int:account_id>/balance-page')
@login_required
def account_balance_page(account_id):
    """صفحة تفاصيل رصيد الحساب"""
    if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        account = Account.query.get_or_404(account_id)
        
        total_balance = calculate_account_balance(account_id, True)
        hierarchy = get_account_hierarchy(account_id)
        children = Account.query.filter_by(parent_id=account_id, is_active=True).all()
        
        recent_transactions = TransactionEntry.query.filter_by(account_id=account_id)\
            .join(Transaction)\
            .filter(Transaction.is_approved == True)\
            .order_by(desc(Transaction.transaction_date))\
            .limit(10).all()
        
        return render_template('accounting/account_balance.html',
                             account=account,
                             total_balance=total_balance,
                             hierarchy=hierarchy,
                             children=children,
                             recent_transactions=recent_transactions)
        
    except Exception as e:
        flash(f'خطأ في جلب تفاصيل الحساب: {str(e)}', 'danger')
        return redirect(url_for('accounting_charts.chart_of_accounts'))


@charts_bp.route('/account/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    """حذف حساب"""
    if not current_user._is_admin_role():
        flash('غير مسموح لك بتنفيذ هذا الإجراء', 'danger')
        return redirect(url_for('accounting_charts.chart_of_accounts'))
    
    try:
        account = Account.query.get_or_404(account_id)
        
        children_count = Account.query.filter_by(parent_id=account_id, is_active=True).count()
        if children_count > 0:
            flash(f'لا يمكن حذف الحساب لأنه يحتوي على {children_count} حساب فرعي', 'danger')
            return redirect(url_for('accounting_charts.account_balance_page', account_id=account_id))
        
        transactions_count = TransactionEntry.query.filter_by(account_id=account_id).count()
        if transactions_count > 0:
            flash(f'لا يمكن حذف الحساب لأنه يحتوي على {transactions_count} معاملة مسجلة', 'danger')
            return redirect(url_for('accounting_charts.account_balance_page', account_id=account_id))
        
        if account.balance != 0:
            flash(f'لا يمكن حذف الحساب لأن رصيده غير صفر ({account.balance} ريال)', 'danger')
            return redirect(url_for('accounting_charts.account_balance_page', account_id=account_id))
        
        account_info = f"{account.code} - {account.name}"
        
        db.session.delete(account)
        db.session.commit()
        
        log_activity(f"حذف الحساب: {account_info}")
        flash(f'تم حذف الحساب {account_info} بنجاح', 'success')
        return redirect(url_for('accounting_charts.chart_of_accounts'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ في حذف الحساب: {str(e)}', 'danger')
        return redirect(url_for('accounting_charts.account_balance_page', account_id=account_id))
