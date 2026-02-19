"""
إضافة بيانات تجريبية للعقارات المستأجرة
==========================================
سكريبت لإضافة عقارات تجريبية لاختبار نظام العقارات
"""
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# إضافة المسار للوصول إلى modules
sys.path.insert(0, str(Path(__file__).parent))

from core.extensions import db
from models import RentalProperty
from app import app

print("=" * 80)
print("إضافة بيانات تجريبية للعقارات المستأجرة")
print("=" * 80)

sample_properties = [
    {
        'city': 'الرياض',
        'address': 'حي النرجس، شارع الأمير سلطان، عمارة رقم 123',
        'map_link': 'https://maps.google.com/?q=24.7136,46.6753',
        'location_link': None,
        'contract_number': 'RC-2024-001',
        'owner_name': 'عبدالله محمد السعيد',
        'owner_id': '1234567890',
        'contract_start_date': date(2024, 1, 1),
        'contract_end_date': date(2026, 12, 31),
        'annual_rent_amount': 120000.0,
        'includes_utilities': False,
        'payment_method': 'annually',
        'status': 'active',
        'notes': 'عمارة سكنية للموظفين - 4 شقق'
    },
    {
        'city': 'جدة',
        'address': 'حي الروضة، طريق المدينة، فيلا رقم 456',
        'map_link': 'https://maps.google.com/?q=21.5433,39.1728',
        'location_link': None,
        'contract_number': 'JD-2025-012',
        'owner_name': 'محمد أحمد الغامدي',
        'owner_id': '9876543210',
        'contract_start_date': date(2025, 6, 1),
        'contract_end_date': date(2026, 5, 31),
        'annual_rent_amount': 85000.0,
        'includes_utilities': True,
        'payment_method': 'quarterly',
        'status': 'active',
        'notes': 'فيلا للمديرين - تشمل الماء والكهرباء'
    },
    {
        'city': 'الدمام',
        'address': 'حي الفيصلية، شارع الملك فيصل، بناية رقم 789',
        'map_link': 'https://maps.google.com/?q=26.4207,50.0888',
        'location_link': None,
        'contract_number': 'DM-2023-045',
        'owner_name': 'خالد عبدالرحمن المطيري',
        'owner_id': '5555555555',
        'contract_start_date': date(2023, 3, 15),
        'contract_end_date': date(2026, 3, 14),
        'annual_rent_amount': 96000.0,
        'includes_utilities': False,
        'payment_method': 'semi_annually',
        'status': 'active',
        'notes': 'دور كامل - 6 غرف للسائقين'
    },
    {
        'city': 'الرياض',
        'address': 'حي العليا، شارع العروبة، شقة 205',
        'map_link': 'https://maps.google.com/?q=24.7139,46.6839',
        'location_link': None,
        'contract_number': 'RC-2024-089',
        'owner_name': 'فهد ناصر القحطاني',
        'owner_id': '7777777777',
        'contract_start_date': date(2024, 9, 1),
        'contract_end_date': date(2025, 8, 31),
        'annual_rent_amount': 42000.0,
        'includes_utilities': False,
        'payment_method': 'monthly',
        'status': 'expiring',  # ستنتهي قريباً
        'notes': 'شقة صغيرة - موظف واحد'
    },
    {
        'city': 'مكة المكرمة',
        'address': 'حي الزاهر، شارع إبراهيم الخليل، عمارة الفيصل',
        'map_link': 'https://maps.google.com/?q=21.4225,39.8262',
        'location_link': None,
        'contract_number': 'MK-2022-034',
        'owner_name': 'سعيد حسن الزهراني',
        'owner_id': '3333333333',
        'contract_start_date': date(2022, 1, 1),
        'contract_end_date': date(2025, 12, 31),
        'annual_rent_amount': 72000.0,
        'includes_utilities': True,
        'payment_method': 'annually',
        'status': 'active',
        'notes': 'مبنى سكني - 3 شقق'
    }
]

with app.app_context():
    print("\n1️⃣ التحقق من البيانات الحالية...")
    current_count = RentalProperty.query.filter_by(is_active=True).count()
    print(f"   عدد العقارات الحالي: {current_count}")
    
    if current_count > 0:
        print("\n❓ هل تريد حذف العقارات الموجودة وإضافة بيانات تجريبية جديدة؟")
        answer = input("   اكتب 'نعم' للموافقة أو اضغط Enter للإلغاء: ")
        if answer.strip() != 'نعم':
            print("\n❌ تم إلغاء العملية")
            sys.exit(0)
        
        # حذف العقارات الموجودة
        RentalProperty.query.delete()
        db.session.commit()
        print("   ✅ تم حذف العقارات القديمة")
    
    print("\n2️⃣ إضافة العقارات التجريبية...")
    
    added_count = 0
    for prop_data in sample_properties:
        try:
            property_obj = RentalProperty(**prop_data)
            db.session.add(property_obj)
            added_count += 1
            print(f"   ✅ تم إضافة: {prop_data['city']} - {prop_data['address'][:40]}...")
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
    
    db.session.commit()
    
    print("\n3️⃣ التحقق من البيانات المضافة...")
    final_count = RentalProperty.query.filter_by(is_active=True).count()
    print(f"   عدد العقارات النهائي: {final_count}")
    
    # عرض ملخص
    print("\n4️⃣ ملخص العقارات المضافة:")
    properties = RentalProperty.query.filter_by(is_active=True).all()
    for prop in properties:
        print(f"\n   🏠 ID: {prop.id}")
        print(f"      المدينة: {prop.city}")
        print(f"      العنوان: {prop.address[:60]}...")
        print(f"      المالك: {prop.owner_name}")
        print(f"      الإيجار السنوي: {prop.annual_rent_amount:,.2f} ريال")
        print(f"      تاريخ الانتهاء: {prop.contract_end_date}")
        print(f"      الأيام المتبقية: {prop.remaining_days} يوم")
        print(f"      الحالة: {prop.status}")

print("\n" + "=" * 80)
print(f"✅ تم إضافة {added_count} عقار تجريبي بنجاح!")
print("\n📱 يمكنك الآن زيارة صفحة العقارات:")
print("   http://192.168.8.115:5000/properties/dashboard")
print("=" * 80)
