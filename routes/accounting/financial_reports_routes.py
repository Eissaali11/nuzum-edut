"""
Financial reports routes for accounting extended blueprint.
"""

from datetime import date, datetime
from decimal import Decimal

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func

from core.extensions import db
from models import Module
from models_accounting import (
    Account,
    AccountType,
    EntryType,
    FiscalYear,
    Transaction,
    TransactionEntry,
)


def register_financial_reports_routes(accounting_ext_bp):
    @accounting_ext_bp.route('/reports/trial-balance')
    @login_required
    def trial_balance():
        if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
            flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
            return redirect(url_for('dashboard.index'))

        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
        if not fiscal_year:
            flash('لا توجد سنة مالية نشطة', 'danger')
            return redirect(url_for('accounting.dashboard'))

        if not from_date:
            from_date = fiscal_year.start_date.strftime('%Y-%m-%d')
        if not to_date:
            to_date = date.today().strftime('%Y-%m-%d')

        from sqlalchemy import case

        accounts_balances = db.session.query(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
            func.sum(
                case((TransactionEntry.entry_type == EntryType.DEBIT, TransactionEntry.amount), else_=0)
            ).label('total_debits'),
            func.sum(
                case((TransactionEntry.entry_type == EntryType.CREDIT, TransactionEntry.amount), else_=0)
            ).label('total_credits'),
        ).outerjoin(TransactionEntry).outerjoin(Transaction).filter(
            or_(Transaction.is_approved == True, Transaction.id.is_(None)),
            or_(
                and_(
                    Transaction.transaction_date >= datetime.strptime(from_date, '%Y-%m-%d').date(),
                    Transaction.transaction_date <= datetime.strptime(to_date, '%Y-%m-%d').date(),
                ),
                Transaction.id.is_(None),
            ),
            Account.is_active == True,
        ).group_by(Account.id, Account.code, Account.name, Account.account_type).order_by(Account.code).all()

        trial_balance_data = []
        total_debits = Decimal('0')
        total_credits = Decimal('0')

        for account in accounts_balances:
            debits = account.total_debits or Decimal('0')
            credits = account.total_credits or Decimal('0')

            if account.account_type in [AccountType.ASSETS, AccountType.EXPENSES]:
                balance = debits - credits
                if balance > 0:
                    debit_balance = balance
                    credit_balance = Decimal('0')
                else:
                    debit_balance = Decimal('0')
                    credit_balance = abs(balance)
            else:
                balance = credits - debits
                if balance > 0:
                    credit_balance = balance
                    debit_balance = Decimal('0')
                else:
                    credit_balance = Decimal('0')
                    debit_balance = abs(balance)

            if debit_balance > 0 or credit_balance > 0:
                trial_balance_data.append(
                    {
                        'code': account.code,
                        'name': account.name,
                        'account_type': account.account_type.value,
                        'debit_balance': debit_balance,
                        'credit_balance': credit_balance,
                    }
                )

                total_debits += debit_balance
                total_credits += credit_balance

        return render_template(
            'accounting/reports/trial_balance.html',
            trial_balance_data=trial_balance_data,
            total_debits=total_debits,
            total_credits=total_credits,
            from_date=from_date,
            to_date=to_date,
            fiscal_year=fiscal_year,
        )

    @accounting_ext_bp.route('/reports/balance-sheet')
    @login_required
    def balance_sheet():
        if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
            flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
            return redirect(url_for('dashboard.index'))

        as_of_date = request.args.get('as_of_date', date.today().strftime('%Y-%m-%d'))

        accounts_query = db.session.query(
            Account.code,
            Account.name,
            Account.account_type,
            func.sum(
                func.case((TransactionEntry.entry_type == EntryType.DEBIT, TransactionEntry.amount), else_=0)
                - func.case((TransactionEntry.entry_type == EntryType.CREDIT, TransactionEntry.amount), else_=0)
            ).label('balance'),
        ).outerjoin(TransactionEntry).outerjoin(Transaction).filter(
            Transaction.is_approved == True,
            Transaction.transaction_date <= datetime.strptime(as_of_date, '%Y-%m-%d').date(),
            Account.is_active == True,
            Account.account_type.in_([AccountType.ASSETS, AccountType.LIABILITIES, AccountType.EQUITY]),
        ).group_by(Account.id).order_by(Account.code).all()

        assets = []
        liabilities = []
        equity = []

        total_assets = Decimal('0')
        total_liabilities = Decimal('0')
        total_equity = Decimal('0')

        for account in accounts_query:
            balance = account.balance or Decimal('0')

            if account.account_type == AccountType.ASSETS:
                if balance != 0:
                    assets.append({'code': account.code, 'name': account.name, 'balance': balance})
                    total_assets += balance
            elif account.account_type == AccountType.LIABILITIES:
                if balance != 0:
                    liabilities.append({'code': account.code, 'name': account.name, 'balance': abs(balance)})
                    total_liabilities += abs(balance)
            elif account.account_type == AccountType.EQUITY:
                if balance != 0:
                    equity.append({'code': account.code, 'name': account.name, 'balance': abs(balance)})
                    total_equity += abs(balance)

        revenue_total = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.REVENUE,
            Account.is_active == True,
        ).scalar() or Decimal('0')

        expense_total = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.EXPENSES,
            Account.is_active == True,
        ).scalar() or Decimal('0')

        retained_earnings = revenue_total - expense_total
        total_equity += retained_earnings

        return render_template(
            'accounting/reports/balance_sheet.html',
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            retained_earnings=retained_earnings,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            as_of_date=as_of_date,
        )
