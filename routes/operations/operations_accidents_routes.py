"""
Operations accident reports routes:
- List, view, review, and delete accident reports
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response, current_app, send_file
from flask_login import login_required, current_user
from core.extensions import db
from models import VehicleAccident, VehicleAccidentImage, UserRole
from datetime import datetime
from utils.audit_logger import log_audit
import os
import shutil

operations_accidents_bp = Blueprint('operations_accidents', __name__, url_prefix='/operations')


@operations_accidents_bp.route('/accident-reports', methods=['GET'])
@login_required
def list_accident_reports():
    """عرض قائمة تقارير الحوادث"""
    
    status_filter = request.args.get('status', 'pending')
    query = VehicleAccident.query
    
    if status_filter and status_filter != 'all':
        query = query.filter_by(review_status=status_filter)
    
    accidents = query.order_by(VehicleAccident.accident_date.desc(), VehicleAccident.created_at.desc()).all()
    
    # إحصائيات
    total_pending = VehicleAccident.query.filter_by(review_status='pending').count()
    total_approved = VehicleAccident.query.filter_by(review_status='approved').count()
    total_rejected = VehicleAccident.query.filter_by(review_status='rejected').count()
    total_under_review = VehicleAccident.query.filter_by(review_status='under_review').count()
    
    return render_template('operations/accident_reports_list.html',
                          accidents=accidents,
                          status_filter=status_filter,
                          stats={
                              'total_pending': total_pending,
                              'total_approved': total_approved,
                              'total_rejected': total_rejected,
                              'total_under_review': total_under_review
                          })


@operations_accidents_bp.route('/accident-reports/<int:accident_id>', methods=['GET'])
@login_required
def view_accident_report(accident_id):
    """عرض تفاصيل تقرير حادث"""
    
    accident = VehicleAccident.query.get_or_404(accident_id)
    images = accident.images.all()
    
    return render_template('operations/accident_report_details.html',
                          accident=accident,
                          images=images)


@operations_accidents_bp.route('/accident-reports/<int:accident_id>/review', methods=['POST'])
@login_required
def review_accident_report(accident_id):
    """مراجعة والموافقة/رفض تقرير حادث"""
    
    accident = VehicleAccident.query.get_or_404(accident_id)
    
    action = request.form.get('action')  # approve, reject, under_review
    reviewer_notes = request.form.get('reviewer_notes', '')
    
    if action not in ['approve', 'reject', 'under_review']:
        flash('إجراء غير صالح', 'danger')
        return redirect(url_for('operations_accidents.view_accident_report', accident_id=accident_id))
    
    # تحديث حالة المراجعة
    if action == 'approve':
        accident.review_status = 'approved'
        accident.accident_status = 'معتمد'
        flash_message = 'تم اعتماد تقرير الحادث بنجاح'
        flash_type = 'success'
    elif action == 'reject':
        accident.review_status = 'rejected'
        flash_message = 'تم رفض تقرير الحادث'
        flash_type = 'warning'
    else:
        accident.review_status = 'under_review'
        flash_message = 'تم تحديث حالة التقرير إلى "قيد المراجعة"'
        flash_type = 'info'
    
    accident.reviewed_by = current_user.id
    accident.reviewed_at = datetime.utcnow()
    accident.reviewer_notes = reviewer_notes
    
    if action == 'approve':
        liability_percentage = request.form.get('liability_percentage')
        deduction_amount = request.form.get('deduction_amount')
        vehicle_condition = request.form.get('vehicle_condition')
        
        if liability_percentage:
            accident.liability_percentage = int(liability_percentage)
        if deduction_amount:
            accident.deduction_amount = float(deduction_amount)
        if vehicle_condition:
            accident.vehicle_condition = vehicle_condition
    
    try:
        db.session.commit()
        
        log_audit(
            user_id=current_user.id,
            action=f'accident_report_{action}',
            entity_type='vehicle_accident',
            entity_id=accident.id,
            details=f'مراجعة تقرير الحادث: {flash_message}'
        )
        
        flash(flash_message, flash_type)
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('operations_accidents.view_accident_report', accident_id=accident_id))


@operations_accidents_bp.route('/accident-reports/delete', methods=['POST'])
@login_required
def delete_accident_reports():
    """حذف مجموعة من تقارير الحوادث"""
    
    if not current_user._is_admin_role():
        flash('غير مسموح لك بالوصول لهذه الصفحة', 'danger')
        return redirect(url_for('operations_accidents.list_accident_reports'))
    
    accident_ids = request.form.getlist('accident_ids')
    
    if not accident_ids:
        flash('الرجاء تحديد تقرير واحد على الأقل للحذف', 'warning')
        return redirect(url_for('operations_accidents.list_accident_reports'))
    
    try:
        deleted_count = 0
        for accident_id in accident_ids:
            accident = VehicleAccident.query.get(int(accident_id))
            if accident:
                # حذف الملفات من السيرفر
                accident_folder = os.path.join('static', 'uploads', 'accidents', str(accident.id))
                if os.path.exists(accident_folder):
                    try:
                        shutil.rmtree(accident_folder)
                        current_app.logger.info(f"تم حذف مجلد التقرير: {accident_folder}")
                    except Exception as e:
                        current_app.logger.error(f"خطأ في حذف مجلد التقرير: {e}")
                
                # حذف الصور من قاعدة البيانات
                VehicleAccidentImage.query.filter_by(accident_id=accident.id).delete()
                
                # حذف التقرير من قاعدة البيانات
                db.session.delete(accident)
                deleted_count += 1
                
                log_audit(
                    user_id=current_user.id,
                    action='delete_accident_report',
                    entity_type='vehicle_accident',
                    entity_id=accident.id,
                    details=f'حذف تقرير حادث'
                )
        
        db.session.commit()
        flash(f'تم حذف {deleted_count} تقرير بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في حذف الحوادث: {e}")
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'danger')
    
    return redirect(url_for('operations_accidents.list_accident_reports'))


@operations_accidents_bp.route('/accident-reports/<int:accident_id>/download-pdf', methods=['GET'])
@login_required
def download_accident_report_pdf(accident_id):
    """تنزيل تقرير الحادث بصيغة PDF"""
    
    accident = VehicleAccident.query.get_or_404(accident_id)
    
    try:
        from utils.accident_report_pdf import generate_accident_report_pdf
        
        # إنشاء PDF
        pdf = generate_accident_report_pdf(accident)
        
        # تحويل إلى bytes
        pdf_output = bytes(pdf.output())
        
        response = make_response(pdf_output)
        response.headers['Content-Type'] = 'application/pdf'
        
        filename = f'accident_report_{accident.id}_{accident.vehicle.plate_number}_{accident.accident_date.strftime("%Y%m%d")}.pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        log_audit(
            user_id=current_user.id,
            action='download_accident_pdf',
            entity_type='vehicle_accident',
            entity_id=accident.id,
            details=f'تنزيل تقرير PDF'
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"خطأ في إنشاء PDF: {e}")
        flash(f'حدث خطأ أثناء إنشاء ملف PDF: {str(e)}', 'danger')
        return redirect(url_for('operations_accidents.view_accident_report', accident_id=accident_id))
