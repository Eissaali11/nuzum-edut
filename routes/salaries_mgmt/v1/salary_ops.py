"""salary_ops.py - decomposed salaries routes."""

from .salary_base import *

@salaries_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new salary record"""
    if request.method == 'POST':
        try:
            employee_id = request.form['employee_id']
            month = int(request.form['month'])
            year = int(request.form['year'])
            basic_salary = float(request.form['basic_salary'])
            allowances = float(request.form.get('allowances', 0))
            deductions = float(request.form.get('deductions', 0))
            bonus = float(request.form.get('bonus', 0))
            employee = Employee.query.get(employee_id)
            
            # Calculate net salary + nationality-based GOSI deductions
            salary_breakdown = compute_net_salary(
                basic_salary=basic_salary,
                allowances=allowances,
                bonus=bonus,
                deductions=deductions,
                nationality=getattr(employee, 'nationality', None),
                contract_type=getattr(employee, 'contract_type', None),
                return_breakdown=True
            )
            net_salary = salary_breakdown['net_salary']
            total_deductions = salary_breakdown['total_deductions']
            
            # Check if salary record already exists for this employee/month/year
            existing = Salary.query.filter_by(
                employee_id=employee_id,
                month=month,
                year=year
            ).first()
            
            if existing:
                flash('يوجد سجل راتب لهذا الموظف في نفس الشهر والسنة', 'danger')
                return redirect(url_for('salaries.create'))
            
            # Create new salary record
            salary = Salary(
                employee_id=employee_id,
                month=month,
                year=year,
                basic_salary=basic_salary,
                allowances=allowances,
                deductions=total_deductions,
                bonus=bonus,
                net_salary=net_salary,
                notes=request.form.get('notes', '')
            )
            
            db.session.add(salary)
            
            # Log the action
            audit = SystemAudit(
                action='create',
                entity_type='salary',
                entity_id=employee_id,
                details=f'تم إنشاء سجل راتب للموظف: {employee.name} لشهر {month}/{year}'
            )
            db.session.add(audit)
            db.session.commit()
            
            flash('تم إنشاء سجل الراتب بنجاح', 'success')
            return redirect(url_for('salaries.index', month=month, year=year))
        
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
    
    # Get all active employees for dropdown
    employees = Employee.query.filter_by(status='active').all()
    
    # Default to current month and year
    now = datetime.now()
    
    return render_template('salaries/create.html',
                          employees=employees,
                          current_month=now.month,
                          current_year=now.year)

@salaries_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """تعديل سجل راتب"""
    # الحصول على سجل الراتب
    salary = Salary.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # تحديث بيانات الراتب
            salary.basic_salary = float(request.form['basic_salary'])
            salary.allowances = float(request.form.get('allowances', 0))
            salary.deductions = float(request.form.get('deductions', 0))
            salary.bonus = float(request.form.get('bonus', 0))
            salary.notes = request.form.get('notes', '')
            
            # تحديث الشهر والسنة
            salary.month = int(request.form.get('month', salary.month))
            salary.year = int(request.form.get('year', salary.year))
            
            # إعادة حساب صافي الراتب (صيغة موحدة + GOSI حسب الجنسية)
            salary_breakdown = compute_net_salary(
                basic_salary=salary.basic_salary,
                allowances=salary.allowances,
                bonus=salary.bonus,
                deductions=salary.deductions,
                nationality=getattr(salary.employee, 'nationality', None),
                contract_type=getattr(salary.employee, 'contract_type', None),
                return_breakdown=True
            )
            salary.net_salary = salary_breakdown['net_salary']
            salary.deductions = salary_breakdown['total_deductions']
            
            # تسجيل العملية
            audit = SystemAudit(
                action='update',
                entity_type='salary',
                entity_id=salary.id,
                details=f'تم تعديل سجل راتب للموظف: {salary.employee.name} لشهر {salary.month}/{salary.year}'
            )
            db.session.add(audit)
            
            db.session.commit()
            
            flash('تم تعديل سجل الراتب بنجاح', 'success')
            return redirect(url_for('salaries.index', month=salary.month, year=salary.year))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تعديل سجل الراتب: {str(e)}', 'danger')
    
    # الحصول على قائمة الموظفين للاختيار من القائمة المنسدلة
    employees = Employee.query.order_by(Employee.name).all()
    
    # الحصول على السنة الحالية
    current_year = datetime.now().year
    
    return render_template('salaries/edit.html',
                          salary=salary,
                          employees=employees,
                          current_year=current_year)

@salaries_bp.route('/calculate_from_attendance', methods=['POST'])
def calculate_from_attendance():
    """حساب الراتب من سجلات الحضور (API Endpoint)"""
    try:
        data = request.json
        employee_id = int(data.get('employee_id'))
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        # جلب بيانات الموظف
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                'success': False,
                'message': 'الموظف غير موجود'
            }), 404
        
        # الحصول على الراتب الأساسي من بيانات الموظف
        basic_salary = employee.basic_salary if employee.basic_salary else 0
        
        if basic_salary == 0:
            return jsonify({
                'success': False,
                'message': 'الراتب الأساسي للموظف غير محدد. يرجى تحديثه من صفحة الموظف.'
            })
        
        # حساب الراتب بناءً على الحضور
        # عدد أيام العمل في الشهر (26 يوم افتراضياً - استبعاد الجمعة في السعودية)
        working_days_in_month = 26
        
        result = calculate_salary_with_attendance(
            employee_id=employee_id,
            month=month,
            year=year,
            basic_salary=basic_salary,
            allowances=0,  # يمكن تمريره من النموذج لاحقاً
            bonus=0,
            other_deductions=0,
            working_days_in_month=working_days_in_month,
            exclude_leave=employee.exclude_leave_from_deduction,
            exclude_sick=employee.exclude_sick_from_deduction
        )
        
        if not result:
            return jsonify({
                'success': False,
                'message': 'حدث خطأ أثناء حساب الراتب'
            })
        
        # إعداد الرد
        response = {
            'success': True,
            'data': {
                'basic_salary': result['basic_salary'],
                'allowances': result['allowances'],
                'bonus': result['bonus'],
                'attendance_deduction': result['attendance_deduction'],
                'other_deductions': result['other_deductions'],
                'gosi_deduction': result.get('gosi_deduction', 0),
                'gosi_rate': result.get('gosi_rate', 0),
                'is_saudi': result.get('is_saudi', False),
                'total_deductions': result['total_deductions'],
                'net_salary': result['net_salary']
            },
            'attendance_stats': result.get('attendance_stats'),
            'deductible_days': result.get('deductible_days', 0),
            'summary': get_attendance_summary_text(result.get('attendance_stats')) if result.get('attendance_stats') else 'لا توجد بيانات حضور'
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"خطأ في حساب الراتب من الحضور: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500

@salaries_bp.route('/bulk_calculate_attendance', methods=['POST'])
def bulk_calculate_attendance():
    """حساب رواتب جميع الموظفين في شهر محدد بناءً على الحضور"""
    try:
        data = request.json
        month = int(data.get('month'))
        year = int(data.get('year'))
        department_id = data.get('department_id')  # اختياري
        working_days_in_month = int(data.get('working_days_in_month', 26))  # القيمة المخصصة أو 26 افتراضياً
        
        if not month or not year:
            return jsonify({
                'success': False,
                'message': 'يرجى تحديد الشهر والسنة'
            }), 400
        
        # التحقق من صحة عدد أيام العمل
        if working_days_in_month < 1 or working_days_in_month > 31:
            return jsonify({
                'success': False,
                'message': 'عدد أيام العمل يجب أن يكون بين 1 و 31'
            }), 400
        
        # حساب الفترة الزمنية للشهر المحدد
        from datetime import datetime
        from calendar import monthrange
        first_day = datetime(year, month, 1).date()
        _, last_day_num = monthrange(year, month)
        last_day = datetime(year, month, last_day_num).date()
        
        # جلب معرفات الموظفين الذين لديهم سجلات حضور في هذا الشهر
        from sqlalchemy import distinct
        employees_with_attendance = db.session.query(distinct(Attendance.employee_id)).filter(
            Attendance.date >= first_day,
            Attendance.date <= last_day
        ).all()
        employee_ids_with_attendance = [emp_id[0] for emp_id in employees_with_attendance]
        
        # جلب الموظفين: النشطين + غير النشطين الذين لديهم حضور في هذا الشهر
        if department_id:
            # موظفين نشطين في القسم أو لديهم حضور في الشهر
            employees = Employee.query.filter(
                Employee.department_id == department_id
            ).filter(
                (Employee.status == 'active') | (Employee.id.in_(employee_ids_with_attendance))
            ).all()
        else:
            # موظفين نشطين أو لديهم حضور في الشهر
            employees = Employee.query.filter(
                (Employee.status == 'active') | (Employee.id.in_(employee_ids_with_attendance))
            ).all()
        
        if not employees:
            return jsonify({
                'success': False,
                'message': 'لا يوجد موظفون للمعالجة'
            }), 404
        
        success_count = 0
        error_count = 0
        errors = []
        
        for employee in employees:
            try:
                # التحقق من الراتب الأساسي - نخطر بدلاً من التجاهل
                if not employee.basic_salary or employee.basic_salary == 0:
                    errors.append(f'{employee.name}: تحذير - الراتب الأساسي = 0 (تم الحساب بقيمة 0)')
                    # نستمر في الحساب بدلاً من continue
                
                # التحقق من وجود سجل راتب مسبق
                existing_salary = Salary.query.filter_by(
                    employee_id=employee.id,
                    month=month,
                    year=year
                ).first()
                
                # حساب الراتب من الحضور
                # استخدام 0 إذا كان الراتب الأساسي غير محدد
                basic_salary_value = employee.basic_salary if employee.basic_salary else 0
                attendance_bonus_value = employee.attendance_bonus if employee.attendance_bonus else 0
                result = calculate_salary_with_attendance(
                    employee_id=employee.id,
                    month=month,
                    year=year,
                    basic_salary=basic_salary_value,
                    allowances=0,
                    bonus=0,
                    other_deductions=0,
                    working_days_in_month=working_days_in_month,
                    exclude_leave=employee.exclude_leave_from_deduction if employee.exclude_leave_from_deduction is not None else True,
                    exclude_sick=employee.exclude_sick_from_deduction if employee.exclude_sick_from_deduction is not None else True,
                    attendance_bonus=attendance_bonus_value
                )
                
                if not result:
                    errors.append(f'{employee.name}: فشل حساب الراتب')
                    error_count += 1
                    continue
                
                # إنشاء أو تحديث سجل الراتب
                if existing_salary:
                    # تحديث السجل الموجود
                    existing_salary.basic_salary = result['basic_salary']
                    existing_salary.attendance_bonus = result.get('attendance_bonus', 0)
                    existing_salary.allowances = result['allowances']
                    existing_salary.bonus = result['bonus']
                    existing_salary.deductions = result['total_deductions']
                    existing_salary.net_salary = result['net_salary']
                    existing_salary.attendance_calculated = True
                    existing_salary.attendance_deduction = result['attendance_deduction']
                    
                    if result.get('attendance_stats'):
                        existing_salary.present_days = result['attendance_stats']['present_days']
                        existing_salary.absent_days = result['attendance_stats']['absent_days']
                        existing_salary.leave_days = result['attendance_stats']['leave_days']
                        existing_salary.sick_days = result['attendance_stats']['sick_days']
                else:
                    # إنشاء سجل جديد
                    new_salary = Salary(
                        employee_id=employee.id,
                        month=month,
                        year=year,
                        basic_salary=result['basic_salary'],
                        attendance_bonus=result.get('attendance_bonus', 0),
                        allowances=result['allowances'],
                        bonus=result['bonus'],
                        deductions=result['total_deductions'],
                        net_salary=result['net_salary'],
                        attendance_calculated=True,
                        attendance_deduction=result['attendance_deduction']
                    )
                    
                    if result.get('attendance_stats'):
                        new_salary.present_days = result['attendance_stats']['present_days']
                        new_salary.absent_days = result['attendance_stats']['absent_days']
                        new_salary.leave_days = result['attendance_stats']['leave_days']
                        new_salary.sick_days = result['attendance_stats']['sick_days']
                    
                    db.session.add(new_salary)
                
                success_count += 1
                
            except Exception as e:
                errors.append(f'{employee.name}: {str(e)}')
                error_count += 1
                continue
        
        # حفظ التغييرات
        db.session.commit()
        
        # تسجيل العملية
        audit = SystemAudit(
            action='bulk_calculate_attendance',
            entity_type='salary',
            entity_id=0,
            details=f'تم حساب رواتب {success_count} موظف لشهر {month}/{year}'
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم حساب رواتب {success_count} موظف بنجاح',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في الحساب الجماعي: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500

@salaries_bp.route('/<int:id>/confirm-delete')
def confirm_delete(id):
    """صفحة تأكيد حذف سجل راتب"""
    salary = Salary.query.get_or_404(id)
    return render_template('salaries/confirm_delete.html', salary=salary)

@salaries_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a salary record"""
    salary = Salary.query.get_or_404(id)
    employee_name = salary.employee.name
    month = salary.month
    year = salary.year
    
    try:
        db.session.delete(salary)
        
        # Log the action
        audit = SystemAudit(
            action='delete',
            entity_type='salary',
            entity_id=id,
            details=f'تم حذف سجل راتب للموظف: {employee_name} لشهر {month}/{year}'
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('تم حذف سجل الراتب بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف سجل الراتب: {str(e)}', 'danger')
    
    return redirect(url_for('salaries.index', month=month, year=year))

@salaries_bp.route('/save_all_smart', methods=['POST'])
def save_all_smart():
    """حفظ جميع الرواتب المُدخلة دفعة واحدة"""
    try:
        data = request.json
        salaries_data = data.get('salaries', [])
        
        if not salaries_data:
            return {'success': False, 'message': 'لا توجد بيانات للحفظ'}
        
        saved_count = 0
        
        for salary_data in salaries_data:
            employee_id = salary_data.get('employee_id')
            month = int(salary_data.get('month'))
            year = int(salary_data.get('year'))
            
            # التحقق من وجود سجل سابق
            existing_salary = Salary.query.filter_by(
                employee_id=employee_id,
                month=month,
                year=year
            ).first()
            
            if existing_salary:
                continue  # تخطي إذا كان موجود
            
            # معالجة القيم
            def parse_value(value):
                if value and str(value).strip():
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
                return None
            
            basic_salary = parse_value(salary_data.get('basic_salary'))
            allowances = parse_value(salary_data.get('allowances'))
            deductions = parse_value(salary_data.get('deductions'))
            bonus = parse_value(salary_data.get('bonus'))
            
            # يجب أن يكون الراتب الأساسي موجود
            if basic_salary is None:
                continue
            
            employee = Employee.query.get(employee_id)
            salary_breakdown = compute_net_salary(
                basic_salary=basic_salary,
                allowances=allowances,
                bonus=bonus,
                deductions=deductions,
                nationality=getattr(employee, 'nationality', None),
                contract_type=getattr(employee, 'contract_type', None),
                return_breakdown=True
            )
            net_salary = salary_breakdown['net_salary']
            total_deductions = salary_breakdown['total_deductions']
            
            # إنشاء سجل الراتب
            new_salary = Salary(
                employee_id=employee_id,
                month=month,
                year=year,
                basic_salary=basic_salary,
                allowances=allowances,
                deductions=total_deductions,
                bonus=bonus,
                net_salary=net_salary
            )
            
            db.session.add(new_salary)
            saved_count += 1
        
        db.session.commit()
        
        return {'success': True, 'message': f'تم حفظ {saved_count} راتب بنجاح', 'saved_count': saved_count}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'حدث خطأ: {str(e)}'}

@salaries_bp.route('/save_smart', methods=['POST'])
def save_smart():
    """حفظ ذكي للراتب - يحفظ فقط الحقول التي تم إدخال بيانات فيها"""
    try:
        data = request.json
        employee_id = data.get('employee_id')
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        # التحقق من وجود بيانات أساسية
        if not employee_id or not month or not year:
            return {'success': False, 'message': 'بيانات أساسية مفقودة'}
        
        # فحص الحقول المالية
        basic_salary = data.get('basic_salary')
        allowances = data.get('allowances') 
        deductions = data.get('deductions')
        bonus = data.get('bonus')
        
        # التحقق من أن المستخدم أدخل على الأقل الراتب الأساسي
        if not basic_salary or basic_salary == '' or float(basic_salary) <= 0:
            return {'success': False, 'message': 'يجب إدخال الراتب الأساسي'}
        
        # تحويل القيم الفارغة إلى None بدلاً من 0
        def parse_value(value):
            if value is None or value == '' or value == 'null':
                return None
            try:
                parsed = float(value)
                return parsed if parsed != 0 else None
            except (ValueError, TypeError):
                return None
        
        # معالجة القيم
        basic_salary = float(basic_salary)
        allowances = parse_value(allowances)
        deductions = parse_value(deductions) 
        bonus = parse_value(bonus)
        employee = Employee.query.get(employee_id)
        
        salary_breakdown = compute_net_salary(
            basic_salary=basic_salary,
            allowances=allowances,
            bonus=bonus,
            deductions=deductions,
            nationality=getattr(employee, 'nationality', None),
            contract_type=getattr(employee, 'contract_type', None),
            return_breakdown=True
        )
        net_salary = salary_breakdown['net_salary']
        total_deductions = salary_breakdown['total_deductions']
        
        # التحقق من وجود سجل سابق
        existing = Salary.query.filter_by(
            employee_id=employee_id,
            month=month,
            year=year
        ).first()
        
        if existing:
            return {'success': False, 'message': 'يوجد سجل راتب لهذا الموظف في نفس الشهر والسنة'}
        
        # إنشاء سجل جديد
        salary = Salary(
            employee_id=employee_id,
            month=month,
            year=year,
            basic_salary=basic_salary,
            allowances=allowances,
            deductions=total_deductions,
            bonus=bonus,
            net_salary=net_salary,
            notes=data.get('notes', '')
        )
        
        db.session.add(salary)
        
        # تسجيل العملية
        audit = SystemAudit(
            action='create',
            entity_type='salary',
            entity_id=employee_id,
            details=f'تم إنشاء سجل راتب ذكي للموظف: {employee.name} لشهر {month}/{year}'
        )
        db.session.add(audit)
        db.session.commit()
        
        # إعداد رسالة النجاح مع تفاصيل الحقول المحفوظة
        saved_fields = ['الراتب الأساسي']
        if allowances:
            saved_fields.append('البدلات')
        if deductions:
            saved_fields.append('الخصومات')
        if bonus:
            saved_fields.append('المكافآت')
        
        return {
            'success': True, 
            'message': f'تم حفظ الراتب بنجاح. الحقول المحفوظة: {", ".join(saved_fields)}',
            'net_salary': net_salary,
            'total_deductions': total_deductions,
            'gosi_deduction': salary_breakdown.get('gosi_deduction', 0)
        }
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'حدث خطأ: {str(e)}'}

@salaries_bp.route('/validate_incomplete', methods=['POST'])
def validate_incomplete():
    """التحقق من الحقول غير المكتملة قبل الحفظ"""
    try:
        data = request.json
        
        empty_fields = []
        filled_fields = []
        
        # فحص الحقول
        basic_salary = data.get('basic_salary')
        allowances = data.get('allowances')
        deductions = data.get('deductions') 
        bonus = data.get('bonus')
        
        if not basic_salary or basic_salary == '' or float(basic_salary) <= 0:
            empty_fields.append('الراتب الأساسي')
        else:
            filled_fields.append('الراتب الأساسي')
            
        if not allowances or allowances == '' or float(allowances) <= 0:
            empty_fields.append('البدلات')
        else:
            filled_fields.append('البدلات')
            
        if not deductions or deductions == '' or float(deductions) <= 0:
            empty_fields.append('الخصومات') 
        else:
            filled_fields.append('الخصومات')
            
        if not bonus or bonus == '' or float(bonus) <= 0:
            empty_fields.append('المكافآت')
        else:
            filled_fields.append('المكافآت')
        
        return {
            'empty_fields': empty_fields,
            'filled_fields': filled_fields,
            'has_basic_salary': 'الراتب الأساسي' in filled_fields
        }
        
    except Exception as e:
        return {'error': str(e)}

