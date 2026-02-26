"""Adapter to register export routes for attendance v1.

Delegates to legacy export handlers (Excel/PDF) for incremental migration.
"""

def register_export_routes(attendance_bp):
    import importlib.util
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("_attendance_main", str(parent_dir / "legacy" / "_attendance_main.py"))
    legacy = importlib.util.module_from_spec(spec)
    sys.modules['_attendance_main'] = legacy
    spec.loader.exec_module(legacy)

    attendance_bp.add_url_rule('/export-excel-department', 'export_excel_department', legacy.export_excel_department, methods=['GET'])
    attendance_bp.add_url_rule('/department/export-data', 'export_department_data', legacy.export_department_data, methods=['GET'])
    attendance_bp.add_url_rule('/department/export-period', 'export_department_period', legacy.export_department_period, methods=['GET'])

    return None
