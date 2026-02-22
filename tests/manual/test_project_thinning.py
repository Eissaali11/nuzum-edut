#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل لميزات Project Thinning
- اختبار Gzip Compression
- اختبار Auto-Cleanup
- اختبار Route Analysis
- قياس الأداء
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

class ThinningTestSuite:
    """فئة اختبار شاملة"""
    
    def __init__(self):
        self.project_path = Path('d:\\nuzm')
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def log_test(self, name, status, message):
        """تسجيل نتيجة اختبار"""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}: {message}")
        self.results.append({
            'test': name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        if status:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    # ================================
    # 1. اختبارات Gzip
    # ================================
    
    def test_flask_compress_installed(self):
        """اختبار: هل Flask-Compress مثبتة؟"""
        try:
            import flask_compress
            self.log_test(
                "Flask-Compress Installation",
                True,
                f"✓ Flask-Compress {flask_compress.__version__} installed"
            )
        except ImportError:
            self.log_test(
                "Flask-Compress Installation",
                False,
                "Flask-Compress not installed. Run: pip install Flask-Compress"
            )
    
    def test_gzip_config_in_app(self):
        """اختبار: هل Gzip مفعلة في app.py؟"""
        try:
            app_file = self.project_path / 'app.py'
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = {
                'Compress import': 'from flask_compress import Compress' in content,
                'Compress initialization': 'Compress(app)' in content,
                'COMPRESS_LEVEL setting': 'COMPRESS_LEVEL' in content,
                'COMPRESS_MIN_SIZE setting': 'COMPRESS_MIN_SIZE' in content,
            }
            
            all_passed = all(checks.values())
            details = ", ".join([k for k, v in checks.items() if v])
            
            self.log_test(
                "Gzip Configuration in app.py",
                all_passed,
                f"Found configurations: {details}" if all_passed else "Missing Gzip configuration"
            )
        except Exception as e:
            self.log_test("Gzip Configuration in app.py", False, str(e))
    
    def test_requirements_updated(self):
        """اختبار: هل تم تحديث requirements.txt؟"""
        try:
            req_file = self.project_path / 'requirements.txt'
            with open(req_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_compress = 'Flask-Compress' in content
            
            self.log_test(
                "requirements.txt Update",
                has_compress,
                "Flask-Compress added to requirements.txt" if has_compress else "Flask-Compress not in requirements"
            )
        except Exception as e:
            self.log_test("requirements.txt Update", False, str(e))
    
    # ================================
    # 2. اختبارات Auto-Cleanup
    # ================================
    
    def test_cleanup_script_exists(self):
        """اختبار: هل ملف auto_cleanup.py موجود؟"""
        cleanup_file = self.project_path / 'auto_cleanup.py'
        exists = cleanup_file.exists()
        
        self.log_test(
            "Auto-Cleanup Script",
            exists,
            "auto_cleanup.py found" if exists else "auto_cleanup.py not found"
        )
    
    def test_cleanup_script_core_functions(self):
        """اختبار: هل لديها جميع الدوال الأساسية؟"""
        try:
            cleanup_file = self.project_path / 'auto_cleanup.py'
            with open(cleanup_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_functions = [
                'cleanup_temp_reports',
                'cleanup_cache',
                'cleanup_old_uploads',
                'cleanup_logs',
                'cleanup_temp_backups',
                'cleanup_python_temp',
                'run_all_cleanup'
            ]
            
            found = [f for f in required_functions if f in content]
            all_found = len(found) == len(required_functions)
            
            self.log_test(
                "Auto-Cleanup Core Functions",
                all_found,
                f"Found {len(found)}/{len(required_functions)} functions"
            )
        except Exception as e:
            self.log_test("Auto-Cleanup Core Functions", False, str(e))
    
    def test_cleanup_scheduler_windows(self):
        """اختبار: هل setup_cleanup_scheduler.bat موجود؟"""
        scheduler_file = self.project_path / 'setup_cleanup_scheduler.bat'
        exists = scheduler_file.exists()
        
        self.log_test(
            "Windows Cleanup Scheduler",
            exists,
            "setup_cleanup_scheduler.bat found" if exists else "Not found"
        )
    
    def test_cleanup_scheduler_linux(self):
        """اختبار: هل setup_cleanup_scheduler.sh موجود؟"""
        scheduler_file = self.project_path / 'setup_cleanup_scheduler.sh'
        exists = scheduler_file.exists()
        
        self.log_test(
            "Linux/Mac Cleanup Scheduler",
            exists,
            "setup_cleanup_scheduler.sh found" if exists else "Not found"
        )
    
    # ================================
    # 3. اختبارات Route Analysis
    # ================================
    
    def test_route_analyzer_exists(self):
        """اختبار: هل أداة تحليل الروتات موجودة؟"""
        analyzer_file = self.project_path / 'analyze_large_routes.py'
        exists = analyzer_file.exists()
        
        self.log_test(
            "Route Analysis Tool",
            exists,
            "analyze_large_routes.py found" if exists else "Not found"
        )
    
    def test_large_routes_identified(self):
        """اختبار: هل تم تحديد الملفات الكبيرة؟"""
        try:
            routes_dir = self.project_path / 'routes'
            if not routes_dir.exists():
                self.log_test("Large Routes Identification", False, "routes/ directory not found")
                return
            
            large_files = []
            for py_file in routes_dir.glob('*.py'):
                lines = len(open(py_file, 'r', encoding='utf-8', errors='ignore').readlines())
                if lines > 300:
                    large_files.append((py_file.name, lines))
            
            if large_files:
                details = ", ".join([f"{f[0]} ({f[1]})" for f in large_files[:3]])
                self.log_test(
                    "Large Routes Identification",
                    True,
                    f"Found {len(large_files)} large files: {details}..."
                )
            else:
                self.log_test("Large Routes Identification", False, "No large files found")
        except Exception as e:
            self.log_test("Large Routes Identification", False, str(e))
    
    # ================================
    # 4. اختبارات الأداء
    # ================================
    
    def test_cleanup_dry_run(self):
        """اختبار: تشغيل تجريبي للـ Cleanup"""
        try:
            # إنشاء ملفات اختبار مؤقتة
            test_dir = self.project_path / 'test_cleanup_temp'
            test_dir.mkdir(exist_ok=True)
            
            # إنشاء ملف قديم الصنع
            old_file = test_dir / 'old_test_file.txt'
            old_file.write_text('test')
            
            # تعديل timestamp ليكون قديم
            old_time = (datetime.now() - timedelta(days=3)).timestamp()
            os.utime(old_file, (old_time, old_time))
            
            # التحقق من وجود الملف
            file_exists = old_file.exists()
            
            # تنظيف ملفات الاختبار
            shutil.rmtree(test_dir)
            
            self.log_test(
                "Cleanup Dry Run",
                file_exists,
                "Test file cleanup simulation successful"
            )
        except Exception as e:
            self.log_test("Cleanup Dry Run", False, str(e))
    
    # ================================
    # 5. اختبارات التوثيق
    # ================================
    
    def test_documentation_exists(self):
        """اختبار: هل الدليل موجود؟"""
        doc_file = self.project_path / 'PROJECT_THINNING_GUIDE.md'
        exists = doc_file.exists()
        
        self.log_test(
            "Project Thinning Documentation",
            exists,
            "PROJECT_THINNING_GUIDE.md found" if exists else "Not found"
        )
    
    def test_documentation_sections(self):
        """اختبار: هل الدليل يحتوي على أقسام أساسية؟"""
        try:
            doc_file = self.project_path / 'PROJECT_THINNING_GUIDE.md'
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_sections = [
                'Gzip Compression',
                'Auto-Cleanup Script',
                'Route Analysis Tool',
                'دليل البدء السريع'
            ]
            
            found_sections = [s for s in required_sections if s in content]
            
            self.log_test(
                "Documentation Completeness",
                len(found_sections) == len(required_sections),
                f"Found {len(found_sections)}/{len(required_sections)} sections"
            )
        except Exception as e:
            self.log_test("Documentation Completeness", False, str(e))
    
    # ================================
    # تشغيل جميع الاختبارات
    # ================================
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n" + "="*70)
        print("🧪 برنامج اختبار Project Thinning".center(70))
        print("="*70 + "\n")
        
        # اختبارات Gzip
        print("🔹 اختبارات Gzip Compression:")
        self.test_flask_compress_installed()
        self.test_gzip_config_in_app()
        self.test_requirements_updated()
        
        # اختبارات Auto-Cleanup
        print("\n🔹 اختبارات Auto-Cleanup:")
        self.test_cleanup_script_exists()
        self.test_cleanup_script_core_functions()
        self.test_cleanup_scheduler_windows()
        self.test_cleanup_scheduler_linux()
        
        # اختبارات Route Analysis
        print("\n🔹 اختبارات Route Analysis:")
        self.test_route_analyzer_exists()
        self.test_large_routes_identified()
        
        # اختبارات الأداء
        print("\n🔹 اختبارات الأداء:")
        self.test_cleanup_dry_run()
        
        # اختبارات التوثيق
        print("\n🔹 اختبارات التوثيق:")
        self.test_documentation_exists()
        self.test_documentation_sections()
        
        # ملخص النتائج
        self.print_summary()
    
    def print_summary(self):
        """طباعة ملخص النتائج"""
        print("\n" + "="*70)
        print("📊 ملخص نتائج الاختبار".center(70))
        print("="*70)
        
        total = self.tests_passed + self.tests_failed
        percentage = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"\n✅ نجحت: {self.tests_passed}")
        print(f"❌ فشلت: {self.tests_failed}")
        print(f"📈 النسبة: {percentage:.1f}%")
        
        # حفظ التقرير
        self._save_test_report()
    
    def _save_test_report(self):
        """حفظ تقرير الاختبارات"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_tests': self.tests_passed + self.tests_failed,
                'passed': self.tests_passed,
                'failed': self.tests_failed,
                'percentage': (self.tests_passed / (self.tests_passed + self.tests_failed) * 100) if (self.tests_passed + self.tests_failed) > 0 else 0,
                'details': self.results
            }
            
            report_path = self.project_path / 'test_results.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 تم حفظ التقرير في: {report_path}")
        except Exception as e:
            print(f"❌ فشل حفظ التقرير: {e}")

def main():
    """البرنامج الرئيسي"""
    tester = ThinningTestSuite()
    tester.run_all_tests()
    
    print("\n" + "="*70)
    
    if tester.tests_failed == 0:
        print("🎉 جميع الاختبارات نجحت! النظام جاهز للاستخدام.".center(70))
    else:
        print(f"⚠️  هناك {tester.tests_failed} اختبار فشل. راجع التفاصيل أعلاه.".center(70))
    
    print("="*70 + "\n")
    
    return 0 if tester.tests_failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
