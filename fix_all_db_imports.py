#!/usr/bin/env python
"""
سكريبت شامل لاستبدال 'from core.extensions import db' بـ 'from core.extensions import db' في جميع الملفات
"""
import os
import re

# البحث عن جميع ملفات Python
python_files = []
for root, dirs, files in os.walk('.'):
    # تجاهل مجلدات معينة
    dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules']]
    
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            python_files.append(file_path)

print(f"عدد ملفات Python: {len(python_files)}")

fixed_count = 0
skipped_count = 0

for file_path in python_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # استبدال from core.extensions import db
        modified = content.replace('from core.extensions import db', 'from core.extensions import db')
        
        if modified != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"✅ أصلحت: {file_path}")
            fixed_count += 1
        else:
            skipped_count += 1
    except Exception as e:
        print(f"❌ خطأ في {file_path}: {e}")

print(f"\n📊 النتيجة:")
print(f"   ✅ تم إصلاح: {fixed_count} ملف")
print(f"   ⏭️  تم تجاهل: {skipped_count} ملف (بدون تغييرات)")
print("\n🎉 اكتمل!")
