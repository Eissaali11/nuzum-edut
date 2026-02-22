"""
فحص سريع لعدد البيانات في قاعدة البيانات
"""
import sqlite3

conn = sqlite3.connect('instance/nuzum_local.db')
cursor = conn.cursor()

print("=" * 70)
print("فحص البيانات الحالية في قاعدة البيانات")
print("=" * 70)

tables = [
    ('employee', 'الموظفين'),
    ('vehicle', 'المركبات'),
    ('department', 'الأقسام'),
    ('salary', 'سجلات الرواتب'),
    ('attendance', 'سجلات الحضور'),
    ('employee_departments', 'روابط الموظفين والأقسام')
]

for table, name in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{name}: {count}")
    except Exception as e:
        print(f"{name}: خطأ - {e}")

print("\n" + "=" * 70)
print("فحص الموظفين النشطين حسب الأقسام")
print("=" * 70)

cursor.execute("""
    SELECT d.name, COUNT(e.id) as count
    FROM department d
    LEFT JOIN employee_departments ed ON d.id = ed.department_id
    LEFT JOIN employee e ON ed.employee_id = e.id AND e.status = 'active'
    GROUP BY d.id, d.name
    ORDER BY count DESC
""")

for dept_name, count in cursor.fetchall():
    print(f"{dept_name}: {count} موظف نشط")

conn.close()
print("=" * 70)
