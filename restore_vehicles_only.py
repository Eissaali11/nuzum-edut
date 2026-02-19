"""
استعادة المركبات فقط من ملف الـ Backup
========================================
هذا السكريبت يستعيد المركبات فقط دون التأثير على البيانات الأخرى
"""
import json
import sqlite3
import os

backup_file = r"c:\Users\TWc\Downloads\nuzum_backup_20260215_202113.json"
db_path = 'instance/nuzum_local.db'

if not os.path.exists(backup_file):
    print(f"❌ ملف الـ backup غير موجود: {backup_file}")
    exit(1)

print("=" * 70)
print("استعادة المركبات من ملف الـ Backup")
print("=" * 70)

# قراءة ملف الـ backup
with open(backup_file, 'r', encoding='utf-8') as f:
    backup_data = json.load(f)

vehicles = backup_data['data'].get('vehicles', [])
print(f"\n📦 عدد المركبات في الـ Backup: {len(vehicles)}")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# فحص المركبات الحالية
cursor.execute("SELECT COUNT(*) FROM vehicle")
current_count = cursor.fetchone()[0]
print(f"📊 عدد المركبات الحالية: {current_count}")

print(f"\n⚠️ سيتم:")
print(f"   1. حذف المركبات الحالية ({current_count})")
print(f"   2. إضافة المركبات من الـ Backup ({len(vehicles)})")
print("=" * 70)

response = input("\nهل تريد المتابعة؟ (نعم/لا): ").strip().lower()

if response not in ['نعم', 'yes', 'y']:
    print("تم الإلغاء")
    conn.close()
    exit(0)

try:
    # حذف المركبات الحالية
    print("\n1️⃣ حذف المركبات الحالية...")
    cursor.execute("DELETE FROM vehicle")
    conn.commit()
    print("   ✅ تم الحذف")
    
    # إضافة المركبات من الـ backup
    print("\n2️⃣ إضافة المركبات من الـ Backup...")
    added_count = 0
    errors = []
    
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
            added_count += 1
            if added_count % 10 == 0:
                print(f"   ... تم إضافة {added_count} مركبة")
        except Exception as e:
            errors.append(f"خطأ في مركبة {veh.get('plate_number', '?')}: {str(e)[:50]}")
    
    conn.commit()
    
    print(f"\n✅ تم إضافة {added_count} مركبة بنجاح!")
    
    if errors:
        print(f"\n⚠️ حدثت {len(errors)} أخطاء:")
        for error in errors[:5]:
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... و {len(errors) - 5} خطأ آخر")
    
    # التحقق
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    final_count = cursor.fetchone()[0]
    print(f"\n📊 العدد النهائي للمركبات: {final_count}")
    
    # عرض بعض المركبات
    print(f"\n📋 بعض المركبات المضافة:")
    cursor.execute("SELECT id, plate_number, vehicle_type, status FROM vehicle LIMIT 10")
    for veh_id, plate, vtype, status in cursor.fetchall():
        print(f"   {veh_id}. {plate} - {vtype or 'غير محدد'} ({status})")
    
    print("\n" + "=" * 70)
    print("✅ تم استعادة المركبات بنجاح!")
    print("=" * 70)
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ حدث خطأ: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
