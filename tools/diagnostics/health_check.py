#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Health Check - فحص صحة النظام
يتحقق من جميع الإعدادات والملفات المطلوبة
"""

import os
import sys
import re
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

class SystemHealthCheck:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[2]
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
        # --- فحوصات إضافية حرجة ---
        print("\n5. CRITICAL CHECKS - فحوصات حرجة")
        print("-" * 70)
        self.check_startup_reads_dotenv()
        self.check_env_file()
        self.check_db_schema()
        self.check_blueprint_prefix_collisions()
        self.check_dashboard_latency(max_ms=50)
        
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

    # ---------------------- إضافات فحوصة حرجة ----------------------
    def check_startup_reads_dotenv(self):
        """تأكد أن `startup.py` يستدعي تحميل .env أو يستخدم ATTENDANCE_USE_MODULAR"""
        try:
            p = self.base_dir / 'startup.py'
            content = p.read_text(encoding='utf-8')
            has_load_dotenv = 'load_dotenv' in content or 'dotenv' in content
            has_attendance_env = 'ATTENDANCE_USE_MODULAR' in content
            self.check(
                has_load_dotenv or has_attendance_env,
                "✓ startup.py يبدو أنه يقرأ متغيرات البيئة (.env أو ATTENDANCE_USE_MODULAR)",
                severity='warning' if not has_load_dotenv and has_attendance_env else 'error'
            )
        except Exception:
            self.check(False, "✗ لا يمكن فحص startup.py لوجود قراءة .env")

    def check_env_file(self):
        """فحص وجود ATTENDANCE_USE_MODULAR في .env أو .env.example"""
        found = False
        env_paths = [self.base_dir / '.env', self.base_dir / '.env.example']
        for p in env_paths:
            if p.exists():
                try:
                    txt = p.read_text(encoding='utf-8')
                    m = re.search(r'^\s*ATTENDANCE_USE_MODULAR\s*=\s*([01-9])', txt, re.M)
                    if m:
                        found = True
                        val = m.group(1)
                        self.check(True, f"✓ {p.name} يحتوي ATTENDANCE_USE_MODULAR={val}")
                    else:
                        self.check(False, f"⚠ {p.name} لا يحتوي على ATTENDANCE_USE_MODULAR", severity='warning')
                except Exception:
                    self.check(False, f"✗ لا يمكن قراءة {p}")
        if not any(p.exists() for p in env_paths):
            self.check(False, "✗ لا يوجد ملف .env أو .env.example")

    def check_db_schema(self):
        """تحقق من أعمدة الجداول والفهارس في قاعدة SQLite المحلية"""
        # Support checking both instance/nuzum_local.db and root nuzum_local.db
        candidates = [self.base_dir / 'instance' / 'nuzum_local.db', self.base_dir / 'nuzum_local.db']
        found = False
        last_err = None
        for db_path in candidates:
            if not db_path.exists():
                continue
            try:
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("PRAGMA table_info('vehicle_handover')")
                cols = [r[1] for r in cur.fetchall()]
                if 'is_approved' in cols:
                    self.check(True, f"✓ vehicle_handover يحتوي عمود is_approved (from {db_path.relative_to(self.base_dir)})")
                    found = True
                else:
                    # continue checking other DBs
                    last_err = f"is_approved not in {db_path}"

                # Check attendance indexes (check presence if table exists)
                cur.execute("PRAGMA index_list('attendance')")
                idxs = [r[1] for r in cur.fetchall()]
                self.check('idx_attendance_employee_date' in idxs, "✓ idx_attendance_employee_date موجود على جدول attendance", severity='warning')
                self.check('idx_attendance_date' in idxs, "✓ idx_attendance_date موجود على جدول attendance", severity='warning')

                conn.close()
            except Exception as e:
                last_err = str(e)
        if not found:
            if last_err:
                self.check(False, f"✗ vehicle_handover missing is_approved or DB error: {last_err}")
            else:
                self.check(False, "✗ ملف قاعدة البيانات غير موجود: instance/nuzum_local.db or nuzum_local.db")

    def check_blueprint_prefix_collisions(self):
        """Parse routes/blueprint_registry.py and detect duplicate url_prefix usage"""
        registry = self.base_dir / 'routes' / 'blueprint_registry.py'
        if not registry.exists():
            self.check(False, "✗ لا يمكن إيجاد routes/blueprint_registry.py للتحقق من تسجيل الـ Blueprints")
            return
        try:
            txt = registry.read_text(encoding='utf-8')
            # find lines like: app.register_blueprint(name, url_prefix='/x')
            pattern = re.compile(r"app\.register_blueprint\(([^,\)]+)(?:,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"])?")
            mapping: Dict[str, List[str]] = {}
            for m in pattern.finditer(txt):
                bp = m.group(1).strip()
                prefix = m.group(2) or ''
                mapping.setdefault(prefix, []).append(bp)

            collisions = [(p, bps) for p, bps in mapping.items() if len(bps) > 1 and p != '']
            if collisions:
                for prefix, bps in collisions:
                    self.check(False, f"✗ Collision: multiple blueprints registered with prefix '{prefix}': {', '.join(bps)}")
            else:
                self.check(True, "✓ لا توجد تصادمات واضحة في url_prefix لملف blueprint_registry.py")
        except Exception as e:
            self.check(False, f"✗ فشل في تحليل blueprint_registry.py: {e}")

    def check_dashboard_latency(self, max_ms: int = 50):
        """Attempt to measure /attendance/dashboard latency using Flask test_client if possible"""
        try:
            import importlib
            app_mod = importlib.import_module('app')
            app_obj = getattr(app_mod, 'app', None) or getattr(app_mod, 'create_app', None)
            if app_obj is None:
                self.check(False, "✗ لا يمكن إيجاد كائن Flask في module 'app'")
                return
            # If create_app factory, call it without args
            if callable(app_obj) and not hasattr(app_obj, 'test_client'):
                app_obj = app_obj()

            client = app_obj.test_client()
            start = time.time()
            resp = client.get('/attendance/dashboard')
            elapsed_ms = (time.time() - start) * 1000
            ok = resp.status_code == 200 and elapsed_ms <= max_ms
            self.check(ok, f"✓ /attendance/dashboard => {resp.status_code} in {elapsed_ms:.2f} ms (threshold {max_ms}ms)")
        except Exception as e:
            self.check(False, f"⚠ لم يكن بالإمكان قياس زمن لوحة القيادة تلقائياً: {e}", severity='warning')

if __name__ == "__main__":
    checker = SystemHealthCheck()
    sys.exit(checker.run_all_checks())
