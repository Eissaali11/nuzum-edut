# Check all database files in instance folder
import sqlite3
import os

instance_dir = 'instance'
if os.path.exists(instance_dir):
    db_files = [f for f in os.listdir(instance_dir) if f.endswith('.db')]
    print(f"Found {len(db_files)} database files:\n")
    
    for db_name in db_files:
        db_path = os.path.join(instance_dir, db_name)
        size_kb = os.path.getsize(db_path) / 1024
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            
            # Count rows in key tables
            has_data = False
            row_counts = {}
            for table in ['department', 'employee', 'attendance']:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    row_counts[table] = count
                    if count > 0:
                        has_data = True
            
            conn.close()
            
            indicator = "[DATA]" if has_data else "[EMPTY]"
            print(f"{indicator} {db_name:25} | {size_kb:8.1f} KB | {len(tables):3} tables")
            if row_counts:
                for table, count in row_counts.items():
                    print(f"         - {table}: {count} rows")
        except Exception as e:
            print(f"[ERROR] {db_name:25} | {size_kb:8.1f} KB | {str(e)[:40]}")
    
    print("\n" + "="*70)
    print("Recommendation: Use the database with data for testing Phase 2")
else:
    print("instance folder not found")
