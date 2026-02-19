try:
    from routes.database_backup import database_backup_bp
    print(f"SUCCESS: Blueprint imported")
    print(f"Blueprint name: {database_backup_bp.name}")
    print(f"Blueprint has {len(list(database_backup_bp.deferred_functions))} deferred routes")
except Exception as e:
    print(f"IMPORT FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
