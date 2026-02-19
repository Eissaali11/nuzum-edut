"""
تحليل مفصل لبيانات العقارات
"""
import sqlite3
import json
import os

db_path = 'instance/nuzum_local.db'
backup_file = r"c:\Users\TWc\Downloads\nuzum_backup_20260215_202113.json"

print("=" * 80)
print("تحليل مفصل لبيانات العقارات المستأجرة")
print("=" * 80)

# 1. حالة قاعدة البيانات الحالية
print("\n1️⃣ حالة قاعدة البيانات الحالية:")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# جدول rental_properties
cursor.execute("SELECT COUNT(*) FROM rental_properties")
properties_count = cursor.fetchone()[0]
print(f"   📊 rental_properties: {properties_count} عقار")

# جداول مرتبطة
cursor.execute("SELECT COUNT(*) FROM property_images")
images_count = cursor.fetchone()[0]
print(f"   🖼️  property_images: {images_count} صورة")

cursor.execute("SELECT COUNT(*) FROM property_payments")
payments_count = cursor.fetchone()[0]
print(f"   💰 property_payments: {payments_count} دفعة")

cursor.execute("SELECT COUNT(*) FROM property_furnishings")
furnishings_count = cursor.fetchone()[0]
print(f"   🛋️  property_furnishings: {furnishings_count} عنصر أثاث")

cursor.execute("SELECT COUNT(*) FROM property_employees")
residents_count = cursor.fetchone()[0]
print(f"   👥 property_employees: {residents_count} ساكن")

conn.close()

# 2. محتوى ملف الـ Backup
print("\n2️⃣ محتوى ملف الـ Backup الأصلي:")
if os.path.exists(backup_file):
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    data = backup_data.get('data', {})
    
    print(f"   📅 تاريخ الـ Backup: {backup_data['metadata']['created_at']}")
    print(f"\n   📦 محتوى الـ Backup:")
    
    # عرض جميع الجداول
    for key in sorted(data.keys()):
        count = len(data[key]) if isinstance(data[key], list) else 'N/A'
        # تمييز جداول العقارات
        if 'property' in key.lower() or 'rental_properties' in key:
            print(f"      🏠 {key}: {count} سجل")
        else:
            # عرض فقط الجداول غير الفارغة
            if count > 0:
                print(f"      {key}: {count}")
    
    # التحقق من محتوى rental_properties
    if 'rental_properties' in data:
        rental_props = data['rental_properties']
        print(f"\n   🔍 تفاصيل rental_properties في الـ Backup:")
        print(f"      - العدد: {len(rental_props)}")
        
        if len(rental_props) > 0:
            print(f"      - أول عقار:")
            first = rental_props[0]
            print(f"         ID: {first.get('id')}")
            print(f"         المدينة: {first.get('city', 'N/A')}")
            print(f"         المالك: {first.get('owner_name', 'N/A')}")
        else:
            print(f"      ❌ لا توجد عقارات في ملف الـ Backup!")
else:
    print("   ❌ ملف الـ Backup غير موجود")

print("\n" + "=" * 80)
print("💡 الخلاصة:")
print("=" * 80)

if properties_count == 0:
    print("❌ لا توجد عقارات في قاعدة البيانات الحالية")
    
    if os.path.exists(backup_file):
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        data = backup_data.get('data', {})
        rental_props = data.get('rental_properties', [])
        
        if len(rental_props) == 0:
            print("❌ لا توجد عقارات في ملف الـ Backup الأصلي أيضاً")
            print("")
            print("🔍 التفسير:")
            print("   - قاعدة البيانات الأصلية (في 15 فبراير 2026) لم تكن تحتوي على عقارات")
            print("   - أو أن نظام العقارات تم إضافته بعد تاريخ الـ Backup")
            print("")
            print("✅ الحل:")
            print("   1. ابدأ بإضافة عقارات جديدة من واجهة النظام:")
            print("      http://192.168.8.115:5000/properties/dashboard")
            print("   2. أو قم بعمل backup جديد إذا كانت العقارات موجودة في مكان آخر")
        else:
            print("✅ توجد عقارات في الـ Backup - يمكن استعادتها")
            print(f"   عدد العقارات: {len(rental_props)}")
    else:
        print("⚠️ لم يتم العثور على ملف backup للتحقق منه")
else:
    print(f"✅ توجد {properties_count} عقار في قاعدة البيانات")

print("=" * 80)
