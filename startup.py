#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup Configuration - تهيئة التشغيل
يضمن أن الخادم يبدأ دائماً بالإعدادات الصحيحة
"""

import os
import sys
import subprocess
from pathlib import Path

# إعدادات الخادم - تعريف مركزي
SERVER_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 5000,  # البوابة الرسمية
    'DEBUG': False,
    'APP_THREADED': 'true',
    'ATTENDANCE_USE_MODULAR': '0',  # استخدام الملف الأصلي الموثوق
    'ENVIRONMENT': 'production'
}

# مسارات أساسية
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
APP_FILE = SRC_DIR / "app.py"

# Add src/ to Python path to enable imports
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

def print_config():
    """طباعة الإعدادات الحالية"""
    print("\n" + "="*70)
    print("نُظم - SERVER CONFIGURATION".center(70))
    print("="*70)
    print(f"Host:              {SERVER_CONFIG['HOST']}")
    print(f"Port:              {SERVER_CONFIG['PORT']} [OK]")
    print(f"Debug Mode:        {SERVER_CONFIG['DEBUG']}")
    print(f"Environment:       {SERVER_CONFIG['ENVIRONMENT']}")
    print(f"Modular Mode:      {SERVER_CONFIG['ATTENDANCE_USE_MODULAR']}")
    print("="*70 + "\n")

def verify_files():
    """التحقق من وجود الملفات الأساسية"""
    print("Checking required files...")
    
    required_files = [
        APP_FILE,
        SRC_DIR / "presentation" / "web" / "static" / "css" / "custom.css",
        BASE_DIR / "instance" / "nuzum_local.db",
    ]
    
    all_exist = True
    for file_path in required_files:
        exists = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"  {exists} {file_path.name}")
        if not file_path.exists():
            all_exist = False
    
    return all_exist

def set_environment():
    """تعيين متغيرات البيئة"""
    debug_flag = "true" if SERVER_CONFIG['DEBUG'] else "false"
    os.environ.setdefault("FLASK_DEBUG", debug_flag)
    os.environ.setdefault("FLASK_ENV", "development" if SERVER_CONFIG['DEBUG'] else "production")
    os.environ.setdefault("APP_THREADED", str(SERVER_CONFIG.get('APP_THREADED', 'true')))
    for key, value in SERVER_CONFIG.items():
        if key.startswith('HOST') or key.startswith('PORT'):
            continue
        env_key = key
        os.environ[env_key] = str(value)

def start_server():
    """بدء الخادم بالإعدادات الصحيحة"""
    print_config()
    
    if not verify_files():
        print("\n[ERROR] بعض الملفات المطلوبة غير موجودة!")
        sys.exit(1)
    
    print("\n[OK] جميع الملفات موجودة\n")
    
    # تعيين متغيرات البيئة
    set_environment()
    
    print(f"Starting server at http://<YOUR_IP>:{SERVER_CONFIG['PORT']}/")
    print("Press Ctrl+C to stop the server\n")
    
    # بدء الخادم
    try:
        subprocess.run(
            [str(VENV_PYTHON), str(APP_FILE)],
            cwd=str(BASE_DIR),
            check=False
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped gracefully.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()
