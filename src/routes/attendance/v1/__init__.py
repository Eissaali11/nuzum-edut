"""Attendance v1 scaffold package.

This package provides a thin compatibility layer for the new v1 scaffolding
and re-uses the existing `routes.attendance.views.register_views_routes` to
avoid duplicating logic during the initial refactor steps.
"""

from .attendance_views import register_views_routes

__all__ = ["register_views_routes"]
