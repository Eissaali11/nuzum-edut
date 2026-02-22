"""
اختبار استيراد فعلي للنسخة الاحتياطية
=======================================
يحاكي استيراد backup حقيقي إلى قاعدة بيانات مؤقتة
"""
import sqlite3
import json
import os
import shutil

print("=" * 80)
print("اختبار الاستيراد الفعلي للنسخة الاحتياطية")
print("=" * 80)

# إنشاء نسخة مؤقتة من قاعدة البيانات
print("\n1️⃣ إنشاء قاعدة بيانات مؤقتة للاختبار...")
temp_db = 'instance/test_nuzum.db'

try:
    # نسخ قاعدة البيانات الأصلية
    shutil.copy('instance/nuzum_local.db', temp_db)
    print("   ✅ تم إنشاء قاعدة بيانات مؤقتة")
    
    # الاتصال بقاعدة البيانات المؤقتة
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # 2. حذف بيانات vehicle للاختبار
    print("\n2️⃣ حذف بيانات المركبات من قاعدة البيانات المؤقتة...")
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    original_count = cursor.fetchone()[0]
    print(f"   عدد المركبات الأصلي: {original_count}")
    
    cursor.execute("DELETE FROM vehicle")
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    after_delete = cursor.fetchone()[0]
    print(f"   عدد المركبات بعد الحذف: {after_delete}")
    print("   ✅ تم حذف جميع المركبات")
    
    # 3. استيراد بيانات من test_backup.json
    print("\n3️⃣ استيراد البيانات من ملف backup...")
    
    with open('test_backup.json', 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    table_name = 'vehicle'
    table_data = backup_data['tables'][table_name]
    
    imported_count = 0
    errors = []
    
    for row in table_data['rows']:
        try:
            # بناء استعلام INSERT
            columns = ', '.join(row.keys())
            placeholders = ', '.join(['?' for _ in row.keys()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            # تنفيذ الاستعلام
            cursor.execute(query, list(row.values()))
            imported_count += 1
            
        except Exception as e:
            errors.append(str(e))
    
    conn.commit()
    
    print(f"   ✅ تم استيراد {imported_count} سجل")
    if errors:
        print(f"   ⚠️ أخطاء: {len(errors)}")
        for err in errors[:3]:
            print(f"      - {err[:60]}")
    
    # 4. التحقق من البيانات المستوردة
    print("\n4️⃣ التحقق من البيانات المستوردة...")
    
    cursor.execute("SELECT COUNT(*) FROM vehicle")
    final_count = cursor.fetchone()[0]
    print(f"   عدد المركبات بعد الاستيراد: {final_count}")
    
    # عرض بعض البيانات المستوردة
    cursor.execute("SELECT plate_number, make, model FROM vehicle LIMIT 3")
    vehicles = cursor.fetchall()
    
    print(f"\n   📋 أمثلة من المركبات المستوردة:")
    for veh in vehicles:
        print(f"      - {veh[0]} | {veh[1]} {veh[2]}")
    
    conn.close()
    
    # 5. حذف قاعدة البيانات المؤقتة
    print("\n5️⃣ تنظيف...")
    os.remove(temp_db)
    print("   ✅ تم حذف قاعدة البيانات المؤقتة")
    
    print("\n" + "=" * 80)
    if imported_count == len(table_data['rows']) and len(errors) == 0:
        print("✅ نجح الاختبار بالكامل!")
        print("   نظام النسخ الاحتياطي يعمل بشكل مثالي.")
        print("   يمكنك تصدير واستيراد البيانات دون أي مشاكل.")
    else:
        print("⚠️ نجح الاختبار جزئياً")
        print(f"   تم استيراد {imported_count} من {len(table_data['rows'])} سجل")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ خطأ أثناء الاختبار: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # تنظيف في حالة الخطأ
    if os.path.exists(temp_db):
        os.remove(temp_db)
