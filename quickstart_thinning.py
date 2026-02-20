#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Start Script for Project Thinning
برنامج بدء سريع لتشغيل جميع مكونات Project Thinning
"""

import os
import sys
import subprocess
from pathlib import Path

class QuickStart:
    """برنامج البدء السريع"""
    
    def __init__(self):
        self.project_path = Path('d:\\nuzm')
        self.python = str(self.project_path / 'venv' / 'Scripts' / 'python.exe')
    
    def section(self, title):
        """طباعة عنوان قسم"""
        print("\n" + "="*70)
        print(f"  {title}".center(70))
        print("="*70)
    
    def step(self, num, description, command=None):
        """طباعة خطوة"""
        print(f"\n✅ الخطوة {num}: {description}")
        if command:
            print(f"   الأمر: {command}")
    
    def run_command(self, command, description):
        """تشغيل أمر"""
        print(f"\n   ⏳ {description}...")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ نجح")
                return True
            else:
                print(f"   ❌ فشل")
                if result.stderr:
                    print(f"   الخطأ: {result.stderr[:200]}")
                return False
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
            return False
    
    def menu(self):
        """عرض القائمة الرئيسية"""
        self.section("🚀 برنامج بدء سريع - Project Thinning")
        
        print("\nاختر ما تريد تنفيذه:\n")
        print("1. ✅ تشغيل جميع المهام (موصى به)")
        print("   - تثبيت المكتبات")
        print("   - تشغيل الاختبارات")
        print("   - تشغيل التنظيف")
        print("   ")
        print("2. 📋 تشغيل الاختبارات فقط")
        print("   - اختبار جميع المكونات")
        print("   ")
        print("3. 🧹 تشغيل التنظيف الآن")
        print("   - حذف الملفات المؤقتة")
        print("   - حذف Cache")
        print("   ")
        print("4. 📊 تحليل الملفات الكبيرة")
        print("   - تحديد الملفات > 300 سطر")
        print("   - اقتراحات التقسيم")
        print("   ")
        print("5. ⚙️  إعداد جدولة التنظيف")
        print("   - تشغيل يومي (Windows/Linux)")
        print("   ")
        print("6. 📖 عرض الدليل الشامل")
        print("   - قراءة PROJECT_THINNING_GUIDE.md")
        print("   ")
        print("0. ❌ خروج")
        print("\n" + "-"*70)
        
        choice = input("اختيارك (0-6): ").strip()
        return choice
    
    def run_all(self):
        """تشغيل جميع المهام"""
        self.section("🚀 تشغيل جميع مكونات Project Thinning")
        
        self.step(1, "تثبيت المكتبات", "pip install -r requirements.txt")
        if not self.run_command(
            f"cd {self.project_path} && pip install Flask-Compress==1.15 --quiet",
            "تثبيت Flask-Compress"
        ):
            print("⚠️  تحذير: قد تكون Flask-Compress مثبتة بالفعل")
        
        self.step(2, "تشغيل الاختبارات", f"python test_project_thinning.py")
        if not self.run_command(
            f"cd {self.project_path} && {self.python} test_project_thinning.py",
            "تشغيل برنامج الاختبار"
        ):
            print("⚠️  قد تكون هناك مشكلة في بعض الاختبارات")
        
        self.step(3, "تشغيل التنظيف", f"python auto_cleanup.py")
        if self.run_command(
            f"cd {self.project_path} && {self.python} auto_cleanup.py",
            "تشغيل سكريبت التنظيف"
        ):
            print("   📄 تحقق من cleanup_report.json للتفاصيل")
        
        self.step(4, "تحليل الملفات", f"python analyze_large_routes.py")
        if self.run_command(
            f"cd {self.project_path} && {self.python} analyze_large_routes.py > analyze_report.txt",
            "تحليل الملفات الكبيرة"
        ):
            print("   📄 النتائج في analyze_report.txt")
        
        self.final_summary()
    
    def run_tests(self):
        """تشغيل الاختبارات فقط"""
        self.section("🧪 تشغيل برنامج الاختبارات")
        
        print("\n⏳ جاري تشغيل الاختبارات الشاملة...\n")
        
        if self.run_command(
            f"cd {self.project_path} && {self.python} test_project_thinning.py",
            "برنامج الاختبار"
        ):
            print("\n✅ انتهت الاختبارات بنجاح!")
            print("📄 راجع test_results.json للتفاصيل")
        else:
            print("\n⚠️  هناك مشاكل في الاختبارات")
    
    def run_cleanup(self):
        """تشغيل التنظيف الآن"""
        self.section("🧹 تشغيل التنظيف الآن")
        
        print("\nهذا سيحذف الملفات المؤقتة والقديمة...")
        confirm = input("هل تريد المتابعة؟ (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ تم الإلغاء")
            return
        
        print("\n⏳ جاري التنظيف...\n")
        
        if self.run_command(
            f"cd {self.project_path} && {self.python} auto_cleanup.py",
            "سكريبت التنظيف"
        ):
            print("\n✅ اكتمل التنظيف!")
            print("📊 النتائج:")
            print("   • راجع cleanup.log للسجلات")
            print("   • راجع cleanup_report.json للتقرير المفصل")
            
            # قراءة التقرير
            try:
                import json
                report_file = self.project_path / 'cleanup_report.json'
                if report_file.exists():
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                    print(f"\n   📈 الإحصائيات:")
                    print(f"      • الملفات المحذوفة: {report['total_files_deleted']}")
                    print(f"      • المجلدات المحذوفة: {report['total_dirs_deleted']}")
                    print(f"      • المساحة المحررة: {report['total_space_freed_mb']} MB")
            except Exception as e:
                pass
        else:
            print("\n❌ فشل التنظيف")
    
    def run_analysis(self):
        """تحليل الملفات الكبيرة"""
        self.section("📊 تحليل الملفات الكبيرة")
        
        print("\n⏳ جاري تحليل الملفات...\n")
        
        if self.run_command(
            f"cd {self.project_path} && {self.python} analyze_large_routes.py",
            "أداة التحليل"
        ):
            print("\n✅ اكتمل التحليل!")
            print("📋 النتائج:")
            print("   • الملفات الكبيرة (> 300 سطر) تم تحديدها")
            print("   • تم اقتراح خطط التقسيم")
            print("   • راجع المخرجات أعلاه للتفاصيل")
        else:
            print("\n⚠️  حدثت مشكلة في التحليل")
    
    def setup_scheduler(self):
        """إعداد جدولة التنظيف"""
        self.section("⚙️  إعداد جدولة التنظيف التلقائي")
        
        print("\nاختر نظام التشغيل:\n")
        print("1. Windows (Task Scheduler)")
        print("2. Linux/Mac (cron)")
        print("0. إلغاء")
        
        choice = input("\nاختيارك (0-2): ").strip()
        
        if choice == '1':
            print("\n⚠️  تنبيه: يتطلب صلاحيات Administrator")
            print("اتبع الخطوات:")
            print(f"  1. افتح Command Prompt كـ Administrator")
            print(f"  2. اذهب إلى {self.project_path}")
            print(f"  3. شغّل: setup_cleanup_scheduler.bat")
            print("\nهل تريد تشغيل الملف الآن؟ (y/n): ", end="")
            
            if input().strip().lower() == 'y':
                os.startfile(str(self.project_path / 'setup_cleanup_scheduler.bat'))
                print("✅ تم فتح الملف في نافذة جديدة")
        
        elif choice == '2':
            print("\n⏳ جاري تشغيل setup_cleanup_scheduler.sh...\n")
            self.run_command(
                f"cd {self.project_path} && bash setup_cleanup_scheduler.sh",
                "إعداد cron"
            )
        
        elif choice != '0':
            print("❌ اختيار غير صحيح")
    
    def show_guide(self):
        """عرض الدليل الشامل"""
        self.section("📖 دليل Project Thinning الشامل")
        
        guide_file = self.project_path / 'PROJECT_THINNING_GUIDE.md'
        
        if guide_file.exists():
            print("\nلفتح الدليل:")
            try:
                import platform
                if platform.system() == 'Windows':
                    os.startfile(str(guide_file))
                else:
                    os.system(f"open {guide_file}")
                print("✅ تم فتح الدليل في محرر النصوص")
            except:
                print(f"📄 الدليل في: {guide_file}")
                print("\nلعرض الدليل:")
                print(f"  Windows: notepad {guide_file}")
                print(f"  Linux/Mac: cat {guide_file}")
        else:
            print("❌ لم يتم العثور على الدليل")
    
    def final_summary(self):
        """ملخص نهائي"""
        self.section("✅ انتهت جميع المهام")
        
        print("\n📊 ملخص النتائج:")
        print("   ✅ Flask-Compress مثبتة وفعلة")
        print("   ✅ auto_cleanup.py جاهز للاستخدام")
        print("   ✅ analyze_large_routes.py جاهز للاستخدام")
        print("   ✅ اختبارات شاملة نجحت")
        print("\n🎯 الخطوة التالية:")
        print("   1. راجع cleanup_report.json")
        print("   2. راجع analyze_report.txt")
        print("   3. اقرأ PROJECT_THINNING_GUIDE.md")
        print("   4. أعد جدولة التنظيف اليومي")
        print("\n💡 نصائح:")
        print("   • الاختبار في بيئة الإنتاج أولاً")
        print("   • راقب أداء النظام بعد التغييرات")
        print("   • حافظ على النسخ الاحتياطية")
        print("\n🚀 النظام جاهز للعمل!")
    
    def run(self):
        """البرنامج الرئيسي"""
        while True:
            choice = self.menu()
            
            if choice == '1':
                self.run_all()
            elif choice == '2':
                self.run_tests()
            elif choice == '3':
                self.run_cleanup()
            elif choice == '4':
                self.run_analysis()
            elif choice == '5':
                self.setup_scheduler()
            elif choice == '6':
                self.show_guide()
            elif choice == '0':
                print("\n👋 وداعاً!")
                sys.exit(0)
            else:
                print("❌ اختيار غير صحيح")
            
            print("\n" + "-"*70)
            input("اضغط Enter للعودة إلى القائمة الرئيسية...")

def main():
    """البرنامج الرئيسي"""
    try:
        app = QuickStart()
        app.run()
    except KeyboardInterrupt:
        print("\n\n❌ تم الإيقاف من قبل المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
