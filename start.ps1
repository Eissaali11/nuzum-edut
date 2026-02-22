# Startup Script for Nuzm System - بدء تشغيل نظام نُظم
# هذا السكريبت يضمن تشغيل الخادم على البوابة الصحيحة

param(
    [string]$Port = "5000",
    [bool]$Debug = $false
)

# إعدادات النظام
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
$VenvPython = Join-Path $ScriptDir "venv\Scripts\python.exe"
$AppFile = Join-Path $ScriptDir "app.py"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "نُظم - Attendance Management System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# التحقق من وجود Virtual Environment
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv"
    exit 1
}

# طباعة الإعدادات
Write-Host "[CONFIG] Server Settings:" -ForegroundColor Green
Write-Host "  Port:              $Port"
Write-Host "  Debug Mode:        $Debug"
Write-Host "  Module Mode:       0 (Legacy - Stable)"
Write-Host ""

# تعيين متغيرات البيئة
$env:FLASK_DEBUG = if ($Debug) { "true" } else { "false" }
$env:ATTENDANCE_USE_MODULAR = "0"
$env:APP_PORT = $Port

Write-Host "[INFO] Starting server on http://0.0.0.0:$Port" -ForegroundColor Green
Write-Host "[INFO] Access from your network: http://<YOUR_IP>:$Port" -ForegroundColor Yellow
Write-Host ""

# بدء الخادم
try {
    & $VenvPython $AppFile
}
catch {
    Write-Host "[ERROR] Failed to start server: $_" -ForegroundColor Red
    exit 1
}
