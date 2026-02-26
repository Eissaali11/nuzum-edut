"""Salaries routes v1 aggregator (atomic decomposed modules)."""

from .salary_base import salaries_bp

from . import salary_core  # noqa: F401
from . import salary_ops  # noqa: F401
from . import salary_io  # noqa: F401
from . import salary_approval  # noqa: F401

__all__ = ['salaries_bp']
