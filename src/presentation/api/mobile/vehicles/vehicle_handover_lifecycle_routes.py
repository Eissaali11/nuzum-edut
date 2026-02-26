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
from src.core.extensions import db
from src.routes.operations import create_operation_request
from src.modules.vehicles.application.vehicle_service import update_vehicle_driver
from src.utils.audit_logger import log_activity
from src.utils.decorators import module_access_required, permission_required
from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions, update_vehicle_state

def register_vehicle_handover_lifecycle_routes(bp):
    @bp.route('/vehicles/handover/create/<int:vehicle_id>', methods=['GET', 'POST'])
    @login_required
    def create_handover(vehicle_id):
        """إنشاء نموذج تسليم/استلام للسيارة للنسخة المحمولة"""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
    
        # فحص قيود العمليات للسيارات خارج الخدمة
        from src.utils.vehicle_route_helpers import check_vehicle_operation_restrictions
        restrictions = check_vehicle_operation_restrictions(vehicle)
        if restrictions['blocked']:
            flash(restrictions['message'], 'error')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        if request.method == 'POST':
            # استخراج البيانات من النموذج
            handover_type = request.form.get('handover_type')
            handover_date = datetime.strptime(request.form.get('handover_date'), '%Y-%m-%d').date()
            person_name = request.form.get('person_name')
            supervisor_name = request.form.get('supervisor_name', '')
            form_link = request.form.get('form_link', '')
            vehicle_condition = request.form.get('vehicle_condition')
            fuel_level = request.form.get('fuel_level')
            mileage_str = request.form.get('mileage', '0')
            mileage = int(mileage_str) if mileage_str and mileage_str.isdigit() else 0
            has_spare_tire = 'has_spare_tire' in request.form
            has_fire_extinguisher = 'has_fire_extinguisher' in request.form
            has_tools = 'has_tools' in request.form
            has_first_aid_kit = 'has_first_aid_kit' in request.form
            has_warning_triangle = 'has_warning_triangle' in request.form
            notes = request.form.get('notes', '')
    
            # إنشاء سجل تسليم/استلام جديد
            handover = VehicleHandover(
                vehicle_id=vehicle_id,
                handover_type=handover_type,
                handover_date=handover_date,
                person_name=person_name,
                supervisor_name=supervisor_name,
                form_link=form_link,
                vehicle_condition=vehicle_condition,
                fuel_level=fuel_level,
                mileage=mileage,
                has_spare_tire=has_spare_tire,
                has_fire_extinguisher=has_fire_extinguisher,
                has_tools=has_tools,
                has_first_aid_kit=has_first_aid_kit,
                has_warning_triangle=has_warning_triangle,
                notes=notes
            )
    
            try:
                db.session.add(handover)
                db.session.commit()
    
                # تسجيل نشاط النظام
                description = f"تم إنشاء نموذج {'تسليم' if handover_type == 'delivery' else 'استلام'} للسيارة {vehicle.plate_number}"
                SystemAudit.create_audit_record(
                    current_user.id,
                    'إنشاء',
                    'VehicleHandover',
                    handover.id,
                    description,
                    entity_name=f"سيارة: {vehicle.plate_number}"
                )
    
                flash('تم إنشاء نموذج التسليم/الاستلام بنجاح', 'success')
                return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إنشاء النموذج: {str(e)}', 'danger')
    
        # عرض نموذج إنشاء تسليم/استلام
        return render_template('mobile/create_handover.html', 
                               vehicle=vehicle,
                               now=datetime.now())
    
    # عرض تفاصيل نموذج تسليم/استلام - النسخة المحمولة
    @bp.route('/vehicles/handover/<int:handover_id>')
    @login_required
    def view_handover(handover_id):
        """عرض تفاصيل نموذج تسليم/استلام للنسخة المحمولة"""
        handover = VehicleHandover.query.get_or_404(handover_id)
        vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
        images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
    
        # تنسيق التاريخ للعرض
        handover.formatted_handover_date = handover.handover_date.strftime('%Y-%m-%d')
    
        handover_type_name = 'تسليم' if handover.handover_type == 'delivery' else 'استلام'
    
        return render_template('mobile/handover_view.html',
                               handover=handover,
                               vehicle=vehicle,
                               images=images,
                               handover_type_name=handover_type_name)
    
    # إنشاء ملف PDF لنموذج تسليم/استلام - النسخة المحمولة
    @bp.route('/vehicles/handover/<int:handover_id>/pdf')
    @login_required
    def handover_pdf(handover_id):
        """إنشاء نموذج تسليم/استلام كملف PDF للنسخة المحمولة"""
        from flask import send_file, flash, redirect, url_for
        import io
        import os
        from datetime import datetime
        from src.utils.fpdf_handover_pdf import generate_handover_report_pdf_weasyprint
    
        try:
            # الحصول على بيانات التسليم/الاستلام
            handover = VehicleHandover.query.get_or_404(handover_id)
            vehicle = Vehicle.query.get_or_404(handover.vehicle_id)
            images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
    
            # تجهيز البيانات لملف PDF
            handover_data = {
                'vehicle': {
                    'plate_number': str(vehicle.plate_number),
                    'make': str(vehicle.make),
                    'model': str(vehicle.model),
                    'year': int(vehicle.year),
                    'color': str(vehicle.color)
                },
                'handover_type': 'تسليم' if handover.handover_type == 'delivery' else 'استلام',
                'handover_date': handover.handover_date.strftime('%Y-%m-%d'),
                'person_name': str(handover.person_name),
                'supervisor_name': str(handover.supervisor_name) if handover.supervisor_name else "",
                'vehicle_condition': str(handover.vehicle_condition),
                'fuel_level': str(handover.fuel_level),
                'mileage': int(handover.mileage),
                'has_spare_tire': bool(handover.has_spare_tire),
                'has_fire_extinguisher': bool(handover.has_fire_extinguisher),
                'has_first_aid_kit': bool(handover.has_first_aid_kit),
                'has_warning_triangle': bool(handover.has_warning_triangle),
                'has_tools': bool(handover.has_tools),
                'notes': str(handover.notes) if handover.notes else "",
                'form_link': str(handover.form_link) if handover.form_link else "",
                'image_paths': [image.image_path for image in images] if images else []
            }
    
            # إنشاء ملف PDF باستخدام WeasyPrint مع خط beIN-Normal
            pdf_buffer = generate_handover_report_pdf_weasyprint(handover)
    
            if not pdf_buffer:
                flash('حدث خطأ أثناء إنشاء ملف PDF', 'danger')
                return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
            # تحديد اسم الملف
            filename = f"handover_form_{vehicle.plate_number}.pdf"
    
            # إرسال الملف للمستخدم
            return send_file(
                pdf_buffer,
                download_name=filename,
                as_attachment=True,
                mimetype='application/pdf'
            )
    
        except Exception as e:
            flash(f'حدث خطأ أثناء إنشاء ملف PDF: {str(e)}', 'danger')
            return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
    # اختبار حفظ سجل الورشة تجريبياً - النسخة المحمولة

    @bp.route('/handover/<int:handover_id>/delete', methods=['POST'])
    @login_required
    def delete_handover(handover_id):
        """حذف سجل تسليم أو استلام"""
        try:
            # الحصول على سجل التسليم/الاستلام
            handover = VehicleHandover.query.get_or_404(handover_id)
            vehicle_id = handover.vehicle_id
            handover_type = handover.handover_type
            person_name = handover.person_name
    
            # 💾 حذف الصور من قاعدة البيانات فقط - الملفات تبقى محفوظة
            images = VehicleHandoverImage.query.filter_by(handover_record_id=handover_id).all()
            for image in images:
                # لا حذف للملفات الفعلية - الاحتفاظ بجميع الصور للأمان
                db.session.delete(image)
    
            # حذف سجل التسليم/الاستلام
            db.session.delete(handover)
            db.session.commit()
    
            # تسجيل العملية في السجل
            log_activity(
                action='delete',
                entity_type='vehicle_handover',
                entity_id=handover_id,
                details=f'تم حذف سجل {"تسليم" if handover_type == "delivery" else "استلام"} للسيارة - الشخص: {person_name}'
            )
    
            # تحديث اسم السائق في السيارة بعد الحذف
            update_vehicle_driver(vehicle_id)
    
            flash(f'تم حذف سجل {"التسليم" if handover_type == "delivery" else "الاستلام"} بنجاح', 'success')
            return redirect(url_for('mobile.vehicle_details', vehicle_id=vehicle_id))
    
        except Exception as e:
            db.session.rollback()
            print(f"خطأ في حذف سجل التسليم/الاستلام: {str(e)}")
            flash(f'خطأ في حذف السجل: {str(e)}', 'error')
            return redirect(url_for('mobile.view_handover', handover_id=handover_id))
    
    # --- New Quick Return Functions ---
    
    def get_current_driver_info(vehicle_id):
        """الحصول على معلومات السائق الحالي للسيارة"""
        try:
            # البحث عن آخر سجل تسليم (delivery) للسيارة
            last_delivery = VehicleHandover.query.filter_by(
                vehicle_id=vehicle_id,
                handover_type='delivery'
            ).order_by(VehicleHandover.handover_date.desc()).first()
            
            if last_delivery:
                driver_info = {
                    'name': last_delivery.person_name or '',
                    'phone': last_delivery.driver_phone_number or '',
                    'national_id': last_delivery.driver_residency_number or '',
                    'employee_id': last_delivery.employee_id or ''
                }
                
                # إذا كان هناك معرف موظف، اجلب معلومات إضافية
                if last_delivery.employee_id:
                    employee = Employee.query.get(last_delivery.employee_id)
                    if employee:
                        driver_info['name'] = employee.name
                        driver_info['phone'] = employee.mobilePersonal or employee.mobile or ''
                        driver_info['national_id'] = employee.national_id or ''
                        driver_info['department'] = employee.departments[0].name if employee.departments else 'غير محدد'
                
                return driver_info
        except Exception as e:
            current_app.logger.error(f'خطأ في جلب معلومات السائق الحالي: {str(e)}')
        
        return {'name': '', 'phone': '', 'national_id': '', 'employee_id': ''}
    
    @bp.route('/vehicles/quick_return', methods=['POST'])
    @login_required
    def quick_vehicle_return():
        """استلام سريع للسيارة لتحريرها للاستخدام"""
        try:
            vehicle_id = request.form.get('vehicle_id')
            return_date = request.form.get('return_date')
            return_time = request.form.get('return_time') 
            return_reason = request.form.get('return_reason')
            current_mileage = request.form.get('current_mileage')
            notes = request.form.get('notes', '')
            
            if not vehicle_id or not return_date or not return_time:
                flash('جميع الحقول مطلوبة', 'error')
                return redirect(url_for('mobile.create_handover_mobile'))
            
            # التحقق من وجود السيارة
            vehicle = Vehicle.query.get_or_404(vehicle_id)
            
            # الحصول على معلومات السائق الحالي
            current_driver = get_current_driver_info(vehicle_id)
            
            # إنشاء سجل استلام جديد
            return_handover = VehicleHandover(
                vehicle_id=vehicle_id,
                handover_type='return',
                handover_date=datetime.strptime(return_date, '%Y-%m-%d').date(),
                handover_time=datetime.strptime(return_time, '%H:%M').time() if return_time else None,
                person_name=current_driver.get('name', ''),
                person_phone=current_driver.get('phone', ''),
                person_national_id=current_driver.get('national_id', ''),
                employee_id=current_driver.get('employee_id'),
                mileage=int(current_mileage) if current_mileage else 0,
                notes=f"استلام سريع - {return_reason}. {notes}".strip(),
                created_by=current_user.id,
                created_at=datetime.now()
            )
            
            db.session.add(return_handover)
            
            # تحديث حالة السيارة لتصبح متاحة
            vehicle.status = 'available'
            vehicle.current_driver = None
            
            db.session.commit()
            
            flash(f'تم استلام السيارة {vehicle.plate_number} بنجاح وأصبحت متاحة للاستخدام', 'success')
            return redirect(url_for('mobile.create_handover_mobile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'خطأ في الاستلام السريع: {str(e)}')
            flash('حدث خطأ أثناء استلام السيارة. يرجى المحاولة مرة أخرى.', 'error')
            return redirect(url_for('mobile.create_handover_mobile'))
    
    @bp.route('/get_vehicle_driver_info/<int:vehicle_id>')
    @login_required
    def get_vehicle_driver_info(vehicle_id):
        """API لجلب معلومات السائق الحالي للسيارة"""
        try:
            vehicle = Vehicle.query.get_or_404(vehicle_id)
            current_driver = get_current_driver_info(vehicle_id)
            
            return jsonify({
                'success': True,
                'vehicle_info': {
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'status': vehicle.status
                },
                'driver_info': current_driver
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # تعديل سجل الورشة - النسخة المحمولة
