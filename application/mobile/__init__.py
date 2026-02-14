"""
طبقة التطبيق للجوال — فحوصات، قوائم فحص، وحضور/رواتب.
"""
from .inspection_services import (
    create_periodic_inspection_action,
    create_safety_check_action,
    add_vehicle_checklist_action,
)
from .hr_services import (
    get_attendance_list_data,
    get_attendance_dashboard_data,
    add_attendance_action,
    edit_attendance_action,
    delete_attendance_action,
    get_salaries_list_data,
    get_salary_details_data,
    edit_salary_action,
    share_salary_whatsapp_data,
)

__all__ = [
    "create_periodic_inspection_action",
    "create_safety_check_action",
    "add_vehicle_checklist_action",
    "get_attendance_list_data",
    "get_attendance_dashboard_data",
    "add_attendance_action",
    "edit_attendance_action",
    "delete_attendance_action",
    "get_salaries_list_data",
    "get_salary_details_data",
    "edit_salary_action",
    "share_salary_whatsapp_data",
]
