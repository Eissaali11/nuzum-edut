# Check database tables
import sqlite3
import os

db_path = 'instance/nuzm_dev.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Database: {db_path}")
    print(f"Total tables: {len(tables)}")
    print(f"\nChecking required tables:")
    print(f"  - department: {'YES' if 'department' in tables else 'NO'}")
    print(f"  - employee: {'YES' if 'employee' in tables else 'NO'}")
    print(f"  - attendance: {'YES' if 'attendance' in tables else 'NO'}")
    print(f"\nAll tables: {', '.join(tables[:20])}")
    conn.close()
else:
    print(f"Database not found: {db_path}")
