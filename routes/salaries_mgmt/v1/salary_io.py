"""salary_io.py - decomposed salaries routes."""

from .salary_base import *

@salaries_bp.route('/import', methods=['GET', 'POST'])
def import_excel():
    """Import salary records from Excel file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        
        month = int(request.form['month'])
        year = int(request.form['year'])
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                # Parse Excel file
                salaries_data = parse_salary_excel(file, month, year)
                success_count = 0
                error_count = 0
                
                for data in salaries_data:
                    try:
                        # تنظيف رقم الموظف المستورد (إزالة الأصفار الزائدة والمسافات)
                        employee_id_str = str(data['employee_id']).strip()
                        
                        # محاولة البحث عن الموظف بأكثر من طريقة
                        # 1. البحث المباشر
                        employee = Employee.query.filter_by(employee_id=employee_id_str).first()
                        
                        # 2. البحث بعد إزالة الأصفار من البداية
                        if not employee:
                            clean_id = employee_id_str.lstrip('0')
                            employee = Employee.query.filter_by(employee_id=clean_id).first()
                            
                        # 3. البحث بإضافة أصفار للبداية (حتى 6 أرقام إجمالاً)
                        if not employee:
                            padded_id = employee_id_str.zfill(6)
                            employee = Employee.query.filter_by(employee_id=padded_id).first()
                            
                        # 4. البحث باستخدام like للعثور على تطابق جزئي
                        if not employee:
                            employee = Employee.query.filter(
                                Employee.employee_id.like(f"%{employee_id_str}%")
                            ).first()
                            
                        if not employee:
                            print(f"لم يتم العثور على موظف برقم: {data['employee_id']} بعد محاولة البحث بعدة طرق")
                            raise ValueError(f"لم يتم العثور على موظف برقم: {data['employee_id']}")
                            
                        # التحقق من وجود سجل راتب لهذا الموظف في نفس الشهر والسنة
                        existing = Salary.query.filter_by(
                            employee_id=employee.id,  # استخدام معرف الموظف في قاعدة البيانات
                            month=month,
                            year=year
                        ).first()
                        
                        # تحضير بيانات الراتب
                        salary_data = {
                            'employee_id': employee.id,  # معرف الموظف في قاعدة البيانات وليس رقم الموظف
                            'month': month,
                            'year': year,
                            'basic_salary': data['basic_salary'],
                            'allowances': data['allowances'],
                            'deductions': data['deductions'],
                            'bonus': data['bonus'],
                            'net_salary': data['net_salary']
                        }

                        salary_breakdown = compute_net_salary(
                            basic_salary=salary_data['basic_salary'],
                            allowances=salary_data['allowances'],
                            bonus=salary_data['bonus'],
                            deductions=salary_data['deductions'],
                            nationality=getattr(employee, 'nationality', None),
                            contract_type=getattr(employee, 'contract_type', None),
                            return_breakdown=True
                        )
                        salary_data['deductions'] = salary_breakdown['total_deductions']
                        salary_data['net_salary'] = salary_breakdown['net_salary']
                        
                        if 'notes' in data:
                            salary_data['notes'] = data['notes']
                        
                        if existing:
                            # تحديث السجل الموجود
                            existing.basic_salary = data['basic_salary']
                            existing.allowances = data['allowances']
                            existing.deductions = data['deductions']
                            existing.bonus = data['bonus']
                            existing.net_salary = data['net_salary']
                            if 'notes' in data:
                                existing.notes = data['notes']
                            db.session.commit()
                        else:
                            # إنشاء سجل جديد
                            salary = Salary(**salary_data)
                            db.session.add(salary)
                            db.session.commit()
                        
                        success_count += 1
                    except Exception as e:
                        # طباعة رسالة الخطأ للسجل
                        print(f"Error importing salary: {str(e)}")
                        db.session.rollback()
                        error_count += 1
                
                # Log the import
                audit = SystemAudit(
                    action='import',
                    entity_type='salary',
                    entity_id=0,
                    details=f'تم استيراد {success_count} سجل راتب لشهر {month}/{year} بنجاح و {error_count} فشل'
                )
                db.session.add(audit)
                db.session.commit()
                
                if error_count > 0:
                    flash(f'تم استيراد {success_count} سجل راتب بنجاح و {error_count} فشل', 'warning')
                else:
                    flash(f'تم استيراد {success_count} سجل راتب بنجاح', 'success')
                return redirect(url_for('salaries.index', month=month, year=year))
            except Exception as e:
                flash(f'حدث خطأ أثناء استيراد الملف: {str(e)}', 'danger')
        else:
            flash('الملف يجب أن يكون بصيغة Excel (.xlsx, .xls)', 'danger')
    
    # Default to current month and year
    now = datetime.now()
    
    return render_template('salaries/import.html',
                          current_month=now.month,
                          current_year=now.year)

@salaries_bp.route('/export')
def export_excel():
    """تصدير سجلات الرواتب إلى ملف Excel مع دعم التصفية حسب القسم والشهر والسنة"""
    try:
        # الحصول على معلمات التصفية
        month = request.args.get('month')
        year = request.args.get('year')
        department_id = request.args.get('department_id')
        employee_id = request.args.get('employee_id')
        
        # بناء الاستعلام
        query = Salary.query.join(Employee)
        
        # تطبيق المرشحات
        filename_parts = []
        filter_description = []
        
        # تصفية حسب الشهر
        if month and month.isdigit():
            query = query.filter(Salary.month == int(month))
            filename_parts.append(f"month_{month}")
            
            # قاموس لتحويل رقم الشهر إلى اسمه بالعربية
            arabic_months = {
                1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 
                5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
                9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
            }
            month_name = arabic_months.get(int(month), str(month))
            filter_description.append(f"شهر: {month_name}")
        else:
            filename_parts.append("all_months")
            filter_description.append("جميع الشهور")
        
        # تصفية حسب السنة
        if year and year.isdigit():
            query = query.filter(Salary.year == int(year))
            filename_parts.append(f"year_{year}")
            filter_description.append(f"سنة: {year}")
        else:
            filename_parts.append("all_years")
            filter_description.append("جميع السنوات")
        
        # تصفية حسب القسم
        department_name = "جميع الأقسام"
        if department_id and department_id.isdigit():
            # البحث عن اسم القسم لاستخدامه في وصف التصفية
            department = Department.query.get(int(department_id))
            if department:
                department_name = department.name
                query = query.filter(Employee.department_id == int(department_id))
                filename_parts.append(f"dept_{department_id}")
                filter_description.append(f"قسم: {department_name}")
            else:
                filename_parts.append("all_depts")
                filter_description.append("جميع الأقسام")
        else:
            filename_parts.append("all_depts")
            filter_description.append("جميع الأقسام")
        
        # تصفية حسب الموظف
        if employee_id and employee_id.isdigit():
            employee = Employee.query.get(int(employee_id))
            if employee:
                query = query.filter(Salary.employee_id == int(employee_id))
                filename_parts.append(f"emp_{employee_id}")
                filter_description.append(f"موظف: {employee.name}")
            
        # ترتيب النتائج حسب اسم الموظف
        query = query.order_by(Employee.name)
        
        # تنفيذ الاستعلام
        salaries = query.all()
        
        # توليد ملف Excel
        output = generate_salary_excel(salaries, filter_description)
        
        # تسجيل عملية التصدير
        filters_text = " - ".join(filter_description)
        audit = SystemAudit(
            action='export',
            entity_type='salary',
            entity_id=0,
            details=f'تم تصدير {len(salaries)} سجل راتب إلى ملف Excel [{filters_text}]'
        )
        db.session.add(audit)
        db.session.commit()
        
        # إنشاء اسم الملف
        filename = f'رواتب_{"_".join(filename_parts)}.xlsx'
        
        return send_file(
            BytesIO(output.getvalue()),
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'حدث خطأ أثناء تصدير البيانات: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/report/pdf')
def report_pdf():
    """Generate a PDF salary report for a specific month and year"""
    try:
        # Get filter parameters
        month = request.args.get('month')
        year = request.args.get('year')
        department_id = request.args.get('department_id')

        if not month or not month.isdigit() or not year or not year.isdigit():
            flash('يرجى اختيار شهر وسنة صالحين', 'danger')
            return redirect(url_for('salaries.index'))
        
        month = int(month)
        year = int(year)
        
  

        # Get salary records for the selected month and year
        salaries = Salary.query.filter_by(month=month, year=year).all()

        if not salaries:
            flash('لا توجد سجلات رواتب للشهر والسنة المحددين', 'warning')
            return redirect(url_for('salaries.index'))
        # Generate PDF report
        # pdf_bytes = generate_salary_report_pdf(salaries, month, year)

        pdf_bytes = generate_salary_summary_pdf(salaries, month, year)
        # Log the export
        audit = SystemAudit(
            action='export_pdf',
            entity_type='salary',
            entity_id=0,
            details=f'تم تصدير تقرير رواتب لشهر {month}/{year} بصيغة PDF'
        )
        db.session.add(audit)
        db.session.commit()
        
        return send_file(
            BytesIO(pdf_bytes),
            download_name=f'salary_report_{month}_{year}.pdf',
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'حدث خطأ أثناء إنشاء تقرير PDF: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/notification/<int:id>/pdf')
def salary_notification_pdf(id):
    """إنشاء إشعار راتب لموظف بصيغة PDF"""
    try:
        # الحصول على سجل الراتب
        salary = Salary.query.get_or_404(id)
        
        # إنشاء ملف PDF
        pdf_bytes = generate_salary_notification_pdf(salary)
        
        # تسجيل العملية - بدون تحديد user_id
        audit = SystemAudit(
            action='generate_notification',
            entity_type='salary',
            entity_id=salary.id,
            details=f'تم إنشاء إشعار راتب للموظف: {salary.employee.name} لشهر {salary.month}/{salary.year}',
            user_id=None  # تحديد القيمة بشكل واضح كقيمة فارغة
        )
        db.session.add(audit)
        db.session.commit()
        
        return send_file(
            BytesIO(pdf_bytes),
            download_name=f'salary_notification_{salary.employee.employee_id}_{salary.month}_{salary.year}.pdf',
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'حدث خطأ أثناء إنشاء إشعار الراتب: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/comprehensive_report', methods=['GET', 'POST'])
def comprehensive_report():
    """تقرير شامل للموظفين مع كامل تفاصيل الرواتب"""
    # الحصول على قائمة الأقسام للاختيار
    departments = Department.query.order_by(Department.name).all()
    
    # الحصول على الشهر والسنة الحالية
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if request.method == 'POST':
        try:
            # الحصول على معلمات التصفية
            department_id = request.form.get('department_id')
            if department_id == '':
                department_id = None
            elif department_id:
                department_id = int(department_id)
            
            employee_id = request.form.get('employee_id')
            if employee_id == '':
                employee_id = None
            elif employee_id:
                employee_id = int(employee_id)
            
            month = request.form.get('month')
            if month:
                month = int(month)
            
            year = request.form.get('year')
            if year:
                year = int(year)
            
            # إنشاء التقرير الشامل
            report_excel = generate_comprehensive_employee_report(
                db.session, department_id, employee_id, month, year
            )
            
            # تسجيل العملية
            filter_description = []
            if department_id:
                dept = Department.query.get(department_id)
                filter_description.append(f"القسم: {dept.name}")
            if employee_id:
                emp = Employee.query.get(employee_id)
                filter_description.append(f"الموظف: {emp.name}")
            if month:
                filter_description.append(f"الشهر: {month}")
            if year:
                filter_description.append(f"السنة: {year}")
            
            filter_str = " | ".join(filter_description) if filter_description else "كافة البيانات"
            
            audit = SystemAudit(
                action='comprehensive_report',
                entity_type='employee',
                entity_id=0,
                details=f'تم إنشاء تقرير شامل للموظفين مع تفاصيل الرواتب ({filter_str})',
                user_id=None
            )
            db.session.add(audit)
            db.session.commit()
            
            # إرسال الملف كتنزيل
            return send_file(
                report_excel,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'تقرير_شامل_الموظفين_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            )
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            flash(f'حدث خطأ أثناء إنشاء التقرير الشامل: {str(e)}', 'danger')
            return redirect(url_for('salaries.index'))
    
    # في حالة طلب GET، عرض صفحة اختيار الفلاتر
    return render_template('salaries/comprehensive_report.html',
                          departments=departments,
                          current_month=current_month,
                          current_year=current_year)

@salaries_bp.route('/export/simple_employees_salary')
def export_simple_employees_salary():
    """تصدير بيانات الموظفين مع تفاصيل الرواتب بتنسيق بسيط"""
    # الحصول على معلمات التصفية
    month = request.args.get('month')
    if month:
        month = int(month)
    
    year = request.args.get('year')
    if year:
        year = int(year)
    
    department_id = request.args.get('department_id')
    if department_id:
        department_id = int(department_id)
    
    try:
        # إنشاء ملف Excel بسيط ومرتب للموظفين والرواتب
        output = generate_employee_salary_simple_excel(db.session, month, year, department_id)
        
        # إعداد وصف الفلاتر للسجل
        filter_description = []
        if month:
            filter_description.append(f"الشهر: {month}")
        if year:
            filter_description.append(f"السنة: {year}")
        if department_id:
            department = Department.query.get(department_id)
            if department:
                filter_description.append(f"القسم: {department.name}")
        
        filter_str = " | ".join(filter_description) if filter_description else "كافة البيانات"
        
        # تسجيل العملية
        audit = SystemAudit(
            action='export_simple_employees_salary',
            entity_type='employee_salary',
            entity_id=0,
            details=f'تم تصدير بيانات الموظفين مع تفاصيل الرواتب بتنسيق بسيط ({filter_str})',
            user_id=None
        )
        db.session.add(audit)
        db.session.commit()
        
        # إعداد اسم الملف
        today = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"الموظفين_والرواتب_{today}.xlsx"
        
        # إرسال الملف
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        flash(f'حدث خطأ أثناء تصدير بيانات الموظفين والرواتب: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

