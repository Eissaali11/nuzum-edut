"""
Test script to check departments and active employees using direct SQL
"""
import sqlite3
import os

# Database path
db_path = os.path.join('instance', 'nuzum_local.db')

if not os.path.exists(db_path):
    print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
    
    # Try alternative paths
    alt_paths = ['database/nuzum.db', 'database/nuzum_local.db', 'instance/nuzum.db']
    for path in alt_paths:
        if os.path.exists(path):
            db_path = path
            print(f"✅ تم العثور على قاعدة البيانات: {db_path}")
            break
    else:
        import sys
        sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("فحص الأقسام والموظفين النشطين")
print("=" * 70)
print(f"قاعدة البيانات: {db_path}\n")

# Get all departments
cursor.execute("SELECT id, name FROM department")
departments = cursor.fetchall()

print(f"إجمالي عدد الأقسام: {len(departments)}")

if not departments:
    print("\n❌ لا توجد أقسام في قاعدة البيانات!")
    conn.close()
    import sys
    sys.exit(1)

total_active_employees = 0
departments_with_employees = 0
departments_without_employees = 0

for dept_id, dept_name in departments:
    # Get active employees for this department using employee_departments junction table
    query = """
        SELECT e.id, e.name, e.employee_id, e.status
        FROM employee e
        INNER JOIN employee_departments ed ON e.id = ed.employee_id
        WHERE ed.department_id = ? AND e.status = 'active'
    """
    cursor.execute(query, (dept_id,))
    active_employees = cursor.fetchall()
    employee_count = len(active_employees)
    
    # Get total employees
    cursor.execute("""
        SELECT COUNT(*)
        FROM employee e
        INNER JOIN employee_departments ed ON e.id = ed.employee_id
        WHERE ed.department_id = ?
    """, (dept_id,))
    total_count = cursor.fetchone()[0]
    
    print(f"\n📁 القسم: {dept_name}")
    print(f"   - رقم القسم: {dept_id}")
    print(f"   - عدد الموظفين الكلي: {total_count}")
    print(f"   - عدد الموظفين النشطين: {employee_count}")
    
    if employee_count > 0:
        departments_with_employees += 1
        total_active_employees += employee_count
        print(f"   - أسماء بعض الموظفين النشطين:")
        for i, (emp_id, emp_name, emp_employee_id, emp_status) in enumerate(active_employees[:3], 1):
            print(f"     {i}. {emp_name} (ID: {emp_employee_id}, Status: {emp_status})")
        if len(active_employees) > 3:
            print(f"     ... و {len(active_employees) - 3} موظف آخر")
    else:
        departments_without_employees += 1
        print(f"   ⚠️ لا يوجد موظفين نشطين في هذا القسم")

conn.close()

print("\n" + "=" * 70)
print("📊 الملخص:")
print(f"   - أقسام بها موظفين نشطين: {departments_with_employees}")
print(f"   - أقسام بدون موظفين نشطين: {departments_without_employees}")
print(f"   - إجمالي الموظفين النشطين: {total_active_employees}")

if total_active_employees == 0:
    print("\n❌ المشكلة: لا يوجد موظفين نشطين في أي قسم!")
    print("   الحل: تأكد من:")
    print("   1. إضافة موظفين للأقسام")
    print("   2. تعيين حالة الموظفين إلى 'active'")
    print("   3. ربط الموظفين بالأقسام من خلال جدول employee_departments")
else:
    print("\n✅ يوجد موظفين نشطين جاهزين لتسجيل الحضور")

print("=" * 70)
