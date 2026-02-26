"""Adapter to register recording/action routes for attendance v1.

Delegates to legacy `routes.legacy._attendance_main` handlers for a
safe, incremental migration of action endpoints (record, bulk-record).
"""

def register_recording_routes(attendance_bp):
    import importlib.util
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("_attendance_main", str(parent_dir / "legacy" / "_attendance_main.py"))
    legacy = importlib.util.module_from_spec(spec)
    sys.modules['_attendance_main'] = legacy
    spec.loader.exec_module(legacy)

    # Wire action routes
    attendance_bp.add_url_rule('/record', 'record', legacy.record, methods=['GET', 'POST'])
    attendance_bp.add_url_rule('/bulk-record', 'bulk_record', legacy.bulk_record, methods=['GET', 'POST'])

    return None
