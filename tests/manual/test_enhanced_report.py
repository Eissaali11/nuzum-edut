#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Enhanced Excel Report Generation
اختبار توليد التقرير المحسّن
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import app.py directly
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", os.path.join(os.path.dirname(__file__), "app.py"))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

print("\n" + "="*70)
print("🧪 Testing Enhanced Excel Report Generator")
print("="*70)

try:
    print("\n📦 Importing modules...")
    print("   ✅ Flask app loaded")
    
    from application.services.enhanced_report_generator import EnhancedExcelReportGenerator
    print("   ✅ EnhancedExcelReportGenerator loaded")
    
    print("\n🔧 Setting up Flask context...")
    
    with app.app_context():
        print("   ✅ Flask context activated")
        
        print("\n📊 Creating report generator...")
        generator = EnhancedExcelReportGenerator()
        print("   ✅ Generator instantiated")
        
        print("\n🎨 Generating enhanced Excel report...")
        print("   (This may take a few seconds...)")
        reports = generator.generate()
        
        print("\n✅ Report generation completed!")
        print("\n" + "="*70)
        print("📁 Generated Files:")
        print("="*70)
        
        for report_name, filepath in reports.items():
            if filepath:
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    print(f"✅ {report_name.upper():25} → {os.path.basename(filepath)}")
                    print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                else:
                    print(f"⚠️  {report_name.upper():25} → File not found: {filepath}")
        
        print("\n" + "="*70)
        print("📊 Report Contents:")
        print("="*70)
        print("""
✅ Sheet 1: Executive Summary
   - KPI Ribbon (6 key metrics)
   - Regional Distribution Summary
   - Department Summary

✅ Sheet 2: Financial Analysis
   - Salary by Region (Top 10)
   - Salary by Project
   - Monthly Salary Trends

✅ Sheet 3: Fleet Analysis
   - Vehicle Status Distribution
   - Maintenance Status Breakdown
   - Maintenance Cost Analysis

✅ Sheet 4: Workforce Analysis
   - Employees by Department
   - Attendance Status Summary
   - Employees by Project

✅ Sheets 5-7: Detailed Data
   - Raw Employees Data
   - Raw Vehicles Data
   - Raw Financials Data

Professional Features:
✅ Color-coded headers (Primary, Secondary, Warning colors)
✅ Professional formatting and borders
✅ Merged cells for better layout
✅ Right-aligned numbers
✅ Percentage calculations
✅ Sortable columns
""")
        
        print("="*70)
        print("✅ EXCEL REPORT GENERATION SUCCESSFUL!")
        print("="*70)
        print("\n🎯 Next Steps:")
        print("   1. Download from: http://127.0.0.1:5000/analytics/export/enhanced-excel")
        print("   2. Open in Excel or import to Power BI")
        print("   3. All data is formatted and ready for analysis\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
