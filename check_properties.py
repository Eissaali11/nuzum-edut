"""
فحص بيانات العقارات المستأجرة في قاعدة البيانات
"""
import sqlite3

db_path = 'instance/nuzum_local.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("فحص بيانات العقارات المستأجرة")
print("=" * 80)

# البحث عن جداول العقارات
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%property%' OR name LIKE '%rental%')")
property_tables = cursor.fetchall()

print("\n📊 جداول العقارات الموجودة في قاعدة البيانات:")
if property_tables:
    for table in property_tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   - {table_name}: {count} سجل")
else:
    print("   ❌ لا توجد جداول للعقارات")

# التحقق من جدول rental_property بالتحديد
print("\n📋 التحقق من جدول rental_property:")
try:
    cursor.execute("SELECT COUNT(*) FROM rental_property")
    count = cursor.fetchone()[0]
    print(f"   عدد العقارات: {count}")
    
    if count > 0:
        # عرض بعض العقارات
        cursor.execute("SELECT id, name, property_type, monthly_rent, status FROM rental_property LIMIT 5")
        properties = cursor.fetchall()
        print(f"\n   📝 أول {len(properties)} عقارات:")
        for prop in properties:
            print(f"      ID: {prop[0]} | {prop[1]} | النوع: {prop[2]} | الإيجار: {prop[3]} | الحالة: {prop[4]}")
    else:
        print("   ⚠️ الجدول موجود ولكن لا توجد بيانات فيه")
        
except Exception as e:
    print(f"   ❌ خطأ: {str(e)}")

# التحقق من backup file
print("\n💾 التحقق من ملف الـ Backup:")
import json
import os

backup_file = r"c:\Users\TWc\Downloads\nuzum_backup_20260215_202113.json"
if os.path.exists(backup_file):
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    data = backup_data.get('data', {})
    
    # البحث عن بيانات عقارات في الـ backup
    property_keys = [k for k in data.keys() if 'property' in k.lower() or 'rental' in k.lower()]
    
    if property_keys:
        print(f"   ✅ تم العثور على بيانات عقارات في الـ backup:")
        for key in property_keys:
            count = len(data[key]) if isinstance(data[key], list) else 0
            print(f"      - {key}: {count} سجل")
    else:
        print("   ℹ️ لا توجد بيانات عقارات في ملف الـ backup")
else:
    print("   ℹ️ ملف الـ backup غير موجود")

conn.close()
print("=" * 80)
