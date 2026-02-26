"""
Bank Transfer File Generator Service
خدمة إنشاء ملفات التحويل البنكي
تتوافق مع معايير البنوك السعودية
"""
from datetime import datetime
from decimal import Decimal
from io import StringIO, BytesIO
from sqlalchemy import func
from src.core.extensions import db
from models import Employee
from src.modules.payroll.domain.models import PayrollRecord, BankTransferFile


class BankTransferGenerator:
    """منشئ ملفات التحويل البنكي"""
    
    # رموز البنوك السعودية الرئيسية
    BANK_CODES = {
        'NCB': '0010',      # البنك الأهلي
        'RIYAD': '0020',    # بنك الرياض
        'SAMBA': '0030',    # بنك سامبا
        'RAJHI': '0040',    # البنك الراجحي
        'ALAHLI': '0010',   # البنك الأهلي
        'ADIB': '0050',     # بنك الإمارات
        'ALINMA': '0060',   # بنك الإنماء
        'BANQUE': '0070',   # بنك بنكة
        'FALASA': '0080',   # بنك بلاسة
        'FRANCO': '0090',   # بنك فرانكو
        'GIB': '0100',      # البنك الخليجي
        'GULF': '0110',     # خليج بنك
        'HABIB': '0120',    # بنك الحبيب
        'INVESTCORP': '0130', # إنفست كوربوريشن
        'SAUDI': '0140',    # البنك السعودي للاستثمار
    }
    
    def __init__(self, pay_period_year: int, pay_period_month: int, bank_code: str = 'NCB'):
        self.pay_period_year = pay_period_year
        self.pay_period_month = pay_period_month
        self.bank_code = bank_code
        self.payroll_records = self._get_approved_payrolls()
    
    def _get_approved_payrolls(self) -> list:
        """جلب سجلات الرواتب المعتمدة"""
        records = PayrollRecord.query.filter_by(
            pay_period_year=self.pay_period_year,
            pay_period_month=self.pay_period_month,
            payment_status='approved',
            is_exported=False
        ).all()
        
        return records
    
    def _get_bank_name(self) -> str:
        """الحصول على اسم البنك"""
        bank_names = {
            'NCB': 'البنك الأهلي السعودي',
            'RIYAD': 'بنك الرياض',
            'SAMBA': 'بنك سامبا',
            'RAJHI': 'البنك الراجحي',
            'ALINMA': 'بنك الإنماء',
            'BANQUE': 'بنك بنكة',
        }
        return bank_names.get(self.bank_code, 'البنك غير محدد')
    
    def generate_txt_format(self) -> str:
        """
        إنشاء ملف بصيغة نصية (TXT) للتحويل البنكي
        الصيغة القياسية للبنوك السعودية
        """
        lines = []
        
        # رأس الملف
        header = self._generate_header()
        lines.append(header)
        
        # تفاصيل البيانات
        total_amount = Decimal('0')
        record_count = 0
        
        for payroll in self.payroll_records:
            employee = payroll.employee
            
            # التحقق من وجود معلومات البنك
            if not employee.bank_account:
                continue
            
            record_count += 1
            total_amount += payroll.net_payable
            
            detail_line = self._generate_detail_line(employee, payroll, record_count)
            lines.append(detail_line)
        
        # ذيل الملف
        footer = self._generate_footer(record_count, total_amount)
        lines.append(footer)
        
        return '\n'.join(lines)
    
    def generate_csv_format(self) -> str:
        """
        إنشاء ملف بصيغة CSV
        أسهل للاستيراد والمعالجة
        """
        lines = []
        
        # رأس العمود
        header = 'الاسم,رقم الموظف,رقم الحساب,البنك,المبلغ,التاريخ,الوصف'
        lines.append(header)
        
        for payroll in self.payroll_records:
            employee = payroll.employee
            
            if not employee.bank_account:
                continue
            
            line = f'{employee.name},{employee.employee_id},{employee.bank_account},{employee.bank_name or self._get_bank_name()},{payroll.net_payable},{datetime.now().strftime("%Y-%m-%d")},راتب الموظف'
            lines.append(line)
        
        return '\n'.join(lines)
    
    def generate_xml_format(self) -> str:
        """
        إنشاء ملف بصيغة XML
        صيغة محسنة للتكامل مع الأنظمة
        """
        xml_lines = []
        
        xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        xml_lines.append('<BankTransferFile>')
        
        # معلومات الجلسة
        xml_lines.append(f'  <Header>')
        xml_lines.append(f'    <BankCode>{self.bank_code}</BankCode>')
        xml_lines.append(f'    <BankName>{self._get_bank_name()}</BankName>')
        xml_lines.append(f'    <PayPeriod>{self.pay_period_month}/{self.pay_period_year}</PayPeriod>')
        xml_lines.append(f'    <GeneratedDate>{datetime.now().isoformat()}</GeneratedDate>')
        xml_lines.append(f'  </Header>')
        
        # البيانات
        xml_lines.append(f'  <Transactions>')
        
        total_amount = Decimal('0')
        record_count = 0
        
        for payroll in self.payroll_records:
            employee = payroll.employee
            
            if not employee.bank_account:
                continue
            
            record_count += 1
            total_amount += payroll.net_payable
            
            xml_lines.append(f'    <Transaction>')
            xml_lines.append(f'      <EmployeeId>{employee.employee_id}</EmployeeId>')
            xml_lines.append(f'      <EmployeeName>{employee.name}</EmployeeName>')
            xml_lines.append(f'      <BankAccount>{employee.bank_account}</BankAccount>')
            xml_lines.append(f'      <Amount>{payroll.net_payable}</Amount>')
            xml_lines.append(f'      <PayPeriod>{self.pay_period_month}/{self.pay_period_year}</PayPeriod>')
            xml_lines.append(f'      <GrossSalary>{payroll.gross_salary}</GrossSalary>')
            xml_lines.append(f'      <Deductions>{payroll.total_deductions}</Deductions>')
            xml_lines.append(f'      <NetPayable>{payroll.net_payable}</NetPayable>')
            xml_lines.append(f'    </Transaction>')
        
        xml_lines.append(f'  </Transactions>')
        
        # الملخص
        xml_lines.append(f'  <Summary>')
        xml_lines.append(f'    <TotalRecords>{record_count}</TotalRecords>')
        xml_lines.append(f'    <TotalAmount>{total_amount}</TotalAmount>')
        xml_lines.append(f'  </Summary>')
        
        xml_lines.append('</BankTransferFile>')
        
        return '\n'.join(xml_lines)
    
    def _generate_header(self) -> str:
        """إنشاء رأس الملف"""
        # تنسيق رأس البنك السعودي القياسي
        header_parts = [
            '001',  # نوع السجل
            self.BANK_CODES.get(self.bank_code, '0010'),  # رمز البنك
            datetime.now().strftime('%Y%m%d'),  # التاريخ
            datetime.now().strftime('%H%M%S'),  # الوقت
            'PAYROLL',  # نوع الملف
        ]
        return '|'.join(header_parts)
    
    def _generate_detail_line(self, employee: Employee, payroll: PayrollRecord, sequence_no: int) -> str:
        """إنشاء سطر بيانات موظف واحد"""
        detail_parts = [
            '002',  # نوع السجل
            str(sequence_no).zfill(6),  # رقم تسلسلي
            employee.employee_id,  # رقم الموظف
            employee.name[:30],  # اسم الموظف
            employee.bank_account,  # رقم الحساب
            str(int(payroll.net_payable * 100)).zfill(12),  # المبلغ بالهللة
            datetime.now().strftime('%Y%m%d'),  # تاريخ القيد
        ]
        return '|'.join(detail_parts)
    
    def _generate_footer(self, record_count: int, total_amount: Decimal) -> str:
        """إنشاء ذيل الملف"""
        footer_parts = [
            '999',  # نوع السجل
            str(record_count).zfill(6),  # عدد السجلات
            str(int(total_amount * 100)).zfill(15),  # الإجمالي
            datetime.now().strftime('%Y%m%d'),  # التاريخ
        ]
        return '|'.join(footer_parts)
    
    def create_transfer_file(self, file_format: str = 'txt') -> BankTransferFile:
        """
        إنشاء ملف التحويل البنكي وحفظه
        """
        # توليد الملف بناءً على الصيغة
        if file_format.lower() == 'txt':
            content = self.generate_txt_format()
            file_extension = 'txt'
        elif file_format.lower() == 'csv':
            content = self.generate_csv_format()
            file_extension = 'csv'
        elif file_format.lower() == 'xml':
            content = self.generate_xml_format()
            file_extension = 'xml'
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # إنشاء اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'bank_transfer_{self.bank_code}_{self.pay_period_month:02d}_{self.pay_period_year}_{timestamp}.{file_extension}'
        
        # حفظ الملف
        file_path = f'static/payroll_exports/{file_name}'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # حساب الإحصائيات
        total_amount = sum(p.net_payable for p in self.payroll_records)
        
        # إنشاء سجل في قاعدة البيانات
        transfer_file = BankTransferFile(
            file_name=file_name,
            file_path=file_path,
            file_format=file_extension,
            pay_period_year=self.pay_period_year,
            pay_period_month=self.pay_period_month,
            bank_code=self.bank_code,
            bank_name=self._get_bank_name(),
            total_records=len(self.payroll_records),
            total_amount=total_amount,
            status='ready'
        )
        
        db.session.add(transfer_file)
        db.session.commit()
        
        return transfer_file
    
    def export_to_excel_sheet(self, workbook):
        """
        إضافة ورقة تحويل بنكي إلى ملف Excel
        """
        worksheet = workbook.create_sheet('Bank_Transfer_File')
        
        # الرؤوس
        headers = ['رقم الموظف', 'اسم الموظف', 'رقم الحساب', 'البنك', 'المبلغ الصافي', 'الراتب الإجمالي', 'الخصومات']
        
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF')
        
        # البيانات
        row = 2
        for payroll in self.payroll_records:
            employee = payroll.employee
            
            worksheet.cell(row=row, column=1).value = employee.employee_id
            worksheet.cell(row=row, column=2).value = employee.name
            worksheet.cell(row=row, column=3).value = employee.bank_account
            worksheet.cell(row=row, column=4).value = employee.bank_name or self._get_bank_name()
            worksheet.cell(row=row, column=5).value = float(payroll.net_payable)
            worksheet.cell(row=row, column=6).value = float(payroll.gross_salary)
            worksheet.cell(row=row, column=7).value = float(payroll.total_deductions)
            
            row += 1
        
        # تنسيق الأعمدة
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 25
        worksheet.column_dimensions['C'].width = 20
        worksheet.column_dimensions['D'].width = 25
        worksheet.column_dimensions['E'].width = 15
        worksheet.column_dimensions['F'].width = 15
        worksheet.column_dimensions['G'].width = 15
        
        return worksheet
