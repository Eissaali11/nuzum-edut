#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تشخيص تسجيل Blueprint المركبات — التحقق من جميع الواردات والتوصيلات.
يُشغّل مع: python diagnostic_vehicle_blueprint.py

يقوم بـ:
1. محاكاة استيراد blueprint وتسجيل المسارات (مثل routes/vehicles.py)
2. الكشف عن أي فشل صامت في الاستيراد (Silent Import Failures)
3. الإبلاغ عن جميع المشاكل بشكل واضح وملون
4. إذا كان كل شيء جاهزاً: يطبع رسالة نجاح مفصلة
"""

import sys
import os
import traceback
import logging
from pathlib import Path

# إضافة المسار الحالي إلى sys.path للسماح بالاستيراد النسبي
sys.path.insert(0, str(Path(__file__).parent))

# عرض UTF-8 على Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# إعادة كتابة stdout و stderr لدعم UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# إعداد logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """طباعة عنوان قسم."""
    print(f"\n{'='*80}")
    print(f"  {title:^76}")
    print(f"{'='*80}\n")

def print_success(msg):
    """طباعة رسالة نجاح."""
    print(f"[OK] {msg}")

def print_error(msg):
    """طباعة رسالة خطأ."""
    print(f"[ERROR] {msg}")

def print_info(msg):
    """طباعة رسالة معلومات."""
    print(f"[INFO] {msg}")

def print_warning(msg):
    """طباعة رسالة تحذير."""
    print(f"[WARN] {msg}")

def test_import(module_path, item_name=None):
    """
    اختبار استيراد وحدة أو عنصر محدد.
    يُرجع: (success: bool, error_message: str or None)
    """
    try:
        if item_name:
            exec(f"from {module_path} import {item_name}")
            return True, None
        else:
            exec(f"import {module_path}")
            return True, None
    except Exception as e:
        return False, f"{module_path}.{item_name}: {str(e)}\n{traceback.format_exc()}"

def main():
    """البرنامج الرئيسي."""
    print_section("نظام تشخيص تسجيل Blueprint المركبات")
    
    errors = []
    warnings = []
    
    # ============================================================================
    # المرحلة 1: اختبار التوصيلات الأساسية
    # ============================================================================
    print_section("المرحلة 1: اختبار الواردات الأساسية (Flask، extensions)")
    
    basic_tests = [
        ("flask", "Flask"),
        ("core.extensions", "db"),
        ("core.extensions", "migrate"),
    ]
    
    for module, item in basic_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 2: اختبار نماذج Domain (المركبات)
    # ============================================================================
    print_section("المرحلة 2: اختبار نماذج Domain - المركبات")
    
    domain_tests = [
        ("domain.vehicles.models", "Vehicle"),
        ("domain.vehicles.models", "VehicleRental"),
        ("domain.vehicles.models", "VehicleWorkshop"),
        ("domain.vehicles.models", "VehicleWorkshopImage"),
        ("domain.vehicles.models", "VehicleProject"),
        ("domain.vehicles.models", "VehicleHandover"),
        ("domain.vehicles.models", "VehicleHandoverImage"),
        ("domain.vehicles.handover_models", "VehicleHandover"),
    ]
    
    for module, item in domain_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 3: اختبار نماذج Domain (الموظفين)
    # ============================================================================
    print_section("المرحلة 3: اختبار نماذج Domain - الموظفين")
    
    employee_domain_tests = [
        ("domain.employees.models", "Employee"),
        ("domain.employees.models", "Department"),
        ("domain.employees.models", "employee_departments"),
    ]
    
    for module, item in employee_domain_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 4: اختبار خدمات التطبيق (Application/Vehicles)
    # ============================================================================
    print_section("المرحلة 4: اختبار خدمات التطبيق - المركبات")
    
    app_services_tests = [
        ("application.vehicles.services", "list_vehicles_service"),
        ("application.vehicles.services", "get_vehicle_handover_context"),
        ("application.vehicles.workshop_services", "create_workshop_record_action"),
        ("application.vehicles.accident_services", "create_accident_record_action"),
        ("application.vehicles.vehicle_service", "get_index_context"),
    ]
    
    for module, item in app_services_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 5: اختبار وحدات التقديم (Presentation/Web/Vehicles)
    # ============================================================================
    print_section("المرحلة 5: اختبار وحدات التقديم - المركبات")
    
    presentation_tests = [
        ("presentation.web.vehicle_routes", "register_vehicle_routes"),
        ("presentation.web.vehicles.handover_routes", "register_handover_routes"),
        ("presentation.web.vehicles.workshop_routes", "register_workshop_routes"),
        ("presentation.web.vehicles.accident_routes", "register_accident_routes"),
        ("presentation.web.vehicles.vehicle_extra_routes", "register_vehicle_extra_routes"),
    ]
    
    for module, item in presentation_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 6: اختبار خدمات التصدير والإدارة
    # ============================================================================
    print_section("المرحلة 6: اختبار خدمات التصدير والإدارة")
    
    export_tests = [
        ("application.services.vehicle_list_service", "get_vehicle_list_payload"),
        ("application.services.vehicle_service", "get_vehicle_detail_data"),
        ("application.services.vehicle_management_service", "create_vehicle_record"),
        ("application.services.vehicle_export_service", "build_vehicles_excel"),
    ]
    
    for module, item in export_tests:
        success, error = test_import(module, item)
        if success:
            print_success(f"تم استيراد {item} من {module}")
        else:
            print_error(f"فشل استيراد {item} من {module}")
            errors.append(error)
    
    # ============================================================================
    # المرحلة 7: اختبار تسجيل Blueprint (المحاكاة)
    # ============================================================================
    print_section("المرحلة 7: اختبار تسجيل Blueprint - المحاكاة")
    
    try:
        print_info("يتم محاكاة تسجيل vehicles_bp...")
        
        # استيراد Flask وإنشاء app بسيط للاختبار
        from flask import Flask
        test_app = Flask(__name__)
        test_app.config['TESTING'] = True
        
        print_success("تم إنشاء Flask app اختباري")
        
        # استيراد المسارات (routes/vehicles.py)
        from routes.vehicles import vehicles_bp
        print_success("تم استيراد vehicles_bp من routes/vehicles.py")
        
        # التحقق من توفر المسارات
        route_count = 0
        for rule in vehicles_bp.url_map.iter_rules() if hasattr(vehicles_bp, 'url_map') else []:
            route_count += 1
        
        if route_count == 0:
            # إذا كان غير قابل للعدّ، ننتقل إلى التسجيل
            test_app.register_blueprint(vehicles_bp, url_prefix='/vehicles')
            print_success(f"تم تسجيل vehicles_bp على /vehicles")
            
            # الآن عدّ المسارات بعد التسجيل
            route_count = sum(1 for rule in test_app.url_map.iter_rules() if 'vehicles' in rule.rule)
            print_success(f"تم تسجيل {route_count} مسار تحت /vehicles")
        else:
            print_success(f"البلوبرينت يحتوي على {route_count} مسار")
        
    except Exception as e:
        print_error(f"فشل اختبار Blueprint: {str(e)}")
        errors.append(f"Blueprint Registration Error:\n{traceback.format_exc()}")
    
    # ============================================================================
    # الملخص النهائي
    # ============================================================================
    print_section("الملخص النهائي")
    
    if not errors:
        print_success("جميع الاختبارات نجحت!")
        print_success("النظام جاهز للتشغيل")
        print_info("يمكنك الآن تشغيل: python app.py أو flask run")
        return 0
    else:
        print_error(f"وجدت {len(errors)} أخطاء:")
        for i, error in enumerate(errors, 1):
            print_error(f"\n[خطأ {i}]")
            print(error)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
