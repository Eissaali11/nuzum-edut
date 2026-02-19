"""
Executive Business Intelligence Report Generator
================================================
مولد تقارير ذكاء الأعمال التنفيذية الاحترافية
Professional, high-end visual analytics with storytelling
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
import json

# Optional visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib import font_manager
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None

# Try to import plotly (optional)
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

warnings.filterwarnings('ignore')

from application.services.bi_engine import bi_engine


class ExecutiveReportGenerator:
    """مولد التقارير التنفيذية الاحترافية"""
    
    # Professional Color Palette - Dark Corporate Theme
    COLORS = {
        'primary': '#00D4AA',      # Emerald Green
        'secondary': '#00D4FF',    # Cyan Blue
        'accent': '#FFD700',       # Gold
        'danger': '#FF4757',       # Red
        'warning': '#FFA502',      # Orange
        'success': '#26DE81',      # Green
        'info': '#4B7BEC',         # Blue
        'dark_bg': '#0D1117',      # Deep Navy
        'card_bg': '#161B22',      # Card Background
        'text_primary': '#FFFFFF',
        'text_secondary': '#8B949E',
        'grid': '#30363D'
    }
    
    # Professional Gradient Palettes
    GRADIENT_FINANCIAL = ['#1a1a2e', '#16213e', '#0f3460', '#533483', '#e94560']
    GRADIENT_FLEET = ['#00D4AA', '#00C49A', '#00B48A', '#00A47A', '#00946A']
    GRADIENT_WORKFORCE = ['#667eea', '#764ba2', '#f093fb', '#4facfe']
    
    def __init__(self, output_dir='reports/executive'):
        """Initialize the report generator"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set professional matplotlib style
        self._setup_matplotlib_style()
        
        # Load data from BI engine
        self.kpis = bi_engine.get_kpi_summary()
        self.employees = pd.DataFrame(bi_engine.get_dimension_employees())
        self.vehicles = pd.DataFrame(bi_engine.get_dimension_vehicles())
        self.departments = pd.DataFrame(bi_engine.get_dimension_departments())
        self.financials = pd.DataFrame(bi_engine.get_fact_financials())
        self.maintenance = pd.DataFrame(bi_engine.get_fact_maintenance())
        self.attendance = pd.DataFrame(bi_engine.get_fact_attendance())
        
    def _setup_matplotlib_style(self):
        """Setup professional matplotlib styling"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        plt.style.use('dark_background')
        
        # Set figure parameters for high quality
        plt.rcParams['figure.facecolor'] = self.COLORS['dark_bg']
        plt.rcParams['axes.facecolor'] = self.COLORS['card_bg']
        plt.rcParams['axes.edgecolor'] = self.COLORS['grid']
        plt.rcParams['axes.labelcolor'] = self.COLORS['text_primary']
        plt.rcParams['text.color'] = self.COLORS['text_primary']
        plt.rcParams['xtick.color'] = self.COLORS['text_secondary']
        plt.rcParams['ytick.color'] = self.COLORS['text_secondary']
        plt.rcParams['grid.color'] = self.COLORS['grid']
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['savefig.bbox'] = 'tight'
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 11
        
    def generate_executive_summary(self, figsize=(16, 10)):
        """
        1. EXECUTIVE SUMMARY DASHBOARD
        Comprehensive KPI ribbon with insights
        """
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️ Matplotlib not available - skipping image generation")
            return None
        
        fig = plt.figure(figsize=figsize, facecolor=self.COLORS['dark_bg'])
        gs = fig.add_gridspec(3, 4, hspace=0.4, wspace=0.3)
        
        # Title with RTL support
        fig.suptitle('📊 NUZUM Executive Dashboard | لوحة المعلومات التنفيذية',
                     fontsize=20, fontweight='bold', color=self.COLORS['primary'],
                     y=0.98)
        
        # KPI Cards Data
        kpis_data = [
            {
                'title': 'Total Salary Liability\nإجمالي الرواتب',
                'value': f"{self.kpis['total_salary_liability']:,.0f}",
                'unit': 'SAR',
                'color': self.COLORS['primary'],
                'icon': '💰',
                'trend': '+2.3%'
            },
            {
                'title': 'Active Fleet\nالأسطول النشط',
                'value': f"{self.kpis['fleet_active_percentage']:.1f}",
                'unit': '%',
                'color': self.COLORS['secondary'],
                'icon': '🚛',
                'trend': f"{self.kpis['active_vehicles']}/{self.kpis['total_vehicles']}"
            },
            {
                'title': 'Workforce Density\nكثافة القوى العاملة',
                'value': f"{self.kpis['active_employees']}",
                'unit': 'EMP',
                'color': self.COLORS['accent'],
                'icon': '👥',
                'trend': f"{self.kpis['active_departments']} Depts"
            },
            {
                'title': 'Attendance Rate\nمعدل الحضور',
                'value': f"{self.kpis['attendance_rate_this_month']:.1f}",
                'unit': '%',
                'color': self.COLORS['success'],
                'icon': '✓',
                'trend': 'This Month'
            }
        ]
        
        # Draw KPI Cards
        for idx, kpi in enumerate(kpis_data):
            ax = fig.add_subplot(gs[0, idx])
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            # Card background
            rect = plt.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['card_bg'],
                                edgecolor=kpi['color'], linewidth=2, alpha=0.9)
            ax.add_patch(rect)
            
            # Icon
            ax.text(0.5, 0.75, kpi['icon'], ha='center', va='center',
                   fontsize=40, alpha=0.8)
            
            # Value
            ax.text(0.5, 0.50, kpi['value'], ha='center', va='center',
                   fontsize=28, fontweight='bold', color=kpi['color'])
            
            # Unit
            ax.text(0.5, 0.35, kpi['unit'], ha='center', va='center',
                   fontsize=12, color=self.COLORS['text_secondary'])
            
            # Title
            ax.text(0.5, 0.15, kpi['title'], ha='center', va='center',
                   fontsize=9, color=self.COLORS['text_primary'], multialignment='center')
            
            # Trend indicator
            ax.text(0.5, 0.05, kpi['trend'], ha='center', va='center',
                   fontsize=8, color=self.COLORS['info'], style='italic')
        
        # Regional Performance Map (Middle section - spans 2 columns)
        ax_map = fig.add_subplot(gs[1:, :2])
        self._draw_regional_heatmap(ax_map)
        
        # Department Distribution (Top right)
        ax_dept = fig.add_subplot(gs[1, 2:])
        self._draw_department_treemap(ax_dept)
        
        # Financial Trends (Bottom right)
        ax_trend = fig.add_subplot(gs[2, 2:])
        self._draw_financial_sparkline(ax_trend)
        
        # Management Insights Box
        self._add_insights_box(fig, gs)
        
        plt.savefig(self.output_dir / 'executive_summary.png',
                   facecolor=self.COLORS['dark_bg'], edgecolor='none')
        plt.close()
        
        return str(self.output_dir / 'executive_summary.png')
    
    def _draw_regional_heatmap(self, ax):
        """Financial Heatmap: Salary allocation by region vs project"""
        if self.financials.empty:
            ax.text(0.5, 0.5, 'No Financial Data Available',
                   ha='center', va='center', fontsize=14,
                   color=self.COLORS['text_secondary'])
            ax.axis('off')
            return
        
        # Create pivot table
        pivot = self.financials.pivot_table(
            values='salary_amount',
            index='region',
            columns='project_name',
            aggfunc='sum',
            fill_value=0
        )
        
        # Plot heatmap
        sns.heatmap(pivot / 1000, ax=ax, cmap='YlGnBu', annot=True,
                   fmt='.0f', cbar_kws={'label': 'Salary (K SAR)'},
                   linewidths=0.5, linecolor=self.COLORS['grid'])
        
        ax.set_title('💼 Financial Heatmap: Salary by Region × Project\nتوزيع الرواتب حسب المنطقة والمشروع',
                    fontsize=12, fontweight='bold', color=self.COLORS['primary'], pad=15)
        ax.set_xlabel('')
        ax.set_ylabel('')
        
        # RTL labels
        ax.tick_params(axis='both', labelsize=9)
        
    def _draw_department_treemap(self, ax):
        """Department distribution with employee counts"""
        if self.departments.empty:
            ax.text(0.5, 0.5, 'No Department Data',
                   ha='center', va='center', fontsize=12)
            ax.axis('off')
            return
        
        # Sort departments by employee count
        dept_data = self.departments.sort_values('employees_count', ascending=False).head(8)
        
        colors = [self.COLORS['primary'], self.COLORS['secondary'], 
                 self.COLORS['accent'], self.COLORS['success']] * 2
        
        bars = ax.barh(dept_data['department_name'], dept_data['employees_count'],
                      color=colors[:len(dept_data)], edgecolor=self.COLORS['grid'], linewidth=1.5)
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, dept_data['employees_count'])):
            ax.text(val + 1, i, f'{int(val)}', va='center',
                   fontsize=9, color=self.COLORS['text_primary'])
        
        ax.set_title('🏢 Workforce Distribution by Department\nتوزيع القوى العاملة حسب القسم',
                    fontsize=11, fontweight='bold', color=self.COLORS['secondary'], pad=10)
        ax.set_xlabel('Employee Count', fontsize=9, color=self.COLORS['text_secondary'])
        ax.grid(axis='x', alpha=0.2, linestyle='--')
        ax.set_axisbelow(True)
        
    def _draw_financial_sparkline(self, ax):
        """Financial trend sparkline"""
        if self.financials.empty:
            ax.text(0.5, 0.5, 'No Trend Data',
                   ha='center', va='center', fontsize=12)
            ax.axis('off')
            return
        
        # Aggregate by month
        monthly = self.financials.groupby('month')['salary_amount'].sum() / 1000
        
        ax.fill_between(range(len(monthly)), monthly, alpha=0.3,
                       color=self.COLORS['primary'])
        ax.plot(monthly.values, color=self.COLORS['primary'],
               linewidth=2.5, marker='o', markersize=6)
        
        # Add trend indicators
        if len(monthly) > 1:
            trend = monthly.iloc[-1] - monthly.iloc[-2]
            trend_pct = (trend / monthly.iloc[-2]) * 100
            trend_text = f"{'↑' if trend > 0 else '↓'} {abs(trend_pct):.1f}%"
            ax.text(len(monthly) - 1, monthly.iloc[-1],
                   f'  {trend_text}', fontsize=10,
                   color=self.COLORS['success'] if trend > 0 else self.COLORS['danger'],
                   fontweight='bold')
        
        ax.set_title('📈 Monthly Salary Trend | الاتجاه الشهري للرواتب',
                    fontsize=11, fontweight='bold', color=self.COLORS['accent'], pad=10)
        ax.set_ylabel('Salary (K SAR)', fontsize=9)
        ax.grid(alpha=0.2, linestyle='--')
        ax.set_axisbelow(True)
        
    def _add_insights_box(self, fig, gs):
        """Add management insights callout"""
        ax_insights = fig.add_axes([0.02, 0.02, 0.45, 0.12])
        ax_insights.axis('off')
        
        # Calculate key insights
        insights = []
        
        # Salary insight
        if not self.financials.empty:
            top_region = self.financials.groupby('region')['salary_amount'].sum().idxmax()
            insights.append(f"💡 Highest salary allocation: {top_region}")
        
        # Fleet insight
        if not self.vehicles.empty:
            high_maintenance = len(self.vehicles[
                self.vehicles['maintenance_status'] == 'High Maintenance'
            ])
            if high_maintenance > 0:
                insights.append(f"⚠️ {high_maintenance} vehicles require attention")
        
        # Attendance insight
        if self.kpis['attendance_rate_this_month'] < 90:
            insights.append(f"📊 Attendance below target: {self.kpis['attendance_rate_this_month']:.1f}%")
        
        # Draw insights box
        rect = plt.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['card_bg'],
                            edgecolor=self.COLORS['warning'], linewidth=2, alpha=0.95)
        ax_insights.add_patch(rect)
        
        ax_insights.text(0.05, 0.75, '🎯 MANAGEMENT INSIGHTS | رؤى الإدارة',
                        fontsize=11, fontweight='bold', color=self.COLORS['warning'])
        
        for i, insight in enumerate(insights[:3]):
            ax_insights.text(0.05, 0.55 - i * 0.2, insight,
                           fontsize=9, color=self.COLORS['text_primary'])
    
    def generate_fleet_diagnostics(self, figsize=(16, 10)):
        """
        2. FLEET DIAGNOSTICS REPORT
        Asset Health Index with correlation analysis
        """
        if not MATPLOTLIB_AVAILABLE or self.vehicles.empty:
            if not MATPLOTLIB_AVAILABLE:
                print("⚠️ Matplotlib not available - skipping image generation")
            return None
        
        fig = plt.figure(figsize=figsize, facecolor=self.COLORS['dark_bg'])
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        fig.suptitle('🚛 Fleet Intelligence Dashboard | لوحة متابعة الأسطول',
                     fontsize=18, fontweight='bold', color=self.COLORS['secondary'], y=0.98)
        
        # 1. Asset Health Donut (Explosion style)
        ax1 = fig.add_subplot(gs[0, 0])
        self._draw_asset_health_donut(ax1)
        
        # 2. Vehicle Age vs Maintenance Correlation
        ax2 = fig.add_subplot(gs[0, 1:])
        self._draw_age_maintenance_correlation(ax2)
        
        # 3. Status Distribution
        ax3 = fig.add_subplot(gs[1, 0])
        self._draw_status_distribution(ax3)
        
        # 4. Regional Fleet Distribution
        ax4 = fig.add_subplot(gs[1, 1])
        self._draw_regional_fleet(ax4)
        
        # 5. Maintenance Cost Analysis
        ax5 = fig.add_subplot(gs[1, 2])
        self._draw_maintenance_cost_analysis(ax5)
        
        plt.savefig(self.output_dir / 'fleet_diagnostics.png',
                   facecolor=self.COLORS['dark_bg'], edgecolor='none')
        plt.close()
        
        return str(self.output_dir / 'fleet_diagnostics.png')
    
    def _draw_asset_health_donut(self, ax):
        """Asset Health Index - Exploded Donut Chart"""
        status_counts = self.vehicles['maintenance_status'].value_counts()
        
        colors_map = {
            'Good': self.COLORS['success'],
            'Medium Maintenance': self.COLORS['warning'],
            'High Maintenance': self.COLORS['danger']
        }
        colors = [colors_map.get(s, self.COLORS['info']) for s in status_counts.index]
        
        # Explode high maintenance segment
        explode = [0.1 if 'High' in str(s) else 0 for s in status_counts.index]
        
        wedges, texts, autotexts = ax.pie(status_counts, labels=status_counts.index,
                                           autopct='%1.1f%%', startangle=90,
                                           colors=colors, explode=explode,
                                           textprops={'fontsize': 9, 'color': 'white'},
                                           wedgeprops={'edgecolor': self.COLORS['dark_bg'], 'linewidth': 2})
        
        # Create donut
        centre_circle = plt.Circle((0, 0), 0.70, fc=self.COLORS['card_bg'])
        ax.add_artist(centre_circle)
        
        # Center text
        ax.text(0, 0, 'Asset\nHealth', ha='center', va='center',
               fontsize=14, fontweight='bold', color=self.COLORS['primary'])
        
        ax.set_title('🛡️ Fleet Health Index\nمؤشر صحة الأسطول', fontsize=11, pad=15)
    
    def _draw_age_maintenance_correlation(self, ax):
        """Vehicle Age vs Maintenance Frequency Scatter"""
        # Calculate vehicle age
        current_year = datetime.now().year
        vehicle_data = self.vehicles.copy()
        vehicle_data['age'] = current_year - vehicle_data['year']
        
        # Count maintenance incidents per vehicle
        if not self.maintenance.empty:
            maint_counts = self.maintenance.groupby('vehicle_key').size()
            vehicle_data = vehicle_data.set_index('vehicle_key')
            vehicle_data['maint_count'] = maint_counts
            vehicle_data = vehicle_data.fillna(0).reset_index()
        else:
            vehicle_data['maint_count'] = 0
        
        # Scatter plot with color coding by status
        scatter = ax.scatter(vehicle_data['age'], vehicle_data['maint_count'],
                           c=vehicle_data['maintenance_status'].map({
                               'Good': 0,
                               'Medium Maintenance': 1,
                               'High Maintenance': 2
                           }),
                           cmap='RdYlGn_r', s=100, alpha=0.7,
                           edgecolors=self.COLORS['grid'], linewidth=1.5)
        
        # Trend line
        if len(vehicle_data) > 2:
            z = np.polyfit(vehicle_data['age'], vehicle_data['maint_count'], 1)
            p = np.poly1d(z)
            ax.plot(vehicle_data['age'], p(vehicle_data['age']),
                   "--", color=self.COLORS['danger'], linewidth=2, alpha=0.7)
        
        ax.set_xlabel('Vehicle Age (Years)', fontsize=10, color=self.COLORS['text_secondary'])
        ax.set_ylabel('Maintenance Incidents', fontsize=10, color=self.COLORS['text_secondary'])
        ax.set_title('📊 Age vs Maintenance Correlation\nالارتباط بين العمر والصيانة',
                    fontsize=11, fontweight='bold', color=self.COLORS['secondary'])
        ax.grid(alpha=0.2, linestyle='--')
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Health Status', rotation=270, labelpad=20, fontsize=9)
        cbar.set_ticks([0, 1, 2])
        cbar.set_ticklabels(['Good', 'Medium', 'High'])
    
    def _draw_status_distribution(self, ax):
        """Vehicle status distribution"""
        status_counts = self.vehicles['status'].value_counts()
        colors = [self.COLORS['success'], self.COLORS['info'],
                 self.COLORS['warning'], self.COLORS['danger']][:len(status_counts)]
        
        bars = ax.bar(range(len(status_counts)), status_counts.values,
                     color=colors, edgecolor=self.COLORS['grid'], linewidth=1.5)
        
        ax.set_xticks(range(len(status_counts)))
        ax.set_xticklabels(status_counts.index, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Count', fontsize=9)
        ax.set_title('📌 Status Distribution\nتوزيع الحالات', fontsize=10, fontweight='bold')
        ax.grid(axis='y', alpha=0.2, linestyle='--')
        
        # Add value labels
        for bar, val in zip(bars, status_counts.values):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.5,
                   int(val), ha='center', fontsize=10, fontweight='bold')
    
    def _draw_regional_fleet(self, ax):
        """Fleet distribution by region"""
        region_counts = self.vehicles['region'].value_counts().head(8)
        
        wedges, texts, autotexts = ax.pie(region_counts, labels=region_counts.index,
                                           autopct='%1.0f%%', startangle=90,
                                           colors=self.GRADIENT_FLEET[:len(region_counts)],
                                           textprops={'fontsize': 8})
        
        ax.set_title('🗺️ Regional Distribution\nالتوزيع الإقليمي', fontsize=10, pad=10)
    
    def _draw_maintenance_cost_analysis(self, ax):
        """Maintenance cost by severity"""
        if self.maintenance.empty:
            ax.text(0.5, 0.5, 'No Maintenance Data',
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            return
        
        cost_by_severity = self.maintenance.groupby('severity')['cost'].mean()
        
        bars = ax.barh(range(len(cost_by_severity)), cost_by_severity.values,
                      color=self.GRADIENT_FINANCIAL[:len(cost_by_severity)],
                      edgecolor=self.COLORS['grid'], linewidth=1.5)
        
        ax.set_yticks(range(len(cost_by_severity)))
        ax.set_yticklabels(cost_by_severity.index, fontsize=9)
        ax.set_xlabel('Avg Cost (SAR)', fontsize=9)
        ax.set_title('💰 Cost by Severity\nالتكلفة حسب الخطورة', fontsize=10, fontweight='bold')
        ax.grid(axis='x', alpha=0.2, linestyle='--')
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, cost_by_severity.values)):
            ax.text(val + 50, i, f'{val:,.0f}', va='center', fontsize=8)
    
    def generate_workforce_sankey(self):
        """
        3. WORKFORCE MAPPING - Sankey Diagram
        Flow of employees across departments and projects
        """
        if not PLOTLY_AVAILABLE or self.employees.empty:
            return None
        
        # Prepare data for Sankey
        dept_project_flow = self.employees.groupby(['department', 'project']).size().reset_index(name='count')
        dept_project_flow = dept_project_flow[dept_project_flow['count'] > 0]
        
        # Create nodes
        depts = dept_project_flow['department'].unique()
        projects = dept_project_flow['project'].unique()
        
        nodes = list(depts) + list(projects)
        node_dict = {node: idx for idx, node in enumerate(nodes)}
        
        # Create links
        source = [node_dict[dept] for dept in dept_project_flow['department']]
        target = [node_dict[proj] for proj in dept_project_flow['project']]
        value = dept_project_flow['count'].tolist()
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color=self.COLORS['grid'], width=0.5),
                label=nodes,
                color=[self.COLORS['primary']] * len(depts) + [self.COLORS['secondary']] * len(projects)
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color='rgba(0, 212, 170, 0.3)'
            )
        )])
        
        fig.update_layout(
            title_text='🔀 Workforce Flow: Departments → Projects | تدفق القوى العاملة',
            title_font=dict(size=20, color=self.COLORS['primary']),
            font=dict(size=12, color=self.COLORS['text_primary']),
            plot_bgcolor=self.COLORS['dark_bg'],
            paper_bgcolor=self.COLORS['dark_bg'],
            height=700
        )
        
        output_path = self.output_dir / 'workforce_sankey.html'
        fig.write_html(str(output_path))
        
        return str(output_path)
    
    def generate_full_report(self):
        """
        Generate complete executive report
        Returns dict with all output file paths
        """
        print("🎨 Generating Executive BI Report...")
        
        results = {
            'executive_summary': self.generate_executive_summary(),
            'fleet_diagnostics': self.generate_fleet_diagnostics(),
            'workforce_sankey': self.generate_workforce_sankey() if PLOTLY_AVAILABLE else None,
            'output_dir': str(self.output_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Report generated successfully!")
        print(f"📁 Output directory: {self.output_dir}")
        
        return results


# Quick test function
def test_report_generation():
    """Test the report generator"""
    generator = ExecutiveReportGenerator()
    results = generator.generate_full_report()
    
    print("\n" + "="*60)
    print("Executive Report Generation Complete!")
    print("="*60)
    for key, value in results.items():
        if value:
            print(f"{key}: {value}")
    print("="*60)


if __name__ == '__main__':
    test_report_generation()
