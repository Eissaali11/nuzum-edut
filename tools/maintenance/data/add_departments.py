#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""إضافة أقسام نموذجية"""

if __name__ == "__main__":
    import sys
    import os
    
    sys.path.insert(0, os.getcwd())
    
    # تجنب مشكلة استيراد app/__init__.py
    # استيراد مباشر من app.py
    import importlib.util
    spec = importlib.util.spec_from_file_location("flask_app", "app.py")
    flask_app_module = importlib.util.module_from_spec(spec)
    sys.modules['flask_app'] = flask_app_module
    spec.loader.exec_module(flask_app_module)
    
    app = flask_app_module.app
    
    from core.extensions import db
    from models import Department
    
    # الأقسام
    DEPTS = [
        ('الموارد البشرية', 'HR'),
        ('المبيعات', 'SALES'),
        ('التسويق', 'MARKETING'),
        ('تكنولوجيا المعلومات', 'IT'),
        ('العمليات', 'OPS'),
        ('التمويل', 'FINANCE'),
        ('الإدارة', 'ADMIN'),
        ('خدمة العملاء', 'CS'),
    ]
    
    with app.app_context():
        count = Department.query.count()
        print(f"✓ أقسام موجودة: {count}")
        
        if count == 0:
            print("\n🔄 إضافة أقسام نموذجية...")
            for name, code in DEPTS:
                dept = Department(name=name, code=code, status='active')
                db.session.add(dept)
                print(f"  ✓ {name}")
            
            try:
                db.session.commit()
                print(f"\n✅ تم إضافة {len(DEPTS)} قسم!")
            except Exception as e:
                print(f"❌ خطأ: {e}")
                db.session.rollback()
        
        # عرض الأقسام
        print("\n📋 الأقسام في قاعدة البيانات:")
        for dept in Department.query.all():
            print(f"  {dept.id}: {dept.name} ({dept.code})")
