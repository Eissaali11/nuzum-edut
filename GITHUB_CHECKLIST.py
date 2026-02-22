#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Upload Preparation Checklist
========================================
قائمة التحقق من استعداد الرفع على GitHub

This script verifies that all necessary files are present
and the project is ready for GitHub upload.
"""

import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """طباعة رأس الملف"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}\n")

def check_file(file_path, description):
    """التحقق من وجود الملف"""
    path = Path(file_path)
    exists = path.exists()
    
    status = f"{Colors.GREEN}✓ موجود{Colors.RESET}" if exists else f"{Colors.RED}✗ مفقود{Colors.RESET}"
    print(f"  {status} - {description}")
    
    if exists and path.is_file():
        size = path.stat().st_size
        print(f"      📊 الحجم: {size:,} بايت")
    
    return exists

def check_folder(folder_path, description):
    """التحقق من وجود المجلد"""
    path = Path(folder_path)
    exists = path.is_dir()
    
    status = f"{Colors.GREEN}✓ موجود{Colors.RESET}" if exists else f"{Colors.RED}✗ مفقود{Colors.RESET}"
    print(f"  {status} - {description}")
    
    if exists:
        files = list(path.glob('*'))
        print(f"      📁 الملفات: {len(files)}")
    
    return exists

def main():
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════╗")
    print("║    GitHub Upload Preparation Checklist              ║")
    print("║    قائمة التحقق قبل الرفع على GitHub              ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    all_passed = True
    
    # الملفات الأساسية
    print_header("1️⃣  الملفات الأساسية (Core Files)")
    
    core_files = [
        ("app.py", "تطبيق Flask الرئيسي"),
        ("startup.py", "مدير التشغيل الموحد"),
        ("health_check.py", "فحص صحة النظام"),
        (".env.example", "نموذج المتغيرات البيئية"),
        (".gitignore", "ملف التجاهل"),
        (".gitattributes", "إعدادات نهايات الأسطر"),
        ("README.md", "ملف التعريف الرئيسي"),
        ("LICENSE", "ملف الترخيص"),
        ("CONTRIBUTING.md", "دليل المساهمة"),
    ]
    
    for file, desc in core_files:
        if not check_file(file, desc):
            all_passed = False
    
    # ملفات التوثيق
    print_header("2️⃣  ملفات التوثيق (Documentation)")
    
    doc_files = [
        ("SOLUTION.md", "شرح الحل الجذري"),
        ("STARTUP_GUIDE.md", "دليل التشغيل"),
        ("QUICK_START.md", "البدء السريع"),
        ("GITHUB_UPLOAD_GUIDE.md", "دليل الرفع على GitHub"),
        ("PERMANENT_SOLUTION_SUMMARY.md", "ملخص الحل الدائم"),
    ]
    
    for file, desc in doc_files:
        if not check_file(file, desc):
            all_passed = False
    
    # ملفات التشغيل
    print_header("3️⃣  سكريبتات التشغيل (Startup Scripts)")
    
    script_files = [
        ("start.bat", "سكريبت Windows Batch"),
        ("start.ps1", "سكريبت PowerShell"),
        ("SETUP_GITHUB.ps1", "سكريبت إعداد GitHub"),
    ]
    
    for file, desc in script_files:
        if not check_file(file, desc):
            all_passed = False
    
    # المجلدات الأساسية
    print_header("4️⃣  المجلدات الأساسية (Core Folders)")
    
    core_folders = [
        ("app", "مجلد التطبيق الرئيسي"),
        ("presentation/web", "الواجهة الأمامية"),
        ("presentation/web/static", "الملفات الثابتة"),
        ("presentation/web/templates", "قوالب HTML"),
        ("core", "الكود الأساسي"),
        ("models", "نماذج قاعدة البيانات"),
        ("config", "ملفات التكوين"),
        ("modules", "الوحدات الإضافية"),
        ("instance", "بيانات المثيل"),
    ]
    
    for folder, desc in core_folders:
        if not check_folder(folder, desc):
            all_passed = False
    
    # ملفات قاعدة البيانات
    print_header("5️⃣  قاعدة البيانات (Database)")
    
    db_file = "instance/nuzum_local.db"
    if Path(db_file).exists():
        size = Path(db_file).stat().st_size
        print(f"  {Colors.GREEN}✓ موجودة{Colors.RESET} - قاعدة البيانات الرئيسية")
        print(f"      📊 الحجم: {size:,} بايت ({size/1024/1024:.2f} MB)")
    else:
        print(f"  {Colors.YELLOW}⚠ اختياري{Colors.RESET} - قاعدة البيانات")
        print(f"      (يمكن إنشاؤها بعد الرفع)")
    
    # ملفات CSS
    print_header("6️⃣  ملفات التصميم (CSS Files)")
    
    css_folder = Path("presentation/web/static")
    if css_folder.exists():
        css_files = list(css_folder.glob("*.css"))
        print(f"  {Colors.GREEN}✓ موجودة{Colors.RESET} - ملفات التصميم")
        print(f"      📊 عدد الملفات: {len(css_files)}")
        for css in css_files[:5]:
            size = css.stat().st_size
            print(f"        • {css.name} ({size:,} بايت)")
        if len(css_files) > 5:
            print(f"        • ... و {len(css_files) - 5} ملفات أخرى")
    else:
        print(f"  {Colors.RED}✗ مفقودة{Colors.RESET} - مجلد CSS")
        all_passed = False
    
    # ملفات Python
    print_header("7️⃣  ملفات Python (Python Files)")
    
    py_count = len(list(Path(".").glob("**/*.py")))
    print(f"  {Colors.GREEN}✓ موجودة{Colors.RESET} - ملفات Python")
    print(f"      📊 عدد الملفات: {py_count}")
    
    # ملفات التكوين
    print_header("8️⃣  ملفات التكوين (Configuration)")
    
    config_files = [
        ("requirements.txt", "المكتبات المطلوبة"),
        ("pyproject.toml", "إعدادات المشروع"),
        ("Dockerfile", "صورة Docker (اختياري)"),
        ("docker-compose.yml", "تكوين Docker Compose (اختياري)"),
    ]
    
    for file, desc in config_files:
        if Path(file).exists():
            check_file(file, desc)
        else:
            print(f"  {Colors.YELLOW}⚠ اختياري{Colors.RESET} - {desc}")
    
    # الملخص النهائي
    print_header("✅ الملخص النهائي (Summary)")
    
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ جميع الملفات الأساسية موجودة!{Colors.RESET}")
        print(f"{Colors.GREEN}المشروع جاهز للرفع على GitHub{Colors.RESET}\n")
        
        print(f"{Colors.BLUE}{Colors.BOLD}الخطوات التالية:{Colors.RESET}")
        print(f"{Colors.CYAN}1. انسخ رابط الـ Repository من GitHub{Colors.RESET}")
        print(f"{Colors.CYAN}2. شغّل السكريبت: SETUP_GITHUB.ps1{Colors.RESET}")
        print(f"{Colors.CYAN}3. اتبع التعليمات في GITHUB_UPLOAD_GUIDE.md{Colors.RESET}")
        print(f"{Colors.CYAN}4. تحقق من أن كل شيء رُفع بنجاح{Colors.RESET}\n")
        
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ بعض الملفات مفقودة!{Colors.RESET}")
        print(f"{Colors.RED}يرجى إنشاء الملفات المفقودة قبل الرفع{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}تم الإيقاف من قبل المستخدم{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}خطأ: {e}{Colors.RESET}")
        sys.exit(1)
