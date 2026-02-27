"""
Payroll and quick-entry routes for accounting extended blueprint.
"""

from datetime import datetime, date
from decimal import Decimal

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import extract

from core.extensions import db
from models import Employee, Department, Module
from models_accounting import (
    Account,
    AccountType,
    AccountingSettings,
    CostCenter,
    EntryType,
    FiscalYear,
    Transaction,
    TransactionEntry,
    TransactionType,
)
from forms.accounting import QuickEntryForm, SalaryProcessingForm
from services.accounting_service import AccountingService
from services.finance_bridge import validate_accounting_payload, ERPNextBridgeError
from utils.helpers import log_activity


def register_payroll_routes(accounting_ext_bp):
    @accounting_ext_bp.route('/quick-entry', methods=['GET', 'POST'])
    @login_required
    def quick_entry():
        if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
            flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
            return redirect(url_for('dashboard.index'))

        form = QuickEntryForm()

        accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
        cost_centers = CostCenter.query.filter_by(is_active=True).all()

        form.debit_account_id.choices = [(acc.id, f"{acc.code} - {acc.name}") for acc in accounts]
        form.credit_account_id.choices = [(acc.id, f"{acc.code} - {acc.name}") for acc in accounts]
        form.cost_center_id.choices = [('', 'لا يوجد')] + [(cc.id, cc.name) for cc in cost_centers]

        if form.validate_on_submit():
            ok, payload = AccountingService.create_quick_entry_transaction(form_data=form, user_id=current_user.id)
            if ok:
                log_activity(f"إضافة قيد سريع: {payload}")
                flash('تم إضافة القيد بنجاح', 'success')
                return redirect(url_for('accounting.transactions'))

            flash(payload, 'danger')

        return render_template('accounting/quick_entry.html', form=form)

    @accounting_ext_bp.route('/salary-processing', methods=['GET', 'POST'])
    @login_required
    def salary_processing():
        if not (current_user._is_admin_role() or current_user.has_module_access(Module.ACCOUNTING)):
            flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
            return redirect(url_for('dashboard.index'))

        form = SalaryProcessingForm()

        departments = Department.query.all()
        accounts = Account.query.filter_by(is_active=True).all()

        form.department_id.choices = [('', 'جميع الأقسام')] + [(d.id, d.name) for d in departments]
        form.salary_account_id.choices = [('', 'اختر حساب الرواتب')] + [
            (a.id, f"{a.code} - {a.name}") for a in accounts if 'راتب' in a.name or a.code.startswith('5')
        ]
        form.payable_account_id.choices = [('', 'اختر حساب المستحقات')] + [
            (a.id, f"{a.code} - {a.name}")
            for a in accounts
            if 'دائن' in a.name or 'مستحق' in a.name or a.code.startswith('2')
        ]

        if form.validate_on_submit():
            try:
                existing_processing = Transaction.query.filter(
                    Transaction.transaction_type == TransactionType.SALARY,
                    extract('month', Transaction.transaction_date) == int(form.month.data),
                    extract('year', Transaction.transaction_date) == form.year.data,
                ).first()

                if existing_processing:
                    flash(f'تم معالجة رواتب شهر {form.month.data}/{form.year.data} مسبقاً', 'warning')
                    return render_template('accounting/salary_processing.html', form=form)

                employees_query = Employee.query.filter_by(status='active')

                if not form.process_all.data and form.department_id.data:
                    employees_query = employees_query.join(Employee.departments).filter(
                        Department.id == form.department_id.data
                    )

                employees = employees_query.all()

                if not employees:
                    flash('لا يوجد موظفين للمعالجة', 'warning')
                    return render_template('accounting/salary_processing.html', form=form)

                salary_expense_account = Account.query.filter_by(code='4101').first()
                cash_account = Account.query.filter_by(code='1001').first()

                if not salary_expense_account or not cash_account:
                    missing_accounts = []
                    if not salary_expense_account:
                        missing_accounts.append('مصروف رواتب (4101)')
                    if not cash_account:
                        missing_accounts.append('النقدية (1001)')
                    flash(f'الحسابات المحاسبية المفقودة: {", ".join(missing_accounts)}', 'danger')
                    return render_template('accounting/salary_processing.html', form=form)

                process_date = date(form.year.data, int(form.month.data), 1)
                try:
                    validate_accounting_payload(
                        entries=[
                            {'account_id': salary_expense_account.id, 'debit': 1, 'credit': 0},
                            {'account_id': cash_account.id, 'debit': 0, 'credit': 1},
                        ],
                        entry_date=process_date,
                        require_entries=True,
                    )
                except ERPNextBridgeError as validation_exc:
                    flash(f'فشل التحقق المحاسبي قبل الترحيل: {validation_exc}', 'danger')
                    return render_template('accounting/salary_processing.html', form=form)

                settings = AccountingSettings.query.first()
                if not settings:
                    settings = AccountingSettings(company_name='شركة نُظم', next_transaction_number=1)
                    db.session.add(settings)
                    db.session.flush()

                fiscal_year = FiscalYear.query.filter_by(is_active=True).first()

                total_salaries = Decimal('0')
                processed_count = 0

                for employee in employees:
                    if not employee.salary:
                        continue

                    basic_salary = Decimal(str(employee.salary))
                    allowances = Decimal(str(employee.allowances or 0))
                    deductions = Decimal(str(employee.deductions or 0))
                    net_salary = basic_salary + allowances - deductions

                    if net_salary <= 0:
                        continue

                    transaction_number = f"{settings.transaction_prefix}{settings.next_transaction_number:06d}"

                    transaction = Transaction(
                        transaction_number=transaction_number,
                        transaction_date=process_date,
                        transaction_type=TransactionType.SALARY,
                        description=f"راتب شهر {form.month.data}/{form.year.data} - {employee.name}",
                        total_amount=net_salary,
                        fiscal_year_id=fiscal_year.id,
                        employee_id=employee.id,
                        created_by_id=current_user.id,
                        is_approved=True,
                        approval_date=datetime.utcnow(),
                        approved_by_id=current_user.id,
                    )

                    db.session.add(transaction)
                    db.session.flush()

                    debit_entry = TransactionEntry(
                        transaction_id=transaction.id,
                        account_id=salary_expense_account.id,
                        entry_type=EntryType.DEBIT,
                        amount=net_salary,
                        description=f"راتب {employee.name}",
                    )
                    db.session.add(debit_entry)

                    credit_entry = TransactionEntry(
                        transaction_id=transaction.id,
                        account_id=cash_account.id,
                        entry_type=EntryType.CREDIT,
                        amount=net_salary,
                        description=f"صرف راتب {employee.name}",
                    )
                    db.session.add(credit_entry)

                    salary_expense_account.balance += net_salary
                    cash_account.balance -= net_salary

                    total_salaries += net_salary
                    processed_count += 1
                    settings.next_transaction_number += 1

                db.session.commit()

                log_activity(
                    f"معالجة رواتب شهر {form.month.data}/{form.year.data}: {processed_count} موظف بإجمالي {total_salaries} ريال"
                )
                flash(f'تم معالجة رواتب {processed_count} موظف بإجمالي {total_salaries:,.2f} ريال', 'success')
                return redirect(url_for('accounting.transactions'))

            except Exception as e:
                db.session.rollback()
                flash(f'خطأ في معالجة الرواتب: {str(e)}', 'danger')

        return render_template('accounting/salary_processing.html', form=form)
