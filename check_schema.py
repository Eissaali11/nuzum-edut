"""
فحص schema الجداول في قاعدة البيانات
"""
import sqlite3

conn = sqlite3.connect('instance/nuzm_local.db')
cursor = conn.cursor()

print("=" * 80)
print("فحص schema الجداول")
print("=" *80)

# Vehicle table
print("\n📊 جدول vehicle:")
cursor.execute("PRAGMA table_info(vehicle)")
columns = cursor.fetchall()
if columns:
    for row in columns:
        print(f"   {row[1]} ({row[2]})")
else:
    print("   (جدول فارغ أو غير موجود)")

# Salary table  
print("\n📊 جدول salary:")
cursor.execute("PRAGMA table_info(salary)")
columns = cursor.fetchall()
if columns:
    for row in columns:
        print(f"   {row[1]} ({row[2]})")
else:
    print("   (جدول فارغ أو غير موجود)")

# Employee table
print("\n📊 جدول employee:")
cursor.execute("PRAGMA table_info(employee)")
columns = cursor.fetchall()
if columns:
    for row in columns[:15]:  # First 15 columns only
        print(f"   {row[1]} ({row[2]})")
    if len(columns) > 15:
        print(f"   ... و {len(columns) - 15} عمود آخر")
else:
    print("   (جدول فارغ أو غير موجود)")

conn.close()
print("=" * 80)
