"""
════════════════════════════════════════════════════════════════════════════
📊 لوحة تحكم المحاسبة - Dashboard Routes
════════════════════════════════════════════════════════════════════════════

المسؤولية: عرض الإحصائيات المالية والبيانات الرئيسية للمحاسبة
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from core.extensions import db
from models_accounting import FiscalYear
from utils.helpers import log_activity

from .accounting_helpers import (
    check_accounting_access,
    calculate_monthly_statistics,
    get_recent_transactions,
    get_pending_transactions_count,
    get_top_cost_centers
)

# ────────────────────────────────────────────────────────────────────────────
# 🔧 إنشاء البلوبرينت
# ────────────────────────────────────────────────────────────────────────────

dashboard_bp = Blueprint(
    'accounting_dashboard',
    __name__,
    url_prefix='/accounting'
)


# ════════════════════════════════════════════════════════════════════════════
# 📊 لوحة التحكم والإحصائيات
# ════════════════════════════════════════════════════════════════════════════

@dashboard_bp.route('/')
@login_required
def dashboard():
    """
    لوحة تحكم المحاسبة الرئيسية
    
    تعرض:
    ✓ الإحصائيات المالية الرئيسية
    ✓ النسب المالية المهمة
    ✓ أحدث المعاملات
    ✓ مراكز التكلفة الأكثر إنفاقاً
    ✓ الرسوم البيانية التوضيحية
    """
    
    # ── التحقق من الصلاحيات ──────────────────────────────────────────────
    if not check_accounting_access(current_user):
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        # ── التحقق من السنة المالية النشطة ──────────────────────────────
        active_fiscal_year = FiscalYear.query.filter_by(is_active=True).first()
        if not active_fiscal_year:
            flash('لا توجد سنة مالية نشطة. يرجى إنشاء سنة مالية أولاً.', 'warning')
            return redirect(url_for('accounting.fiscal_years'))
        
        # ── حساب الإحصائيات المالية ──────────────────────────────────────
        stats = calculate_monthly_statistics(active_fiscal_year.id)
        
        if not stats:
            raise Exception('خطأ في حساب الإحصائيات')
        
        # ── بيانات المعاملات ──────────────────────────────────────────────
        recent_transactions = get_recent_transactions(limit=10)
        pending_count = get_pending_transactions_count(active_fiscal_year.id)
        top_cost_centers = get_top_cost_centers(limit=5, 
                                                from_date=stats['date_range']['start'],
                                                to_date=stats['date_range']['end'])
        
        # ── عرض النتائج ───────────────────────────────────────────────────
        return render_template(
            'accounting/dashboard.html',
            # الإحصائيات الأساسية
            total_assets=stats['assets'],
            total_liabilities=stats['liabilities'],
            total_equity=stats['equity'],
            net_profit=stats['net_profit'],
            # النسب المالية
            current_ratio=stats['ratios']['current_ratio'],
            debt_to_equity=stats['ratios']['debt_to_equity'],
            roa=stats['ratios']['roa'],
            roe=stats['ratios']['roe'],
            # البيانات الإضافية
            recent_transactions=recent_transactions,
            pending_transactions=pending_count,
            top_cost_centers=top_cost_centers,
            active_fiscal_year=active_fiscal_year
        )
    
    except Exception as e:
        flash(f'خطأ في تحميل لوحة التحكم: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))
