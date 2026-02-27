"""
════════════════════════════════════════════════════════════════════════════
📊 نظام المحاسبة المتكامل - Integrated Accounting System
════════════════════════════════════════════════════════════════════════════

البلوبرينت الموحد للمحاسبة يجمع كل الوحدات المتخصصة

يتضمن:
✓ لوحة التحكم والإحصائيات
✓ إدارة الحسابات وشجرة الحسابات
✓ القيود المحاسبية والمعاملات
✓ مراكز التكلفة والميزانيات

════════════════════════════════════════════════════════════════════════════
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from .accounting_dashboard_routes import dashboard_bp
from .accounting_accounts_routes import accounts_bp
from .accounting_transactions_routes import transactions_bp
from .accounting_charts_routes import charts_bp
from .accounting_costcenters_routes import costcenters_bp
from .finance_bridge_routes import finance_bridge_bp

# ────────────────────────────────────────────────────────────────────────────
# 🔧 البلوبرينت الرئيسي (يعيد توجيه إلى dashboard)
# ────────────────────────────────────────────────────────────────────────────

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')


@accounting_bp.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('profitability.dashboard'))

# تسجيل جميع البلوبرينتات الفرعية
def register_accounting_blueprints(app):
    """تسجيل جميع بلوبرينتات المحاسبة في التطبيق"""
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(costcenters_bp)
    app.register_blueprint(finance_bridge_bp)

__all__ = [
    'accounting_bp',
    'register_accounting_blueprints',
    'dashboard_bp',
    'accounts_bp',
    'transactions_bp',
    'charts_bp',
    'costcenters_bp',
    'finance_bridge_bp',
]
