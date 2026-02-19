# Power BI Dashboard Layout Guide for Nuzum Executive Report
# دليل تخطيط لوحة Power BI للتقرير التنفيذي

## 📊 Dashboard Architecture | بنية اللوحة

### **Page 1: Executive Overview (الصفحة التنفيذية)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  🏢 NUZUM Executive Dashboard - January 2026            🔄 Auto-Refresh │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │  💰 SALARY   │ │  🚛 FLEET    │ │  👥 WORKFORCE│ │  ✓ ATTENDANCE││
│  │  Liability   │ │  Readiness   │ │  Density     │ │  Rate        ││
│  │  ─────────── │ │  ─────────── │ │  ─────────── │ │  ─────────── ││
│  │  1.2M SAR    │ │  85.5%       │ │  92 EMP      │ │  94.2%       ││
│  │  ↑ +2.3%     │ │  32/37       │ │  9 Depts     │ │  This Month  ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘│
│                                                                       │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐│
│  │  🔥 FINANCIAL HEATMAP          │  │  🗺️ REGIONAL MAP            ││
│  │  Salary by Region × Project    │  │  Employee Distribution      ││
│  │  ───────────────────────────── │  │  ──────────────────────────││
│  │         P1    P2    P3    P4   │  │    [Saudi Arabia Filled Map]││
│  │  Riyadh  120K  85K  95K  110K  │  │    • Riyadh: 35 emp        ││
│  │  Jeddah  95K   75K  80K  90K   │  │    • Jeddah: 28 emp        ││
│  │  Dammam  80K   65K  70K  75K   │  │    • Dammam: 18 emp        ││
│  │  Makkah  70K   55K  60K  65K   │  │    • Others: 11 emp        ││
│  │  [Color: Yellow→Green→Blue]    │  │                             ││
│  └────────────────────────────────┘  └─────────────────────────────┘│
│                                                                       │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐│
│  │  🏢 DEPARTMENT TREEMAP         │  │  📈 SALARY TREND            ││
│  │  Employee Distribution         │  │  Monthly Growth             ││
│  │  ───────────────────────────── │  │  ──────────────────────────││
│  │  ┌─────────────┬──────────────┐│  │  [Line Chart]              ││
│  │  │ Operations  │  IT (12)     ││  │  Jan  Feb  Mar  Apr  May   ││
│  │  │    (28)     ├──────────────┤│  │  1.1M 1.15M 1.18M 1.2M 1.2M││
│  │  ├─────────────┤ HR (8)       ││  │  ↑ Trend: +2.3% MoM        ││
│  │  │ Logistics   ├──────────────┤│  │                             ││
│  │  │   (22)      │ Finance (7)  ││  │                             ││
│  │  └─────────────┴──────────────┘│  │                             ││
│  └────────────────────────────────┘  └─────────────────────────────┘│
│                                                                       │
│  💡 MANAGEMENT INSIGHTS:                                             │
│  • ⚠️ Qassim region shows 15% higher maintenance costs               │
│  • 📊 IT department salary 8% above industry average                 │
│  • 🚛 5 vehicles exceed optimal maintenance cycle                     │
└─────────────────────────────────────────────────────────────────────┘
```

### **Page 2: Fleet Intelligence (لوحة الأسطول)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  🚛 Fleet Diagnostics & Predictive Maintenance                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐│
│  │  🛡️ ASSET HEALTH INDEX         │  │  📊 AGE vs MAINTENANCE      ││
│  │  (Donut - Exploded)            │  │  Correlation Analysis       ││
│  │  ───────────────────────────── │  │  ──────────────────────────││
│  │       ┌───────────┐             │  │  [Scatter Plot]            ││
│  │      /  Good: 20  \             │  │  • Trend: +0.3 incidents   ││
│  │     /   (54%)      \            │  │    per year of age         ││
│  │    │  Medium: 12    │           │  │  • R² = 0.67 (Strong)      ││
│  │     \   (32%)      /            │  │  • Vehicles >5 yrs need    ││
│  │      \ High: 5    /             │  │    proactive maintenance   ││
│  │       └───────────┘             │  │                             ││
│  │  [Colors: Green/Yellow/Red]    │  │                             ││
│  └────────────────────────────────┘  └─────────────────────────────┘│
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  💰 MAINTENANCE COST BREAKDOWN                                 │ │
│  │  ──────────────────────────────────────────────────────────────│ │
│  │  [Stacked Bar Chart]                                            │ │
│  │  Good: ████████ 2,500 SAR avg                                  │ │
│  │  Medium: ████████████████ 5,200 SAR avg                        │ │
│  │  High: ████████████████████████████ 12,800 SAR avg            │ │
│  │                                                                  │ │
│  │  💡 Insight: High-maintenance vehicles cost 5.1x more           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐│
│  │  🗓️ MAINTENANCE SCHEDULE       │  │  🔧 TOP 10 VEHICLES         ││
│  │  Next 30 Days                  │  │  By Maintenance Cost        ││
│  │  ───────────────────────────── │  │  ──────────────────────────││
│  │  [Gantt Chart]                 │  │  [Horizontal Bar]          ││
│  │  • 12 vehicles due service     │  │  1. ABC-1234: 45K SAR      ││
│  │  • 3 critical inspections      │  │  2. DEF-5678: 38K SAR      ││
│  │  • 7 routine checks            │  │  3. GHI-9012: 32K SAR      ││
│  │                                 │  │  ...                        ││
│  └────────────────────────────────┘  └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### **Page 3: Workforce Intelligence (لوحة القوى العاملة)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  👥 Workforce Analytics & Predictive HR                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  🔀 SANKEY DIAGRAM: Department → Project Flow                    ││
│  │  ─────────────────────────────────────────────────────────────────││
│  │                                                                    ││
│  │  Operations ════════════════► Project Alpha (15)                 ││
│  │      (28)     ════════════► Project Beta (8)                     ││
│  │               ════════► Project Gamma (5)                        ││
│  │                                                                    ││
│  │  Logistics ═════════════► Project Alpha (12)                     ││
│  │      (22)    ════════► Project Beta (7)                          ││
│  │              ═══► Project Delta (3)                              ││
│  │                                                                    ││
│  │  IT (12) ═══════► Project Beta (8) ═══► Project Alpha (4)       ││
│  │                                                                    ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐│
│  │  🎻 SALARY DISTRIBUTION        │  │  📊 ATTENDANCE HEATMAP      ││
│  │  Violin Plot (Pay Equity)      │  │  Last 30 Days               ││
│  │  ───────────────────────────── │  │  ──────────────────────────││
│  │  [Violin Plot by Department]   │  │  [Calendar Heatmap]        ││
│  │  • Operations: 4.5K-8.2K SAR   │  │    Mon Tue Wed Thu Fri     ││
│  │  • IT: 6.2K-12.5K SAR          │  │  W1 ██ ██ ██ ██ ██ 98%    ││
│  │  • Logistics: 4.0K-7.5K SAR    │  │  W2 ██ ██ ██ ██ ██ 96%    ││
│  │  • Pay Dispersion Index: 0.32  │  │  W3 ██ ██ ██ ██ ██ 94%    ││
│  │    (0.3-0.4 = Healthy)         │  │  W4 ██ ██ ██ ██ ██ 92%    ││
│  └────────────────────────────────┘  └─────────────────────────────┘│
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  📈 PREDICTIVE ANALYTICS: Next Month Budget Forecast             ││
│  │  ─────────────────────────────────────────────────────────────────││
│  │  [Forecasting Line Chart with Confidence Intervals]              ││
│  │  Historical: Jan-May 2026                                        ││
│  │  Forecast: June 2026 → 1,245,000 SAR (±3.2%)                    ││
│  │  Growth Rate: +2.1% MoM (Linear Regression)                     ││
│  │  Confidence: 87% (Based on 5-month trend)                       ││
│  └──────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Power BI Design System

### **Color Palette (Dark Corporate Theme)**
```css
Primary (Emerald):   #00D4AA
Secondary (Cyan):    #00D4FF
Accent (Gold):       #FFD700
Danger (Red):        #FF4757
Warning (Orange):    #FFA502
Success (Green):     #26DE81
Background:          #0D1117
Card Background:     #161B22
```

### **Typography**
- **Headers**: Segoe UI Bold, 18-24pt
- **Body**: Segoe UI Regular, 11-14pt
- **KPIs**: Segoe UI Semibold, 28-36pt

### **Visual Hierarchy**
1. **Top Row**: KPI Cards (Card Visual) - 4 equal-width cards
2. **Middle Row**: Primary Analytics (2 columns, 60%/40% split)
3. **Bottom Row**: Supporting Visuals (3 equal columns)
4. **Footer**: Insights Callout Box

---

## 🔧 DAX Measures for Advanced Analytics

### **1. Total Salary Liability**
```dax
Total Salary = SUM(FACT_Financials[salary_amount])
```

### **2. Fleet Active Percentage**
```dax
Fleet Active % = 
DIVIDE(
    CALCULATE(COUNT(DIM_Vehicles[vehicle_key]), DIM_Vehicles[status] = "available"),
    COUNT(DIM_Vehicles[vehicle_key]),
    0
) * 100
```

### **3. YoY Salary Growth**
```dax
Salary YoY Growth % = 
VAR CurrentYearSalary = [Total Salary]
VAR PreviousYearSalary = 
    CALCULATE(
        [Total Salary],
        SAMEPERIODLASTYEAR(DIM_Time[date])
    )
RETURN
    DIVIDE(CurrentYearSalary - PreviousYearSalary, PreviousYearSalary, 0) * 100
```

### **4. Maintenance Cost per Vehicle**
```dax
Avg Maintenance Cost = 
DIVIDE(
    SUM(FACT_Maintenance[cost]),
    DISTINCTCOUNT(FACT_Maintenance[vehicle_key]),
    0
)
```

### **5. Attendance Rate (Dynamic)**
```dax
Attendance Rate = 
VAR TotalDays = COUNTROWS(FACT_Attendance)
VAR PresentDays = CALCULATE(
    COUNTROWS(FACT_Attendance),
    FACT_Attendance[status] = "present"
)
RETURN
    DIVIDE(PresentDays, TotalDays, 0) * 100
```

### **6. Salary Forecast (Next Month)**
```dax
Forecasted Salary = 
VAR LastMonthSalary = [Total Salary]
VAR AvgGrowthRate = 0.023  // 2.3% from historical data
RETURN
    LastMonthSalary * (1 + AvgGrowthRate)
```

### **7. Pay Dispersion Index**
```dax
Pay Dispersion = 
VAR Median = MEDIANX(DIM_Employees, DIM_Employees[salary])
VAR Mean = AVERAGE(DIM_Employees[salary])
RETURN
    ABS(DIVIDE(Mean - Median, Mean, 0))
```

---

## 🔗 Data Model Relationships

```
DIM_Employees (1) ──────────────► (∞) FACT_Financials
    employee_key                        employee_key

DIM_Vehicles (1) ───────────────► (∞) FACT_Maintenance
    vehicle_key                         vehicle_key

DIM_Employees (1) ──────────────► (∞) FACT_Attendance
    employee_key                        employee_key

DIM_Departments (1) ────────────► (∞) FACT_Financials
    department_key                      department_key

DIM_Time (1) ───────────────────► (∞) FACT_Financials
    date_key                            date_key

DIM_Time (1) ───────────────────► (∞) FACT_Maintenance
    date_key                            date_key
```

### **Relationship Settings**
- **Cardinality**: One-to-Many (1:∞)
- **Cross Filter Direction**: Single (Dimension → Fact)
- **Make Active**: ✓ (All relationships active)

---

## 📊 Visual Recommendations by Section

### **Executive Summary Page**
| Visual Type          | Data Source           | Configuration                          |
|----------------------|-----------------------|----------------------------------------|
| Card (KPIs)          | DAX Measures          | Large font, conditional formatting     |
| Matrix               | FACT_Financials       | Row: Region, Column: Project           |
| Filled Map           | DIM_Employees         | Location: Region, Size: Count          |
| Treemap              | DIM_Departments       | Category: Dept, Values: Emp Count      |
| Line Chart           | FACT_Financials       | X: Month, Y: Total Salary              |

### **Fleet Intelligence Page**
| Visual Type          | Data Source           | Configuration                          |
|----------------------|-----------------------|----------------------------------------|
| Donut Chart          | DIM_Vehicles          | Legend: Status, Values: Count          |
| Scatter Chart        | DIM_Vehicles + Facts  | X: Age, Y: Maint Count, Color: Status  |
| Stacked Bar          | FACT_Maintenance      | Category: Severity, Values: Cost       |
| Table                | TOP N Vehicles        | OrderBy: Total Cost DESC, Top 10       |

### **Workforce Intelligence Page**
| Visual Type          | Data Source           | Configuration                          |
|----------------------|-----------------------|----------------------------------------|
| Sankey Diagram       | DIM_Employees         | Source: Dept, Target: Project          |
| Violin Plot          | DIM_Employees         | Category: Dept, Distribution: Salary   |
| Calendar Heatmap     | FACT_Attendance       | Rows: Week, Columns: Day, Color: Rate  |
| Forecast Line        | FACT_Financials       | Analytics: Forecast 1 month ahead      |

---

## 🎯 Interactive Features

### **1. Slicers (Filters)**
```
┌──────────────────────────────────────┐
│  📅 Date Range                       │
│  [Jan 2026] ──────────── [May 2026] │
├──────────────────────────────────────┤
│  🗺️ Region (Multi-select)           │
│  ☑ Riyadh  ☑ Jeddah  ☑ Dammam      │
│  ☐ Makkah  ☐ Qassim  ☐ Tabuk        │
├──────────────────────────────────────┤
│  🏢 Department (Dropdown)            │
│  [All Departments ▼]                 │
└──────────────────────────────────────┘
```

### **2. Drill-Through Pages**
- **Employee Details**: Right-click any employee → Drill through
  - Shows: Full profile, salary history, attendance breakdown
- **Vehicle Details**: Right-click any vehicle → Drill through
  - Shows: Maintenance history, cost trend, current status

### **3. Tooltips (Custom)**
When hovering over charts:
```
┌────────────────────────────────────┐
│  Employee: Ahmed Al-Mutairi        │
│  ─────────────────────────────────│
│  Department: Operations            │
│  Project: Alpha                    │
│  Salary: 7,500 SAR/month           │
│  Attendance: 96.5% (Last 30 days)  │
└────────────────────────────────────┘
```

### **4. Bookmarks**
- **View 1**: Executive Summary (Default)
- **View 2**: Financial Deep Dive
- **View 3**: Fleet Focus
- **View 4**: HR Analytics
- **View 5**: Regional Comparison

---

## 🚀 Advanced Features

### **1. R/Python Integration**
```python
# Correlation Matrix (Python Visual)
import matplotlib.pyplot as plt
import seaborn as sns

corr_matrix = dataset[['salary', 'attendance_rate', 'project_count']].corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm')
plt.show()
```

### **2. AI Insights**
Enable "Analyze" feature on visuals:
- Automatic anomaly detection
- Key drivers of salary increase
- Trend explanations

### **3. Q&A Natural Language**
Users can ask:
- "What is the average salary in Riyadh?"
- "Show me vehicles older than 5 years"
- "Which department has the highest attendance?"

---

## 📱 Mobile Layout Optimization

```
┌──────────────┐
│ 📱 MOBILE    │
│ ────────────│
│  KPI Cards   │
│  (Vertical)  │
│              │
│  💰 1.2M SAR │
│  🚛 85.5%    │
│  👥 92 EMP   │
│  ✓ 94.2%     │
│              │
│  [Tap for    │
│   Details]   │
└──────────────┘
```

---

## 📧 Report Subscriptions

### **Email Schedule**
- **Daily**: 8 AM - KPI Summary (Text only)
- **Weekly**: Monday 9 AM - Full Dashboard (PDF)
- **Monthly**: 1st of month - Executive Report (PDF + Excel)

### **Recipients**
- CEO / General Manager
- CFO / Finance Director
- Operations Manager
- Fleet Manager
- HR Director

---

## 🔐 Security & Permissions

### **Row-Level Security (RLS)**
```dax
// Regional Managers see only their region
[Region] = USERNAME()

// Department Heads see only their department
[Department] = USERPRINCIPALNAME()
```

### **Access Levels**
1. **Executive View**: Full access, all pages
2. **Manager View**: Department/Region filtered
3. **Read-Only**: View only, no export

---

## 📊 Performance Optimization

### **Best Practices**
1. Use **Aggregations** for large fact tables
2. Enable **Query Folding** in Power Query
3. Create **Composite Models** for DirectQuery
4. Implement **Incremental Refresh** (monthly partitions)
5. Optimize DAX with **Variables** and **CALCULATE**

### **Expected Performance**
- Initial Load: <5 seconds
- Slicer Interaction: <1 second
- Drill-through: <2 seconds
- Export to PDF: <10 seconds

---

## 🎓 Training Resources

### **For Analysts**
- Power BI Desktop basics (2 hours)
- DAX fundamentals (4 hours)
- Data modeling (3 hours)

### **For Executives**
- Dashboard navigation (30 minutes)
- Interactive features (30 minutes)
- Mobile app usage (15 minutes)

---

**Document Version:** 1.0  
**Last Updated:** February 19, 2026  
**Author:** Nuzum BI Team  
**Contact:** analytics@nuzum.com
