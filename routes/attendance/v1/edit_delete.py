"""Adapter to register CRUD/edit/delete routes for attendance v1.

Delegates to legacy `routes.legacy._attendance_main` handlers for safe
migration of edit/delete endpoints.
"""

def register_crud_routes(attendance_bp):
    import importlib.util
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("_attendance_main", str(parent_dir / "legacy" / "_attendance_main.py"))
    legacy = importlib.util.module_from_spec(spec)
    sys.modules['_attendance_main'] = legacy
    spec.loader.exec_module(legacy)

    attendance_bp.add_url_rule('/delete/<int:id>/confirm', 'confirm_delete_attendance', legacy.confirm_delete_attendance, methods=['GET'])
    attendance_bp.add_url_rule('/delete/<int:id>', 'delete_attendance', legacy.delete_attendance, methods=['POST'])
    attendance_bp.add_url_rule('/bulk_delete', 'bulk_delete_attendance', legacy.bulk_delete_attendance, methods=['POST'])
    attendance_bp.add_url_rule('/edit/<int:id>', 'edit_attendance_page', legacy.edit_attendance_page, methods=['GET'])
    attendance_bp.add_url_rule('/edit/<int:id>', 'update_attendance_page', legacy.update_attendance_page, methods=['POST'])

    return None
