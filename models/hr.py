"""
HR domain model exports.

This module provides a stable domain-specific entrypoint without changing
actual model declarations or database schema.
"""

from core.domain.models import User
from modules.employees.domain.models import Department, Employee

# NOTE:
# Contract is currently represented as fields on Employee and related business
# logic, not as a dedicated db.Model table.
Contract = None

__all__ = [
    "Employee",
    "Department",
    "Contract",
    "User",
]
