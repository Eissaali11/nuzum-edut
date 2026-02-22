#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Health Check - فحص صحة النظام
يتحقق من جميع الإعدادات والملفات المطلوبة
"""

import os
import sys
from pathlib import Path

class SystemHealthCheck:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        
    def print_header(self):
        print("\n" + "="*70)
        print("نُظم - SYSTEM HEALTH CHECK".center(70))
        print("="*70 + "\n")
    
    def check(self, condition, description, severity="error"):
        """فحص واحد"""
        if condition:
            print(f"✓ {description}")
            self.passed += 1
            return True
        else:
            if severity == "error":
                print(f"✗ {description}")
                self.failed += 1
            elif severity == "warning":
                print(f"⚠ {description}")
                self.warnings += 1
            return False
    
    def run_all_checks(self):
        """تشغيل جميع الفحوصات"""
        self.print_header()
        
        # === فحص الملفات ===
        print("1. FILE CHECKS - فحص الملفات")
        print("-" * 70)
        
        self.check(
            (self.base_dir / "app.py").exists(),
            "✓ app.py موجود"
        )
        self.check(
            (self.base_dir / "startup.py").exists(),
            "✓ startup.py موجود"
        )
        self.check(
            (self.base_dir / "instance" / "nuzum_local.db").exists(),
            "✓ Database (nuzum_local.db) موجود"
        )
        self.check(
            (self.base_dir / "presentation" / "web" / "static").exists(),
            "✓ Static folder موجود"
        )
        self.check(
            (self.base_dir / "presentation" / "web" / "templates").exists(),
            "✓ Templates folder موجود"
        )
        
        # === فحص CSS Files ===
        print("\n2. CSS FILES - فحص ملفات الأسلوب")
        print("-" * 70)
        
        css_files = [
            "custom.css",
            "logo.css",
        ]
        
        css_dir = self.base_dir / "presentation" / "web" / "static" / "css"
        for css_file in css_files:
            self.check(
                (css_dir / css_file).exists(),
                f"✓ {css_file} موجود"
            )
        
        mobile_files = [
            "mobile-theme.css",
            "mobile-style.css",
        ]
        
        mobile_dir = css_dir / ".." / "mobile" / "css"
        for mobile_file in mobile_files:
            self.check(
                (mobile_dir / mobile_file).exists(),
                f"✓ {mobile_file} موجود",
                severity="warning"
            )
        
        # === فحص الإعدادات ===
        print("\n3. CONFIGURATION - فحص الإعدادات")
        print("-" * 70)
        
        # فحص port في app.py
        try:
            with open(self.base_dir / "app.py", 'r', encoding='utf-8') as f:
                content = f.read()
                has_port_5000 = 'default_port = 5000' in content
                self.check(
                    has_port_5000,
                    "✓ البوابة مضبوطة على 5000"
                )
        except:
            self.check(False, "✗ لا يمكن قراءة app.py")
        
        # === فحص البيئة ===
        print("\n4. ENVIRONMENT - فحص البيئة")
        print("-" * 70)
        
        self.check(
            (self.base_dir / "venv").exists(),
            "✓ Virtual environment موجود"
        )
        self.check(
            (self.base_dir / ".env.example").exists(),
            "✓ .env.example موجود",
            severity="warning"
        )
        
        # === الملخص ===
        print("\n" + "="*70)
        print("SUMMARY - الملخص".center(70))
        print("="*70)
        print(f"✓ Passed:   {self.passed}")
        print(f"✗ Failed:   {self.failed}")
        print(f"⚠ Warnings: {self.warnings}")
        print("="*70 + "\n")
        
        # النتيجة
        if self.failed == 0:
            print("🎉 النظام سليم تماماً - جاهز للعمل!")
            return 0
        else:
            print("❌ يوجد مشاكل - يرجى إصلاحها قبل التشغيل")
            return 1

if __name__ == "__main__":
    checker = SystemHealthCheck()
    sys.exit(checker.run_all_checks())
