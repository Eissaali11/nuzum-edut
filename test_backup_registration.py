from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'

from routes.database_backup import database_backup_bp
print(f"Importing blueprint: {database_backup_bp.name}")

app.register_blueprint(database_backup_bp, url_prefix='/backup')
print(f"Registered database_backup_bp")

# Check registered routes
backup_routes = [r for r in app.url_map.iter_rules() if 'backup' in str(r)]
print(f"\nFound {len(backup_routes)} backup routes:")
for route in backup_routes:
    print(f"  {route.rule} -> {route.endpoint}")

if not backup_routes:
    print("ERROR: No backup routes registered!")
    print("\nAll routes:")
    for r in app.url_map.iter_rules():
        print(f"  {r.rule} -> {r.endpoint}")
