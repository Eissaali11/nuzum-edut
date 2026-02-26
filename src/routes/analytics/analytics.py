"""
Analytics & Business Intelligence Routes
=========================================
مسارات التحليلات والذكاء التجاري
"""
from datetime import datetime
from flask import Blueprint, render_template, jsonify, send_file, request
from flask_login import login_required, current_user
from functools import wraps

from src.application.services.bi_engine import bi_engine
from src.application.services.powerbi_exporter import export_to_powerbi
from src.application.services.excel.exporter import ExcelExporter


analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


def admin_required(f):
    """Decorator للتأكد من أن المستخدم admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@analytics_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """لوحة التحكم الرئيسية للتحليلات"""
    kpis = bi_engine.get_kpi_summary()
    
    return render_template(
        'analytics/dashboard.html',
        kpis=kpis,
        page_title='Analytics & Business Intelligence'
    )


@analytics_bp.route('/dimensions')
@login_required
@admin_required
def dimensions_dashboard():
    """واجهة عرض أبعاد البيانات (Dimensions)."""
    return render_template(
        'analytics/dimensions.html',
        page_title='Dimensions Studio'
    )


@analytics_bp.route('/api/kpis')
@login_required
@admin_required
def api_get_kpis():
    """API للحصول على KPIs"""
    kpis = bi_engine.get_kpi_summary()
    return jsonify(kpis)


@analytics_bp.route('/api/employee-distribution')
@login_required
@admin_required
def api_employee_distribution():
    """توزيع الموظفين حسب المشروع"""
    employees = bi_engine.get_dimension_employees()
    
    # تجميع حسب المشروع
    distribution = {}
    for emp in employees:
        project = emp['project']
        if project not in distribution:
            distribution[project] = 0
        distribution[project] += 1
    
    # تنسيق للرسم البياني
    labels = list(distribution.keys())
    values = list(distribution.values())
    
    return jsonify({
        'labels': labels,
        'values': values
    })


@analytics_bp.route('/api/employee-by-region')
@login_required
@admin_required
def api_employee_by_region():
    """توزيع الموظفين حسب المنطقة"""
    employees = bi_engine.get_dimension_employees()
    
    distribution = {}
    for emp in employees:
        region = emp['region']
        if region not in distribution:
            distribution[region] = 0
        distribution[region] += 1
    
    return jsonify({
        'labels': list(distribution.keys()),
        'values': list(distribution.values())
    })


@analytics_bp.route('/api/vehicle-status')
@login_required
@admin_required
def api_vehicle_status():
    """حالة المركبات"""
    vehicles = bi_engine.get_dimension_vehicles()
    
    status_count = {}
    for veh in vehicles:
        status = veh['status']
        if status not in status_count:
            status_count[status] = 0
        status_count[status] += 1
    
    return jsonify({
        'labels': list(status_count.keys()),
        'values': list(status_count.values())
    })


@analytics_bp.route('/api/vehicle-by-region')
@login_required
@admin_required
def api_vehicle_by_region():
    """توزيع المركبات حسب المنطقة"""
    vehicles = bi_engine.get_dimension_vehicles()
    
    distribution = {}
    for veh in vehicles:
        region = veh['region']
        if region not in distribution:
            distribution[region] = 0
        distribution[region] += 1
    
    return jsonify({
        'labels': list(distribution.keys()),
        'values': list(distribution.values())
    })


@analytics_bp.route('/api/maintenance-status')
@login_required
@admin_required
def api_maintenance_status():
    """حالة الصيانة للمركبات"""
    vehicles = bi_engine.get_dimension_vehicles()
    
    maintenance_count = {}
    for veh in vehicles:
        status = veh['maintenance_status']
        if status not in maintenance_count:
            maintenance_count[status] = 0
        maintenance_count[status] += 1
    
    return jsonify({
        'labels': list(maintenance_count.keys()),
        'values': list(maintenance_count.values())
    })


@analytics_bp.route('/api/salary-by-department')
@login_required
@admin_required
def api_salary_by_department():
    """إجمالي الرواتب حسب القسم"""
    financials = bi_engine.get_fact_financials()
    
    dept_salaries = {}
    for fact in financials:
        dept = fact['department']
        salary = fact['net_salary']
        
        if dept not in dept_salaries:
            dept_salaries[dept] = 0
        dept_salaries[dept] += salary
    
    return jsonify({
        'labels': list(dept_salaries.keys()),
        'values': list(dept_salaries.values())
    })


@analytics_bp.route('/api/salary-by-region')
@login_required
@admin_required
def api_salary_by_region():
    """إجمالي الرواتب حسب المنطقة"""
    financials = bi_engine.get_fact_financials()
    
    region_salaries = {}
    for fact in financials:
        region = fact['region']
        salary = fact['net_salary']
        
        if region not in region_salaries:
            region_salaries[region] = 0
        region_salaries[region] += salary
    
    return jsonify({
        'labels': list(region_salaries.keys()),
        'values': list(region_salaries.values())
    })


@analytics_bp.route('/api/maintenance-cost-trend')
@login_required
@admin_required
def api_maintenance_cost_trend():
    """اتجاه تكاليف الصيانة"""
    maintenance = bi_engine.get_fact_maintenance()
    
    # تجميع حسب الشهر
    from collections import defaultdict
    monthly_cost = defaultdict(float)
    
    for fact in maintenance:
        if fact['entry_date']:
            # استخراج السنة والشهر
            date_str = fact['entry_date']
            year_month = date_str[:7]  # YYYY-MM
            monthly_cost[year_month] += fact['cost']
    
    # ترتيب حسب التاريخ
    sorted_months = sorted(monthly_cost.keys())
    
    return jsonify({
        'labels': sorted_months,
        'values': [monthly_cost[month] for month in sorted_months]
    })


@analytics_bp.route('/api/attendance-rate-trend')
@login_required
@admin_required
def api_attendance_rate_trend():
    """اتجاه معدل الحضور"""
    from datetime import date, timedelta
    from collections import defaultdict
    
    # آخر 30 يوم
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    attendance = bi_engine.get_fact_attendance(start_date, end_date)
    
    # تجميع حسب اليوم
    daily_stats = defaultdict(lambda: {'total': 0, 'present': 0})
    
    for fact in attendance:
        day = fact['attendance_date']
        daily_stats[day]['total'] += 1
        if fact['is_present']:
            daily_stats[day]['present'] += 1
    
    # حساب النسبة
    sorted_days = sorted(daily_stats.keys())
    rates = []
    
    for day in sorted_days:
        stats = daily_stats[day]
        rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
        rates.append(round(rate, 2))
    
    return jsonify({
        'labels': sorted_days,
        'values': rates
    })


@analytics_bp.route('/export/powerbi')
@login_required
@admin_required
def export_powerbi():
    """تصدير التقرير الاحترافي - Power BI Report"""
    try:
        exporter = ExcelExporter()
        buffer, filename, mimetype = exporter.export_to_buffer()
        
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in export_powerbi: {error_details}")
        return jsonify({
            'error': 'Failed to generate Power BI export',
            'details': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/export/professional-report')
def export_professional_report():
    """تصدير التقرير الاحترافي (بدون مصادقة للتطوير)"""
    try:
        exporter = ExcelExporter()
        buffer, filename, mimetype = exporter.export_to_buffer()
        
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in export_professional_report: {error_details}")
        return jsonify({
            'error': 'Failed to export professional report',
            'details': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/export/latest-report')
def export_latest_report():
    """الحصول على أحدث تقرير محفوظ"""
    try:
        exporter = ExcelExporter()
        result = exporter.get_latest_report()
        
        if result is None:
            # إنشاء تقرير جديد إذا لم يوجد
            buffer, filename, mimetype = exporter.export_to_buffer()
        else:
            buffer, filename, mimetype = result
        
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in export_latest_report: {error_details}")
        return jsonify({
            'error': 'Failed to export latest report',
            'details': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/data/dimensions')
@login_required
@admin_required
def get_dimensions():
    """الحصول على جميع Dimension Tables"""
    return jsonify({
        'employees': bi_engine.get_dimension_employees(),
        'vehicles': bi_engine.get_dimension_vehicles(),
        'departments': bi_engine.get_dimension_departments()
    })


@analytics_bp.route('/data/facts')
@login_required
@admin_required
def get_facts():
    """الحصول على جميع Fact Tables"""
    return jsonify({
        'financials': bi_engine.get_fact_financials(),
        'maintenance': bi_engine.get_fact_maintenance(),
        'attendance': bi_engine.get_fact_attendance()
    })


# ============================================================
# EXECUTIVE REPORT ENDPOINTS
# ============================================================

@analytics_bp.route('/executive-report')
@login_required
@admin_required
def executive_report_dashboard():
    """Executive Report Dashboard"""
    return render_template(
        'analytics/executive_report.html',
        page_title='Executive Intelligence Report'
    )


@analytics_bp.route('/generate-executive-report')
@login_required
@admin_required
def generate_executive_report():
    """Generate complete executive report with visualizations"""
    try:
        from src.application.services.executive_report_generator import ExecutiveReportGenerator
        
        generator = ExecutiveReportGenerator()
        results = generator.generate_full_report()
        
        return jsonify({
            'success': True,
            'message': 'Executive report generated successfully',
            'files': results
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'error': 'Failed to generate executive report',
            'details': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/executive-summary-image')
@login_required
@admin_required
def get_executive_summary_image():
    """Serve the generated executive summary image"""
    from pathlib import Path
    image_path = Path('reports/executive/executive_summary.png')
    
    if not image_path.exists():
        return jsonify({'error': 'Report not generated yet. Please generate first.'}), 404
    
    return send_file(image_path, mimetype='image/png')


@analytics_bp.route('/fleet-diagnostics-image')
@login_required
@admin_required
def get_fleet_diagnostics_image():
    """Serve the generated fleet diagnostics image"""
    from pathlib import Path
    image_path = Path('reports/executive/fleet_diagnostics.png')
    
    if not image_path.exists():
        return jsonify({'error': 'Report not generated yet. Please generate first.'}), 404
    
    return send_file(image_path, mimetype='image/png')


# ============================================================
# ENHANCED EXCEL REPORT ENDPOINTS
# ============================================================

@analytics_bp.route('/export/enhanced-excel')
@login_required
@admin_required
def export_enhanced_excel():
    """Export enhanced Excel report with professional charts and analysis"""
    try:
        from src.application.services.enhanced_report_generator import EnhancedExcelReportGenerator
        from pathlib import Path
        import os
        
        generator = EnhancedExcelReportGenerator()
        
        # Generate report
        reports = generator.generate()
        
        # Get the filepath
        excel_file = reports.get('enhanced')
        
        if not excel_file or not os.path.exists(excel_file):
            return jsonify({
                'error': 'Failed to generate Excel report',
                'details': 'Report generation failed'
            }), 500
        
        # Get filename
        filename = Path(excel_file).name
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'error': 'Failed to generate enhanced Excel report',
            'details': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/generate/enhanced-excel')
@login_required
@admin_required
def generate_enhanced_excel():
    """Generate enhanced Excel report"""
    try:
        from src.application.services.enhanced_report_generator import EnhancedExcelReportGenerator
        
        generator = EnhancedExcelReportGenerator()
        reports = generator.generate()
        
        return jsonify({
            'success': True,
            'message': 'Enhanced Excel report generated successfully',
            'files': reports,
            'download_url': '/analytics/export/enhanced-excel'
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'error': 'Failed to generate enhanced Excel report',
            'details': str(e),
            'traceback': error_details
        }), 500


# ============================================================================
# Strategic Dashboard Endpoints (Visual Excel Dashboard Engine)
# محرك تقارير إكسل الاستراتيجية - Corporate-Grade Excel Dashboards
# ============================================================================

@analytics_bp.route('/strategic-dashboard')
@login_required
@admin_required
def strategic_dashboard_page():
    """Strategic Dashboard page - Generate visual Excel dashboards"""
    return render_template(
        'analytics/strategic_dashboard.html',
        page_title='Strategic Dashboard Generator'
    )


@analytics_bp.route('/generate/strategic-dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def generate_strategic_dashboard():
    """
    Generate professional Excel dashboard with embedded charts.
    
    Endpoint for generating corporate-grade Excel reports with:
    - Visual summary dashboard with KPI ribbon
    - Embedded charts (Bar, Doughnut, Trend Line)
    - Professional formatting and color coding
    - Advanced Excel features (Tables, Freeze panes)
    - RTL support for Arabic text
    
    Returns:
        JSON response with file status and download URL
    """
    try:
        from src.application.services.excel_dashboard_engine import ExcelDashboardEngine
        
        # Initialize the Excel Dashboard Engine
        engine = ExcelDashboardEngine()
        
        # Generate the professional dashboard
        result = engine.generate()
        
        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'message': 'Strategic Dashboard generated successfully',
                'file_path': result['file_path'],
                'file_name': result['file_name'],
                'file_size': result['file_size'],
                'download_url': '/analytics/export/strategic-dashboard'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result['message'],
                'error': result.get('error', 'Unknown error')
            }), 500
        
    except ImportError as e:
        return jsonify({
            'status': 'error',
            'message': 'xlsxwriter is required for Strategic Dashboard',
            'error': 'Install with: pip install xlsxwriter',
            'details': str(e)
        }), 500
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate strategic dashboard',
            'error': str(e),
            'traceback': error_details
        }), 500


@analytics_bp.route('/export/strategic-dashboard')
@login_required
@admin_required
def export_strategic_dashboard():
    """
    Download the most recently generated strategic dashboard Excel file.
    
    Returns:
        Excel file download
    """
    try:
        import os
        from pathlib import Path
        
        # Get the most recent dashboard file
        reports_dir = Path('instance/reports')
        
        if not reports_dir.exists():
            return jsonify({
                'error': 'No reports found. Please generate a dashboard first.'
            }), 404
        
        # Find the most recent Strategic_Dashboard file
        dashboard_files = list(reports_dir.glob('Strategic_Dashboard_*.xlsx'))
        
        if not dashboard_files:
            return jsonify({
                'error': 'No dashboards found. Please generate one first.'
            }), 404
        
        # Get the most recent file
        latest_file = max(dashboard_files, key=os.path.getctime)
        
        return send_file(
            latest_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Strategic_Dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': f'Error downloading dashboard: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
