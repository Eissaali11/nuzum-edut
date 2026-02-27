"""
طرق إضافية للنظام المحاسبي - Wrapper متوافق بعد التفكيك.
"""

from flask import Blueprint

from .financial_reports_routes import register_financial_reports_routes
from .payroll_routes import register_payroll_routes
from .vehicle_expense_routes import register_vehicle_expense_routes


accounting_ext_bp = Blueprint('accounting_ext', __name__, url_prefix='/accounting')


register_payroll_routes(accounting_ext_bp)
register_vehicle_expense_routes(accounting_ext_bp)
register_financial_reports_routes(accounting_ext_bp)
