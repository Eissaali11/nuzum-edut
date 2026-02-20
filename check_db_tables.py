#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""قائمة الجداول الموجودة في قاعدة البيانات"""

from sqlalchemy import create_engine, text, inspect

engine = create_engine('sqlite:///nuzum_local.db')
inspector = inspect(engine)
tables = inspector.get_table_names()

print("الجداول الموجودة في قاعدة البيانات:")
if tables:
    for table in sorted(tables):
        print(f"  ✓ {table}")
else:
    print("  (لا توجد جداول)")

# التحقق من جدول department
if 'department' in tables:
    print("\n✅ جدول department موجود!")
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) as count FROM department'))
        count = result.fetchone()[0]
        print(f"عدد الأقسام: {count}")
        
        if count > 0:
            result = conn.execute(text('SELECT id, name FROM department LIMIT 5'))
            print("الأقسام:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
else:
    print("\n❌ جدول department غير موجود!")
