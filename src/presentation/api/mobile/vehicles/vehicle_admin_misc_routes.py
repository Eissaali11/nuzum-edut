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

def register_vehicle_admin_misc_routes(bp):
    @bp.route('/fees_old')
    @login_required
    def fees_old():
        """صفحة الرسوم والتكاليف للنسخة المحمولة (النسخة القديمة)"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # فلترة حسب نوع الوثيقة
        document_type = request.args.get('document_type', '')
        # فلترة حسب حالة الرسوم
        status = request.args.get('status', '')
        # فلترة حسب التاريخ
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
    
        # بناء استعلام قاعدة البيانات
        query = Fee.query
    
        # تطبيق الفلاتر إذا تم تحديدها
        if document_type:
            query = query.filter(Fee.document_type == document_type)
    
        if status:
            query = query.filter(Fee.payment_status == status)
    
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                query = query.filter(Fee.due_date >= from_date_obj)
            except ValueError:
                pass
    
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                query = query.filter(Fee.due_date <= to_date_obj)
            except ValueError:
                pass
    
        # تنفيذ الاستعلام مع الترتيب والتصفح
        paginator = query.order_by(Fee.due_date.asc()).paginate(page=page, per_page=per_page, error_out=False)
        fees = paginator.items
    
        # الحصول على أنواع الوثائق المتاحة
        document_types = db.session.query(Fee.document_type).distinct().all()
        document_types = [d[0] for d in document_types if d[0]]
    
        # حساب إجماليات الرسوم
        all_fees = query.all()
        fees_summary = {
            'pending_fees': sum(fee.total_fees for fee in all_fees if fee.payment_status == 'pending'),
            'paid_fees': sum(fee.total_fees for fee in all_fees if fee.payment_status == 'paid'),
            'total_fees': sum(fee.total_fees for fee in all_fees)
        }
    
        return render_template('mobile/fees.html', 
                              fees=fees, 
                              fees_summary=fees_summary,
                              pagination=paginator,
                              document_types=document_types,
                              selected_type=document_type,
                              selected_status=status,
                              from_date=from_date,
                              to_date=to_date)
    
    # إضافة رسم جديد - النسخة المحمولة
    @bp.route('/fees/add', methods=['GET', 'POST'])
    @login_required
    def add_fee():
        """إضافة رسم جديد للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/add_fee.html')
    
    # تعديل رسم - النسخة المحمولة
    @bp.route('/fees/<int:fee_id>/edit', methods=['POST'])
    @login_required
    def edit_fee(fee_id):
        """تعديل رسم قائم للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        if request.method == 'POST':
            # تحديث بيانات الرسم من النموذج
            fee.document_type = request.form.get('document_type')
    
            # تحديث تاريخ الاستحقاق
            due_date_str = request.form.get('due_date')
            if due_date_str:
                fee.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    
            # تحديث حالة الدفع
            fee.payment_status = request.form.get('payment_status')
    
            # تحديث تاريخ السداد إذا كانت الحالة "مدفوع"
            if fee.payment_status == 'paid':
                payment_date_str = request.form.get('payment_date')
                if payment_date_str:
                    fee.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            else:
                fee.payment_date = None
    
            # تحديث قيم الرسوم
            fee.passport_fee = float(request.form.get('passport_fee', 0))
            fee.labor_office_fee = float(request.form.get('labor_office_fee', 0))
            fee.insurance_fee = float(request.form.get('insurance_fee', 0))
            fee.social_insurance_fee = float(request.form.get('social_insurance_fee', 0))
    
            # تحديث حالة نقل الكفالة
            fee.transfer_sponsorship = 'transfer_sponsorship' in request.form
    
            # تحديث الملاحظات
            fee.notes = request.form.get('notes', '')
    
            # حفظ التغييرات في قاعدة البيانات
            try:
                db.session.commit()
                flash('تم تحديث الرسم بنجاح', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث الرسم: {str(e)}', 'danger')
    
        # العودة إلى صفحة تفاصيل الرسم
        return redirect(url_for('mobile.fee_details', fee_id=fee_id))
    
    # تسجيل رسم كمدفوع - النسخة المحمولة
    @bp.route('/fees/<int:fee_id>/mark-as-paid', methods=['POST'])
    @login_required
    def mark_fee_as_paid(fee_id):
        """تسجيل رسم كمدفوع للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        if request.method == 'POST':
            # تحديث حالة الدفع
            fee.payment_status = 'paid'
    
            # تحديث تاريخ السداد
            payment_date_str = request.form.get('payment_date')
            if payment_date_str:
                fee.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            else:
                fee.payment_date = datetime.now().date()
    
            # إضافة ملاحظات السداد إلى ملاحظات الرسم
            payment_notes = request.form.get('payment_notes')
            if payment_notes:
                if fee.notes:
                    fee.notes = f"{fee.notes}\n\nملاحظات السداد ({fee.payment_date}):\n{payment_notes}"
                else:
                    fee.notes = f"ملاحظات السداد ({fee.payment_date}):\n{payment_notes}"
    
            # حفظ التغييرات في قاعدة البيانات
            try:
                db.session.commit()
                flash('تم تسجيل الرسم كمدفوع بنجاح', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تسجيل الرسم كمدفوع: {str(e)}', 'danger')
    
        # العودة إلى صفحة تفاصيل الرسم
        return redirect(url_for('mobile.fee_details', fee_id=fee_id))
    
    # تفاصيل الرسم - النسخة المحمولة 
    @bp.route('/fees/<int:fee_id>')
    @login_required
    def fee_details(fee_id):
        """تفاصيل الرسم للنسخة المحمولة"""
        # الحصول على بيانات الرسم من قاعدة البيانات
        fee = Fee.query.get_or_404(fee_id)
    
        # إرسال التاريخ الحالي لاستخدامه في النموذج
        now = datetime.now()
    
        return render_template('mobile/fee_details.html', fee=fee, now=now)
    
    # صفحة الإشعارات - النسخة المحمولة
    @bp.route('/notifications')
    def notifications():
        """صفحة الإشعارات للنسخة المحمولة"""
        # إنشاء بيانات إشعارات تجريبية
        notifications = [
            {
                'id': '1',
                'type': 'document',
                'title': 'وثيقة على وشك الانتهاء: جواز سفر',
                'message': 'متبقي 10 أيام على انتهاء جواز السفر',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': False
            },
            {
                'id': '2',
                'type': 'fee',
                'title': 'رسوم مستحقة قريباً: تأشيرة',
                'message': 'رسوم مستحقة بعد 5 أيام بقيمة 2000.00',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': False
            },
            {
                'id': '3',
                'type': 'system',
                'title': 'تحديث في النظام',
                'message': 'تم تحديث النظام إلى الإصدار الجديد',
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'is_read': True
            }
        ]
    
        pagination = {
            'page': 1,
            'per_page': 20,
            'total': len(notifications),
            'pages': 1,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None,
            'iter_pages': lambda: range(1, 2)
        }
    
        return render_template('mobile/notifications.html',
                              notifications=notifications,
                              pagination=pagination)
    
    # API endpoint لتعليم إشعار كمقروء
    @bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
    def mark_notification_as_read(notification_id):
        """تعليم إشعار كمقروء"""
        # في الإصدار الحقيقي سيتم حفظ حالة قراءة الإشعارات في قاعدة البيانات
    
        # للإصدار الحالي البسيط نستخدم session لتخزين الإشعارات المقروءة
        read_notifications = session.get('read_notifications', [])
    
        if notification_id not in read_notifications:
            read_notifications.append(notification_id)
            session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # API endpoint لتعليم جميع الإشعارات كمقروءة
    @bp.route('/api/notifications/read-all', methods=['POST'])
    def mark_all_notifications_as_read():
        """تعليم جميع الإشعارات كمقروءة"""
        # في الإصدار التجريبي، نعلم فقط الإشعارات التجريبية كمقروءة
        read_notifications = ['1', '2', '3']
        session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # API endpoint لحذف إشعار
    @bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
    def delete_notification(notification_id):
        """حذف إشعار"""
        # في الإصدار الحقيقي سيتم حذف الإشعار من قاعدة البيانات أو تحديث حالته
    
        # للإصدار الحالي البسيط نستخدم session لتخزين الإشعارات المحذوفة
        deleted_notifications = session.get('deleted_notifications', [])
    
        if notification_id not in deleted_notifications:
            deleted_notifications.append(notification_id)
            session['deleted_notifications'] = deleted_notifications
    
        # إذا كان الإشعار مقروءاً، نحذفه من قائمة الإشعارات المقروءة
        read_notifications = session.get('read_notifications', [])
        if notification_id in read_notifications:
            read_notifications.remove(notification_id)
            session['read_notifications'] = read_notifications
    
        return jsonify({'success': True})
    
    # صفحة الإعدادات - النسخة المحمولة
    @bp.route('/settings')
    @login_required
    def settings():
        """صفحة الإعدادات للنسخة المحمولة"""
        current_year = datetime.now().year
        return render_template('mobile/settings.html', current_year=current_year)
    
    # صفحة شروط الاستخدام - النسخة المحمولة
    @bp.route('/terms')
    def terms():
        """صفحة شروط الاستخدام للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/terms.html')
    
    # صفحة سياسة الخصوصية - النسخة المحمولة
    @bp.route('/privacy')
    def privacy():
        """صفحة سياسة الخصوصية للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/privacy.html')
    
    # صفحة تواصل معنا - النسخة المحمولة
    @bp.route('/contact')
    def contact():
        """صفحة تواصل معنا للنسخة المحمولة"""
        # يمكن تنفيذ هذه الوظيفة لاحقًا
        return render_template('mobile/contact.html')
    
    # صفحة التطبيق غير متصل بالإنترنت - النسخة المحمولة
    @bp.route('/offline')
    def offline():
        """صفحة التطبيق غير متصل بالإنترنت للنسخة المحمولة"""
        return render_template('mobile/offline.html')
    
    # نقطة نهاية للتحقق من حالة الاتصال - النسخة المحمولة
    @bp.route('/api/check-connection')
    def check_connection():
        """نقطة نهاية للتحقق من حالة الاتصال والتتبع للنسخة المحمولة"""
        try:
            # ✅ التحقق من اتصال قاعدة البيانات
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            
            return jsonify({
                'status': 'online',
                'tracking_status': 'active',
                'database': 'connected',
                'timestamp': datetime.now().isoformat(),
                'message': 'تطبيق النُظم جاهز'
            }), 200
        except Exception as e:
            # ❌ في حالة فشل الاتصال
            current_app.logger.error(f"Connection check failed: {str(e)}")
            return jsonify({
                'status': 'offline',
                'tracking_status': 'stopped',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
    
    
    @bp.route('/api/tracking-status/<int:employee_id>')
    def tracking_status(employee_id):
        """الحصول على حالة التتبع والموقع الحالي للموظف"""
        try:
            employee = Employee.query.get(employee_id)
            if not employee:
                return jsonify({
                    'success': False,
                    'tracking_status': 'unknown',
                    'error': 'الموظف غير موجود'
                }), 404
            
            # جلب آخر موقع
            latest_location = EmployeeLocation.query.filter_by(
                employee_id=employee_id
            ).order_by(EmployeeLocation.recorded_at.desc()).first()
            
            # جلب آخر جلسة جيوفنس
            from models import GeofenceSession
            latest_session = GeofenceSession.query.filter_by(
                employee_id=employee_id
            ).order_by(GeofenceSession.entry_time.desc()).first()
            
            tracking_active = latest_location is not None and (
                datetime.utcnow() - latest_location.recorded_at
            ).total_seconds() < 3600  # آخر ساعة
            
            return jsonify({
                'success': True,
                'tracking_status': 'active' if tracking_active else 'inactive',
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'employee_id': employee.employee_id
                },
                'location': {
                    'latitude': float(latest_location.latitude) if latest_location else None,
                    'longitude': float(latest_location.longitude) if latest_location else None,
                    'accuracy': float(latest_location.accuracy_m) if latest_location and latest_location.accuracy_m else None,
                    'recorded_at': latest_location.recorded_at.isoformat() if latest_location else None
                } if latest_location else None,
                'session': {
                    'entry_time': latest_session.entry_time.isoformat() if latest_session else None,
                    'exit_time': latest_session.exit_time.isoformat() if latest_session else None
                } if latest_session else None,
                'timestamp': datetime.now().isoformat()
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error getting tracking status: {str(e)}")
            return jsonify({
                'success': False,
                'tracking_status': 'error',
                'error': str(e)
            }), 500
    
    
    # تم حذف صفحة مصروفات الوقود كما هو مطلوب
    
    
    # ==================== مسارات إدارة المستخدمين - النسخة المحمولة المطورة ====================
    
    # صفحة إدارة المستخدمين - النسخة المحمولة المطورة
    @bp.route('/users_new')
    @login_required
    @module_access_required('users')
    def users_new():
        """صفحة إدارة المستخدمين للنسخة المحمولة المطورة"""
    
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # إنشاء الاستعلام الأساسي
        query = User.query
    
        # تطبيق الفلترة حسب الاستعلام
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(
                (User.name.like(search_term)) |
                (User.email.like(search_term))
            )
    
        # ترتيب النتائج
        query = query.order_by(User.name)
    
        # تنفيذ الاستعلام مع الصفحات
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
    
        return render_template('mobile/users_new.html',
                              users=users,
                              pagination=pagination)
    
    # إضافة مستخدم جديد - النسخة المحمولة المطورة
    @bp.route('/users_new/add', methods=['GET', 'POST'])
    @login_required
    @module_access_required('users')
    def add_user_new():
        """إضافة مستخدم جديد للنسخة المحمولة المطورة"""
    
        # معالجة النموذج المرسل
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
    
            # التحقق من البيانات المطلوبة
            if not (username and email and password and role):
                flash('جميع الحقول المطلوبة يجب ملؤها', 'danger')
                return render_template('mobile/add_user_new.html', roles=UserRole)
    
            # التحقق من عدم وجود البريد الإلكتروني مسبقاً
            if User.query.filter_by(email=email).first():
                flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                return render_template('mobile/add_user_new.html', roles=UserRole)
    
            # إنشاء مستخدم جديد
            new_user = User(
                username=username,
                email=email,
                role=role
            )
            new_user.set_password(password)
    
            try:
                db.session.add(new_user)
                db.session.commit()
    
                flash('تم إضافة المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.users_new'))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء إضافة المستخدم: {str(e)}', 'danger')
    
        # عرض النموذج
        return render_template('mobile/add_user_new.html', roles=UserRole)
    
    # تفاصيل المستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>')
    @login_required
    @module_access_required('users')
    def user_details_new(user_id):
        """تفاصيل المستخدم للنسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        return render_template('mobile/user_details_new.html', user=user)
    
    # تعديل بيانات المستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>/edit', methods=['GET', 'POST'])
    @login_required
    @module_access_required('users')
    def edit_user_new(user_id):
        """تعديل بيانات المستخدم للنسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        # معالجة النموذج المرسل
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            role = request.form.get('role')
            is_active = request.form.get('is_active') == 'on'
    
            # التحقق من البيانات المطلوبة
            if not (username and email and role):
                flash('جميع الحقول المطلوبة يجب ملؤها', 'danger')
                return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
            # التحقق من عدم وجود البريد الإلكتروني لمستخدم آخر
            email_user = User.query.filter_by(email=email).first()
            if email_user and email_user.id != user.id:
                flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
            # تحديث بيانات المستخدم
            user.name = username
            user.email = email
            user.role = role
            user.is_active = is_active
    
            # تحديث كلمة المرور إذا تم تقديمها
            new_password = request.form.get('password')
            if new_password:
                user.set_password(new_password)
    
            try:
                db.session.commit()
                flash('تم تحديث بيانات المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.user_details_new', user_id=user.id))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء تحديث بيانات المستخدم: {str(e)}', 'danger')
    
        # عرض النموذج
        return render_template('mobile/edit_user_new.html', user=user, roles=UserRole)
    
    # حذف مستخدم - النسخة المحمولة المطورة
    @bp.route('/users_new/<int:user_id>/delete', methods=['GET', 'POST'])
    @login_required
    @permission_required('users', 'delete')
    def delete_user_new(user_id):
        """حذف مستخدم من النسخة المحمولة المطورة"""
    
        user = User.query.get_or_404(user_id)
    
        # منع حذف المستخدم الحالي
        if user.id == current_user.id:
            flash('لا يمكنك حذف المستخدم الحالي', 'danger')
            return redirect(url_for('mobile.users_new'))
    
        if request.method == 'POST':
            try:
                # حذف المستخدم
                db.session.delete(user)
                db.session.commit()
    
                flash('تم حذف المستخدم بنجاح', 'success')
                return redirect(url_for('mobile.users_new'))
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء حذف المستخدم: {str(e)}', 'danger')
                return redirect(url_for('mobile.user_details_new', user_id=user.id))
    
        return render_template('mobile/delete_user_new.html', user=user)
    
    
    # ==================== مسارات الرسوم والتكاليف - النسخة المحمولة المطورة ====================
    
    # صفحة إدارة الرسوم والتكاليف - النسخة المحمولة المطورة
    @bp.route('/fees_new')
    @login_required
    @module_access_required('fees')
    def fees_new():
        """صفحة الرسوم والتكاليف للنسخة المحمولة المطورة"""
    
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
        status = request.args.get('status', 'all')
        document_type = request.args.get('document_type', 'all')
    
        # إنشاء الاستعلام الأساسي
        query = Fee.query.join(Document)
    
        # تطبيق الفلاتر
        if status != 'all':
            query = query.filter(Fee.payment_status == status)
    
        if document_type != 'all':
            query = query.filter(Fee.document_type == document_type)
    
        # البحث
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.join(Document.employee).filter(
                (Employee.name.like(search_term)) |
                (Employee.employee_id.like(search_term)) |
                (Document.document_number.like(search_term))
            )
    
        # ترتيب النتائج حسب تاريخ الاستحقاق (الأقرب أولاً)
        query = query.order_by(Fee.due_date)
    
        # تنفيذ الاستعلام مع الصفحات
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        fees = pagination.items
    
        # حساب إحصائيات الرسوم
        current_date = datetime.now().date()
        due_count = Fee.query.filter(Fee.due_date <= current_date, Fee.payment_status == 'pending').count()
        paid_count = Fee.query.filter(Fee.payment_status == 'paid').count()
        overdue_count = Fee.query.filter(Fee.due_date < current_date, Fee.payment_status == 'pending').count()
    
        stats = {
            'due': due_count,
            'paid': paid_count,
            'overdue': overdue_count,
            'total': Fee.query.count()
        }
    
        # أنواع الوثائق للفلترة
        document_types = [
            'هوية وطنية',
            'إقامة',
            'جواز سفر',
            'رخصة قيادة',
            'شهادة صحية',
            'شهادة تأمين',
            'أخرى'
        ]
    
        return render_template('mobile/fees_new.html',
                              fees=fees,
                              pagination=pagination,
                              stats=stats,
                              document_types=document_types,
                              current_date=current_date,
                              selected_status=status,
                              selected_document_type=document_type)
    
    # ==================== مسارات الإشعارات - النسخة المحمولة المطورة ====================
    
    @bp.route('/notifications_new')
    @login_required
    def notifications_new():
        """صفحة الإشعارات للنسخة المحمولة المطورة"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # عدد العناصر في الصفحة الواحدة
    
        # هنا يمكن تنفيذ استعلام الإشعارات بناءً على نظام الإشعارات المستخدم
    
        # مثال: استعلام للوثائق التي على وشك الانتهاء كإشعارات
        current_date = datetime.now().date()
        expiring_30_days = current_date + timedelta(days=30)
        expiring_documents = Document.query.filter(
            Document.expiry_date > current_date,
            Document.expiry_date <= expiring_30_days
        ).order_by(Document.expiry_date).all()
    
        # مثال: الرسوم المستحقة (استخدام النموذج المتاح Fee المستورد من FeesCost)
        # ملاحظة: تم تعديل هذا الجزء لاستخدام النموذج المتاح بدلاً من الأصلي
        due_fees = Fee.query.join(Document).filter(
            Document.expiry_date > current_date,
            Document.expiry_date <= current_date + timedelta(days=30)
        ).order_by(Document.expiry_date).all()
    
        # تحضير قائمة الإشعارات المدمجة
        notifications = []
    
        for doc in expiring_documents:
            remaining_days = (doc.expiry_date - current_date).days
            notifications.append({
                'id': f'doc_{doc.id}',
                'type': 'document',
                'title': f'وثيقة على وشك الانتهاء: {doc.document_type}',
                'description': f'متبقي {remaining_days} يوم على انتهاء {doc.document_type} للموظف {doc.employee.name}',
                'date': doc.expiry_date,
                'url': url_for('mobile.document_details', document_id=doc.id),
                'is_read': False  # يمكن تنفيذ حالة القراءة لاحقاً
            })
    
        for fee in due_fees:
            # استخدام تاريخ انتهاء الوثيقة المرتبطة بالرسوم
            doc = Document.query.get(fee.document_id)
            if not doc:
                continue
    
            remaining_days = (doc.expiry_date - current_date).days
            document_type = fee.document_type
            total_amount = sum([
                fee.passport_fee or 0,
                fee.labor_office_fee or 0,
                fee.insurance_fee or 0,
                fee.social_insurance_fee or 0
            ])
            notifications.append({
                'id': f'fee_{fee.id}',
                'type': 'fee',
                'title': f'رسوم مستحقة قريباً: {document_type}',
                'description': f'رسوم مستحقة بعد {remaining_days} يوم بقيمة {total_amount:.2f}',
                'date': doc.expiry_date,
                'url': url_for('mobile.fee_details', fee_id=fee.id),
                'is_read': False
            })
    
        # ترتيب الإشعارات حسب التاريخ (الأقرب أولاً)
        notifications.sort(key=lambda x: x['date'])
    
        # تقسيم النتائج
        total_notifications = len(notifications)
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_notifications)
        current_notifications = notifications[start_idx:end_idx]
    
        # إنشاء كائن تقسيم صفحات بسيط
        # نستخدم قاموس بدلاً من كائن Pagination لتبسيط التنفيذ
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_notifications,
            'pages': (total_notifications + per_page - 1) // per_page,
            'items': current_notifications,
            'has_prev': page > 1,
            'has_next': page < ((total_notifications + per_page - 1) // per_page),
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < ((total_notifications + per_page - 1) // per_page) else None
        }
    
        return render_template('mobile/notifications_new.html',
                              notifications=current_notifications,
                              pagination=pagination,
                              current_date=current_date)
    
    # إنشاء نموذج تسليم/استلام - النسخة المحمولة
