#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""إضافة أقسام مباشرة إلى قاعدة البيانات"""

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # الاتصال بقاعدة البيانات مباشرة
    # تحديد مسار قاعدة البيانات من إعدادات التطبيق
    db_path = 'sqlite:///nuzum_local.db'
    
    engine = create_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # استيراد model Department
    from models import Department
    
    # الأقسام المراد إضافتها
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
    
    try:
        # check إذا كانت الأقسام موجودة
        count = session.query(Department).count()
        print(f"✓ أقسام موجودة حالياً: {count}")
        
        if count == 0:
            print("\n🔄 إضافة أقسام نموذجية...")
            for name, code in DEPTS:
                dept = Department(name=name, code=code, status='active')
                session.add(dept)
                print(f"  ✓ {name}")
            
            session.commit()
            print(f"\n✅ تم إضافة {len(DEPTS)} قسم بنجاح!")
        else:
            print("✓ الأقسام موجودة بالفعل")
        
        # عرض الأقسام
        print("\n📋 الأقسام في قاعدة البيانات:")
        depts = session.query(Department).all()
        for dept in depts:
            print(f"  {dept.id}: {dept.name:30} ({dept.code})")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
