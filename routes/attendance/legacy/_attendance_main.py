"""Legacy Stub for Attendance Module

This stub provides minimal callables expected by the v1 loader
so that missing legacy sources do not block initialization.
"""

def department_attendance_view(*args, **kwargs):
    # Minimal placeholder: v1 controllers should take precedence.
    return "Legacy Placeholder - please use Modular v1"


def get_department_employees(*args, **kwargs):
    return []


def export_department_data(*args, **kwargs):
    # Return a harmless sentinel; real export handled by v1.
    return None
