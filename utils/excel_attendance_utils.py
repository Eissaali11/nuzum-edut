from .excel_base import ExcelStyles
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
from utils.date_converter import parse_date, format_date_gregorian, format_date_hijri
from calendar import monthrange
import xlsxwriter
def export_employee_attendance_to_excel(employee, month=None, year=None):
    """
    تصدير بيانات الحضور لموظف معين إلى ملف إكسل
    
    Args:
        employee: كائن الموظف
        month: الشهر (اختياري)
        year: السنة (اختياري)
        
    Returns:
        BytesIO object containing the Excel file
    """
    try:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # اختصار اسم ورقة Excel لتكون أقل من 31 حرفاً (الحد الأقصى المسموح به)
        sheet_name = f"Attendance-{employee.employee_id}"
        worksheet = workbook.add_worksheet(sheet_name)
        ExcelStyles.apply_rtl(worksheet, engine="xlsxwriter")
        
        # تنسيقات الخلايا
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })
        
        date_header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'text_wrap': True  # لسماح النص بالانتقال للسطر التالي
        })
        
        normal_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })
        
        present_format = workbook.add_format({
            'align': 'center',
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
            'border': 1
        })
        
        absent_format = workbook.add_format({
            'align': 'center',
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006',
            'border': 1
        })
        
        leave_format = workbook.add_format({
            'align': 'center',
            'bg_color': '#FFEB9C',
            'font_color': '#9C5700',
            'border': 1
        })
        
        sick_format = workbook.add_format({
            'align': 'center',
            'bg_color': '#FFCC99',
            'font_color': '#974706',
            'border': 1
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # تحديد الشهر والسنة إذا لم يتم توفيرهما
        current_date = datetime.now()
        if not year:
            year = current_date.year
        if not month:
            month = current_date.month
            
        # الحصول على عدد أيام الشهر
        _, days_in_month = monthrange(year, month)
        
        # إنشاء عنوان الملف
        title = f"سجل حضور {employee.name}"
        
        # إضافة عنوان
        worksheet.merge_range('A1:H1', title, title_format)
        
        # تحديد أسماء الأعمدة الثابتة وترتيبها كما في الصورة
        col_headers = ["Name", "ID Number", "Emp. No.", "Job Title", "Location", "Project", "Total"]
        
        # كتابة العناوين الرئيسية
        for col_idx, header in enumerate(col_headers):
            worksheet.write(2, col_idx, header, header_format)
        
        # تحديد نطاق التواريخ للشهر المحدد
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # استخدام استعلام أكثر فعالية للحصول على سجلات الحضور
        from core.extensions import db
        from models import Attendance
        
        # استعلام من قاعدة البيانات مباشرة
        attendances = db.session.query(Attendance).filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date).all()
        
        # تخزين بيانات الحضور في قاموس للوصول السريع وإنشاء قائمة بالتواريخ الفعلية للحضور
        attendance_data = {}
        date_list = []  # فقط التواريخ التي يوجد بها سجلات حضور
        
        for attendance in attendances:
            # تخزين معلومات الحضور
            attendance_data[attendance.date] = {
                'status': attendance.status,
                'notes': attendance.notes if hasattr(attendance, 'notes') else None
            }
            # إضافة التاريخ إلى قائمة التواريخ
            date_list.append(attendance.date)
        
        # إعداد أيام الأسبوع
        weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        # كتابة عناوين أيام الأسبوع
        first_date_col = len(col_headers)
        
        # إنشاء الصف الأول بعناوين أيام الأسبوع
        for col_idx, date in enumerate(date_list):
            # تنسيق عنوان اليوم ليظهر كما في الصورة المرفقة: يوم الأسبوع مع التاريخ (مثال: Mon 01/04/2025)
            day_of_week = weekdays[date.weekday()]
            date_str = date.strftime("%d/%m/%Y")
            day_header = f"{day_of_week}\n{date_str}"
            
            col = first_date_col + col_idx
            worksheet.write(2, col, day_header, date_header_format)
        
        # كتابة معلومات الموظف والحضور
        row = 3  # البدء من الصف الرابع بعد عنوان الجدول
        
        # استخراج معلومات لموقع العمل والمشروع
        location = "AL QASSIM"  # قيمة افتراضية أو استخراجها من الموظف
        if hasattr(employee, 'departments') and employee.departments:
            location = employee.departments[0].name[:20]  # استخدام اسم أول قسم كموقع
            
        project = "ARAMEX"  # قيمة افتراضية، يمكن استخراجها من بيانات الموظف
        
        # عدد الحضور
        present_days = 0
        
        # كتابة معلومات الموظف
        worksheet.write(row, 0, employee.name, normal_format)  # Name
        worksheet.write(row, 1, employee.national_id or "", normal_format)  # ID Number
        worksheet.write(row, 2, employee.employee_id or "", normal_format)  # Emp. No.
        worksheet.write(row, 3, employee.job_title or "courier", normal_format)  # Job Title
        worksheet.write(row, 4, location, normal_format)  # Location
        worksheet.write(row, 5, project, normal_format)  # Project
        
        # كتابة سجلات الحضور لكل يوم
        for col_idx, date in enumerate(date_list):
            col = first_date_col + col_idx  # بداية أعمدة التواريخ
            cell_value = ""  # القيمة الافتراضية فارغة
            cell_format = normal_format
            
            if date in attendance_data:
                att_data = attendance_data[date]
                
                if att_data['status'] == 'present':
                    cell_value = "P"  # استخدام حرف P للحضور
                    cell_format = present_format
                    present_days += 1
                elif att_data['status'] == 'absent':
                    cell_value = "A"  # استخدام حرف A للغياب
                    cell_format = absent_format
                elif att_data['status'] == 'leave':
                    cell_value = "L"  # استخدام حرف L للإجازة
                    cell_format = leave_format
                elif att_data['status'] == 'sick':
                    cell_value = "S"  # استخدام حرف S للمرض
                    cell_format = sick_format
            # لا نحتاج للحالة else هنا لأن date_list تحتوي فقط على التواريخ التي لها سجلات حضور فعلية
            
            worksheet.write(row, col, cell_value, cell_format)
        
        # كتابة إجمالي أيام الحضور
        worksheet.write(row, 6, present_days, normal_format)  # Total
        
        # إضافة تفسير للرموز المستخدمة في صفحة منفصلة
        legend_sheet = workbook.add_worksheet('دليل الرموز')
        
        # تنسيق العناوين
        legend_title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # تنسيق الشرح
        description_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        # كتابة العنوان
        legend_sheet.merge_range('A1:B1', 'دليل رموز الحضور والغياب', legend_title_format)
        
        # ضبط عرض الأعمدة
        legend_sheet.set_column(0, 0, 10)
        legend_sheet.set_column(1, 1, 40)
        
        # إضافة تفسير الرموز
        legend_sheet.write(2, 0, 'P', present_format)
        legend_sheet.write(2, 1, 'حاضر (Present)', description_format)
        
        legend_sheet.write(3, 0, 'A', absent_format)
        legend_sheet.write(3, 1, 'غائب (Absent)', description_format)
        
        legend_sheet.write(4, 0, 'L', leave_format)
        legend_sheet.write(4, 1, 'إجازة (Leave)', description_format)
        
        legend_sheet.write(5, 0, 'S', sick_format)
        legend_sheet.write(5, 1, 'مرضي (Sick Leave)', description_format)
        
        # ضبط عرض الأعمدة في الصفحة الرئيسية
        worksheet.set_column(0, 0, 30)  # عمود الاسم
        worksheet.set_column(1, 1, 15)  # عمود ID Number
        worksheet.set_column(2, 2, 10)  # عمود Emp. No.
        worksheet.set_column(3, 3, 15)  # عمود Job Title
        worksheet.set_column(4, 4, 13)  # عمود Location
        worksheet.set_column(5, 5, 13)  # عمود Project
        worksheet.set_column(6, 6, 8)   # عمود Total
        worksheet.set_column(first_date_col, first_date_col + len(date_list) - 1, 5)  # أعمدة التواريخ
        
        workbook.close()
        output.seek(0)
        return output
        
    except Exception as e:
        import traceback
        print(f"Error generating employee attendance Excel file: {str(e)}")
        print(traceback.format_exc())
        raise

def export_attendance_by_department(employees, attendances, start_date, end_date=None):
    """
    تصدير بيانات الحضور إلى ملف إكسل في صيغة جدول
    حيث تكون معلومات الموظفين في الأعمدة الأولى
    وتواريخ الحضور في الأعمدة الباقية مع استخدام P للحضور

    Args:
        employees: قائمة بجميع الموظفين
        attendances: قائمة بسجلات الحضور
        start_date: تاريخ البداية
        end_date: تاريخ النهاية (اختياري، إذا لم يتم تحديده سيتم استخدام تاريخ البداية فقط)

    Returns:
        BytesIO: كائن يحتوي على ملف اكسل
    """
    try:
        output = BytesIO()
        
        # إنشاء ملف إكسل جديد باستخدام xlsxwriter
        workbook = xlsxwriter.Workbook(output)
        
        # تعريف التنسيقات
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#00B0B0',  # لون أخضر فاتح مائل للأزرق
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        date_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#00B0B0',  # لون أخضر فاتح مائل للأزرق
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        normal_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        right_aligned_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })
        
        present_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'font_color': '#006100'  # اللون الأخضر لحرف P
        })
        
        absent_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'font_color': '#FF0000'  # اللون الأحمر لحرف A
        })
        
        leave_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#FF9900'  # اللون البرتقالي لحرف L
        })
        
        sick_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#0070C0'  # اللون الأزرق لحرف S
        })
        
        # تحديد الفترة الزمنية
        if end_date is None:
            end_date = start_date
        
        # تحديد قائمة التواريخ
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        
        # تنظيم الموظفين حسب الأقسام
        departments = {}
        for employee in employees:
            dept_name = ', '.join([dept.name for dept in employee.departments]) if employee.departments else 'بدون قسم'
            if dept_name not in departments:
                departments[dept_name] = []
            departments[dept_name].append(employee)
        
        # تنظيم بيانات الحضور حسب الموظفين
        attendance_data = {}
        for attendance in attendances:
            emp_id = attendance.employee_id
            if emp_id not in attendance_data:
                attendance_data[emp_id] = {}
            
            # تخزين حالة الحضور لهذا اليوم
            attendance_data[emp_id][attendance.date] = {
                'status': attendance.status
            }
        
        # عمل قائمة بأيام الأسبوع للعناوين
        weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        # إنشاء ورقة عمل لكل قسم
        for dept_name, dept_employees in departments.items():
            # تحويل الاسم ليكون صالحًا كاسم ورقة Excel
            sheet_name = dept_name[:31]  # Excel يدعم حد أقصى 31 حرف لأسماء الأوراق
            worksheet = workbook.add_worksheet(sheet_name)
            ExcelStyles.apply_rtl(worksheet, engine="xlsxwriter")

            # تحديد أسماء الأعمدة الثابتة وترتيبها كما في الصورة
            col_headers = ["Name", "ID Number", "Emp. No.", "Job Title", "No. Mobile", "Car", "Location", "Project", "Total"]
            
            # كتابة العناوين الرئيسية
            for col_idx, header in enumerate(col_headers):
                worksheet.write(1, col_idx, header, header_format)
            
            # كتابة عناوين أيام الأسبوع
            first_date_col = len(col_headers)
            
            # إنشاء الصف الأول بعناوين أيام الأسبوع
            for col_idx, date in enumerate(date_list):
                # تنسيق عنوان اليوم ليظهر كما في الصورة المرفقة: يوم الأسبوع مع التاريخ (مثال: Mon 01/04/2025)
                day_of_week = weekdays[date.weekday()]
                date_str = date.strftime("%d/%m/%Y")
                day_header = f"{day_of_week}\n{date_str}"
                
                col = first_date_col + col_idx
                worksheet.write(0, col, day_header, date_header_format)
                
                # لم نعد بحاجة لكتابة التاريخ في صف منفصل لأننا دمجناه مع اسم اليوم
            
            # ضبط عرض الأعمدة
            worksheet.set_column(0, 0, 30)  # عمود الاسم
            worksheet.set_column(1, 1, 15)  # عمود ID Number
            worksheet.set_column(2, 2, 10)  # عمود Emp. No.
            worksheet.set_column(3, 3, 15)  # عمود Job Title
            worksheet.set_column(4, 4, 15)  # عمود No. Mobile
            worksheet.set_column(5, 5, 13)  # عمود Car
            worksheet.set_column(6, 6, 13)  # عمود Location
            worksheet.set_column(7, 7, 13)  # عمود Project
            worksheet.set_column(8, 8, 8)   # عمود Total
            worksheet.set_column(first_date_col, first_date_col + len(date_list) - 1, 5)  # أعمدة التواريخ
            
            # كتابة بيانات الموظفين وسجلات الحضور
            for row_idx, employee in enumerate(sorted(dept_employees, key=lambda e: e.name)):
                row = row_idx + 2  # صف البيانات (بعد صفي العناوين)
                
                # استخراج رقم الهاتف من المعلومات الإضافية إن وجد
                phone_number = ""
                if hasattr(employee, 'phone'):
                    phone_number = employee.phone
                
                # كتابة معلومات الموظف
                worksheet.write(row, 0, employee.name, normal_format)  # Name
                worksheet.write(row, 1, employee.national_id or "", normal_format)  # ID Number
                worksheet.write(row, 2, employee.employee_id or "", normal_format)  # Emp. No.
                worksheet.write(row, 3, employee.job_title or "courier", normal_format)  # Job Title
                worksheet.write(row, 4, phone_number, normal_format)  # No. Mobile
                
                # معلومات إضافية (قد تحتاج لتكييفها حسب هيكل البيانات الفعلي)
                car = ""  # يمكن إضافة منطق لاستخراج رقم السيارة إن وجد
                worksheet.write(row, 5, car, normal_format)  # Car
                
                # أحضر اسم الموقع من القسم
                location = "AL QASSIM"  # قيمة افتراضية أو استخراجها من الموظف
                if employee.departments:
                    location = employee.departments[0].name[:20]  # استخدام اسم أول قسم كموقع
                worksheet.write(row, 6, location, normal_format)  # Location
                
                # اسم المشروع
                project = "ARAMEX"  # قيمة افتراضية، يمكن استخراجها من بيانات الموظف
                worksheet.write(row, 7, project, normal_format)  # Project
                
                # عداد للحضور
                present_days = 0
                
                # كتابة سجلات الحضور لكل يوم
                for col_idx, date in enumerate(date_list):
                    col = first_date_col + col_idx  # بداية أعمدة التواريخ
                    cell_value = ""  # القيمة الافتراضية فارغة
                    cell_format = normal_format
                    
                    if employee.id in attendance_data and date in attendance_data[employee.id]:
                        att_data = attendance_data[employee.id][date]
                        
                        if att_data['status'] == 'present':
                            cell_value = "P"  # استخدام حرف P للحضور
                            cell_format = present_format
                            present_days += 1
                        elif att_data['status'] == 'absent':
                            cell_value = "A"  # استخدام حرف A للغياب
                            cell_format = absent_format
                        elif att_data['status'] == 'leave':
                            cell_value = "L"  # استخدام حرف L للإجازة
                            cell_format = leave_format
                        elif att_data['status'] == 'sick':
                            cell_value = "S"  # استخدام حرف S للمرض
                            cell_format = sick_format
                    else:
                        # إذا لم يوجد سجل لهذا اليوم، نفترض أنه حاضر (كما في الصورة المرفقة)
                        cell_value = "P"
                        cell_format = present_format
                        present_days += 1
                    
                    worksheet.write(row, col, cell_value, cell_format)
                
                # كتابة إجمالي أيام الحضور
                worksheet.write(row, 8, present_days, normal_format)  # Total
        
        # إضافة تفسير للرموز المستخدمة في صفحة منفصلة
        legend_sheet = workbook.add_worksheet('دليل الرموز')
        
        # تنسيق العناوين
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # تنسيق الشرح
        description_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        # كتابة العنوان
        legend_sheet.merge_range('A1:B1', 'دليل رموز الحضور والغياب', title_format)
        
        # ضبط عرض الأعمدة
        legend_sheet.set_column(0, 0, 10)
        legend_sheet.set_column(1, 1, 40)
        
        # إضافة تفسير الرموز
        legend_sheet.write(2, 0, 'P', present_format)
        legend_sheet.write(2, 1, 'حاضر (Present)', description_format)
        
        legend_sheet.write(3, 0, 'A', absent_format)
        legend_sheet.write(3, 1, 'غائب (Absent)', description_format)
        
        legend_sheet.write(4, 0, 'L', leave_format)
        legend_sheet.write(4, 1, 'إجازة (Leave)', description_format)
        
        legend_sheet.write(5, 0, 'S', sick_format)
        legend_sheet.write(5, 1, 'مرضي (Sick Leave)', description_format)
        
        # إغلاق الملف وإعادة المخرجات
        workbook.close()
        output.seek(0)
        return output
    
    except Exception as e:
        import traceback
        print(f"Error generating attendance Excel file: {str(e)}")
        print(traceback.format_exc())
        raise
