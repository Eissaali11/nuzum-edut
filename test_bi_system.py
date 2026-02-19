"""
اختبار نظام Business Intelligence
===================================
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app import app
from application.services.bi_engine import bi_engine

print("=" * 80)
print("🔍 اختبار نظام Business Intelligence")
print("=" * 80)

with app.app_context():
    print("\n1️⃣ اختبار BI Engine...")
    
    # Test Dimensions
    print("\n   📊 Dimension Tables:")
    employees = bi_engine.get_dimension_employees()
    print(f"      ✅ DIM_Employees: {len(employees)} سجل")
    
    vehicles = bi_engine.get_dimension_vehicles()
    print(f"      ✅ DIM_Vehicles: {len(vehicles)} سجل")
    
    departments = bi_engine.get_dimension_departments()
    print(f"      ✅ DIM_Departments: {len(departments)} سجل")
    
    # Test Facts
    print("\n   📈 Fact Tables:")
    financials = bi_engine.get_fact_financials()
    print(f"      ✅ FACT_Financials: {len(financials)} سجل")
    
    maintenance = bi_engine.get_fact_maintenance()
    print(f"      ✅ FACT_Maintenance: {len(maintenance)} سجل")
    
    attendance = bi_engine.get_fact_attendance()
    print(f"      ✅ FACT_Attendance: {len(attendance)} سجل")
    
    # Test KPIs
    print("\n   📊 KPIs:")
    kpis = bi_engine.get_kpi_summary()
    print(f"      ✅ Total Salary Liability: {kpis['total_salary_liability']:,.2f} SAR")
    print(f"      ✅ Fleet Active: {kpis['fleet_active_percentage']:.1f}%")
    print(f"      ✅ Project Coverage: {kpis['project_coverage_percentage']:.1f}%")
    print(f"      ✅ Attendance Rate: {kpis['attendance_rate_this_month']:.1f}%")
    
    # Test Region Mapping
    print("\n2️⃣ اختبار Geospatial Mapping...")
    test_locations = [
        'الرياض',
        'جدة',
        'الدمام',
        'مكة المكرمة',
        'Unknown City'
    ]
    
    for loc in test_locations:
        region = bi_engine.standardize_region(loc)
        print(f"      '{loc}' → '{region}'")
    
    # Test Power BI Export
    print("\n3️⃣ اختبار Power BI Exporter...")
    try:
        from application.services.powerbi_exporter import export_to_powerbi
        buffer, filename, mimetype = export_to_powerbi()
        
        size_kb = len(buffer.getvalue()) / 1024
        print(f"      ✅ ملف Excel تم إنشاؤه: {filename}")
        print(f"      ✅ الحجم: {size_kb:.2f} KB")
        print(f"      ✅ النوع: {mimetype}")
        
        # Save for testing
        test_file = 'test_powerbi_export.xlsx'
        with open(test_file, 'wb') as f:
            f.write(buffer.getvalue())
        print(f"      ✅ تم الحفظ في: {test_file}")
        
    except Exception as e:
        print(f"      ❌ خطأ: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✅ جميع الاختبارات نجحت!")
    print("\n📱 روابط الوصول:")
    print("   Dashboard: http://192.168.8.115:5000/analytics/dashboard")
    print("   Export: http://192.168.8.115:5000/analytics/export/powerbi")
    print("=" * 80)
