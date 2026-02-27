"""
Compatibility wrapper for profitability-related accounting blueprints.

This module preserves legacy import paths while delegating implementation
into focused route modules.
"""

from routes.accounting.profitability_dashboard_routes import profitability_bp
from routes.accounting.contracts_routes import contracts_bp
from routes.accounting.utility_bills_routes import utility_bp

__all__ = ['profitability_bp', 'contracts_bp', 'utility_bp']
