import sqlite3
conn = sqlite3.connect('instance/nuzum_local.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print(f"عدد الجداول الموجودة: {len(tables)}\n")
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
    count = cursor.fetchone()[0]
    print(f"{t[0]}: {count} سجل")
conn.close()
