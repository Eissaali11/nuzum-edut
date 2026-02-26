"""
════════════════════════════════════════════════════════════════════════════
🔧 مساعد النظام المحاسبي - Accounting Helpers Module
════════════════════════════════════════════════════════════════════════════

يحتوي على دوال مساعدة مشتركة لجميع مسارات النظام المحاسبي
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, desc
from src.core.extensions import db

# ────────────────────────────────────────────────────────────────────────────
# ✓ التحقق من الصلاحيات
# ────────────────────────────────────────────────────────────────────────────

def check_accounting_access(current_user):
    """التحقق من صلاحية الوصول للنظام المحاسبي"""
    from models import UserRole, Module
    return (current_user.role == UserRole.ADMIN or 
            current_user.has_module_access(Module.ACCOUNTING))


# ────────────────────────────────────────────────────────────────────────────
# ✓ حسابات الإحصائيات المالية
# ────────────────────────────────────────────────────────────────────────────

def calculate_monthly_statistics(fiscal_year_id=None):
    """
    حساب الإحصائيات المالية الشهرية
    
    Returns:
        dict: قاموس يحتوي على الإحصائيات
    """
    from models_accounting import Account, Transaction, AccountType, TransactionType
    
    try:
        current_month_start = date.today().replace(day=1)
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # إجمالي الأصول
        total_assets = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.ASSETS,
            Account.is_active == True
        ).scalar() or 0
        
        # إجمالي الخصوم
        total_liabilities = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.LIABILITIES,
            Account.is_active == True
        ).scalar() or 0
        
        # حقوق الملكية
        total_equity = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.EQUITY,
            Account.is_active == True
        ).scalar() or 0
        
        # صافي الأرباح هذا الشهر
        monthly_revenue = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.REVENUE,
            Account.is_active == True
        ).scalar() or 0
        
        monthly_expenses = db.session.query(func.sum(Account.balance)).filter(
            Account.account_type == AccountType.EXPENSES,
            Account.is_active == True
        ).scalar() or 0
        
        net_profit = monthly_revenue - monthly_expenses
        
        # النسب المالية
        current_ratio = float(total_assets) / float(total_liabilities) if total_liabilities != 0 else 0
        debt_to_equity = float(total_liabilities) / float(total_equity) if total_equity != 0 else 0
        roa = (float(net_profit) / float(total_assets) * 100) if total_assets != 0 else 0
        roe = (float(net_profit) / float(total_equity) * 100) if total_equity != 0 else 0
        
        return {
            'assets': total_assets,
            'liabilities': total_liabilities,
            'equity': total_equity,
            'revenue': monthly_revenue,
            'expenses': monthly_expenses,
            'net_profit': net_profit,
            'ratios': {
                'current_ratio': current_ratio,
                'debt_to_equity': debt_to_equity,
                'roa': roa,
                'roe': roe
            },
            'date_range': {
                'start': current_month_start,
                'end': current_month_end
            }
        }
    
    except Exception as e:
        print(f"خطأ في حساب الإحصائيات: {str(e)}")
        return None


def get_recent_transactions(limit=10, approved_only=True):
    """الحصول على المعاملات الأخيرة"""
    from models_accounting import Transaction
    
    query = Transaction.query
    
    if approved_only:
        query = query.filter(Transaction.is_approved == True)
    
    return query.order_by(desc(Transaction.transaction_date)).limit(limit).all()


def get_pending_transactions_count(fiscal_year_id=None):
    """عدد المعاملات المعلقة (غير المعتمدة)"""
    from models_accounting import Transaction
    
    query = Transaction.query.filter(Transaction.is_approved == False)
    
    if fiscal_year_id:
        query = query.filter(Transaction.fiscal_year_id == fiscal_year_id)
    
    return query.count()


# ────────────────────────────────────────────────────────────────────────────
# ✓ تحليل مراكز التكلفة
# ────────────────────────────────────────────────────────────────────────────

def get_top_cost_centers(limit=5, from_date=None, to_date=None):
    """الحصول على مراكز التكلفة الأكثر إنفاقاً"""
    from models_accounting import CostCenter, Transaction, TransactionType
    
    query = db.session.query(
        CostCenter.name,
        func.sum(Transaction.total_amount).label('total_spent')
    ).join(Transaction)
    
    if from_date:
        query = query.filter(Transaction.transaction_date >= from_date)
    
    if to_date:
        query = query.filter(Transaction.transaction_date <= to_date)
    
    return query.filter(
        Transaction.is_approved == True,
        Transaction.transaction_type.in_([
            TransactionType.VEHICLE_EXPENSE,
            TransactionType.SALARY
        ])
    ).group_by(CostCenter.id).order_by(desc('total_spent')).limit(limit).all()


# ────────────────────────────────────────────────────────────────────────────
# ✓ بيانات الرسوم البيانية
# ────────────────────────────────────────────────────────────────────────────

def get_account_distribution_data():
    """توزيع الحسابات حسب النوع"""
    from models_accounting import Account
    
    return db.session.query(
        Account.account_type,
        func.sum(Account.balance).label('total')
    ).filter(Account.is_active == True).group_by(Account.account_type).all()


def get_monthly_expenses_data(months=6):
    """بيانات المصروفات عبر الأشهر"""
    from models_accounting import Transaction, TransactionType
    from sqlalchemy import extract
    
    start_date = date.today() - timedelta(days=30 * months)
    
    return db.session.query(
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.total_amount).label('total')
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.is_approved == True,
        Transaction.transaction_type == TransactionType.SALARY
    ).group_by('month').order_by('month').all()


# ────────────────────────────────────────────────────────────────────────────
# ✓ التحقق من صحة البيانات
# ────────────────────────────────────────────────────────────────────────────

def validate_transaction_balance(debits, credits, tolerance=0.01):
    """التحقق من توازن القيد"""
    total_debits = sum(float(amount) if amount else 0 for amount in debits)
    total_credits = sum(float(amount) if amount else 0 for amount in credits)
    return abs(total_debits - total_credits) <= tolerance


def validate_account_code_unique(code, exclude_id=None):
    """التحقق من عدم تكرار رمز الحساب"""
    from models_accounting import Account
    
    query = Account.query.filter_by(code=code)
    
    if exclude_id:
        query = query.filter(Account.id != exclude_id)
    
    return query.first() is None


# ────────────────────────────────────────────────────────────────────────────
# ✓ عمليات قاعدة البيانات
# ────────────────────────────────────────────────────────────────────────────

def get_next_transaction_number(prefix='TXN'):
    """الحصول على رقم المعاملة التالي"""
    from models_accounting import AccountingSettings
    
    settings = AccountingSettings.query.first()
    
    if not settings:
        settings = AccountingSettings(
            company_name='شركة نُظم',
            transaction_prefix=prefix,
            next_transaction_number=1
        )
        db.session.add(settings)
        db.session.flush()
    
    transaction_number = f"{settings.transaction_prefix}{settings.next_transaction_number:06d}"
    settings.next_transaction_number += 1
    db.session.commit()
    
    return transaction_number


def apply_changes_to_account_balance(account_id, debit_amount=0, credit_amount=0):
    """تطبيق التغييرات على رصيد الحساب"""
    from models_accounting import Account
    
    try:
        account = Account.query.get(account_id)
        
        if account:
            # حساب التغيير بناءً على نوع الحساب
            if account.account_type.value in ['assets', 'expenses']:
                account.balance += (debit_amount - credit_amount)
            else:
                account.balance += (credit_amount - debit_amount)
            
            db.session.commit()
            return True
        
        return False
    
    except Exception as e:
        print(f"خطأ في تحديث رصيد الحساب: {str(e)}")
        db.session.rollback()
        return False


# ────────────────────────────────────────────────────────────────────────────
# ✓ البحث والتصفية
# ────────────────────────────────────────────────────────────────────────────

def search_accounts(search_term, account_type_filter=None):
    """البحث في الحسابات"""
    from models_accounting import Account
    from sqlalchemy import or_
    
    query = Account.query
    
    if search_term:
        query = query.filter(or_(
            Account.name.contains(search_term),
            Account.code.contains(search_term)
        ))
    
    if account_type_filter:
        query = query.filter(Account.account_type == account_type_filter)
    
    return query.order_by(Account.code).all()


def search_transactions(search_term=None, transaction_type=None, 
                       status=None, from_date=None, to_date=None):
    """البحث في المعاملات"""
    from models_accounting import Transaction
    from sqlalchemy import or_
    
    query = Transaction.query
    
    if search_term:
        query = query.filter(or_(
            Transaction.description.contains(search_term),
            Transaction.reference_number.contains(search_term),
            Transaction.transaction_number.contains(search_term)
        ))
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if status == 'pending':
        query = query.filter(Transaction.is_approved == False)
    elif status == 'approved':
        query = query.filter(Transaction.is_approved == True)
    
    if from_date:
        query = query.filter(Transaction.transaction_date >= from_date)
    
    if to_date:
        query = query.filter(Transaction.transaction_date <= to_date)
    
    return query.order_by(desc(Transaction.transaction_date)).all()


# ════════════════════════════════════════════════════════════════════════════
# تاريخ التحديث: 2024
# آخر تعديل: تنظيم شامل للدوال المساعدة
# ════════════════════════════════════════════════════════════════════════════
