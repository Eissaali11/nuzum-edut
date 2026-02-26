"""
Compatibility wrapper for legacy salaries routes.

The implementation moved to:
- routes/salaries_mgmt/v1/salary_routes.py
"""

from flask import Blueprint

try:
    from .v1.salary_routes import salaries_bp  # noqa: F401
except ImportError:
    salaries_bp = Blueprint('salaries', __name__)

__all__ = ['salaries_bp']
