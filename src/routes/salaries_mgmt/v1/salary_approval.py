"""salary_approval.py - decomposed salaries routes."""

from .salary_base import *

@salaries_bp.route('/notification/<int:id>/share_whatsapp')
def share_salary_via_whatsapp(id):
    """مشاركة إشعار راتب عبر الواتس اب باستخدام رابط المشاركة المباشر"""
    try:
        # الحصول على سجل الراتب
        salary = Salary.query.get_or_404(id)
        employee = salary.employee
        
        # الحصول على اسم الشهر بالعربية
        month_names = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        month_name = month_names.get(salary.month, str(salary.month))
        
        # إنشاء رابط لتحميل ملف PDF
        pdf_url = url_for('salaries.salary_notification_pdf', id=salary.id, _external=True)
        
        # إعداد نص الرسالة مع رابط التحميل
        message_text = f"""
        *إشعار راتب - نُظم*

        السلام عليكم ورحمة الله وبركاته،

        تحية طيبة،

        نود إشعاركم بإيداع راتب شهر {month_name} {salary.year}.

        الموظف: {employee.name}
        الشهر: {month_name} {salary.year}

        صافي الراتب: *{salary.net_salary:.2f}*

        للاطلاع على تفاصيل الراتب، يمكنكم تحميل نسخة الإشعار من الرابط التالي:
        {pdf_url}

        مع تحيات إدارة الموارد البشرية
        نُظم - نظام إدارة متكامل
        """
        
        # تسجيل العملية
        audit = SystemAudit(
            action='share_whatsapp_link',
            entity_type='salary',
            entity_id=salary.id,
            details=f'تم مشاركة إشعار راتب عبر رابط واتس اب للموظف: {employee.name} لشهر {salary.month}/{salary.year}',
            user_id=None
        )
        db.session.add(audit)
        db.session.commit()
        
        # إنشاء رابط الواتس اب مع نص الرسالة
        from urllib.parse import quote
        
        # التحقق مما إذا كان رقم الهاتف متوفر للموظف
        if employee.mobile:
            # تنسيق رقم الهاتف (إضافة رمز الدولة +966 إذا لم يكن موجودًا)
            to_phone = employee.mobile
            if not to_phone.startswith('+'):
                # إذا كان الرقم يبدأ بـ 0، نحذفه ونضيف رمز الدولة
                if to_phone.startswith('0'):
                    to_phone = "+966" + to_phone[1:]
                else:
                    to_phone = "+966" + to_phone
            
            # إنشاء رابط مباشر للموظف
            whatsapp_url = f"https://wa.me/{to_phone}?text={quote(message_text)}"
        else:
            # إذا لم يكن هناك رقم هاتف، استخدم الطريقة العادية
            whatsapp_url = f"https://wa.me/?text={quote(message_text)}"
        
        # إعادة توجيه المستخدم إلى رابط الواتس اب
        return redirect(whatsapp_url)
        
    except Exception as e:
        flash(f'حدث خطأ أثناء مشاركة إشعار الراتب عبر الواتس اب: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/notification/<int:id>/share_deduction_whatsapp')
def share_deduction_via_whatsapp(id):
    """مشاركة إشعار خصم راتب عبر الواتس اب باستخدام رابط المشاركة المباشر"""
    try:
        # الحصول على سجل الراتب
        salary = Salary.query.get_or_404(id)
        employee = salary.employee
        
        # التحقق من وجود خصم على الراتب
        if salary.deductions <= 0:
            flash('لا يوجد خصم على هذا الراتب', 'warning')
            return redirect(url_for('salaries.index'))
        
        # الحصول على اسم الشهر بالعربية
        month_names = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        month_name = month_names.get(salary.month, str(salary.month))
        
        # إنشاء رابط لتحميل ملف PDF
        pdf_url = url_for('salaries.salary_notification_pdf', id=salary.id, _external=True)
        
        # إعداد نص الرسالة مع رابط التحميل
        message_text = f"""
        *إشعار خصم على الراتب - نُظم*

        السلام عليكم ورحمة الله وبركاته،

        تحية طيبة،

        نود إبلاغكم عن وجود خصم على راتب شهر {month_name} {salary.year}.

        الموظف: {employee.name}
        الشهر: {month_name} {salary.year}     

        مبلغ الخصم: *{salary.deductions:.2f}*

        الراتب بعد الخصم: {salary.net_salary:.2f}

        للاطلاع على تفاصيل الراتب والخصم، يمكنكم تحميل نسخة الإشعار من الرابط التالي:
        {pdf_url}  

        مع تحيات إدارة الموارد البشرية
        نُظم - نظام إدارة متكامل
        """
        
        # تسجيل العملية
        audit = SystemAudit(
            action='share_deduction_whatsapp_link',
            entity_type='salary',
            entity_id=salary.id,
            details=f'تم مشاركة إشعار خصم عبر رابط واتس اب للموظف: {employee.name} لشهر {salary.month}/{salary.year}',
            user_id=None
        )
        db.session.add(audit)
        db.session.commit()
        
        # إنشاء رابط الواتس اب مع نص الرسالة
        from urllib.parse import quote
        
        # التحقق مما إذا كان رقم الهاتف متوفر للموظف
        if employee.mobile:
            # تنسيق رقم الهاتف (إضافة رمز الدولة +966 إذا لم يكن موجودًا)
            to_phone = employee.mobile
            if not to_phone.startswith('+'):
                # إذا كان الرقم يبدأ بـ 0، نحذفه ونضيف رمز الدولة
                if to_phone.startswith('0'):
                    to_phone = "+966" + to_phone[1:]
                else:
                    to_phone = "+966" + to_phone
            
            # إنشاء رابط مباشر للموظف
            whatsapp_url = f"https://wa.me/{to_phone}?text={quote(message_text)}"
        else:
            # إذا لم يكن هناك رقم هاتف، استخدم الطريقة العادية
            whatsapp_url = f"https://wa.me/?text={quote(message_text)}"
        
        # إعادة توجيه المستخدم إلى رابط الواتس اب
        return redirect(whatsapp_url)
        
    except Exception as e:
        flash(f'حدث خطأ أثناء مشاركة إشعار الخصم عبر الواتس اب: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/notification/<int:id>/whatsapp', methods=['GET'])
def salary_notification_whatsapp(id):
    """إرسال إشعار راتب لموظف عبر WhatsApp"""
    try:
        # الحصول على سجل الراتب
        salary = Salary.query.get_or_404(id)
        employee = salary.employee
        
        # إرسال الإشعار عبر WhatsApp
        success, message = send_salary_notification_whatsapp(employee, salary)
        
        if success:
            # تسجيل العملية
            audit = SystemAudit(
                action='send_whatsapp_notification',
                entity_type='salary',
                entity_id=salary.id,
                details=f'تم إرسال إشعار راتب عبر WhatsApp للموظف: {employee.name} لشهر {salary.month}/{salary.year}',
                user_id=None
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f'تم إرسال إشعار الراتب عبر WhatsApp بنجاح للموظف {employee.name}', 'success')
        else:
            flash(f'فشل إرسال إشعار الراتب عبر WhatsApp: {message}', 'danger')
        
        return redirect(url_for('salaries.index'))
    except Exception as e:
        flash(f'حدث خطأ أثناء إرسال إشعار الراتب عبر WhatsApp: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/notification/<int:id>/deduction/whatsapp', methods=['GET'])
def salary_deduction_notification_whatsapp(id):
    """إرسال إشعار خصم على الراتب لموظف عبر WhatsApp"""
    try:
        # الحصول على سجل الراتب
        salary = Salary.query.get_or_404(id)
        employee = salary.employee
        
        # التحقق من وجود خصم على الراتب
        if salary.deductions <= 0:
            flash('لا يوجد خصم على هذا الراتب', 'warning')
            return redirect(url_for('salaries.index'))
        
        # إرسال الإشعار عبر WhatsApp
        success, message = send_salary_deduction_notification_whatsapp(employee, salary)
        
        if success:
            # تسجيل العملية
            audit = SystemAudit(
                action='send_whatsapp_deduction_notification',
                entity_type='salary',
                entity_id=salary.id,
                details=f'تم إرسال إشعار خصم على الراتب عبر WhatsApp للموظف: {employee.name} لشهر {salary.month}/{salary.year}',
                user_id=None
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f'تم إرسال إشعار الخصم عبر WhatsApp بنجاح للموظف {employee.name}', 'success')
        else:
            flash(f'فشل إرسال إشعار الخصم عبر WhatsApp: {message}', 'danger')
        
        return redirect(url_for('salaries.index'))
    except Exception as e:
        flash(f'حدث خطأ أثناء إرسال إشعار الخصم عبر WhatsApp: {str(e)}', 'danger')
        return redirect(url_for('salaries.index'))

@salaries_bp.route('/notifications/deduction/batch', methods=['GET', 'POST'])
def batch_deduction_notifications():
    """إرسال إشعارات خصومات مجمعة للموظفين عبر WhatsApp"""
    # الحصول على الأقسام للاختيار
    departments = Department.query.all()
    
    if request.method == 'POST':
        try:
            # الحصول على المعلمات
            department_id = request.form.get('department_id')
            month = request.form.get('month')
            year = request.form.get('year')
            
            if not month or not month.isdigit() or not year or not year.isdigit():
                flash('يرجى اختيار شهر وسنة صالحين', 'danger')
                return redirect(url_for('salaries.batch_deduction_notifications'))
                
            month = int(month)
            year = int(year)
            
            # إذا تم تحديد قسم
            if department_id and department_id != 'all':
                department_id = int(department_id)
                department = Department.query.get(department_id)
                department_name = department.name if department else "غير معروف"
                
                # إرسال إشعارات الخصم عبر WhatsApp
                success_count, failure_count, error_messages = send_batch_deduction_notifications_whatsapp(department_id, month, year)
                
                if success_count > 0:
                    # تسجيل العملية
                    audit = SystemAudit(
                        action='batch_whatsapp_deduction_notifications',
                        entity_type='salary',
                        entity_id=0,
                        details=f'تم إرسال {success_count} إشعار خصم عبر WhatsApp لموظفي قسم {department_name} لشهر {month}/{year}',
                        user_id=None
                    )
                    db.session.add(audit)
                    db.session.commit()
                    
                    # عرض رسالة نجاح مع تفاصيل النجاح/الفشل
                    if failure_count > 0:
                        flash(f'تم إرسال {success_count} إشعار خصم بنجاح و {failure_count} فشل', 'warning')
                        for error in error_messages[:5]:  # عرض أول 5 أخطاء فقط
                            flash(error, 'danger')
                        if len(error_messages) > 5:
                            flash(f'... و {len(error_messages) - 5} أخطاء أخرى', 'danger')
                    else:
                        flash(f'تم إرسال {success_count} إشعار خصم عبر WhatsApp بنجاح', 'success')
                else:
                    flash(f'لم يتم إرسال أي إشعارات خصم. {error_messages[0] if error_messages else "لا توجد خصومات مسجلة لموظفي قسم " + department_name + " في شهر " + str(month) + "/" + str(year)}', 'warning')
            else:
                # إرسال إشعارات الخصم لجميع الموظفين
                success_count, failure_count, error_messages = send_batch_deduction_notifications_whatsapp(None, month, year)
                
                if success_count > 0:
                    # تسجيل العملية
                    audit = SystemAudit(
                        action='batch_whatsapp_deduction_notifications',
                        entity_type='salary',
                        entity_id=0,
                        details=f'تم إرسال {success_count} إشعار خصم عبر WhatsApp لجميع الموظفين لشهر {month}/{year}',
                        user_id=None
                    )
                    db.session.add(audit)
                    db.session.commit()
                    
                    # عرض رسالة نجاح مع تفاصيل النجاح/الفشل
                    if failure_count > 0:
                        flash(f'تم إرسال {success_count} إشعار خصم بنجاح و {failure_count} فشل', 'warning')
                        for error in error_messages[:5]:  # عرض أول 5 أخطاء فقط
                            flash(error, 'danger')
                        if len(error_messages) > 5:
                            flash(f'... و {len(error_messages) - 5} أخطاء أخرى', 'danger')
                    else:
                        flash(f'تم إرسال {success_count} إشعار خصم عبر WhatsApp بنجاح', 'success')
                else:
                    flash(f'لم يتم إرسال أي إشعارات خصم. {error_messages[0] if error_messages else "لا توجد خصومات مسجلة لشهر " + str(month) + "/" + str(year)}', 'warning')
                
            return redirect(url_for('salaries.index', month=month, year=year))
                
        except Exception as e:
            flash(f'حدث خطأ أثناء إرسال إشعارات الخصم: {str(e)}', 'danger')
    
    # Default to current month and year
    now = datetime.now()
    
    return render_template('salaries/batch_deduction_notifications.html',
                          departments=departments,
                          current_month=now.month,
                          current_year=now.year)

@salaries_bp.route('/notifications/batch', methods=['GET', 'POST'])
def batch_salary_notifications():
    """إنشاء إشعارات رواتب مجمعة للموظفين حسب القسم"""
    # الحصول على الأقسام للاختيار
    departments = Department.query.all()
    
    if request.method == 'POST':
        try:
            # الحصول على المعلمات
            department_id = request.form.get('department_id')
            month = request.form.get('month')
            year = request.form.get('year')
            notification_type = request.form.get('notification_type', 'pdf')  # نوع الإشعار (pdf أو whatsapp)
            
            if not month or not month.isdigit() or not year or not year.isdigit():
                flash('يرجى اختيار شهر وسنة صالحين', 'danger')
                return redirect(url_for('salaries.batch_salary_notifications'))
                
            month = int(month)
            year = int(year)
            
            # إذا تم تحديد قسم
            if department_id and department_id != 'all':
                department_id = int(department_id)
                department = Department.query.get(department_id)
                department_name = department.name if department else "غير معروف"
                
                if notification_type == 'whatsapp':
                    # إرسال الإشعارات عبر WhatsApp
                    success_count, failure_count, error_messages = send_batch_salary_notifications_whatsapp(department_id, month, year)
                    
                    if success_count > 0:
                        # تسجيل العملية
                        audit = SystemAudit(
                            action='batch_whatsapp_notifications',
                            entity_type='salary',
                            entity_id=0,
                            details=f'تم إرسال {success_count} إشعار راتب عبر WhatsApp لموظفي قسم {department_name} لشهر {month}/{year}',
                            user_id=None
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        # عرض رسالة نجاح مع تفاصيل النجاح/الفشل
                        if failure_count > 0:
                            flash(f'تم إرسال {success_count} إشعار راتب بنجاح و {failure_count} فشل', 'warning')
                            for error in error_messages[:5]:  # عرض أول 5 أخطاء فقط
                                flash(error, 'danger')
                            if len(error_messages) > 5:
                                flash(f'... و {len(error_messages) - 5} أخطاء أخرى', 'danger')
                        else:
                            flash(f'تم إرسال {success_count} إشعار راتب عبر WhatsApp بنجاح', 'success')
                    else:
                        flash(f'لم يتم إرسال أي إشعارات. {error_messages[0] if error_messages else "لا توجد رواتب مسجلة لموظفي قسم " + department_name + " في شهر " + str(month) + "/" + str(year)}', 'warning')
                else:
                    # إنشاء ملفات PDF (السلوك الافتراضي)
                    processed_employees = generate_batch_salary_notifications(department_id, month, year)
                    
                    if processed_employees:
                        # تسجيل العملية
                        audit = SystemAudit(
                            action='batch_notifications',
                            entity_type='salary',
                            entity_id=0,
                            details=f'تم إنشاء {len(processed_employees)} إشعار راتب لموظفي قسم {department_name} لشهر {month}/{year}',
                            user_id=None
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        flash(f'تم إنشاء {len(processed_employees)} إشعار راتب لموظفي قسم {department_name}', 'success')
                    else:
                        flash(f'لا توجد رواتب مسجلة لموظفي قسم {department_name} في شهر {month}/{year}', 'warning')
            else:
                # معالجة الإشعارات لجميع الموظفين
                if notification_type == 'whatsapp':
                    # إرسال الإشعارات عبر WhatsApp
                    success_count, failure_count, error_messages = send_batch_salary_notifications_whatsapp(None, month, year)
                    
                    if success_count > 0:
                        # تسجيل العملية
                        audit = SystemAudit(
                            action='batch_whatsapp_notifications',
                            entity_type='salary',
                            entity_id=0,
                            details=f'تم إرسال {success_count} إشعار راتب عبر WhatsApp لجميع الموظفين لشهر {month}/{year}',
                            user_id=None
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        # عرض رسالة نجاح مع تفاصيل النجاح/الفشل
                        if failure_count > 0:
                            flash(f'تم إرسال {success_count} إشعار راتب بنجاح و {failure_count} فشل', 'warning')
                            for error in error_messages[:5]:  # عرض أول 5 أخطاء فقط
                                flash(error, 'danger')
                            if len(error_messages) > 5:
                                flash(f'... و {len(error_messages) - 5} أخطاء أخرى', 'danger')
                        else:
                            flash(f'تم إرسال {success_count} إشعار راتب عبر WhatsApp بنجاح', 'success')
                    else:
                        flash(f'لم يتم إرسال أي إشعارات. {error_messages[0] if error_messages else "لا توجد رواتب مسجلة لشهر " + str(month) + "/" + str(year)}', 'warning')
                else:
                    # إنشاء ملفات PDF (السلوك الافتراضي)
                    processed_employees = generate_batch_salary_notifications(None, month, year)
                    
                    if processed_employees:
                        # تسجيل العملية
                        audit = SystemAudit(
                            action='batch_notifications',
                            entity_type='salary',
                            entity_id=0,
                            details=f'تم إنشاء {len(processed_employees)} إشعار راتب لجميع الموظفين لشهر {month}/{year}',
                            user_id=None
                        )
                        db.session.add(audit)
                        db.session.commit()
                        
                        flash(f'تم إنشاء {len(processed_employees)} إشعار راتب لجميع الموظفين', 'success')
                    else:
                        flash(f'لا توجد رواتب مسجلة لشهر {month}/{year}', 'warning')
                    
            return redirect(url_for('salaries.index', month=month, year=year))
                
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء إشعارات الرواتب: {str(e)}', 'danger')
    
    # Default to current month and year
    now = datetime.now()
    
    return render_template('salaries/batch_notifications.html',
                          departments=departments,
                          current_month=now.month,
                          current_year=now.year)

