#!/usr/bin/env python
"""
سكريبت لإصلاح أسماء الأدوار غير الموجودة
"""
import os

# قائمة الملفات المحتملة
files_to_fix = [
    "forms/user_forms.py",
    "utils/user_helpers.py"
]

replacements = [
    ("UserRole.FINANCE", "UserRole.ACCOUNTANT"),
    ("UserRole.FLEET", "UserRole.SUPERVISOR"),
    ("UserRole.USER", "UserRole.VIEWER"),
]

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        print(f"⏭️ ملف غير موجود: {file_path}")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = content
    for old, new in replacements:
        modified = modified.replace(old, new)
    
    if modified != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified)
        print(f"✅ تم إصلاح: {file_path}")  
    else:
        print(f"⏭️  لا حاجة لتعديل: {file_path}")

print("\n🎉 اكتمل الإصلاح!")
