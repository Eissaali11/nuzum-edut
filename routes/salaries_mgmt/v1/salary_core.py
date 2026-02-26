"""salary_core.py - decomposed salaries routes."""

from .salary_base import *

@salaries_bp.route('/')
def index():
    """عرض سجلات الرواتب مع خيارات التصفية"""
    # الحصول على الشهر والسنة الحالية
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # الحصول على بيانات التصفية من الطلب
    month = request.args.get('month', None)
    year = request.args.get('year', None)
    employee_id = request.args.get('employee_id', '')
    department_id = request.args.get('department_id', '')
    
    # إذا تم تحديد قيمة خالية للشهر أو السنة، فهذا يعني تصفية كل الشهور أو كل السنوات
    show_all_months = month == ''  # اختار المستخدم "جميع الشهور" بشكل صريح
    show_all_years = year == ''    # اختار المستخدم "جميع السنوات" بشكل صريح
    
    # البحث عن الشهر والسنة التي تحتوي على بيانات إذا لم يتم تحديدها (فقط إذا لم يطلب المستخدم كل الشهور أو كل السنوات)
    if (not month and not show_all_months) or (not year and not show_all_years):
        # محاولة العثور على آخر شهر/سنة يحتوي على بيانات
        latest_salary = Salary.query.order_by(Salary.year.desc(), Salary.month.desc()).first()
        if latest_salary:
            # تحديد قيم افتراضية فقط إذا لم يطلب المستخدم "جميع..." بشكل صريح
            if not month and not show_all_months:
                month = str(latest_salary.month)
            if not year and not show_all_years:
                year = str(latest_salary.year)
        else:
            # إذا لم توجد بيانات، استخدم الشهر والسنة الحالية
            if not month and not show_all_months:
                month = str(current_month)
            if not year and not show_all_years:
                year = str(current_year)
    
    # بناء استعلام قاعدة البيانات
    salaries = []
    employee_records = []
    try:
        # استخدام القيم الافتراضية في حالة عدم وجود قيم في الرابط
        filter_month = int(month) if month and month.isdigit() else current_month
        filter_year = int(year) if year and year.isdigit() else current_year
        filter_employee = int(employee_id) if employee_id and employee_id.isdigit() else None
        filter_department = int(department_id) if department_id and department_id.isdigit() else None
        
        # بناء الاستعلام الأساسي
        query = Salary.query
        
        # إضافة فلتر الشهر (فقط إذا لم يطلب المستخدم كل الشهور)
        if not show_all_months:
            query = query.filter(Salary.month == filter_month)
            
        # إضافة فلتر السنة (فقط إذا لم يطلب المستخدم كل السنوات)
        if not show_all_years:
            query = query.filter(Salary.year == filter_year)
        
        # إضافة تصفية الموظف إذا تم تحديدها
        if filter_employee:
            query = query.filter(Salary.employee_id == filter_employee)
            
        # إضافة تصفية القسم إذا تم تحديدها
        if filter_department:
            # هنا نقوم بعمل join مع جدول الموظفين ثم الأقسام للفلترة
            query = query.join(Employee).join(Employee.departments).filter(Department.id == filter_department)
        
        # تنفيذ الاستعلام
        salaries = query.all()
        
        # **منطق معالجة عرض الموظفين بدون رواتب**
        # نريد أن نعرض موظفين للإدخال في الحالات التالية:
        # 1. عدم وجود رواتب للشهر والسنة المحددين
        # 2. عرض جميع الشهور 
        # 3. تم تحديد قسم معين (لإظهار موظفيه حتى لو لم تكن لديهم رواتب)
        # ولكن ليس إذا تم تحديد موظف معين
        should_show_employees_for_input = (not filter_employee) and (
            not salaries or  # لا توجد رواتب
            show_all_months or  # عرض جميع الشهور
            filter_department  # تم تحديد قسم معين
        )
        
        if should_show_employees_for_input:
            # الحصول على قائمة الموظفين النشطين
            active_employees_query = Employee.query.filter_by(status='active')
            
            # إذا تم تحديد قسم، قم بتصفية الموظفين حسب القسم
            if filter_department:
                active_employees_query = active_employees_query.join(Employee.departments).filter(Department.id == filter_department)
                
            active_employees = active_employees_query.all()
            
            # معالجة حالات الفلترة المختلفة
            if show_all_months and show_all_years:
                # عرض جميع الشهور وجميع السنوات - عرض جميع السجلات وإضافة الموظفين الذين ليس لديهم سجلات
                # في هذه الحالة نعتمد على السجلات المجمعة مما ورد من قاعدة البيانات
                print(f"تم العثور على {len(salaries)} سجل في جميع الشهور وجميع السنوات")
                
                # إضافة الموظفين الذين ليس لديهم سجلات على الإطلاق
                if filter_department:
                    # إذا تم تحديد قسم، أحضر الموظفين الذين ليس لديهم أي سجلات راتب في هذا القسم
                    employee_ids_with_salaries = db.session.query(Salary.employee_id).join(Employee).join(Employee.departments).filter(Department.id == filter_department).distinct().all()
                else:
                    # إذا لم يتم تحديد قسم، أحضر كل الموظفين الذين ليس لديهم سجلات راتب
                    employee_ids_with_salaries = db.session.query(Salary.employee_id).distinct().all()
                employee_ids_with_salaries_set = {id[0] for id in employee_ids_with_salaries}
                employees_without_salaries = [e for e in active_employees if e.id not in employee_ids_with_salaries_set]
                
                for employee in employees_without_salaries:
                    temp_salary = Salary(
                        employee_id=employee.id,
                        employee=employee,
                        month=1,  # شهر افتراضي
                        year=current_year,  # سنة افتراضية (الحالية)
                        basic_salary=0,
                        allowances=0,
                        deductions=0,
                        bonus=0,
                        net_salary=0
                    )
                    employee_records.append(temp_salary)
                
            elif show_all_months and not show_all_years:
                # عرض جميع الشهور لسنة محددة
                # الحصول على قائمة الموظفين الذين لديهم رواتب في السنة المحددة
                salary_query = db.session.query(Salary.employee_id).filter(Salary.year == filter_year)
                if filter_department:
                    salary_query = salary_query.join(Employee).join(Employee.departments).filter(Department.id == filter_department)
                employee_ids_with_salaries = salary_query.distinct().all()
                
                # تحويل القائمة إلى مجموعة (set) للبحث بسرعة
                employee_ids_with_salaries_set = {id[0] for id in employee_ids_with_salaries}
                
                # إنشاء قائمة بالموظفين الذين ليس لديهم رواتب في السنة المحددة
                employees_without_salaries = [e for e in active_employees if e.id not in employee_ids_with_salaries_set]
                
                # إذا كان هناك موظفين بدون رواتب، قم بإنشاء سجلات مؤقتة لهم
                for employee in employees_without_salaries:
                    # إنشاء كائن راتب مؤقت فقط لأغراض العرض (لن يتم حفظه)
                    temp_salary = Salary(
                        employee_id=employee.id,
                        employee=employee,
                        month=1,  # شهر افتراضي
                        year=filter_year,
                        basic_salary=0,
                        allowances=0,
                        deductions=0,
                        bonus=0,
                        net_salary=0
                    )
                    employee_records.append(temp_salary)
                
                print(f"تم العثور على {len(salaries)} سجل راتب للسنة {filter_year} مع {len(employee_records)} موظف بدون رواتب")
                
            elif not show_all_months and show_all_years:
                # عرض شهر محدد لجميع السنوات
                # هنا نبحث عن الموظفين الذين ليس لديهم سجلات في هذا الشهر بغض النظر عن السنة
                employee_ids_with_salaries = db.session.query(Salary.employee_id).filter(
                    Salary.month == filter_month
                ).distinct().all()
                
                employee_ids_with_salaries_set = {id[0] for id in employee_ids_with_salaries}
                employees_without_salaries = [e for e in active_employees if e.id not in employee_ids_with_salaries_set]
                
                for employee in employees_without_salaries:
                    temp_salary = Salary(
                        employee_id=employee.id,
                        employee=employee,
                        month=filter_month,
                        year=current_year,  # سنة افتراضية (الحالية)
                        basic_salary=0,
                        allowances=0,
                        deductions=0,
                        bonus=0,
                        net_salary=0
                    )
                    employee_records.append(temp_salary)
                    
                print(f"تم العثور على {len(salaries)} سجل راتب للشهر {filter_month} في جميع السنوات مع {len(employee_records)} موظف بدون سجلات")
            else:
                # إنشاء كائنات مؤقتة لعرض الموظفين بدون رواتب للشهر المحدد
                # احصل على معرفات الموظفين الذين لديهم رواتب في هذا الشهر والسنة
                employee_ids_with_salaries = {s.employee_id for s in salaries}
                
                for employee in active_employees:
                    # إذا لم يكن لديه راتب في هذا الشهر والسنة، أضف سجل مؤقت
                    if employee.id not in employee_ids_with_salaries:
                        temp_salary = Salary(
                            employee_id=employee.id,
                            employee=employee,
                            month=filter_month,
                            year=filter_year,
                            basic_salary=0,
                            allowances=0,
                            deductions=0,
                            bonus=0,
                            net_salary=0
                        )
                        employee_records.append(temp_salary)
                
                if len(salaries) == 0:
                    print(f"لا توجد سجلات رواتب للشهر {filter_month} والسنة {filter_year}. تم إنشاء {len(employee_records)} سجل مؤقت للموظفين النشطين")
                else:
                    print(f"تم العثور على {len(salaries)} سجل راتب للشهر {filter_month} والسنة {filter_year}. تم إنشاء {len(employee_records)} سجل مؤقت للموظفين الآخرين")
        else:
            if show_all_months and show_all_years:
                print(f"تم العثور على {len(salaries)} سجل في جميع الشهور والسنوات")
            elif show_all_months and not show_all_years:
                print(f"تم العثور على {len(salaries)} سجل في جميع الشهور للسنة {filter_year}")
            elif not show_all_months and show_all_years:
                print(f"تم العثور على {len(salaries)} سجل للشهر {filter_month} في جميع السنوات")
            else:
                print(f"تم العثور على {len(salaries)} سجل للشهر {filter_month} والسنة {filter_year}")
    except Exception as e:
        print(f"خطأ في استرجاع بيانات الرواتب: {str(e)}")
        flash(f'حدث خطأ أثناء استرجاع بيانات الرواتب: {str(e)}', 'danger')
    
    # حساب قيمة التأمينات (GOSI) للعرض والشفافية
    for salary_record in salaries:
        gosi_info = calculate_gosi_deduction(
            basic_salary=salary_record.basic_salary,
            nationality=getattr(salary_record.employee, 'nationality', None),
            contract_type=getattr(salary_record.employee, 'contract_type', None)
        )
        salary_record.gosi_deduction_display = gosi_info['gosi_deduction']

    # حساب الإحصائيات
    total_basic = sum(s.basic_salary for s in salaries)
    total_allowances = sum(s.allowances for s in salaries)
    total_deductions = sum(s.deductions for s in salaries)
    total_gosi = sum(getattr(s, 'gosi_deduction_display', 0) for s in salaries)
    total_bonus = sum(s.bonus for s in salaries)
    total_net = sum(s.net_salary for s in salaries)
    
    # Get all employees for filter dropdown
    employees = Employee.query.filter_by(status='active').all()
    
    # Get all departments for filter dropdown
    departments = Department.query.order_by(Department.name).all()
    
    # Get available months and years for dropdown
    # عرض جميع الشهور (1-12) بغض النظر عن وجودها في قاعدة البيانات
    available_months = [(i,) for i in range(1, 13)]
    
    # إضافة عدة سنوات ثابتة (3 سنوات سابقة + السنة الحالية + 2 سنوات قادمة)
    fixed_years = [(current_year + i,) for i in range(-3, 3)]  # مثلا: 2022, 2023, 2024, 2025, 2026, 2027
    
    # الحصول على السنوات المتاحة من قاعدة البيانات
    db_years = db.session.query(Salary.year).distinct().order_by(Salary.year.desc()).all()
    
    # دمج السنوات الثابتة مع السنوات الموجودة في قاعدة البيانات وإزالة التكرار
    all_years = set(fixed_years + db_years)
    
    # ترتيب السنوات تنازليًا
    available_years = sorted(list(all_years), reverse=True)
    
    # معالجة السجلات المؤقتة والفعلية لعرضها
    if show_all_months:
        # في حالة "جميع الشهور"، نعرض السجلات الفعلية مع السجلات المؤقتة للموظفين الذين ليس لهم سجلات
        display_records = list(salaries) + employee_records
    else:
        # في حالة الشهر المحدد، عرض السجلات الفعلية مع السجلات المؤقتة للموظفين الآخرين
        display_records = list(salaries) + employee_records
        
    return render_template('salaries/index.html',
                          salaries=display_records,
                          has_salary_data=(len(salaries) > 0),  # علامة توضح ما إذا كانت هناك بيانات رواتب فعلية
                          employees=employees,
                          departments=departments,
                          available_months=available_months,
                          available_years=available_years,
                          selected_month=month,
                          selected_year=year,
                          selected_employee=employee_id,
                          selected_department=department_id,
                          total_basic=total_basic,
                          total_allowances=total_allowances,
                          total_deductions=total_deductions,
                          total_gosi=total_gosi,
                          total_bonus=total_bonus,
                          total_net=total_net)

@salaries_bp.route('/report')
def report():
    """Generate a salary report for a specific month and year"""
    # Get filter parameters
    month = request.args.get('month', str(datetime.now().month))
    year = request.args.get('year', str(datetime.now().year))
    
    # Validate parameters
    if not month.isdigit() or not year.isdigit():
        flash('يرجى اختيار شهر وسنة صالحين', 'danger')
        return redirect(url_for('salaries.index'))
    
    month = int(month)
    year = int(year)
    
    # Get salary records for the selected month and year
    salaries = Salary.query.filter_by(month=month, year=year).all()
    
    if not salaries:
        flash('لا توجد سجلات رواتب للشهر والسنة المحددين', 'warning')
        return redirect(url_for('salaries.index'))
    
    # Get summary statistics
    for salary_record in salaries:
        gosi_info = calculate_gosi_deduction(
            basic_salary=salary_record.basic_salary,
            nationality=getattr(salary_record.employee, 'nationality', None),
            contract_type=getattr(salary_record.employee, 'contract_type', None)
        )
        salary_record.gosi_deduction_display = gosi_info['gosi_deduction']

    total_basic = sum(s.basic_salary for s in salaries)
    total_allowances = sum(s.allowances for s in salaries)
    total_deductions = sum(s.deductions for s in salaries)
    total_gosi = sum(getattr(s, 'gosi_deduction_display', 0) for s in salaries)
    total_bonus = sum(s.bonus for s in salaries)
    total_net = sum(s.net_salary for s in salaries)
    
    return render_template('salaries/report.html',
                          salaries=salaries,
                          month=month,
                          year=year,
                          total_basic=total_basic,
                          total_allowances=total_allowances,
                          total_deductions=total_deductions,
                          total_gosi=total_gosi,
                          total_bonus=total_bonus,
                          total_net=total_net)

