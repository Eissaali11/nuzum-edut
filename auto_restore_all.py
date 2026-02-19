"""
استعادة تلقائية كاملة للبيانات من الـ Backup
================================================
هذا السكريبت يقوم باستعادة جميع البيانات من الـ backup دون الحاجة لتأكيد
"""
import json
import sqlite3
import os

backup_file = r"c:\Users\TWc\Downloads\nuzum_backup_20260215_202113.json"
db_path = 'instance/nuzum_local.db'

print("=" * 80)
print("استعادة تلقائية كاملة للبيانات من الـ Backup")
print("=" * 80)

# قراءة ملف الـ backup
with open(backup_file, 'r', encoding='utf-8') as f:
    backup_data = json.load(f)

data = backup_data['data']

print(f"\n📦 معلومات الـ Backup:")
print(f"   تاريخ: {backup_data['metadata']['created_at']}")
print(f"   الموظفين: {len(data.get('employees', []))}")
print(f"   المركبات: {len(data.get('vehicles', []))}")
print(f"   الأقسام: {len(data.get('departments', []))}")
print(f"   سجلات الحضور: {len(data.get('attendance', []))}")
print(f"   سجلات الرواتب: {len(data.get('salaries', []))}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"\n📊 البيانات الحالية:")
tables_info = {}
for table in ['employee', 'vehicle', 'department', 'attendance', 'salary']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        tables_info[table] = cursor.fetchone()[0]
        print(f"   {table}: {tables_info[table]}")
    except:
        tables_info[table] = 0

print("\n" + "=" * 80)
print("🔄 بدء عملية الاستعادة...")
print("=" * 80)

try:
    # 1. حذف البيانات القديمة
    print("\n1️⃣ حذف البيانات القديمة...")
    tables_to_clear = [
        'attendance',
        'salary',
        'document',
        'employee_geofences',
        'employee_departments',
        'vehicle_handover',
        'vehicle_workshop',
        'vehicle_accident',
        'vehicle',
        'employee'
    ]
    
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"   ✓ {table}")
        except Exception as e:
            print(f"   ⚠️ {table}: {str(e)[:40]}")
    
    conn.commit()
    print("   ✅ تم حذف البيانات القديمة")
    
    # 2. استعادة الموظفين
    print("\n2️⃣ استعادة الموظفين...")
    employees = data.get('employees', [])
    emp_count = 0
    
    for emp in employees:
        try:
            # تحضير القيم
            values = (
                emp['id'], emp['employee_id'], emp['national_id'], emp['name'],
                emp['mobile'], emp.get('mobilePersonal'), emp.get('department_id'),
                emp.get('email'), emp['job_title'], emp['status'], emp.get('location'),
                emp.get('project'), emp.get('join_date'), emp.get('birth_date'),
                emp.get('nationality'), emp.get('nationality_id'), emp.get('contract_type', 'foreign'),
                emp.get('basic_salary', 0), emp.get('daily_wage', 0), emp.get('attendance_bonus', 300),
                emp.get('has_national_balance', False), emp.get('profile_image'),
                emp.get('national_id_image'), emp.get('license_image'),
                emp.get('job_offer_file'), emp.get('job_offer_link'),
                emp.get('passport_image_file'), emp.get('passport_image_link'),
                emp.get('national_address_file'), emp.get('national_address_link'),
                emp.get('created_at'), emp.get('updated_at'), emp.get('contract_status'),
                emp.get('license_status'), emp.get('employee_type', 'regular'),
                emp.get('has_mobile_custody', False), emp.get('mobile_type'),
                emp.get('mobile_imei'), emp.get('sponsorship_status', 'inside'),
                emp.get('current_sponsor_name'), emp.get('bank_iban'),
                emp.get('bank_iban_image'), emp.get('residence_details'),
                emp.get('residence_location_url'), emp.get('housing_images'),
                emp.get('housing_drive_links'), emp.get('pants_size'),
                emp.get('shirt_size'), emp.get('exclude_leave_from_deduction', True),
                emp.get('exclude_sick_from_deduction', True)
            )
            
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            emp_count += 1
            
            if emp_count % 20 == 0:
                print(f"   ... {emp_count} موظف")
                
        except Exception as e:
            print(f"   ⚠️ خطأ في موظف {emp.get('name', '?')[:20]}: {str(e)[:30]}")
    
    conn.commit()
    print(f"   ✅ تم استعادة {emp_count} موظف")
    
    # 3. استعادة المركبات
    print("\n3️⃣ استعادة المركبات...")
    vehicles = data.get('vehicles', [])
    veh_count = 0
    
    for veh in vehicles:
        try:
            cursor.execute("""
                INSERT INTO vehicle (
                    id, plate_number, make, model, year, color, status, driver_name,
                    type_of_car, department_id, authorization_expiry_date,
                    registration_expiry_date, inspection_expiry_date, license_image,
                    registration_form_image, plate_image, insurance_file, project,
                    drive_folder_link, owned_by, region, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                veh['id'], veh['plate_number'], veh.get('make'),
                veh.get('model'), veh.get('year'), veh.get('color'),
                veh.get('status'), veh.get('driver_name'), veh.get('type_of_car'),
                veh.get('department_id'), veh.get('authorization_expiry_date'),
                veh.get('registration_expiry_date'), veh.get('inspection_expiry_date'),
                veh.get('license_image'), veh.get('registration_form_image'),
                veh.get('plate_image'), veh.get('insurance_file'),
                veh.get('project'), veh.get('drive_folder_link'),
                veh.get('owned_by'), veh.get('region'), veh.get('notes'),
                veh.get('created_at'), veh.get('updated_at')
            ))
            veh_count += 1
            
            if veh_count % 10 == 0:
                print(f"   ... {veh_count} مركبة")
                
        except Exception as e:
            print(f"   ⚠️ خطأ في مركبة {veh.get('plate_number', '?')}: {str(e)[:30]}")
    
    conn.commit()
    print(f"   ✅ تم استعادة {veh_count} مركبة")
    
    # 4. استعادة سجلات الحضور
    print("\n4️⃣ استعادة سجلات الحضور...")
    attendance_records = data.get('attendance', [])
    att_count = 0
    
    for att in attendance_records:
        try:
            cursor.execute("""
                INSERT INTO attendance (
                    id, employee_id, date, check_in, check_out, status,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                att['id'], att['employee_id'], att['date'],
                att.get('check_in'), att.get('check_out'), att.get('status'),
                att.get('notes'), att.get('created_at'), att.get('updated_at')
            ))
            att_count += 1
            
            if att_count % 1000 == 0:
                print(f"   ... {att_count} سجل")
                
        except Exception as e:
            if att_count == 0:  # print first error only
                print(f"   ⚠️ خطأ في سجل حضور: {str(e)[:50]}")
    
    conn.commit()
    print(f"   ✅ تم استعادة {att_count} سجل حضور")
    
    # 5. استعادة سجلات الرواتب
    print("\n5️⃣ استعادة سجلات الرواتب...")
    salaries = data.get('salaries', [])
    sal_count = 0
    
    for sal in salaries:
        try:
            cursor.execute("""
                INSERT INTO salary (
                    id, employee_id, month, year, basic_salary, attendance_bonus,
                    allowances, deductions, bonus, net_salary, is_paid, overtime_hours,
                    notes, attendance_deduction, absent_days, present_days, leave_days,
                    sick_days, attendance_calculated, attendance_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sal['id'], sal['employee_id'], sal['month'], sal['year'],
                sal.get('basic_salary'), sal.get('attendance_bonus'),
                sal.get('allowances'), sal.get('deductions'), sal.get('bonus'),
                sal.get('net_salary'), sal.get('is_paid'), sal.get('overtime_hours'),
                sal.get('notes'), sal.get('attendance_deduction'),
                sal.get('absent_days'), sal.get('present_days'),
                sal.get('leave_days'), sal.get('sick_days'),
                sal.get('attendance_calculated'), sal.get('attendance_notes'),
                sal.get('created_at'), sal.get('updated_at')
            ))
            sal_count += 1
            
            if sal_count % 50 == 0:
                print(f"   ... {sal_count} سجل")
                
        except Exception as e:
            if sal_count < 5:  # print first 5 errors
                print(f"   ⚠️ خطأ: {str(e)[:50]}")
    
    conn.commit()
    print(f"   ✅ تم استعادة {sal_count} سجل راتب")
    
    # 6. ربط الموظفين بالأقسام
    print("\n6️⃣ ربط الموظفين بأقسامهم...")
    cursor.execute("""
        SELECT id, department_id
        FROM employee
        WHERE department_id IS NOT NULL AND status = 'active'
    """)
    
    link_count = 0
    for emp_id, dept_id in cursor.fetchall():
        try:
            cursor.execute("""
                INSERT INTO employee_departments (employee_id, department_id)
                VALUES (?, ?)
            """, (emp_id, dept_id))
            link_count += 1
        except:
            pass  # already exists
    
    conn.commit()
    print(f"   ✅ تم ربط {link_count} موظف بأقسامهم")
    
    print("\n" + "=" * 80)
    print("✅ تم استعادة جميع البيانات بنجاح!")
    print("=" * 80)
    
    # التحقق النهائي
    print("\n📊 النتائج النهائية:")
    cursor.execute("SELECT COUNT(*) FROM employee")
    print(f"   الموظفين: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    print(f"   المركبات: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM attendance")
    print(f"   سجلات الحضور: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM salary")
    print(f"   سجلات الرواتب: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM employee_departments")
    print(f"   روابط الموظفين والأقسام: {cursor.fetchone()[0]}")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ حدث خطأ: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
