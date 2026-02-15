"""Core domain models package"""
from core.domain.models import (
    User,
    UserRole,
    UserPermission,
    Module,
    Permission,
    SystemAudit,
    AuditLog,
    Notification,
    user_accessible_departments,
    vehicle_user_access
)

__all__ = [
    'User',
    'UserRole',
    'UserPermission',
    'Module',
    'Permission',
    'SystemAudit',
    'AuditLog',
    'Notification',
    'user_accessible_departments',
    'vehicle_user_access'
]
