"""
مُصدِّر ملفات Excel الاحترافي
============================
معالجة إنشاء وتصدير ملفات Excel الاحترافية
"""

from typing import Tuple, Optional
from io import BytesIO
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
import os

from .report_builder import ReportBuilder


class ExcelExporter:
    """مُصدِّر ملفات Excel"""
    
    def __init__(self, reports_dir: str = 'instance/reports'):
        """
        تهيئة المُصدِّر
        
        Args:
            reports_dir: مجلد حفظ التقارير
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.report_builder = ReportBuilder()
    
    def generate_report(self) -> Tuple[BytesIO, str]:
        """
        إنشاء تقرير احترافي
        
        Returns:
            (BytesIO buffer, filename)
        """
        try:
            # إنشاء دفتر العمل
            workbook = Workbook()
            
            # حذف الورقة الافتراضية
            if 'Sheet' in workbook.sheetnames:
                del workbook['Sheet']
            
            # بناء التقرير الكامل
            workbook = self.report_builder.build_complete_report(workbook)
            
            # حفظ إلى BytesIO
            buffer = BytesIO()
            workbook.save(buffer)
            buffer.seek(0)
            
            # إنشاء اسم الملف
            filename = self._generate_filename()
            
            # حفظ نسخة محلية
            self._save_local_copy(workbook, filename)
            
            return buffer, filename
        except Exception as e:
            print(f"خطأ في إنشاء التقرير: {e}")
            raise
    
    def export_to_buffer(self) -> Tuple[BytesIO, str, str]:
        """
        تصدير التقرير إلى BytesIO
        
        Returns:
            (buffer, filename, mimetype)
        """
        buffer, filename = self.generate_report()
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return buffer, filename, mimetype
    
    def get_latest_report(self) -> Optional[Tuple[BytesIO, str, str]]:
        """
        الحصول على أحدث تقرير موجود
        
        Returns:
            (buffer, filename, mimetype) أو None
        """
        try:
            # البحث عن الملفات
            report_files = sorted(
                self.reports_dir.glob('Report_*.xlsx'),
                key=os.path.getctime,
                reverse=True
            )
            
            if report_files:
                latest_file = report_files[0]
                
                # قراءة الملف
                with open(latest_file, 'rb') as f:
                    buffer = BytesIO(f.read())
                
                filename = latest_file.name
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                
                return buffer, filename, mimetype
            
            return None
        except Exception as e:
            print(f"خطأ في الحصول على أحدث تقرير: {e}")
            return None
    
    def _generate_filename(self) -> str:
        """
        إنشاء اسم ملف فريد
        
        Returns:
            اسم الملف
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"Report_{timestamp}.xlsx"
    
    def _save_local_copy(self, workbook: Workbook, filename: str) -> None:
        """
        حفظ نسخة محلية من التقرير
        
        Args:
            workbook: دفتر العمل
            filename: اسم الملف
        """
        try:
            filepath = self.reports_dir / filename
            workbook.save(filepath)
            print(f"تم حفظ التقرير: {filepath}")
        except Exception as e:
            print(f"خطأ في حفظ النسخة المحلية: {e}")
    
    def cleanup_old_reports(self, keep_count: int = 10) -> None:
        """
        حذف التقارير القديمة
        
        Args:
            keep_count: عدد التقارير المحتفظ بها
        """
        try:
            report_files = sorted(
                self.reports_dir.glob('Report_*.xlsx'),
                key=os.path.getctime,
                reverse=True
            )
            
            # حذف التقارير الزائدة
            for file in report_files[keep_count:]:
                file.unlink()
                print(f"تم حذف: {file.name}")
        except Exception as e:
            print(f"خطأ في تنظيف التقارير القديمة: {e}")
