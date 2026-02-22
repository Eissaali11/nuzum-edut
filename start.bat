@echo off
REM Startup Script for Nuzm System - بدء تشغيل نظام نُظم
REM يضمن تشغيل الخادم على البوابة الصحيحة 5000

cd /d %~dp0

cls
echo ========================================
echo   نُظم - Attendance Management System
echo ========================================
echo.

REM تعيين الإعدادات
set FLASK_DEBUG=0
set ATTENDANCE_USE_MODULAR=0
set PORT=5000

echo [INFO] Configuration:
echo   Port: %PORT%
echo   Debug: %FLASK_DEBUG%
echo   Module Mode: %ATTENDANCE_USE_MODULAR%
echo.

REM التحقق من البايثون
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

echo [INFO] Starting server...
echo.

REM بدء الخادم
.\venv\Scripts\python.exe startup.py

pause
