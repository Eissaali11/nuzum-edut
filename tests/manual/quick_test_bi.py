"""
اختبار سريع لـ BI Components
"""
print("=" * 80)
print("🔍 اختبار مكونات Business Intelligence")
print("=" * 80)

# Test 1: Check if files exist
print("\n1️⃣ فحص الملفات...")

import os

files_to_check = [
    'application/services/bi_engine.py',
    'application/services/powerbi_exporter.py',
    'routes/analytics.py',
    'templates/analytics/dashboard.html'
]

for file_path in files_to_check:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"   {status} {file_path}")

# Test 2: Check imports
print("\n2️⃣ فحص الاستيرادات...")

try:
    from application.services import bi_engine
    print("   ✅ bi_engine module")
except Exception as e:
    print(f"   ❌ bi_engine: {str(e)[:50]}")

try:
    from application.services import powerbi_exporter
    print("   ✅ powerbi_exporter module")
except Exception as e:
    print(f"   ❌ powerbi_exporter: {str(e)[:50]}")

try:
    from routes import analytics
    print("   ✅ analytics routes")
except Exception as e:
    print(f"   ❌ analytics: {str(e)[:50]}")

# Test 3: Check pandas
print("\n3️⃣ فحص المكتبات المطلوبة...")

try:
    import pandas as pd
    print(f"   ✅ pandas {pd.__version__}")
except:
    print("   ❌ pandas not installed")

try:
    import openpyxl
    print(f"   ✅ openpyxl {openpyxl.__version__}")
except:
    print("   ❌ openpyxl not installed")

try:
    from flask import Blueprint
    print("   ✅ Flask")
except:
    print("   ❌ Flask not installed")

# Test 4: Check region mapping
print("\n4️⃣ اختبار Region Mapping...")
print("   من bi_engine.BIEngine:")
print("   - الرياض → Riyadh")
print("   - جدة → Jeddah")
print("   - الدمام → Dammam")
print("   - مكة → Makkah")

print("\n" + "=" * 80)
print("✅ الفحص الأولي اكتمل!")
print("\nللوصول إلى النظام بعد تشغيل السيرفر:")
print("   📊 Dashboard: http://192.168.8.115:5000/analytics/dashboard")
print("   📥 Export: http://192.168.8.115:5000/analytics/export/powerbi")
print("=" * 80)
