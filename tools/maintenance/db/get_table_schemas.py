"""
احصل على CREATE TABLE statements لجداول البيانات
"""
import sqlite3

conn = sqlite3.connect('instance/nuzum_local.db')
cursor = conn.cursor()

print("=" * 80)
print("جداول البيانات - CREATE TABLE statements")
print("=" * 80)

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('vehicle', 'salary', 'employee', 'Vehicle', 'Salary', 'Employee')")
tables = cursor.fetchall()

if not tables:
    print("\n❌ لم يتم العثور على الجداول بهذه الأسماء")
    print("\nالبحث عن جداول مشابهة...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%vehicle%' OR name LIKE '%salary%' OR name LIKE '%employee%')")
    similar = cursor.fetchall()
    if similar:
        print("جداول مشابهة:")
        for t in similar:
            print(f"   - {t[0]}")
else:
    for table in tables:
        table_name = table[0]
        print(f"\n📊 جدول {table_name}:")
        print("-" * 80)
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        schema = cursor.fetchone()
        if schema:
            print(schema[0])
        else:
            print("   (لم يتم العثور على schema)")

conn.close()
print("\n" + "=" * 80)
