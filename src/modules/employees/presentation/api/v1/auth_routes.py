import os
import jwt
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from sqlalchemy.orm import joinedload

from src.core.extensions import db
from models import (
    Employee, Department, EmployeeLocation, Attendance, Salary, 
    Document, EmployeeRequest, Vehicle, RequestStatus
)

logger = logging.getLogger(__name__)

auth_api_v1 = Blueprint('auth_api_v1', __name__, url_prefix='/api/v1')

def get_secret_key():
    secret = os.environ.get('SESSION_SECRET')
    if not secret:
        logger.error("SESSION_SECRET environment variable is required for JWT authentication")
    return secret

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'message': 'صيغة التوكن غير صحيحة. استخدم: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'التوكن مفقود'
            }), 401
        
        try:
            secret = get_secret_key()
            if not secret:
                return jsonify({'success': False, 'message': 'Server configuration error'}), 500
                
            data = jwt.decode(token, secret, algorithms=['HS256'])
            current_employee = Employee.query.filter_by(employee_id=data['employee_id']).first()
            
            if not current_employee:
                return jsonify({
                    'success': False,
                    'message': 'الموظف غير موجود'
                }), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'message': 'التوكن منتهي الصلاحية'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'message': 'التوكن غير صالح'
            }), 401
        
        return f(current_employee, *args, **kwargs)
    
    return decorated

@auth_api_v1.route('/auth/login', methods=['POST'])
def login():
    """
    تسجيل الدخول والحصول على JWT Token
    """
    data = request.get_json()
    
    if not data or not data.get('employee_id') or not data.get('national_id'):
        return jsonify({
            'success': False,
            'message': 'رقم الموظف ورقم الهوية مطلوبان'
        }), 400
    
    try:
        result = db.session.execute(text("""
            SELECT id FROM employee 
            WHERE national_id::text = :national_id 
            AND employee_id::text = :employee_id
            AND status = 'active'
            LIMIT 1
        """), {
            'national_id': data['national_id'],
            'employee_id': data['employee_id']
        }).fetchone()
        
        employee = Employee.query.get(result[0]) if result else None
        
    except Exception as e:
        logger.error(f"Database error during login: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء تسجيل الدخول'
        }), 500
    
    if not employee:
        return jsonify({
            'success': False,
            'message': 'بيانات الدخول غير صحيحة أو الحساب غير نشط'
        }), 401
    
    secret = get_secret_key()
    if not secret:
        return jsonify({'success': False, 'message': 'Server configuration error'}), 500
        
    token = jwt.encode({
        'employee_id': employee.employee_id,
        'exp': datetime.utcnow() + timedelta(days=30)
    }, secret, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'employee': {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.name,
            'email': employee.email,
            'job_title': employee.job_title,
            'department': employee.department.name if employee.department else None,
            'profile_image': employee.profile_image,
            'mobile': employee.mobile,
            'status': employee.status
        }
    }), 200

@auth_api_v1.route('/employee/complete-profile', methods=['POST'])
@token_required
def get_employee_complete_profile_jwt(current_employee):
    """
    جلب الملف الشامل للموظف (محمي بـ JWT)
    """
    try:
        from src.routes.api_external import (
            parse_date_filters, get_employee_data, get_vehicle_assignments,
            get_attendance_records, get_salary_records, get_operations_records,
            calculate_statistics
        )
        
        # الحصول على البيانات (اختياري)
        data = request.get_json() or {}
        
        # تحليل فلاتر التواريخ
        try:
            start_date, end_date = parse_date_filters(data)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': 'طلب غير صحيح',
                'error': str(e)
            }), 400
        
        # جلب معلومات الموظف
        request_origin = request.host_url.rstrip('/')
        employee_data = get_employee_data(current_employee, request_origin)
        
        # جلب السيارات
        current_car, previous_cars = get_vehicle_assignments(current_employee.id)
        
        # جلب الحضور
        attendance = get_attendance_records(current_employee.id, start_date, end_date)
        
        # جلب الرواتب
        salaries = get_salary_records(current_employee.id, start_date, end_date)
        
        # جلب العمليات
        operations = get_operations_records(current_employee.id)
        
        # حساب الإحصائيات
        statistics = calculate_statistics(attendance, salaries, current_car, previous_cars, operations)
        
        # بناء الاستجابة
        response_data = {
            'employee': employee_data,
            'current_car': current_car,
            'previous_cars': previous_cars,
            'attendance': attendance,
            'salaries': salaries,
            'operations': operations,
            'statistics': statistics
        }
        
        logger.info(f"✅ تم جلب الملف الشامل للموظف {current_employee.name} ({current_employee.employee_id}) عبر JWT")
        
        return jsonify({
            'success': True,
            'message': 'تم جلب البيانات بنجاح',
            'data': response_data
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ في جلب الملف الشامل للموظف: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء جلب التفاصيل',
            'error': str(e)
        }), 500

@auth_api_v1.route('/employees/all-data', methods=['GET'])
def get_all_employees_complete_data():
    """
    إرجاع جميع بيانات جميع الموظفين بشكل شامل وكامل
    """
    try:
        # معاملات الفلترة
        department_id = request.args.get('department_id', type=int)
        status = request.args.get('status', 'active')
        has_location = request.args.get('has_location', type=lambda v: v.lower() == 'true')
        with_vehicle = request.args.get('with_vehicle', type=lambda v: v.lower() == 'true')
        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        # بناء الاستعلام الأساسي مع تحميل جميع العلاقات مسبقاً (تجنب N+1 queries)
        query = db.session.query(Employee).options(
            joinedload(Employee.departments),
            joinedload(Employee.nationality_rel)
        )
        
        # تطبيق الفلاتر
        if status:
            query = query.filter(Employee.status == status)
        
        if department_id:
            query = query.join(Employee.departments).filter(Department.id == department_id)
        
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Employee.name.like(search_pattern),
                    Employee.employee_id.like(search_pattern),
                    Employee.national_id.like(search_pattern)
                )
            )
        
        # إجمالي العدد قبل الترقيم
        total_employees = query.count()
        
        # تطبيق الترقيم
        employees = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # إحصائيات عامة
        total_active = db.session.query(Employee).filter(Employee.status == 'active').count()
        employees_with_location_count = 0
        employees_with_vehicle_count = 0
        
        # بناء قائمة البيانات الكاملة
        employees_data = []
        
        for emp in employees:
            # 1. البيانات الشخصية الأساسية
            employee_dict = {
                'id': emp.id,
                'employee_id': emp.employee_id,
                'name': emp.name,
                'national_id': emp.national_id,
                'mobile': emp.mobile,
                'mobile_personal': emp.mobilePersonal,
                'email': emp.email,
                'job_title': emp.job_title,
                'status': emp.status,
                'employee_type': emp.employee_type,
                'contract_type': emp.contract_type,
                'birth_date': emp.birth_date.isoformat() if emp.birth_date else None,
                'join_date': emp.join_date.isoformat() if emp.join_date else None,
                'profile_image': emp.profile_image,
                'national_id_image': emp.national_id_image,
                'license_image': emp.license_image,
                'bank_iban_image': emp.bank_iban_image,
                'created_at': emp.created_at.isoformat() if emp.created_at else None,
                'updated_at': emp.updated_at.isoformat() if emp.updated_at else None
            }
            
            # 2. معلومات القسم/الأقسام
            departments_list = []
            if emp.departments:
                for dept in emp.departments:
                    departments_list.append({
                        'id': dept.id,
                        'name': dept.name,
                        'description': dept.description
                    })
            employee_dict['departments'] = departments_list
            employee_dict['primary_department'] = departments_list[0] if departments_list else None
            
            # 3. معلومات الجنسية
            if emp.nationality_rel:
                employee_dict['nationality'] = {
                    'id': emp.nationality_rel.id,
                    'name_ar': emp.nationality_rel.name_ar,
                    'name_en': emp.nationality_rel.name_en,
                    'country_code': emp.nationality_rel.country_code
                }
            else:
                employee_dict['nationality'] = {
                    'name_ar': emp.nationality,
                    'name_en': None,
                    'country_code': None
                } if emp.nationality else None
            
            # 4. معلومات الراتب
            employee_dict['salary_info'] = {
                'basic_salary': float(emp.basic_salary) if emp.basic_salary else 0.0,
                'daily_wage': float(emp.daily_wage) if emp.daily_wage else 0.0,
                'attendance_bonus': float(emp.attendance_bonus) if emp.attendance_bonus else 0.0,
                'has_national_balance': emp.has_national_balance,
                'bank_iban': emp.bank_iban
            }
            
            # 5. معلومات الكفالة
            employee_dict['sponsorship'] = {
                'status': emp.sponsorship_status,
                'current_sponsor': emp.current_sponsor_name
            }
            
            # 6. معلومات السكن
            employee_dict['housing'] = {
                'residence_details': emp.residence_details,
                'residence_location_url': emp.residence_location_url,
                'housing_images': emp.housing_images.split(',') if emp.housing_images else [],
                'housing_drive_links': emp.housing_drive_links.split(',') if emp.housing_drive_links else []
            }
            
            # 7. معلومات العهدة
            employee_dict['custody'] = {
                'has_mobile_custody': emp.has_mobile_custody,
                'mobile_type': emp.mobile_type,
                'mobile_imei': emp.mobile_imei
            }
            
            # 8. مقاسات الزي
            employee_dict['uniform_sizes'] = {
                'pants_size': emp.pants_size,
                'shirt_size': emp.shirt_size
            }
            
            # 9. حالات المستندات
            employee_dict['documents_status'] = {
                'contract_status': emp.contract_status,
                'license_status': emp.license_status
            }
            
            # 10. آخر موقع GPS
            latest_location = db.session.query(EmployeeLocation)\
                .filter(EmployeeLocation.employee_id == emp.id)\
                .order_by(EmployeeLocation.recorded_at.desc())\
                .first()
            
            if latest_location:
                employees_with_location_count += 1
                time_diff = datetime.utcnow() - latest_location.recorded_at
                minutes_ago = int(time_diff.total_seconds() / 60)
                
                # حساب time_ago بالعربية
                if minutes_ago < 1:
                    time_ago = "الآن"
                elif minutes_ago < 60:
                    time_ago = f"قبل {minutes_ago} دقيقة"
                elif minutes_ago < 1440:  # أقل من يوم
                    hours_ago = minutes_ago // 60
                    time_ago = f"قبل {hours_ago} ساعة"
                else:
                    days_ago = minutes_ago // 1440
                    time_ago = f"قبل {days_ago} يوم"
                
                # تحديد إذا كان يتحرك (سرعة > 5 km/h)
                is_moving = latest_location.speed_kmh and float(latest_location.speed_kmh) > 5.0
                
                employee_dict['location'] = {
                    'has_location': True,
                    'latitude': float(latest_location.latitude),
                    'longitude': float(latest_location.longitude),
                    'accuracy_meters': float(latest_location.accuracy_m) if latest_location.accuracy_m else None,
                    'speed_kmh': float(latest_location.speed_kmh) if latest_location.speed_kmh else 0.0,
                    'is_moving': is_moving,
                    'recorded_at': latest_location.recorded_at.isoformat(),
                    'received_at': latest_location.received_at.isoformat(),
                    'time_ago': time_ago,
                    'minutes_ago': minutes_ago,
                    'source': latest_location.source,
                    'notes': latest_location.notes
                }
                
                # معلومات السيارة المرتبطة بالموقع
                if latest_location.vehicle_id:
                    location_vehicle = Vehicle.query.get(latest_location.vehicle_id)
                    if location_vehicle:
                        employee_dict['location']['vehicle'] = {
                            'id': location_vehicle.id,
                            'plate_number': location_vehicle.plate_number,
                            'make': location_vehicle.make,
                            'model': location_vehicle.model
                        }
            else:
                employee_dict['location'] = {
                    'has_location': False,
                    'message': 'لا يوجد موقع مسجل'
                }
            
            # 11. السيارة المخصصة الحالية (من آخر تسليم)
            from models import VehicleHandover
            latest_handover = db.session.query(VehicleHandover)\
                .filter(
                    VehicleHandover.employee_id == emp.id,
                    VehicleHandover.handover_type == 'delivery'
                )\
                .order_by(VehicleHandover.handover_date.desc())\
                .first()
            
            if latest_handover and latest_handover.vehicle:
                employees_with_vehicle_count += 1
                vehicle = latest_handover.vehicle
                employee_dict['assigned_vehicle'] = {
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'year': vehicle.year,
                    'color': vehicle.color,
                    'status': vehicle.status,
                    'handover_date': latest_handover.handover_date.isoformat() if latest_handover.handover_date else None,
                    'handover_mileage': latest_handover.mileage if latest_handover.mileage else None
                }
            else:
                employee_dict['assigned_vehicle'] = None
            
            # 12. إحصائيات الحضور (آخر 30 يوم)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            attendance_records = db.session.query(Attendance)\
                .filter(
                    Attendance.employee_id == emp.id,
                    Attendance.date >= thirty_days_ago.date()
                )\
                .all()
            
            present_count = sum(1 for a in attendance_records if a.status == 'present')
            absent_count = sum(1 for a in attendance_records if a.status == 'absent')
            leave_count = sum(1 for a in attendance_records if a.status == 'leave')
            
            employee_dict['attendance_stats'] = {
                'last_30_days': {
                    'total_days': len(attendance_records),
                    'present': present_count,
                    'absent': absent_count,
                    'leave': leave_count,
                    'attendance_rate': round((present_count / len(attendance_records) * 100), 2) if attendance_records else 0
                }
            }
            
            # 13. آخر سجلات الحضور (آخر 7 أيام)
            recent_attendance = db.session.query(Attendance)\
                .filter(Attendance.employee_id == emp.id)\
                .order_by(Attendance.date.desc())\
                .limit(7)\
                .all()
            
            employee_dict['recent_attendance'] = []
            for att in recent_attendance:
                employee_dict['recent_attendance'].append({
                    'date': att.date.isoformat(),
                    'status': att.status,
                    'check_in': att.check_in.isoformat() if att.check_in else None,
                    'check_out': att.check_out.isoformat() if att.check_out else None,
                    'notes': att.notes
                })
            
            # 14. آخر راتب
            latest_salary = db.session.query(Salary)\
                .filter(Salary.employee_id == emp.id)\
                .order_by(Salary.month.desc(), Salary.year.desc())\
                .first()
            
            if latest_salary:
                employee_dict['latest_salary'] = {
                    'month': latest_salary.month,
                    'year': latest_salary.year,
                    'basic_salary': float(latest_salary.basic_salary) if latest_salary.basic_salary else 0,
                    'attendance_bonus': float(latest_salary.attendance_bonus) if latest_salary.attendance_bonus else 0,
                    'allowances': float(latest_salary.allowances) if latest_salary.allowances else 0,
                    'deductions': float(latest_salary.deductions) if latest_salary.deductions else 0,
                    'attendance_deduction': float(latest_salary.attendance_deduction) if latest_salary.attendance_deduction else 0,
                    'bonus': float(latest_salary.bonus) if latest_salary.bonus else 0,
                    'net_salary': float(latest_salary.net_salary) if latest_salary.net_salary else 0,
                    'overtime_hours': float(latest_salary.overtime_hours) if latest_salary.overtime_hours else 0,
                    'is_paid': latest_salary.is_paid,
                    'absent_days': latest_salary.absent_days if latest_salary.absent_days else 0,
                    'present_days': latest_salary.present_days if latest_salary.present_days else 0,
                    'notes': latest_salary.notes
                }
            else:
                employee_dict['latest_salary'] = None
            
            # 15. المستندات (انتهاء الصلاحية)
            documents = db.session.query(Document)\
                .filter(Document.employee_id == emp.id)\
                .all()
            
            documents_list = []
            expired_count = 0
            expiring_soon_count = 0
            
            for doc in documents:
                doc_data = {
                    'id': doc.id,
                    'document_type': doc.document_type,
                    'document_number': doc.document_number,
                    'issue_date': doc.issue_date.isoformat() if doc.issue_date else None,
                    'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                    'file_path': doc.file_path
                }
                
                # حساب حالة الانتهاء
                if doc.expiry_date:
                    today = datetime.utcnow().date()
                    if doc.expiry_date < today:
                        doc_data['status'] = 'expired'
                        expired_count += 1
                    elif doc.expiry_date <= today + timedelta(days=30):
                        doc_data['status'] = 'expiring_soon'
                        expiring_soon_count += 1
                    else:
                        doc_data['status'] = 'valid'
                else:
                    doc_data['status'] = 'unknown'
                
                documents_list.append(doc_data)
            
            employee_dict['documents'] = {
                'total': len(documents_list),
                'expired': expired_count,
                'expiring_soon': expiring_soon_count,
                'list': documents_list
            }
            
            # 16. إحصائيات الطلبات
            requests_query = db.session.query(EmployeeRequest)\
                .filter(EmployeeRequest.employee_id == emp.id)
            
            total_requests = requests_query.count()
            pending_requests = requests_query.filter(EmployeeRequest.status == RequestStatus.PENDING).count()
            approved_requests = requests_query.filter(EmployeeRequest.status == RequestStatus.APPROVED).count()
            rejected_requests = requests_query.filter(EmployeeRequest.status == RequestStatus.REJECTED).count()
            
            # آخر طلب
            latest_request = requests_query.order_by(EmployeeRequest.created_at.desc()).first()
            
            employee_dict['requests_stats'] = {
                'total': total_requests,
                'pending': pending_requests,
                'approved': approved_requests,
                'rejected': rejected_requests,
                'last_request': {
                    'id': latest_request.id,
                    'type': latest_request.request_type.value if latest_request.request_type else None,
                    'status': latest_request.status.value if latest_request.status else None,
                    'created_at': latest_request.created_at.isoformat()
                } if latest_request else None
            }
            
            # 17. آخر طلبات (آخر 5 طلبات)
            recent_requests = requests_query.order_by(EmployeeRequest.created_at.desc()).limit(5).all()
            employee_dict['recent_requests'] = []
            
            for req in recent_requests:
                employee_dict['recent_requests'].append({
                    'id': req.id,
                    'type': req.request_type.value if req.request_type else None,
                    'status': req.status.value if req.status else None,
                    'title': req.title,
                    'amount': float(req.amount) if req.amount else None,
                    'created_at': req.created_at.isoformat()
                })
            
            employees_data.append(employee_dict)
        
        # تطبيق فلترة إضافية بعد جمع البيانات (للمواقع والسيارات)
        if has_location is not None:
            employees_data = [e for e in employees_data if e['location']['has_location'] == has_location]
        
        if with_vehicle is not None:
            employees_data = [e for e in employees_data if (e['assigned_vehicle'] is not None) == with_vehicle]
        
        # حساب الصفحات
        total_pages = (total_employees + per_page - 1) // per_page
        
        # الاستجابة النهائية
        return jsonify({
            'success': True,
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'total_employees': total_employees,
                'total_active': total_active,
                'employees_with_location': employees_with_location_count,
                'employees_with_vehicle': employees_with_vehicle_count,
                'filters_applied': {
                    'department_id': department_id,
                    'status': status,
                    'has_location': has_location,
                    'with_vehicle': with_vehicle,
                    'search': search_query
                }
            },
            'employees': employees_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_employees,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching all employees data: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'حدث خطأ أثناء جلب بيانات الموظفين',
            'error': str(e)
        }), 500
