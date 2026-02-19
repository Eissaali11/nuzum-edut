"""
إصلاح ربط الموظفين بالأقسام
================================
هذا السكريبت يقوم بربط الموظفين بأقسامهم من خلال جدول employee_departments
بناءً على حقل department_id الموجود في جدول employee
"""
import sqlite3
import os

db_path = 'instance/nuzum_local.db'

if not os.path.exists(db_path):
    print("❌ قاعدة البيانات غير موجودة!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("إصلاح ربط الموظفين بالأقسام")
print("=" * 70)

# التحقق من الموظفين الموجودين
cursor.execute("SELECT COUNT(*) FROM employee WHERE status = 'active'")
active_employee_count = cursor.fetchone()[0]

print(f"\nعدد الموظفين النشطين في قاعدة البيانات: {active_employee_count}")

if active_employee_count == 0:
    print("\n❌ لا يوجد موظفين نشطين في قاعدة البيانات!")
    print("   الرجاء إضافة موظفين أولاً من صفحة الموظفين في النظام")
    conn.close()
    exit(1)

# الحصول على الموظفين الذين لديهم department_id لكن غير مربوطين في employee_departments
query = """
    SELECT e.id, e.name, e.employee_id, e.department_id, d.name as dept_name
    FROM employee e
    LEFT JOIN employee_departments ed ON e.id = ed.employee_id
    LEFT JOIN department d ON e.department_id = d.id
    WHERE e.status = 'active' 
      AND e.department_id IS NOT NULL
      AND ed.employee_id IS NULL
"""

cursor.execute(query)
unlinked_employees = cursor.fetchall()

print(f"\nالموظفين غير المربوطين بأقسامهم: {len(unlinked_employees)}")

if len(unlinked_employees) == 0:
    print("\n✅ جميع الموظفين مربوطون بأقسامهم بشكل صحيح!")
    conn.close()
    exit(0)

print("\nالموظفين الذين سيتم ربطهم:")
print("-" * 70)

for emp_id, emp_name, emp_employee_id, dept_id, dept_name in unlinked_employees[:10]:
    print(f"  {emp_name} ({emp_employee_id}) -> {dept_name}")

if len(unlinked_employees) > 10:
    print(f"  ... و {len(unlinked_employees) - 10} موظف آخر")

print("\n" + "=" * 70)
response = input("هل تريد ربط هؤلاء الموظفين بأقسامهم؟ (yes/no): ").strip().lower()

if response not in ['yes', 'y', 'نعم']:
    print("تم الإلغاء")
    conn.close()
    exit(0)

# ربط الموظفين بأقسامهم
linked_count = 0
for emp_id, _, _, dept_id, _ in unlinked_employees:
    try:
        cursor.execute("""
            INSERT INTO employee_departments (employee_id, department_id)
            VALUES (?, ?)
        """, (emp_id, dept_id))
        linked_count += 1
    except sqlite3.IntegrityError:
        # Already exists - skip
        pass

conn.commit()

print(f"\n✅ تم ربط {linked_count} موظف بأقسامهم بنجاح!")

# التحقق من النتائج
print("\n" + "=" * 70)
print("التحقق من النتائج:")
print("=" * 70)

cursor.execute("""
    SELECT d.name, COUNT(e.id) as employee_count
    FROM department d
    LEFT JOIN employee_departments ed ON d.id = ed.department_id
    LEFT JOIN employee e ON ed.employee_id = e.id AND e.status = 'active'
    GROUP BY d.id, d.name
    HAVING employee_count > 0
    ORDER BY employee_count DESC
""")

results = cursor.fetchall()

if results:
    print("\nالأقسام بعد الإصلاح:")
    for dept_name, count in results:
        print(f"  📁 {dept_name}: {count} موظف نشط")
    
    print("\n✅ يمكنك الآن استخدام صفحة تسجيل الحضور الجماعي!")
else:
    print("\n⚠️ لم يتم العثور على أقسام بموظفين نشطين")
    print("   تأكد من أن الموظفين لديهم department_id صحيح")

conn.close()

print("=" * 70)
print("تم الإصلاح بنجاح! 🎉")
print("=" * 70)
