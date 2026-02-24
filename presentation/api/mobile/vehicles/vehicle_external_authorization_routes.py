"""Auto-split from vehicle_lifecycle_routes.py: mobile vehicle lifecycle subdomain routes."""

"""Auto-split from vehicle_routes.py: mobile vehicle domain routes."""

"""
مسارات المركبات (السيارات، الورشة، التسليم/الاستلام، التصريحات الخارجية) للجوال.
مستخرجة من routes/mobile.py. تُسجّل على mobile_bp عبر register_vehicle_routes(mobile_bp).
"""
import base64
import io
import os
import uuid
from datetime import datetime, timedelta, date

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from models import (
    Department,
    Employee,
    ExternalAuthorization,
    GeofenceSession,
    OperationNotification,
    OperationRequest,
    Vehicle,
    VehicleAccident,
    VehicleChecklist,
    VehicleChecklistImage,
    VehicleChecklistItem,
    VehicleDamageMarker,
    VehicleFuelConsumption,
    VehicleHandover,
    VehicleHandoverImage,
    VehicleMaintenance,
    VehicleMaintenanceImage,
    VehiclePeriodicInspection,
    VehicleProject,
    VehicleRental,
    VehicleSafetyCheck,
    VehicleWorkshop,
    VehicleWorkshopImage,
    employee_departments,
)
from core.extensions import db
from routes.operations import create_operation_request
from modules.vehicles.application.vehicle_service import update_vehicle_driver
from utils.audit_logger import log_activity
from utils.decorators import module_access_required, permission_required
from utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state

def register_vehicle_external_authorization_routes(bp):
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/view')
    @login_required
    def view_external_authorization(vehicle_id, auth_id):
        """عرض تفاصيل التفويض الخارجي في الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        return render_template('mobile/view_external_authorization.html',
                             vehicle=vehicle,
                             authorization=authorization)
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_external_authorization(vehicle_id, auth_id):
        """تعديل التفويض الخارجي في الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        if request.method == 'POST':
            try:
                # تحديث البيانات
                authorization.employee_id = request.form.get('employee_id')
                authorization.project_name = request.form.get('project_name')
                authorization.authorization_type = request.form.get('authorization_type')
                authorization.city = request.form.get('city')
                authorization.external_link = request.form.get('form_link')
                authorization.notes = request.form.get('notes')
    
                # معالجة رفع الملف الجديد
                if 'file' in request.files and request.files['file'].filename:
                    file = request.files['file']
                    if file:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
    
                        # إنشاء مجلد الرفع إذا لم يكن موجوداً
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
    
                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)
    
                        # 💾 لا حذف للملفات القديمة - الاحتفاظ بجميع الملفات للأمان
                        authorization.file_path = f"uploads/authorizations/{filename}"
    
                db.session.commit()
                flash('تم تحديث التفويض بنجاح', 'success')
                return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث التفويض: {str(e)}', 'error')
    
        # الحصول على البيانات للنموذج
        departments = Department.query.all()
        employees = Employee.query.all()
    
        return render_template('mobile/edit_external_authorization.html',
                             vehicle=vehicle,
                             authorization=authorization,
                             departments=departments,
                             employees=employees)
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/delete')
    @login_required
    def delete_external_authorization(vehicle_id, auth_id):
        """حذف التفويض الخارجي من الموبايل"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        authorization = ExternalAuthorization.query.get_or_404(auth_id)
    
        try:
            # 💾 الملف يبقى محفوظاً - نحذف فقط المرجع من قاعدة البيانات
            # لا حذف للملفات الفعلية
            db.session.delete(authorization)
            db.session.commit()
            flash('تم حذف التفويض بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حذف التفويض: {str(e)}', 'error')
    
        return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/create', methods=['GET', 'POST'])
    @login_required
    def create_external_authorization(vehicle_id):
        """إنشاء تفويض خارجي جديد من الموبايل"""
        from models import Vehicle, Employee, Department, ExternalAuthorization
        from werkzeug.utils import secure_filename
        import os
    
        try:
            # الحصول على السيارة
            vehicle = Vehicle.query.get_or_404(vehicle_id)
    
            # فحص قيود العمليات للسيارات خارج الخدمة
            from utils.vehicle_route_helpers import check_vehicle_operation_restrictions
            restrictions = check_vehicle_operation_restrictions(vehicle)
            if restrictions['blocked']:
                flash(restrictions['message'], 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            # الحصول على الموظفين والأقسام
            employees = Employee.query.all()
            departments = Department.query.all()
    
            if request.method == 'POST':
                # إنشاء تفويض جديد
                authorization = ExternalAuthorization(
                    vehicle_id=vehicle_id,
                    employee_id=request.form.get('employee_id'),
                    authorization_type=request.form.get('authorization_type'),
                    project_name=request.form.get('project_name'),
                    city=request.form.get('city'),
    
                    external_link=request.form.get('external_link'),
                    notes=request.form.get('notes'),
                    status='pending'
                )
    
                # معالجة رفع الملف
                if 'file' in request.files:
                    file = request.files['file']
                    if file and file.filename:
                        # حفظ الملف
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
    
                        upload_dir = os.path.join('static', 'uploads', 'authorizations')
                        os.makedirs(upload_dir, exist_ok=True)
    
                        file_path = os.path.join(upload_dir, filename)
                        file.save(file_path)
                        authorization.file_path = file_path
    
                db.session.add(authorization)
                db.session.commit()
    
                flash('تم إنشاء التفويض بنجاح', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            return render_template('mobile/create_external_authorization.html',
                                 vehicle=vehicle,
                                 employees=employees,
                                 departments=departments)
    
        except Exception as e:
            print(f"خطأ في إنشاء التفويض: {str(e)}")
            flash(f'خطأ في إنشاء التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/approve', methods=['GET', 'POST'])
    @login_required
    def approve_external_authorization(vehicle_id, auth_id):
        """موافقة على تفويض خارجي"""
        try:
            authorization = ExternalAuthorization.query.filter_by(
                id=auth_id, 
                vehicle_id=vehicle_id
            ).first()
    
            if not authorization:
                flash('التفويض غير موجود', 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            authorization.status = 'approved'
            authorization.updated_at = datetime.utcnow()
            db.session.commit()
    
            flash('تم الموافقة على التفويض بنجاح', 'success')
            return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
        except Exception as e:
            print(f"خطأ في موافقة التفويض: {str(e)}")
            flash(f'خطأ في موافقة التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
    @bp.route('/vehicles/<int:vehicle_id>/external-authorization/<int:auth_id>/reject', methods=['GET', 'POST'])
    @login_required
    def reject_external_authorization(vehicle_id, auth_id):
        """رفض تفويض خارجي"""
        try:
            authorization = ExternalAuthorization.query.filter_by(
                id=auth_id, 
                vehicle_id=vehicle_id
            ).first()
    
            if not authorization:
                flash('التفويض غير موجود', 'error')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
            authorization.status = 'rejected'
            authorization.updated_at = datetime.utcnow()
            db.session.commit()
    
            flash('تم رفض التفويض', 'info')
            return redirect(url_for('mobile.view_external_authorization', vehicle_id=vehicle_id, auth_id=auth_id))
    
        except Exception as e:
            print(f"خطأ في رفض التفويض: {str(e)}")
            flash(f'خطأ في رفض التفويض: {str(e)}', 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
