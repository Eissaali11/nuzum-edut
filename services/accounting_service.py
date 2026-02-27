"""
خدمات النظام المحاسبي
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
from core.extensions import db
from models_accounting import *
from models import Employee, Vehicle, Department, employee_departments
from modules.accounting.domain.profitability_models import ContractResource


logger = logging.getLogger(__name__)


class AccountingService:
    """خدمات النظام المحاسبي"""
    
    @staticmethod
    def initialize_chart_of_accounts():
        """إنشاء دليل الحسابات الأساسي"""
        try:
            # التحقق من وجود حسابات
            if Account.query.count() > 0:
                return True, "دليل الحسابات موجود مسبقاً"
            
            # الحسابات الأساسية
            base_accounts = [
                # الأصول (1xxx)
                {'code': '1000', 'name': 'الأصول', 'type': AccountType.ASSETS, 'parent': None},
                {'code': '1001', 'name': 'النقدية في الصندوق', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1002', 'name': 'البنك - الراجحي', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1003', 'name': 'البنك - الأهلي', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1100', 'name': 'العملاء', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1200', 'name': 'المخزون', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1300', 'name': 'الأصول الثابتة', 'type': AccountType.ASSETS, 'parent': '1000'},
                {'code': '1301', 'name': 'المركبات', 'type': AccountType.ASSETS, 'parent': '1300'},
                {'code': '1302', 'name': 'الأثاث والتجهيزات', 'type': AccountType.ASSETS, 'parent': '1300'},
                {'code': '1303', 'name': 'الحاسب الآلي', 'type': AccountType.ASSETS, 'parent': '1300'},
                
                # الخصوم (2xxx)
                {'code': '2000', 'name': 'الخصوم', 'type': AccountType.LIABILITIES, 'parent': None},
                {'code': '2001', 'name': 'الموردون', 'type': AccountType.LIABILITIES, 'parent': '2000'},
                {'code': '2100', 'name': 'الرواتب المستحقة', 'type': AccountType.LIABILITIES, 'parent': '2000'},
                {'code': '2200', 'name': 'الضرائب المستحقة', 'type': AccountType.LIABILITIES, 'parent': '2000'},
                {'code': '2300', 'name': 'القروض طويلة الأجل', 'type': AccountType.LIABILITIES, 'parent': '2000'},
                
                # حقوق الملكية (3xxx)
                {'code': '3000', 'name': 'حقوق الملكية', 'type': AccountType.EQUITY, 'parent': None},
                {'code': '3001', 'name': 'رأس المال', 'type': AccountType.EQUITY, 'parent': '3000'},
                {'code': '3002', 'name': 'الأرباح المحتجزة', 'type': AccountType.EQUITY, 'parent': '3000'},
                
                # الإيرادات (4xxx)
                {'code': '4000', 'name': 'الإيرادات', 'type': AccountType.REVENUE, 'parent': None},
                {'code': '4001', 'name': 'إيرادات الخدمات', 'type': AccountType.REVENUE, 'parent': '4000'},
                {'code': '4002', 'name': 'إيرادات أخرى', 'type': AccountType.REVENUE, 'parent': '4000'},
                
                # المصروفات (5xxx)
                {'code': '5000', 'name': 'المصروفات', 'type': AccountType.EXPENSES, 'parent': None},
                {'code': '5001', 'name': 'مصروف الرواتب', 'type': AccountType.EXPENSES, 'parent': '5000'},
                {'code': '5002', 'name': 'مصروف البدلات', 'type': AccountType.EXPENSES, 'parent': '5000'},
                {'code': '5100', 'name': 'مصروفات المركبات', 'type': AccountType.EXPENSES, 'parent': '5000'},
                {'code': '5101', 'name': 'مصروف الوقود', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5102', 'name': 'مصروف الصيانة', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5103', 'name': 'مصروف التأمين', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5104', 'name': 'مصروف التسجيل', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5105', 'name': 'المخالفات', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5199', 'name': 'مصروفات مركبات أخرى', 'type': AccountType.EXPENSES, 'parent': '5100'},
                {'code': '5200', 'name': 'المصروفات الإدارية', 'type': AccountType.EXPENSES, 'parent': '5000'},
                {'code': '5201', 'name': 'مصروف الإيجار', 'type': AccountType.EXPENSES, 'parent': '5200'},
                {'code': '5202', 'name': 'مصروف الكهرباء', 'type': AccountType.EXPENSES, 'parent': '5200'},
                {'code': '5203', 'name': 'مصروف الاتصالات', 'type': AccountType.EXPENSES, 'parent': '5200'},
                {'code': '5204', 'name': 'مصروف القرطاسية', 'type': AccountType.EXPENSES, 'parent': '5200'},
                {'code': '5299', 'name': 'مصروفات إدارية أخرى', 'type': AccountType.EXPENSES, 'parent': '5200'},
            ]
            
            # إنشاء الحسابات
            account_map = {}
            for acc_data in base_accounts:
                parent_id = None
                if acc_data['parent']:
                    parent_id = account_map.get(acc_data['parent'])
                
                account = Account(
                    code=acc_data['code'],
                    name=acc_data['name'],
                    account_type=acc_data['type'],
                    parent_id=parent_id,
                    level=1 if parent_id else 0,
                    is_active=True
                )
                
                db.session.add(account)
                db.session.flush()
                account_map[acc_data['code']] = account.id
            
            db.session.commit()
            return True, "تم إنشاء دليل الحسابات بنجاح"
            
        except Exception as e:
            db.session.rollback()
            return False, f"خطأ في إنشاء دليل الحسابات: {str(e)}"
    
    @staticmethod
    def create_fiscal_year(year, name=None):
        """إنشاء سنة مالية جديدة"""
        try:
            if not name:
                name = f"السنة المالية {year}"
            
            # التحقق من عدم وجود سنة مالية مشابهة
            existing = FiscalYear.query.filter(
                func.extract('year', FiscalYear.start_date) == year
            ).first()
            
            if existing:
                return False, f"السنة المالية {year} موجودة مسبقاً"
            
            # إلغاء تفعيل السنوات السابقة
            FiscalYear.query.update({'is_active': False})
            
            fiscal_year = FiscalYear(
                name=name,
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
                is_active=True,
                is_closed=False
            )
            
            db.session.add(fiscal_year)
            db.session.commit()
            
            return True, f"تم إنشاء السنة المالية {year} بنجاح"
            
        except Exception as e:
            db.session.rollback()
            return False, f"خطأ في إنشاء السنة المالية: {str(e)}"
    
    @staticmethod
    def create_cost_centers():
        """إنشاء مراكز التكلفة من الأقسام الموجودة"""
        try:
            from models import Department
            
            departments = Department.query.all()
            created_count = 0
            
            for dept in departments:
                # التحقق من عدم وجود مركز تكلفة لهذا القسم
                existing = CostCenter.query.filter_by(name=dept.name).first()
                if existing:
                    continue
                
                cost_center = CostCenter(
                    code=f"CC{dept.id:03d}",
                    name=dept.name,
                    description=f"مركز تكلفة قسم {dept.name}",
                    is_active=True
                )
                
                db.session.add(cost_center)
                created_count += 1
            
            db.session.commit()
            return True, f"تم إنشاء {created_count} مركز تكلفة"
            
        except Exception as e:
            db.session.rollback()
            return False, f"خطأ في إنشاء مراكز التكلفة: {str(e)}"
    
    @staticmethod
    def auto_create_salary_entries(month, year, department_id=None):
        """إنشاء قيود الرواتب تلقائياً"""
        try:
            # التحقق من وجود معالجة سابقة
            existing = Transaction.query.filter(
                Transaction.transaction_type == TransactionType.SALARY,
                func.extract('month', Transaction.transaction_date) == month,
                func.extract('year', Transaction.transaction_date) == year
            ).first()
            
            if existing:
                return False, f"تم معالجة رواتب شهر {month}/{year} مسبقاً"
            
            # الحصول على الموظفين
            query = Employee.query.filter_by(status='نشط')
            if department_id:
                query = query.join(Employee.departments).filter(Department.id == department_id)
            
            employees = query.all()
            
            if not employees:
                return False, "لا يوجد موظفين للمعالجة"
            
            # الحسابات المطلوبة
            salary_account = Account.query.filter_by(code='5001').first()
            cash_account = Account.query.filter_by(code='1001').first()
            
            if not salary_account or not cash_account:
                return False, "الحسابات المحاسبية للرواتب غير موجودة"
            
            # الإعدادات
            settings = AccountingSettings.query.first()
            if not settings:
                settings = AccountingSettings(
                    company_name='شركة نُظم',
                    next_transaction_number=1
                )
                db.session.add(settings)
                db.session.flush()
            
            fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
            
            total_processed = 0
            total_amount = Decimal('0')
            
            for employee in employees:
                if not employee.salary or employee.salary <= 0:
                    continue
                
                net_salary = Decimal(str(employee.salary))
                if employee.allowances:
                    net_salary += Decimal(str(employee.allowances))
                if employee.deductions:
                    net_salary -= Decimal(str(employee.deductions))
                
                if net_salary <= 0:
                    continue
                
                # إنشاء معاملة الراتب
                transaction_number = f"{settings.transaction_prefix}{settings.next_transaction_number:06d}"
                
                transaction = Transaction(
                    transaction_number=transaction_number,
                    transaction_date=date(year, month, 1),
                    transaction_type=TransactionType.SALARY,
                    description=f"راتب شهر {month}/{year} - {employee.name}",
                    total_amount=net_salary,
                    fiscal_year_id=fiscal_year.id,
                    employee_id=employee.id,
                    created_by_id=1,  # النظام
                    is_approved=True,
                    approval_date=datetime.utcnow()
                )
                
                db.session.add(transaction)
                db.session.flush()
                
                # القيود
                debit_entry = TransactionEntry(
                    transaction_id=transaction.id,
                    account_id=salary_account.id,
                    entry_type=EntryType.DEBIT,
                    amount=net_salary,
                    description=f"راتب {employee.name}"
                )
                
                credit_entry = TransactionEntry(
                    transaction_id=transaction.id,
                    account_id=cash_account.id,
                    entry_type=EntryType.CREDIT,
                    amount=net_salary,
                    description=f"صرف راتب {employee.name}"
                )
                
                db.session.add(debit_entry)
                db.session.add(credit_entry)
                
                # تحديث الأرصدة
                salary_account.balance += net_salary
                cash_account.balance -= net_salary
                
                total_processed += 1
                total_amount += net_salary
                settings.next_transaction_number += 1
            
            db.session.commit()
            return True, f"تم معالجة {total_processed} راتب بإجمالي {total_amount:,.2f} ريال"
            
        except Exception as e:
            db.session.rollback()
            return False, f"خطأ في معالجة الرواتب: {str(e)}"
    
    @staticmethod
    def calculate_account_balance(account_id, as_of_date=None):
        """حساب رصيد حساب معين"""
        try:
            if not as_of_date:
                as_of_date = date.today()
            
            account = Account.query.get(account_id)
            if not account:
                return Decimal('0')
            
            # جمع المدين والدائن
            debits = db.session.query(func.sum(TransactionEntry.amount)).join(Transaction).filter(
                TransactionEntry.account_id == account_id,
                TransactionEntry.entry_type == EntryType.DEBIT,
                Transaction.transaction_date <= as_of_date,
                Transaction.is_approved == True
            ).scalar() or Decimal('0')
            
            credits = db.session.query(func.sum(TransactionEntry.amount)).join(Transaction).filter(
                TransactionEntry.account_id == account_id,
                TransactionEntry.entry_type == EntryType.CREDIT,
                Transaction.transaction_date <= as_of_date,
                Transaction.is_approved == True
            ).scalar() or Decimal('0')
            
            # حساب الرصيد حسب نوع الحساب
            if account.account_type in [AccountType.ASSETS, AccountType.EXPENSES]:
                balance = debits - credits
            else:
                balance = credits - debits
            
            return balance
            
        except Exception as e:
            return Decimal('0')
    
    @staticmethod
    def get_financial_summary(as_of_date=None):
        """الحصول على الملخص المالي"""
        try:
            if not as_of_date:
                as_of_date = date.today()
            
            # إجمالي الأصول
            total_assets = db.session.query(func.sum(Account.balance)).filter(
                Account.account_type == AccountType.ASSETS,
                Account.is_active == True
            ).scalar() or Decimal('0')
            
            # إجمالي الخصوم
            total_liabilities = db.session.query(func.sum(Account.balance)).filter(
                Account.account_type == AccountType.LIABILITIES,
                Account.is_active == True
            ).scalar() or Decimal('0')
            
            # إجمالي الإيرادات
            total_revenue = db.session.query(func.sum(Account.balance)).filter(
                Account.account_type == AccountType.REVENUE,
                Account.is_active == True
            ).scalar() or Decimal('0')
            
            # إجمالي المصروفات
            total_expenses = db.session.query(func.sum(Account.balance)).filter(
                Account.account_type == AccountType.EXPENSES,
                Account.is_active == True
            ).scalar() or Decimal('0')
            
            # صافي الدخل
            net_income = total_revenue - total_expenses
            
            return {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_income': net_income,
                'equity': total_assets - total_liabilities
            }
            
        except Exception as e:
            return None
    
    @staticmethod
    def update_account_balances():
        """تحديث أرصدة جميع الحسابات"""
        try:
            accounts = Account.query.filter_by(is_active=True).all()
            
            for account in accounts:
                balance = AccountingService.calculate_account_balance(account.id)
                account.balance = balance
                account.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, "تم تحديث الأرصدة بنجاح"
            
        except Exception as e:
            db.session.rollback()
            return False, f"خطأ في تحديث الأرصدة: {str(e)}"

    @staticmethod
    def get_profitability_dashboard_data(month=None, year=None):
        """تجهيز سياق لوحة ربحية المشاريع."""
        from modules.accounting.application.profitability_service import get_all_projects_summary

        now = datetime.now()
        month = int(month or now.month)
        year = int(year or now.year)

        months = [
            (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'),
            (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'),
            (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
        ]

        return {
            'summary': get_all_projects_summary(month, year),
            'months': months,
            'selected_month': month,
            'selected_year': year,
            'current_year': now.year,
        }

    @staticmethod
    def get_profitability_report_data(department_id, month=None, year=None):
        """تجهيز سياق تقرير ربحية مشروع مفرد."""
        from modules.accounting.application.profitability_service import calculate_project_profitability

        if not department_id:
            return None

        now = datetime.now()
        month = int(month or now.month)
        year = int(year or now.year)

        result = calculate_project_profitability(department_id, month, year)
        if not result:
            return None

        return {
            'result': result,
            'selected_month': month,
            'selected_year': year,
            'selected_department': department_id,
        }

    @staticmethod
    def _parse_non_negative_float(value, default=0.0):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return float(default)
        return max(0.0, parsed)

    @staticmethod
    def get_contract_resources_view_data(contract):
        dept_employees = (
            Employee.query
            .join(employee_departments)
            .filter(
                employee_departments.c.department_id == contract.department_id,
                Employee.status == 'active'
            )
            .order_by(Employee.name)
            .all()
        )

        existing_resources = {r.employee_id: r for r in contract.resources.all()}

        employees_data = []
        for emp in dept_employees:
            res = existing_resources.get(emp.id)
            employees_data.append({
                'employee': emp,
                'billing_rate': float(res.billing_rate) if res else 0,
                'billing_type': res.billing_type if res else 'monthly',
                'overhead': float(res.overhead_monthly) if res else 0,
                'housing': float(res.housing_allowance) if res else 0,
            })

        return {
            'dept_employees': dept_employees,
            'existing_resources': existing_resources,
            'employees_data': employees_data,
        }

    @staticmethod
    def save_contract_resources(contract, form_data):
        employee_ids = form_data.getlist('employee_ids')
        billing_rates = form_data.getlist('billing_rates')
        billing_types = form_data.getlist('billing_types')
        overheads = form_data.getlist('overheads')
        housings = form_data.getlist('housings')

        list_len = len(employee_ids)
        if not (len(billing_rates) == len(billing_types) == len(overheads) == len(housings) == list_len):
            return False, 'خطأ في البيانات المرسلة — عدم تطابق الحقول'

        view_data = AccountingService.get_contract_resources_view_data(contract)
        dept_employees = view_data['dept_employees']
        existing_resources = view_data['existing_resources']
        valid_emp_ids = {e.id for e in dept_employees}

        try:
            for emp_id_str, rate_str, btype, overhead_str, housing_str in zip(
                employee_ids, billing_rates, billing_types, overheads, housings
            ):
                emp_id = int(emp_id_str)
                if emp_id not in valid_emp_ids:
                    continue

                rate = AccountingService._parse_non_negative_float(rate_str or 0)
                overhead_val = AccountingService._parse_non_negative_float(overhead_str or 0)
                housing_val = AccountingService._parse_non_negative_float(housing_str or 0)
                btype = btype if btype in ('monthly', 'daily') else 'monthly'

                if emp_id in existing_resources:
                    res = existing_resources[emp_id]
                    res.billing_rate = rate
                    res.billing_type = btype
                    res.overhead_monthly = overhead_val
                    res.housing_allowance = housing_val
                    res.is_active = True
                else:
                    res = ContractResource(
                        contract_id=contract.id,
                        employee_id=emp_id,
                        billing_rate=rate,
                        billing_type=btype,
                        overhead_monthly=overhead_val,
                        housing_allowance=housing_val,
                        is_active=True,
                    )
                    db.session.add(res)

            db.session.commit()
            return True, 'تم حفظ بيانات الموارد بنجاح'
        except (ValueError, TypeError) as e:
            db.session.rollback()
            logger.error(f'Error saving resources: {e}')
            return False, 'خطأ في البيانات المرسلة'

    @staticmethod
    def create_quick_entry_transaction(form_data, user_id):
        try:
            settings = AccountingSettings.query.first()
            if not settings:
                settings = AccountingSettings(company_name='شركة نُظم', next_transaction_number=1)
                db.session.add(settings)
                db.session.flush()

            transaction_number = f"{settings.transaction_prefix}{settings.next_transaction_number:06d}"

            fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
            if not fiscal_year:
                return False, 'لا توجد سنة مالية نشطة'

            amount = form_data.amount.data
            transaction = Transaction(
                transaction_number=transaction_number,
                transaction_date=form_data.transaction_date.data,
                transaction_type=TransactionType.MANUAL,
                reference_number=form_data.reference_number.data,
                description=form_data.description.data,
                total_amount=amount,
                fiscal_year_id=fiscal_year.id,
                cost_center_id=form_data.cost_center_id.data if form_data.cost_center_id.data else None,
                created_by_id=user_id,
                is_approved=True,
                approval_date=datetime.utcnow(),
                approved_by_id=user_id,
            )

            db.session.add(transaction)
            db.session.flush()

            debit_entry = TransactionEntry(
                transaction_id=transaction.id,
                account_id=form_data.debit_account_id.data,
                entry_type=EntryType.DEBIT,
                amount=amount,
                description=form_data.description.data,
            )
            credit_entry = TransactionEntry(
                transaction_id=transaction.id,
                account_id=form_data.credit_account_id.data,
                entry_type=EntryType.CREDIT,
                amount=amount,
                description=form_data.description.data,
            )
            db.session.add(debit_entry)
            db.session.add(credit_entry)

            debit_account = Account.query.get(form_data.debit_account_id.data)
            credit_account = Account.query.get(form_data.credit_account_id.data)

            if debit_account.account_type in [AccountType.ASSETS, AccountType.EXPENSES]:
                debit_account.balance += amount
            else:
                debit_account.balance -= amount

            if credit_account.account_type in [AccountType.ASSETS, AccountType.EXPENSES]:
                credit_account.balance -= amount
            else:
                credit_account.balance += amount

            settings.next_transaction_number += 1
            db.session.commit()
            return True, transaction.transaction_number
        except Exception as e:
            db.session.rollback()
            return False, f'خطأ في إضافة القيد: {str(e)}'

    @staticmethod
    def create_vehicle_expense_transaction(form_data, user_id):
        try:
            expense_accounts = {
                'fuel': Account.query.filter_by(code='5101').first(),
                'maintenance': Account.query.filter_by(code='5102').first(),
                'insurance': Account.query.filter_by(code='5103').first(),
                'registration': Account.query.filter_by(code='5104').first(),
                'fines': Account.query.filter_by(code='5105').first(),
                'other': Account.query.filter_by(code='5199').first(),
            }

            expense_account = expense_accounts.get(form_data.expense_type.data)
            cash_account = Account.query.filter_by(code='1001').first()
            if not expense_account or not cash_account:
                return False, 'الحسابات المحاسبية للمصروفات غير موجودة'

            settings = AccountingSettings.query.first()
            if not settings:
                return False, 'إعدادات النظام المحاسبي غير مهيأة'

            fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
            if not fiscal_year:
                return False, 'لا توجد سنة مالية نشطة'

            vehicle = Vehicle.query.get(form_data.vehicle_id.data)
            if not vehicle:
                return False, 'المركبة المحددة غير موجودة'

            transaction_number = f"{settings.transaction_prefix}{settings.next_transaction_number:06d}"
            amount = form_data.amount.data
            transaction = Transaction(
                transaction_number=transaction_number,
                transaction_date=form_data.expense_date.data,
                transaction_type=TransactionType.VEHICLE_EXPENSE,
                reference_number=form_data.receipt_number.data if hasattr(form_data, 'receipt_number') else '',
                description=form_data.description.data,
                total_amount=amount,
                fiscal_year_id=fiscal_year.id,
                vehicle_id=vehicle.id,
                vendor_id=form_data.vendor_id.data if form_data.vendor_id.data else None,
                created_by_id=user_id,
                is_approved=True,
                approval_date=datetime.utcnow(),
                approved_by_id=user_id,
            )
            db.session.add(transaction)
            db.session.flush()

            debit_entry = TransactionEntry(
                transaction_id=transaction.id,
                account_id=expense_account.id,
                entry_type=EntryType.DEBIT,
                amount=amount,
                description=f"{form_data.description.data} - {vehicle.plate_number}",
            )
            db.session.add(debit_entry)

            if form_data.vendor_id.data:
                vendor = Vendor.query.get(form_data.vendor_id.data)
                vendor_account = Account.query.filter_by(code=f"2{vendor.id:03d}").first() if vendor else None
                credit_account = vendor_account or cash_account
            else:
                credit_account = cash_account

            credit_entry = TransactionEntry(
                transaction_id=transaction.id,
                account_id=credit_account.id,
                entry_type=EntryType.CREDIT,
                amount=amount,
                description=f"دفع {form_data.description.data}",
            )
            db.session.add(credit_entry)

            expense_account.balance += amount
            credit_account.balance -= amount
            settings.next_transaction_number += 1

            db.session.commit()
            return True, {'transaction_number': transaction.transaction_number, 'vehicle_plate': vehicle.plate_number, 'amount': amount}
        except Exception as e:
            db.session.rollback()
            return False, f'خطأ في إضافة مصروف المركبة: {str(e)}'