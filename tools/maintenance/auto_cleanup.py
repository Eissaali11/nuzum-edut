#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-Cleanup Script for Nuzum HR System

يقوم بـ:
1. حذف ملفات التقارير المؤقتة (>48 ساعة)
2. تنظيف ملفات الـ Cache المنتهية الصلاحية
3. حذف الملفات المرفوعة غير المستخدمة
4. تنظيف سجلات النظام المؤرخة

يجب تشغيله بانتظام (scheduled task كل يوم)
"""

import os
import sys
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json

# إعداد Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ProjectCleaner:
    """فئة تقوم بتنظيف المشروع"""
    
    def __init__(self, base_path='d:\\nuzm', age_threshold_hours=48):
        """
        تهيئة المنظف
        
        المعاملات:
            base_path: مسار المشروع الأساسي
            age_threshold_hours: عدد الساعات لاعتبار الملف قديماً
        """
        self.base_path = Path(base_path)
        self.age_threshold = timedelta(hours=age_threshold_hours)
        self.cleaned_files = []
        self.cleaned_dirs = []
        self.total_space_freed = 0  # بالبايت
        
    def is_old(self, file_path):
        """التحقق من أن الملف قديم الصنع (أقدم من العتبة الزمنية)"""
        try:
            file_age = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(file_path)
            )
            return file_age > self.age_threshold
        except (OSError, ValueError):
            return False
    
    def get_file_size(self, file_path):
        """الحصول على حجم الملف"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    def delete_file(self, file_path, reason=""):
        """حذف ملف واحد بأمان"""
        try:
            size = self.get_file_size(file_path)
            os.remove(file_path)
            self.cleaned_files.append({
                'path': str(file_path),
                'size': size,
                'reason': reason
            })
            self.total_space_freed += size
            logger.info(f"✅ تم حذف: {file_path} ({self._format_size(size)}) - {reason}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حذف {file_path}: {str(e)}")
            return False
    
    def delete_directory(self, dir_path, reason=""):
        """حذف مجلد كامل بأمان"""
        try:
            size = sum(
                f.stat().st_size for f in Path(dir_path).rglob('*') 
                if f.is_file()
            )
            shutil.rmtree(dir_path)
            self.cleaned_dirs.append({
                'path': str(dir_path),
                'size': size,
                'reason': reason
            })
            self.total_space_freed += size
            logger.info(f"✅ تم حذف المجلد: {dir_path} ({self._format_size(size)}) - {reason}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حذف {dir_path}: {str(e)}")
            return False
    
    def _format_size(self, bytes_size):
        """تنسيق حجم الملف بشكل مقروء"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    # ================================
    # 1. تنظيف ملفات التقارير المؤقتة
    # ================================
    
    def cleanup_temp_reports(self):
        """حذف ملفات التقارير المؤقتة القديمة"""
        logger.info("\n=" * 60)
        logger.info("🧹 تنظيف ملفات التقارير المؤقتة...")
        logger.info("=" * 60)
        
        report_dirs = [
            'static/temp_reports',
            'static/exports',
            'static/downloads',
            'reports/temp',
            'temp_data'
        ]
        
        count = 0
        for dir_name in report_dirs:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.glob('*'):
                if file_path.is_file() and self.is_old(file_path):
                    if self.delete_file(file_path, "ملف تقرير مؤقت قديم"):
                        count += 1
        
        logger.info(f"📊 تم حذف {count} ملف تقرير مؤقت")
        return count
    
    # ================================
    # 2. تنظيف Cache والملفات المؤقتة
    # ================================
    
    def cleanup_cache(self):
        """تنظيف ملفات Cache والبيانات المؤقتة"""
        logger.info("\n" + "=" * 60)
        logger.info("🧹 تنظيف ملفات Cache...")
        logger.info("=" * 60)
        
        cache_dirs = [
            '__pycache__',
            '.pytest_cache',
            '.mypy_cache',
            'static/.cache',
            'node_modules/.cache'
        ]
        
        count = 0
        for dir_name in cache_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                if self.delete_directory(dir_path, "مجلد cache"):
                    count += 1
        
        logger.info(f"📊 تم حذف {count} مجلد cache")
        return count
    
    # ================================
    # 3. تنظيف الملفات المرفوعة القديمة
    # ================================
    
    def cleanup_old_uploads(self, max_age_days=90):
        """حذف الملفات المرفوعة القديمة (أكثر من 90 يوم)"""
        logger.info("\n" + "=" * 60)
        logger.info(f"🧹 تنظيف الملفات المرفوعة (أقدم من {max_age_days} يوم)...")
        logger.info("=" * 60)
        
        upload_dirs = [
            'static/uploads',
            'uploads',
            'static/images/uploads'
        ]
        
        old_threshold = timedelta(days=max_age_days)
        count = 0
        
        for dir_name in upload_dirs:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_age = datetime.now() - datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        )
                        if file_age > old_threshold:
                            if self.delete_file(file_path, f"ملف مرفوع قديم ({file_age.days} يوم)"):
                                count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ تجاهل الملف {file_path}: {str(e)}")
        
        logger.info(f"📊 تم حذف {count} ملف مرفوع قديم")
        return count
    
    # ================================
    # 4. تنظيف سجلات النظام
    # ================================
    
    def cleanup_logs(self, max_age_days=30):
        """حذف ملفات السجلات القديمة"""
        logger.info("\n" + "=" * 60)
        logger.info(f"🧹 تنظيف ملفات السجلات (أقدم من {max_age_days} يوم)...")
        logger.info("=" * 60)
        
        log_files = list((self.base_path / 'logs').glob('*.log')) if (self.base_path / 'logs').exists() else []
        log_files += list(self.base_path.glob('*.log'))
        
        old_threshold = timedelta(days=max_age_days)
        count = 0
        
        for file_path in log_files:
            try:
                file_age = datetime.now() - datetime.fromtimestamp(
                    file_path.stat().st_mtime
                )
                if file_age > old_threshold:
                    if self.delete_file(file_path, f"ملف سجل قديم ({file_age.days} يوم)"):
                        count += 1
            except Exception as e:
                logger.warning(f"⚠️ تجاهل الملف {file_path}: {str(e)}")
        
        logger.info(f"📊 تم حذف {count} ملف سجل قديم")
        return count
    
    # ================================
    # 5. تنظيف ملفات النسخ الاحتياطية المؤقتة
    # ================================
    
    def cleanup_temp_backups(self):
        """حذف ملفات النسخ الاحتياطية المؤقتة القديمة"""
        logger.info("\n" + "=" * 60)
        logger.info("🧹 تنظيف ملفات النسخ الاحتياطية المؤقتة...")
        logger.info("=" * 60)
        
        backup_dirs = [
            'backups/temp',
            'backups/old',
            'instance/backups/temp'
        ]
        
        count = 0
        for dir_name in backup_dirs:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.glob('*'):
                if file_path.is_file() and self.is_old(file_path):
                    if self.delete_file(file_path, "ملف نسخة احتياطية مؤقتة قديمة"):
                        count += 1
        
        logger.info(f"📊 تم حذف {count} ملف نسخة احتياطية مؤقتة")
        return count
    
    # ================================
    # 6. تنظيف ملفات Python المؤقتة
    # ================================
    
    def cleanup_python_temp(self):
        """حذف ملفات Python المؤقتة .pyc و .pyo"""
        logger.info("\n" + "=" * 60)
        logger.info("🧹 تنظيف ملفات Python المؤقتة (.pyc, .pyo)...")
        logger.info("=" * 60)
        
        count = 0
        for file_path in self.base_path.rglob('*.pyc'):
            if self.delete_file(file_path, "ملف Python مؤقت"):
                count += 1
        
        for file_path in self.base_path.rglob('*.pyo'):
            if self.delete_file(file_path, "ملف Python محسّن مؤقت"):
                count += 1
        
        logger.info(f"📊 تم حذف {count} ملف Python مؤقت")
        return count
    
    # ================================
    # تشغيل جميع عمليات التنظيف
    # ================================
    
    def run_all_cleanup(self):
        """تشغيل جميع عمليات التنظيف"""
        logger.info("\n")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + "  🧹 بدء عملية تنظيف شاملة للمشروع  ".center(58) + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info(f"📍 المسار الأساسي: {self.base_path}")
        logger.info(f"⏱️  الحد الزمني: {self.age_threshold.total_seconds() / 3600} ساعة")
        logger.info("")
        
        # تشغيل جميع العمليات
        self.cleanup_temp_reports()
        self.cleanup_cache()
        self.cleanup_python_temp()
        self.cleanup_old_uploads()
        self.cleanup_logs()
        self.cleanup_temp_backups()
        
        # طباعة النتائج
        self._print_summary()
    
    def _print_summary(self):
        """طباعة ملخص النتائج"""
        logger.info("\n")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + "  📊 ملخص نتائج التنظيف  ".center(58) + "║")
        logger.info("╠" + "=" * 58 + "╣")
        
        total_files = len(self.cleaned_files)
        total_dirs = len(self.cleaned_dirs)
        
        logger.info(f"║ ✅ الملفات المحذوفة: {total_files}".ljust(59) + "║")
        logger.info(f"║ ✅ المجلدات المحذوفة: {total_dirs}".ljust(59) + "║")
        logger.info(f"║ 💾 المساحة المحررة: {self._format_size(self.total_space_freed)}".ljust(59) + "║")
        logger.info("╚" + "=" * 58 + "╝")
        
        # حفظ النتائج في ملف JSON
        self._save_cleanup_report()
    
    def _save_cleanup_report(self):
        """حفظ تقرير التنظيف في ملف JSON"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_files_deleted': len(self.cleaned_files),
                'total_dirs_deleted': len(self.cleaned_dirs),
                'total_space_freed_bytes': self.total_space_freed,
                'total_space_freed_mb': round(self.total_space_freed / (1024 * 1024), 2),
                'files': self.cleaned_files,
                'directories': self.cleaned_dirs
            }
            
            report_path = self.base_path / 'cleanup_report.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n📄 تم حفظ التقرير في: {report_path}")
        except Exception as e:
            logger.error(f"❌ فشل حفظ التقرير: {str(e)}")


def main():
    """تشغيل برنامج التنظيف"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='تنظيف ملفات وملفات المشروع المؤقتة',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--path',
        default='d:\\nuzm',
        help='مسار المشروع الأساسي (افتراضي: d:\\nuzm)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=48,
        help='عدد الساعات لاعتبار الملف قديماً (افتراضي: 48 ساعة)'
    )
    parser.add_argument(
        '--max-upload-days',
        type=int,
        default=90,
        help='عدد الأيام لحذف الملفات المرفوعة (افتراضي: 90 يوم)'
    )
    parser.add_argument(
        '--max-log-days',
        type=int,
        default=30,
        help='عدد الأيام لحذف ملفات السجلات (افتراضي: 30 يوم)'
    )
    
    args = parser.parse_args()
    
    cleaner = ProjectCleaner(base_path=args.path, age_threshold_hours=args.hours)
    cleaner.run_all_cleanup()
    
    logger.info("\n✅ انتهت عملية التنظيف بنجاح!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
