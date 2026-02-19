"""
استعادة البيانات من ملف الـ Backup JSON
==========================================
هذا السكريبت يقوم باستعادة البيانات من ملف backup JSON إلى قاعدة البيانات
"""
import json
import sqlite3
import os
from datetime import datetime

# مسار ملف الـ backup
backup_file = r"c:\Users\TWc\Downloads\nuzum_backup_20260215_202113.json"
db_path = 'instance/nuzum_local.db'

if not os.path.exists(backup_file):
    print(f"❌ ملف الـ backup غير موجود: {backup_file}")
    exit(1)

if not os.path.exists(db_path):
    print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
    exit(1)

print("=" * 70)
print("استعادة البيانات من ملف الـ Backup")
print("=" * 70)

# قراءة ملف الـ backup
with open(backup_file, 'r', encoding='utf-8') as f:
    backup_data = json.load(f)

print(f"\n📦 معلومات الـ Backup:")
print(f"   - تاريخ الإنشاء: {backup_data['metadata']['created_at']}")
print(f"   - الإصدار: {backup_data['metadata']['version']}")
print(f"   - عدد الجداول: {backup_data['metadata']['total_tables']}")

data = backup_data['data']

print(f"\n📊 إحصائيات البيانات:")
print(f"   - الموظفين: {len(data.get('employees', []))}")
print(f"   - المركبات: {len(data.get('vehicles', []))}")
print(f"   - الأقسام: {len(data.get('departments', []))}")
print(f"   - المستخدمين: {len(data.get('users', []))}")
print(f"   - الرواتب: {len(data.get('salaries', []))}")
print(f"   - الحضور: {len(data.get('attendance', []))}")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# فحص البيانات الحالية
print(f"\n📋 البيانات الحالية في قاعدة البيانات:")
tables_to_check = {
    'employee': 'الموظفين',
    'vehicle': 'المركبات',
    'department': 'الأقسام',
    'users': 'المستخدمين',
    'salary': 'الرواتب',
    'attendance': 'الحضور'
}

current_counts = {}
for table, name in tables_to_check.items():
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        current_counts[table] = count
        print(f"   - {name}: {count}")
    except:
        current_counts[table] = 0
        print(f"   - {name}: 0 (جدول غير موجود)")

print("\n" + "=" * 70)
print("⚠️ تحذير: استعادة البيانات ستقوم بـ:")
print("   1. حذف جميع البيانات الحالية")
print("   2. استبدالها ببيانات الـ Backup من 15 فبراير 2026")
print("   3. أي بيانات أضيفت بعد 15 فبراير ستضيع")
print("=" * 70)

response = input("\nهل تريد المتابعة؟ اكتب 'نعم' للتأكيد: ").strip()

if response != 'نعم':
    print("تم الإلغاء")
    conn.close()
    exit(0)

print("\n🔄 جاري الاستعادة...")

try:
    # حذف البيانات الحالية (باستثناء الجداول الأساسية)
    tables_to_clear = [
        'attendance',
        'salary',
        'document',
        'employee_geofences',
        'employee_departments',
        'employee',
        'vehicle_handover',
        'vehicle_workshop',
        'vehicle_accident',
        'vehicle',
        'sim_card',
        'mobile_device'
    ]
    
    print("\n1️⃣ حذف البيانات الحالية...")
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"   ✓ تم حذف بيانات {table}")
        except Exception as e:
            print(f"   ⚠️ خطأ في حذف {table}: {e}")
    
    conn.commit()
    print("   ✅ تم حذف البيانات القديمة")
    
    # استعادة الأقسام أولاً
    print("\n2️⃣ استعادة الأقسام...")
    departments = data.get('departments', [])
    dept_count = 0
    for dept in departments:
        try:
            cursor.execute("""
                INSERT INTO department (id, name, description, manager_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                dept['id'],
                dept['name'],
                dept.get('description'),
                dept.get('manager_id'),
                dept.get('created_at'),
                dept.get('updated_at')
            ))
            dept_count += 1
        except Exception as e:
            print(f"   ⚠️ خطأ في إضافة قسم {dept['name']}: {e}")
    
    print(f"   ✅ تم استعادة {dept_count} قسم")
    
    # استعادة الموظفين
    print("\n3️⃣ استعادة الموظفين...")
    employees = data.get('employees', [])
    emp_count = 0
    for emp in employees:
        try:
            cursor.execute("""
                INSERT INTO employee (
                    id, employee_id, national_id, name, mobile, mobilePersonal,
                    department_id, email, job_title, status, location, project,
                    join_date, birth_date, nationality, nationality_id, contract_type,
                    basic_salary, daily_wage, attendance_bonus, has_national_balance,
                    profile_image, national_id_image, license_image, job_offer_file,
                    job_offer_link, passport_image_file, passport_image_link,
                    national_address_file, national_address_link, created_at, updated_at,
                    contract_status, license_status, employee_type, has_mobile_custody,
                    mobile_type, mobile_imei, sponsorship_status, current_sponsor_name,
                    bank_iban, bank_iban_image, residence_details, residence_location_url,
                    housing_images, housing_drive_links, pants_size, shirt_size,
                    exclude_leave_from_deduction, exclude_sick_from_deduction
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                emp['id'], emp['employee_id'], emp['national_id'], emp['name'],
                emp['mobile'], emp.get('mobilePersonal'), emp.get('department_id'),
                emp.get('email'), emp['job_title'], emp['status'], emp.get('location'),
                emp.get('project'), emp.get('join_date'), emp.get('birth_date'),
                emp.get('nationality'), emp.get('nationality_id'), emp.get('contract_type'),
                emp.get('basic_salary'), emp.get('daily_wage'), emp.get('attendance_bonus'),
                emp.get('has_national_balance'), emp.get('profile_image'),
                emp.get('national_id_image'), emp.get('license_image'),
                emp.get('job_offer_file'), emp.get('job_offer_link'),
                emp.get('passport_image_file'), emp.get('passport_image_link'),
                emp.get('national_address_file'), emp.get('national_address_link'),
                emp.get('created_at'), emp.get('updated_at'), emp.get('contract_status'),
                emp.get('license_status'), emp.get('employee_type'),
                emp.get('has_mobile_custody'), emp.get('mobile_type'),
                emp.get('mobile_imei'), emp.get('sponsorship_status'),
                emp.get('current_sponsor_name'), emp.get('bank_iban'),
                emp.get('bank_iban_image'), emp.get('residence_details'),
                emp.get('residence_location_url'), emp.get('housing_images'),
                emp.get('housing_drive_links'), emp.get('pants_size'),
                emp.get('shirt_size'), emp.get('exclude_leave_from_deduction'),
                emp.get('exclude_sick_from_deduction')
            ))
            emp_count += 1
        except Exception as e:
            print(f"   ⚠️ خطأ في إضافة موظف {emp.get('name', 'غير معروف')}: {e}")
    
    print(f"   ✅ تم استعادة {emp_count} موظف")
    
    # استعادة المركبات
    print("\n4️⃣ استعادة المركبات...")
    vehicles = data.get('vehicles', [])
    veh_count = 0
    for veh in vehicles:
        try:
            cursor.execute("""
                INSERT INTO vehicle (
                    id, plate_number, vehicle_type, model, year, chassis_number,
                    color, status, last_maintenance_date, next_maintenance_date,
                    insurance_expiry, registration_expiry, notes, current_driver_id,
                    ownership_type, purchase_date, purchase_price, fuel_type,
                    seating_capacity, department, location, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                veh['id'], veh['plate_number'], veh.get('vehicle_type'),
                veh.get('model'), veh.get('year'), veh.get('chassis_number'),
                veh.get('color'), veh.get('status'), veh.get('last_maintenance_date'),
                veh.get('next_maintenance_date'), veh.get('insurance_expiry'),
                veh.get('registration_expiry'), veh.get('notes'),
                veh.get('current_driver_id'), veh.get('ownership_type'),
                veh.get('purchase_date'), veh.get('purchase_price'),
                veh.get('fuel_type'), veh.get('seating_capacity'),
                veh.get('department'), veh.get('location'),
                veh.get('created_at'), veh.get('updated_at')
            ))
            veh_count += 1
        except Exception as e:
            print(f"   ⚠️ خطأ في إضافة مركبة {veh.get('plate_number', 'غير معروف')}: {e}")
    
    print(f"   ✅ تم استعادة {veh_count} مركبة")
    
    # استعادة الرواتب
    print("\n5️⃣ استعادة سجلات الرواتب...")
    salaries = data.get('salaries', [])
    sal_count = 0
    for sal in salaries:
        try:
            cursor.execute("""
                INSERT INTO salary (
                    id, employee_id, month, year, basic_salary, allowances,
                    deductions, net_salary, paid, payment_date, notes,
                    created_at, updated_at, days_worked, daily_wage,
                    attendance_bonus, attendance_days, late_deduction,
                    absent_deduction, leave_deduction, sick_deduction,
                    advance_deduction, loan_deduction, other_deduction,
                    total_earned, is_final
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sal['id'], sal['employee_id'], sal['month'], sal['year'],
                sal.get('basic_salary'), sal.get('allowances'),
                sal.get('deductions'), sal.get('net_salary'),
                sal.get('paid'), sal.get('payment_date'), sal.get('notes'),
                sal.get('created_at'), sal.get('updated_at'),
                sal.get('days_worked'), sal.get('daily_wage'),
                sal.get('attendance_bonus'), sal.get('attendance_days'),
                sal.get('late_deduction'), sal.get('absent_deduction'),
                sal.get('leave_deduction'), sal.get('sick_deduction'),
                sal.get('advance_deduction'), sal.get('loan_deduction'),
                sal.get('other_deduction'), sal.get('total_earned'),
                sal.get('is_final')
            ))
            sal_count += 1
        except Exception as e:
            print(f"   ⚠️ خطأ في إضافة راتب: {e}")
    
    print(f"   ✅ تم استعادة {sal_count} سجل راتب")
    
    conn.commit()
    
    print("\n" + "=" * 70)
    print("✅ تم استعادة البيانات بنجاح!")
    print("=" * 70)
    
    print("\n📊 النتائج النهائية:")
    print(f"   - الأقسام: {dept_count}")
    print(f"   - الموظفين: {emp_count}")
    print(f"   - المركبات: {veh_count}")
    print(f"   - الرواتب: {sal_count}")
    
    print("\n⚠️ خطوة مهمة:")
    print("   يجب الآن ربط الموظفين بأقسامهم!")
    print("   شغل السكريبت التالي:")
    print("   .\\venv\\Scripts\\python.exe fix_department_links.py")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ حدث خطأ: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

print("\n" + "=" * 70)
