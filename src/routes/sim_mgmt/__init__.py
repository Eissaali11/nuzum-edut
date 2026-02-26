"""
إدارة بطاقات SIM - Blueprint مركزي
يجمع كل مسارات إدارة بطاقات SIM والهواتف (13 مسار)
"""

from flask import Blueprint
from src.routes.sim_mgmt.sim_helpers import (
    get_sim_card_by_phone_number,
    get_sim_cards_for_employee,
    get_available_sim_cards,
    get_sim_cards_statistics,
    validate_phone_number,
    get_device_assignments_for_sim,
    get_imported_phone_numbers,
    get_sim_assignment_history,
    check_sim_duplicate,
    get_sim_cards_needing_renewal
)


def register_sim_routes(app):
    """تسجيل مسارات إدارة بطاقات SIM"""
    # استيراد المسارات الأصلية كبديل مؤقت
    try:
        from src.routes.sim_management import sim_management_bp
        app.register_blueprint(sim_management_bp)
    except ImportError:
        pass


__all__ = [
    'register_sim_routes',
    'get_sim_card_by_phone_number',
    'get_sim_cards_for_employee',
    'get_available_sim_cards',
    'get_sim_cards_statistics',
    'validate_phone_number',
    'get_device_assignments_for_sim',
    'get_imported_phone_numbers',
    'get_sim_assignment_history',
    'check_sim_duplicate',
    'get_sim_cards_needing_renewal'
]
