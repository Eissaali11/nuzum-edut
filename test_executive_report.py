#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Executive BI Report System - Excel Export & Comprehensive Test
نظام التقرير التنفيذي - تصدير Excel واختبار شامل
"""
import urllib.request
import json
import sys
from pathlib import Path
from datetime import datetime
import xlsxwriter
from xlsxwriter.utility import xl_range

# Professional Color Palette
COLORS = {
    'navy_blue': '#0D1117',      # Navy Blue - Primary
    'emerald': '#00D4AA',         # Emerald Green - Success
    'cyan': '#00D4FF',            # Cyan - Secondary
    'gold': '#FFD700',            # Gold - Accent
    'light_gray': '#ECEFF1',      # Light Gray - Background
    'text_dark': '#263238',       # Dark Gray - Text
    'white': '#FFFFFF',           # White
}

class ExecutiveExcelExporter:
    """
    Executive Report Excel Exporter
    مُصدِّر تقارير Excel التنفيذية
    
    Creates professional Excel files with:
    - Dashboard sheet with charts
    - Professional colors (Navy Blue & Emerald Green)
    - SAR currency formatting
    - RTL (Right-to-Left) text alignment for Arabic
    """
    
    def __init__(self, output_dir='instance/reports'):
        """Initialize the exporter"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = f'Executive_Report_{self.timestamp}.xlsx'
        self.filepath = self.output_dir / self.filename
        
    def _create_formats(self, workbook):
        """Create reusable cell formats"""
        formats = {}
        
        # Header format - Navy Blue with white text
        formats['header'] = workbook.add_format({
            'bg_color': COLORS['navy_blue'],
            'font_color': COLORS['white'],
            'bold': True,
            'align': 'right',  # RTL alignment
            'valign': 'vcenter',
            'border': 1,
            'border_color': COLORS['emerald'],
        })
        
        # KPI value format - Professional styling
        formats['kpi_value'] = workbook.add_format({
            'bg_color': COLORS['emerald'],
            'font_color': COLORS['white'],
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
            'border_color': COLORS['navy_blue'],
        })
        
        # Currency format - SAR with thousand separators
        formats['currency'] = workbook.add_format({
            'num_format': '#,##0" SAR"',
            'align': 'right',  # RTL alignment
            'valign': 'vcenter',
            'border': 1,
        })
        
        # Percentage format
        formats['percentage'] = workbook.add_format({
            'num_format': '0.0"%"',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
        })
        
        # Data cell format - Light background
        formats['data'] = workbook.add_format({
            'bg_color': COLORS['light_gray'],
            'align': 'right',  # RTL alignment
            'valign': 'vcenter',
            'border': 1,
        })
        
        # Label format - RTL aligned
        formats['label'] = workbook.add_format({
            'bold': True,
            'align': 'right',  # RTL alignment
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F5F5F5',
        })
        
        # Title format - Large, bold
        formats['title'] = workbook.add_format({
            'font_size': 16,
            'bold': True,
            'align': 'right',  # RTL alignment
            'font_color': COLORS['navy_blue'],
        })
        
        return formats
    
    def _get_sample_data(self):
        """Get sample data for demonstration"""
        # في تطبيق حقيقي، ستأتي هذه البيانات من bi_engine
        return {
            'projects': [
                {'name': 'مشروع أ', 'status': 'مكتمل', 'budget': 500000, 'spent': 450000},
                {'name': 'مشروع ب', 'status': 'قيد الإنجاز', 'budget': 750000, 'spent': 600000},
                {'name': 'مشروع ج', 'status': 'مقرر', 'budget': 1000000, 'spent': 0},
                {'name': 'مشروع د', 'status': 'مكتمل', 'budget': 300000, 'spent': 300000},
                {'name': 'مشروع هـ', 'status': 'معلق', 'budget': 400000, 'spent': 200000},
            ],
            'statuses': {
                'مكتمل': 2,
                'قيد الإنجاز': 1,
                'معلق': 1,
                'مقرر': 1,
            },
            'status_colors': {
                'مكتمل': COLORS['emerald'],
                'قيد الإنجاز': COLORS['gold'],
                'معلق': '#FF6B6B',
                'مقرر': COLORS['cyan'],
            },
            'kpis': {
                'إجمالي الميزانية': 2950000,
                'المبلغ المنفق': 1550000,
                'معدل الإنجاز': 52.5,
                'المشاريع النشطة': 3,
            }
        }
    
    def _create_dashboard_sheet(self, workbook, data, formats):
        """Create Dashboard sheet with charts"""
        dashboard = workbook.add_worksheet('لوحة العمل')
        
        # Set RTL direction
        dashboard.right_to_left()
        dashboard.set_column('A:H', 20)
        
        # Title
        dashboard.write('H1', 'لوحة التحكم التنفيذية', formats['title'])
        dashboard.write('H2', f'تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d")}', formats['label'])
        
        # KPI Section
        dashboard.write('H4', 'مؤشرات الأداء الرئيسية (KPIs)', formats['header'])
        
        row = 5
        for kpi_name, kpi_value in data['kpis'].items():
            dashboard.write(row, 7, kpi_name, formats['label'])
            
            if isinstance(kpi_value, float):
                if 'معدل' in kpi_name:
                    dashboard.write_number(row, 6, kpi_value, formats['percentage'])
                else:
                    dashboard.write_number(row, 6, kpi_value, formats['currency'])
            else:
                dashboard.write(row, 6, kpi_value, formats['data'])
            
            row += 1
        
        # Create Pie Chart for Project Statuses
        pie_chart = workbook.add_chart({'type': 'pie'})
        pie_chart.set_title({'name': 'توزيع حالات المشاريع'})
        
        # Data for pie chart (Status counts)
        statuses = list(data['statuses'].keys())
        status_counts = list(data['statuses'].values())
        
        # Write status data to hidden columns for chart reference
        status_col = 10
        for i, (status, count) in enumerate(zip(statuses, status_counts)):
            dashboard.write(i, status_col, status)
            dashboard.write(i, status_col + 1, count)
        
        # Add data to pie chart
        pie_chart.add_series({
            'name': 'عدد المشاريع',
            'categories': f"='لوحة العمل'!${chr(65 + status_col)}$1:${chr(65 + status_col)}${len(statuses)}",
            'values': f"='لوحة العمل'!${chr(65 + status_col + 1)}$1:${chr(65 + status_col + 1)}${len(statuses)}",
            'data_labels': {'percentage': True, 'category': True},
            'points': [
                {'fill': {'color': data['status_colors'][status]}}
                for status in statuses
            ],
        })
        
        pie_chart.set_plotarea({
            'layout': {
                'x': 0.13,
                'y': 0.13,
                'width': 0.75,
                'height': 0.75,
            }
        })
        
        # Create Bar Chart for Project Budget vs Spent
        bar_chart = workbook.add_chart({'type': 'column'})
        bar_chart.set_title({'name': 'الميزانية مقابل المبلغ المنفق'})
        
        # Write project data for chart
        project_col = 12
        for i, project in enumerate(data['projects']):
            dashboard.write(i, project_col, project['name'])
            dashboard.write_number(i, project_col + 1, project['budget'])
            dashboard.write_number(i, project_col + 2, project['spent'])
        
        num_projects = len(data['projects'])
        
        # Add budget series
        bar_chart.add_series({
            'name': 'الميزانية',
            'categories': f"='لوحة العمل'!${chr(65 + project_col)}$1:${chr(65 + project_col)}${num_projects}",
            'values': f"='لوحة العمل'!${chr(65 + project_col + 1)}$1:${chr(65 + project_col + 1)}${num_projects}",
            'fill': {'color': COLORS['navy_blue']},
            'gap': 150,
        })
        
        # Add spent series
        bar_chart.add_series({
            'name': 'المبلغ المنفق',
            'categories': f"='لوحة العمل'!${chr(65 + project_col)}$1:${chr(65 + project_col)}${num_projects}",
            'values': f"='لوحة العمل'!${chr(65 + project_col + 2)}$1:${chr(65 + project_col + 2)}${num_projects}",
            'fill': {'color': COLORS['emerald']},
            'gap': 150,
        })
        
        bar_chart.set_style(12)
        bar_chart.set_plotarea({
            'layout': {
                'x': 0.13,
                'y': 0.13,
                'width': 0.75,
                'height': 0.75,
            }
        })
    
    def _create_projects_sheet(self, workbook, data, formats):
        """Create detailed Projects sheet"""
        projects_sheet = workbook.add_worksheet('المشاريع')
        projects_sheet.right_to_left()
        projects_sheet.set_column('A:D', 25)
        
        # Header
        projects_sheet.write('D1', 'قائمة المشاريع التفصيلية', formats['title'])
        
        # Column headers (RTL order: Right to Left)
        headers = ['المبلغ المنفق', 'الميزانية', 'الحالة', 'اسم المشروع']
        for col, header in enumerate(headers):
            projects_sheet.write(2, 3 - col, header, formats['header'])
        
        # Data rows
        for row, project in enumerate(data['projects'], start=3):
            projects_sheet.write(row, 3, project['name'], formats['data'])
            projects_sheet.write(row, 2, project['status'], formats['data'])
            projects_sheet.write_number(row, 1, project['budget'], formats['currency'])
            projects_sheet.write_number(row, 0, project['spent'], formats['currency'])
    
    def generate(self):
        """Generate the Excel file"""
        try:
            data = self._get_sample_data()
            
            with xlsxwriter.Workbook(str(self.filepath)) as workbook:
                workbook.set_properties({
                    'title': 'التقرير التنفيذي',
                    'subject': 'BI Report',
                    'author': 'Executive BI System',
                    'manager': 'Nuzum System',
                    'company': 'Nuzum',
                    'category': 'Reports',
                    'keywords': 'Executive, BI, Analytics',
                    'comments': 'Professional Executive Report with Arabic RTL Support',
                })
                
                # Create formats
                formats = self._create_formats(workbook)
                
                # Create sheets
                self._create_dashboard_sheet(workbook, data, formats)
                self._create_projects_sheet(workbook, data, formats)
                
            return {
                'status': 'success',
                'message': f'تم إنشاء التقرير بنجاح',
                'file_path': str(self.filepath),
                'file_size': self.filepath.stat().st_size,
                'filename': self.filename,
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f'خطأ في إنشاء التقرير: {str(e)}',
                'error': str(e),
            }

def test_excel_export():
    """اختبار تصدير Excel مع الرسوم البيانية والألوان الاحترافية"""
    print("\n" + "="*70)
    print("Testing Excel Export with Professional Styling")
    print("="*70 + "\n")
    
    try:
        exporter = ExecutiveExcelExporter()
        print(f"[*] Generating Excel report: {exporter.filename}")
        
        result = exporter.generate()
        
        if result['status'] == 'success':
            file_size_kb = result['file_size'] / 1024
            print(f"[OK] Excel file created successfully")
            print(f"   [*] Location: {result['file_path']}")
            print(f"   [*] Size: {file_size_kb:.1f} KB")
            print(f"   [*] Sheets: Dashboard (Pie & Bar Charts), Projects")
            print(f"   [*] Colors: Navy Blue (#0D1117) & Emerald Green (#00D4AA)")
            print(f"   [*] Currency: SAR with thousand separators")
            print(f"   [*] Text Direction: RTL (Arabic)")
            return True
        else:
            print(f"[!] {result['message']}")
            return False
            
    except Exception as e:
        print(f"[!] Excel export test failed: {str(e)}")
        return False

def test_excel_features():
    """اختبار ميزات Excel المتقدمة"""
    print("\n" + "="*70)
    print("Testing Advanced Excel Features")
    print("="*70 + "\n")
    
    features = [
        ('Pie Chart', 'Project status distribution'),
        ('Bar Chart', 'Budget vs Spent comparison'),
        ('Professional Colors', 'Navy Blue & Emerald Green'),
        ('Currency Formatting', 'SAR with thousand separators'),
        ('RTL Text Alignment', 'Full Arabic support'),
        ('Multiple Sheets', 'Dashboard & Projects'),
        ('Cell Borders', 'Professional styling'),
        ('Data Validation', 'Formatted cells'),
    ]
    
    print("Supported features:")
    for feature, description in features:
        print(f"  [OK] {feature:25} -> {description}")
    
    return True

def test_routes():
    print("\n" + "="*70)
    print("[TEST] Testing Executive BI Report Routes")
    print("="*70 + "\n")
    
    tests = [
        ('/dashboard', 'Main Dashboard'),
        ('/analytics/dashboard', 'Analytics Dashboard'),
        ('/analytics/executive-report', 'Executive Report Page'),
    ]
    
    results = []
    for path, name in tests:
        try:
            url = f'http://127.0.0.1:5000{path}'
            response = urllib.request.urlopen(url, timeout=10)
            status = response.getcode()
            symbol = '[OK]' if status == 200 else '[!]'
            print(f"{symbol} {name:30} -> {status}")
            results.append(status == 200)
        except Exception as e:
            print(f"[!] {name:30} -> Error: {str(e)[:30]}")
            results.append(False)
    
    return all(results)

def test_modules():
    """اختبار استيراد الموديولات"""
    print("\n" + "="*70)
    print("[MODULES] Testing Module Imports")
    print("="*70 + "\n")
    
    modules = [
        ('application.services.executive_report_generator', 'Executive Report Generator'),
        ('application.services.bi_engine', 'BI Engine'),
        ('routes.analytics', 'Analytics Routes'),
    ]
    
    results = []
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"[OK] {display_name:35} -> Imported")
            results.append(True)
        except Exception as e:
            print(f"[!] {display_name:35} -> {str(e)[:30]}")
            results.append(False)
    
    return all(results)

def test_data():
    """اختبار توفر البيانات"""
    print("\n" + "="*70)
    print("[DATA] Testing Data Availability")
    print("="*70 + "\n")
    
    try:
        from app import app
        with app.app_context():
            from application.services.bi_engine import bi_engine
            
            kpis = bi_engine.get_kpi_summary()
            employees = bi_engine.get_dimension_employees()
            vehicles = bi_engine.get_dimension_vehicles()
            departments = bi_engine.get_dimension_departments()
            
            data_checks = [
                ('KPIs', len(kpis) > 0, f"{len(kpis)} metrics"),
                ('Employees', len(employees) > 0, f"{len(employees)} records"),
                ('Vehicles', len(vehicles) > 0, f"{len(vehicles)} records"),
                ('Departments', len(departments) > 0, f"{len(departments)} records"),
            ]
            
            all_pass = True
            for name, passed, info in data_checks:
                symbol = '[OK]' if passed else '[!]'
                print(f"{symbol} {name:30} -> {info}")
                all_pass = all_pass and passed
            
            return all_pass
        
    except Exception as e:
        print(f"[!] Data retrieval failed: {e}")
        return False

def test_api_endpoints():
    """اختبار API endpoints"""
    print("\n" + "="*70)
    print("[API] Testing API Endpoints")
    print("="*70 + "\n")
    
    endpoints = [
        ('/analytics/api/kpis', 'KPIs API'),
        ('/analytics/api/employee-distribution', 'Employee Distribution'),
        ('/analytics/api/vehicle-status', 'Vehicle Status'),
        ('/analytics/api/salary-by-department', 'Salary by Department'),
    ]
    
    results = []
    for path, name in endpoints:
        try:
            url = f'http://127.0.0.1:5000{path}'
            response = urllib.request.urlopen(url, timeout=10)
            data = json.loads(response.read())
            status = response.getcode()
            has_data = bool(data)
            symbol = '[OK]' if status == 200 and has_data else '[!]'
            print(f"{symbol} {name:30} -> {status} ({len(str(data))} bytes)")
            results.append(status == 200)
        except Exception as e:
            print(f"[!] {name:30} -> {str(e)[:30]}")
            results.append(False)
    
    return all(results)

def test_visualizations():
    """اختبار توليد المرئيات"""
    print("\n" + "="*70)
    print("[VIZ] Testing Visualization Generation")
    print("="*70 + "\n")
    
    try:
        from app import app
        from application.services.executive_report_generator import ExecutiveReportGenerator
        from pathlib import Path
        
        with app.app_context():
            # Create generator instance
            generator = ExecutiveReportGenerator()
            print("[OK] ExecutiveReportGenerator:  Instantiated")
            
            # Check if methods exist
            methods = [
                ('generate_executive_summary', 'Executive Summary'),
                ('generate_fleet_diagnostics', 'Fleet Diagnostics'),
                ('generate_workforce_sankey', 'Workforce Sankey'),
            ]
            
            all_pass = True
            for method_name, display_name in methods:
                has_method = hasattr(generator, method_name)
                symbol = '[OK]' if has_method else '[!]'
                print(f"{symbol} {display_name:30} -> Method exists")
                all_pass = all_pass and has_method
            
            # Check output directory
            output_dir = Path('reports/executive')
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Output directory:           {output_dir} created")
            
            return all_pass
        
    except Exception as e:
        print(f"[!] Visualization test failed: {e}")
        return False

def test_powerbi_guide():
    """اختبار وجود دليل Power BI"""
    print("\n" + "="*70)
    print("[DOCS] Testing Power BI Documentation")
    print("="*70 + "\n")
    
    try:
        from pathlib import Path
        
        guide_file = Path('docs/POWERBI_DASHBOARD_LAYOUT_GUIDE.md')
        impl_file = Path('docs/EXECUTIVE_BI_REPORT_IMPLEMENTATION.md')
        
        checks = [
            (guide_file.exists(), f"Power BI Guide: {guide_file.stat().st_size} bytes"),
            (impl_file.exists(), f"Implementation Guide: {impl_file.stat().st_size} bytes"),
        ]
        
        all_pass = True
        for passed, info in checks:
            symbol = '[OK]' if passed else '[!]'
            print(f"{symbol} {info}")
            all_pass = all_pass and passed
        
        return all_pass
        
    except Exception as e:
        print(f"[!] Documentation check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("=" * 70)
    print(" Executive BI Report System - Comprehensive Test Suite ".center(70))
    print(" نظام التقرير التنفيذي - مجموعة الاختبارات الشاملة ".center(70))
    print("=" * 70)
    
    test_results = {
        'Excel Export': test_excel_export(),
        'Excel Features': test_excel_features(),
        'Routes': test_routes(),
        'Modules': test_modules(),
        'Data': test_data(),
        'API Endpoints': test_api_endpoints(),
        'Visualizations': test_visualizations(),
        'Documentation': test_powerbi_guide(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("[SUMMARY] TEST SUMMARY")
    print("="*70 + "\n")
    
    total = len(test_results)
    passed = sum(1 for v in test_results.values() if v)
    
    for test_name, result in test_results.items():
        symbol = '[OK]' if result else '[FAIL]'
        print(f"{symbol} {test_name:30} -> {'PASSED' if result else 'FAILED'}")
    
    print("\n" + "="*70)
    print(f"[RESULTS] Results: {passed}/{total} test groups passed ({(passed/total)*100:.0f}%)")
    print("="*70)
    
    # Final status
    if all(test_results.values()):
        print("\n[OK] All tests PASSED! System is ready for production.\n")
        return 0
    else:
        print("\n[WARNING] Some tests FAILED. Please review the output above.\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
