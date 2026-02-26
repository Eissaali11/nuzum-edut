"""Helper utilities for employee routes"""
from flask import flash, redirect, url_for, render_template, send_file, request


def handle_unlink_flash(result):
    """Flash messages for SIM/assignment unlinking operations"""
    unlink_info = (result.data or {}).get("unlink") or {}
    if not unlink_info:
        return
    
    sim_count = unlink_info.get("sim_count", 0)
    assignment_count = unlink_info.get("assignment_count", 0)
    
    if sim_count or assignment_count:
        parts = []
        if sim_count:
            parts.append(f"{sim_count} رقم SIM مرتبط مباشرة")
        if assignment_count:
            parts.append(f"{assignment_count} تخصيص جهاز/رقم")
        flash(f"تم فك ربط {' و '.join(parts)} بالموظف تلقائياً", "info")
    
    if unlink_info.get("warning"):
        flash("تحذير: حدث خطأ في فك ربط أرقام SIM. يرجى فحص الأرقام يدوياً", "warning")


def extract_department_id_from_url(url):
    """Extract department ID from URL if present"""
    if not url or '/departments/' not in url:
        return None
    try:
        return url.split('/departments/')[1].split('/')[0]
    except:
        return None


def send_file_or_error(file_func, download_name, fallback_url, error_msg):
    """Execute file generation function and send file, or redirect with error message"""
    try:
        output = file_func()
        if isinstance(output, tuple):
            output, download_name = output
        return send_file(output, download_name=download_name, as_attachment=True,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        flash(f'{error_msg}: {str(e)}', 'danger')
        return redirect(url_for(fallback_url))


def send_report_file(report_func, employee_id):
    """Send report file or redirect with error"""
    result = report_func(employee_id)
    if not result.success:
        flash(result.message, result.category)
        return redirect(url_for('employees.view', id=employee_id))
    
    return send_file(result.output, as_attachment=True, download_name=result.filename,
                     mimetype=result.mimetype)


def send_report_file_track(report_func, employee_id):
    """Send track history report file or redirect"""
    result = report_func(employee_id)
    if not result.success:
        flash(result.message, result.category)
        return redirect(url_for('employees.track_history', id=employee_id))
    return send_file(result.output, as_attachment=True, download_name=result.filename,
                     mimetype=result.mimetype)


def handle_form_submission(form_handler, template_name, context_func, redirect_url, 
                           translate_msg_func=None, unlink_handler=None, dept_redirect_func=None):
    """Generic form submission handler for create/edit patterns"""
    if request.method == 'POST':
        result = form_handler(request.form, getattr(request, 'files', {}))
        if translate_msg_func:
            flash(translate_msg_func(result), result.category)
        else:
            flash(result.message, result.category)
        
        if result.success:
            if unlink_handler:
                unlink_handler(result)
            
            if dept_redirect_func:
                url = dept_redirect_func()
                if url:
                    return url
            
            return redirect(redirect_url)
        
        context = context_func()
        context['form_data'] = request.form.to_dict() if hasattr(request.form, 'to_dict') else request.form
        return render_template(f'employees/{template_name}.html', **context)
    
    context = context_func()
    return render_template(f'employees/{template_name}.html', **context)
