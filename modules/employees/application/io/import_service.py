"""Employee Excel import/export service."""
import pandas as pd
from io import BytesIO
from typing import Dict, List, Tuple

from core.extensions import db
from models import Employee, Department, SystemAudit
from utils.excel import parse_employee_excel


class ImportResult:
    """Result of import operation."""
    def __init__(self, success_count: int, error_count: int, error_details: List[str]):
        self.success_count = success_count
        self.error_count = error_count
        self.error_details = error_details
        self.success = error_count == 0
        
    @property
    def message(self) -> str:
        error_detail_str = ", ".join(self.error_details[:5])
        if len(self.error_details) > 5:
            error_detail_str += " وغيرها من الأخطاء..."
        
        if self.error_count > 0:
            return f'تم استيراد {self.success_count} موظف بنجاح و {self.error_count} فشل. {error_detail_str}'
        return f'تم استيراد {self.success_count} موظف بنجاح'
    
    @property
    def category(self) -> str:
        return 'warning' if self.error_count > 0 else 'success'


def process_employee_import(file) -> ImportResult:
    """
    Process Excel file and import employees.
    Returns ImportResult with success/error counts and details.
    """
    try:
        employees_data = parse_employee_excel(file)
        print(f"Parsed {len(employees_data)} employee records from Excel")
        
        success_count = 0
        error_count = 0
        error_details = []
        
        for index, data in enumerate(employees_data):
            try:
                print(f"Processing employee {index+1}: {data.get('name', 'Unknown')}")
                
                # Check for duplicate employee_id
                existing = Employee.query.filter_by(employee_id=data['employee_id']).first()
                if existing:
                    print(f"Employee with ID {data['employee_id']} already exists")
                    error_count += 1
                    error_details.append(f"الموظف برقم {data['employee_id']} موجود مسبقا")
                    continue
                
                # Check for duplicate national_id
                existing = Employee.query.filter_by(national_id=data['national_id']).first()
                if existing:
                    print(f"Employee with national ID {data['national_id']} already exists")
                    error_count += 1
                    error_details.append(f"الموظف برقم هوية {data['national_id']} موجود مسبقا")
                    continue
                
                # Extract department data
                department_name = data.pop('department', None)
                
                # Create employee
                employee = Employee(**data)
                db.session.add(employee)
                db.session.flush()
                
                # Handle department assignment
                if department_name:
                    department = Department.query.filter_by(name=department_name).first()
                    if department:
                        employee.departments.append(department)
                    else:
                        new_department = Department(name=department_name)
                        db.session.add(new_department)
                        db.session.flush()
                        employee.departments.append(new_department)
                
                db.session.commit()
                success_count += 1
                print(f"Successfully added employee: {data.get('name')}")
                
            except Exception as e:
                db.session.rollback()
                error_count += 1
                print(f"Error adding employee {index+1}: {str(e)}")
                error_details.append(f"خطأ في السجل {index+1}: {str(e)}")
        
        # Log the import
        result = ImportResult(success_count, error_count, error_details)
        
        details = f'تم استيراد {success_count} موظف بنجاح و {error_count} فشل'
        if error_details:
            error_detail_str = ", ".join(error_details[:5])
            if len(error_details) > 5:
                error_detail_str += " وغيرها من الأخطاء..."
            details += f". أخطاء: {error_detail_str}"
        
        audit = SystemAudit(
            action='import',
            entity_type='employee',
            entity_id=0,
            details=details
        )
        db.session.add(audit)
        db.session.commit()
        
        return result
        
    except Exception as e:
        return ImportResult(0, 1, [f'حدث خطأ أثناء استيراد الملف: {str(e)}'])


def generate_sample_import_template() -> BytesIO:
    """
    Generate Excel template with sample data for employee import.
    Returns BytesIO object ready for download.
    """
    template_data = {
        'الاسم الكامل': ['محمد أحمد علي', 'فاطمة سالم محمد'],
        'رقم الموظف': ['EMP001', 'EMP002'],
        'رقم الهوية الوطنية': ['1234567890', '0987654321'],
        'رقم الجوال': ['0501234567', '0509876543'],
        'الجوال الشخصي': ['0551234567', ''],
        'المسمى الوظيفي': ['مطور برمجيات', 'محاسبة'],
        'الحالة الوظيفية': ['active', 'active'],
        'الموقع': ['الرياض', 'جدة'],
        'المشروع': ['مشروع الرياض', 'مشروع جدة'],
        'البريد الإلكتروني': ['mohamed@company.com', 'fatima@company.com'],
        'الأقسام': ['تقنية المعلومات', 'المحاسبة'],
        'تاريخ الانضمام': ['2024-01-15', '2024-02-01'],
        'تاريخ انتهاء الإقامة': ['2025-12-31', '2025-11-30'],
        'حالة العقد': ['محدد المدة', 'دائم'],
        'حالة الرخصة': ['سارية', 'سارية'],
        'الجنسية': ['سعودي', 'مصري'],
        'ملاحظات': ['موظف متميز', '']
    }
    
    df = pd.DataFrame(template_data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sample data sheet
        df.to_excel(writer, sheet_name='البيانات النموذجية', index=False)
        
        # Empty sheet for actual import
        empty_df = pd.DataFrame(columns=template_data.keys())
        empty_df.to_excel(writer, sheet_name='استيراد الموظفين', index=False)
        
        # Instructions sheet
        instructions_data = {
            'العمود': list(template_data.keys()),
            'مطلوب/اختياري': [
                'مطلوب', 'مطلوب', 'مطلوب', 'مطلوب', 'اختياري', 'مطلوب',
                'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري', 
                'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري'
            ],
            'التنسيق المطلوب': [
                'نص', 'نص فريد', 'رقم من 10 أرقام', 'رقم جوال سعودي',
                'رقم جوال (اختياري)', 'نص', 'active/inactive/on_leave', 'نص',
                'نص', 'بريد إلكتروني صحيح', 'اسم القسم', 'YYYY-MM-DD',
                'YYYY-MM-DD', 'نص', 'نص', 'اسم الجنسية', 'نص (اختياري)'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='التعليمات', index=False)
    
    output.seek(0)
    
    # Log the download
    audit = SystemAudit(
        action='download_template',
        entity_type='employee_import',
        entity_id=0,
        details='تم تحميل قالب استيراد الموظفين المحسن'
    )
    db.session.add(audit)
    db.session.commit()
    
    return output


def generate_empty_import_template() -> BytesIO:
    """
    Generate empty Excel template for employee import.
    Returns BytesIO object ready for download.
    """
    empty_template_data = {
        'الاسم الكامل': [],
        'رقم الموظف': [],
        'رقم الهوية الوطنية': [],
        'رقم الجوال': [],
        'الجوال الشخصي': [],
        'المسمى الوظيفي': [],
        'الحالة الوظيفية': [],
        'الموقع': [],
        'المشروع': [],
        'البريد الإلكتروني': [],
        'الأقسام': [],
        'تاريخ الانضمام': [],
        'تاريخ انتهاء الإقامة': [],
        'حالة العقد': [],
        'حالة الرخصة': [],
        'الجنسية': [],
        'ملاحظات': []
    }
    
    df = pd.DataFrame(empty_template_data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Empty template
        df.to_excel(writer, sheet_name='استيراد الموظفين', index=False)
        
        # Instructions sheet with examples
        instructions_data = {
            'العمود': [
                'الاسم الكامل', 'رقم الموظف', 'رقم الهوية الوطنية', 'رقم الجوال',
                'الجوال الشخصي', 'المسمى الوظيفي', 'الحالة الوظيفية', 'الموقع',
                'المشروع', 'البريد الإلكتروني', 'الأقسام', 'تاريخ الانضمام',
                'تاريخ انتهاء الإقامة', 'حالة العقد', 'حالة الرخصة', 'الجنسية', 'ملاحظات'
            ],
            'مطلوب/اختياري': [
                'مطلوب', 'مطلوب', 'مطلوب', 'مطلوب', 'اختياري', 'مطلوب',
                'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري',
                'اختياري', 'اختياري', 'اختياري', 'اختياري', 'اختياري'
            ],
            'التنسيق المطلوب': [
                'نص', 'نص فريد', 'رقم من 10 أرقام', 'رقم جوال سعودي',
                'رقم جوال (اختياري)', 'نص', 'active/inactive/on_leave', 'نص',
                'نص', 'بريد إلكتروني صحيح', 'اسم القسم', 'YYYY-MM-DD',
                'YYYY-MM-DD', 'نص', 'نص', 'اسم الجنسية', 'نص (اختياري)'
            ],
            'مثال': [
                'محمد أحمد علي', 'EMP001', '1234567890', '0501234567',
                '0551234567', 'مطور برمجيات', 'active', 'الرياض',
                'مشروع الرياض', 'mohamed@company.com', 'تقنية المعلومات', '2024-01-15',
                '2025-12-31', 'محدد المدة', 'سارية', 'سعودي', 'موظف متميز'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='التعليمات والأمثلة', index=False)
    
    output.seek(0)
    
    # Log the download
    audit = SystemAudit(
        action='download_empty_template',
        entity_type='employee_import',
        entity_id=0,
        details='تم تحميل نموذج فارغ لاستيراد الموظفين'
    )
    db.session.add(audit)
    db.session.commit()
    
    return output
