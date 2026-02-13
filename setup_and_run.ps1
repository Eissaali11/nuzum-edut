# سكريبت تثبيت وتشغيل مشروع نُظم
# Script to setup and run Nuzum Project
# يجب تشغيل هذا السكريبت بعد تثبيت Python

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "مشروع نُظم - سكريبت الإعداد والتشغيل" -ForegroundColor Cyan
Write-Host "Nuzum Project - Setup & Run Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 1. فحص Python
Write-Host "1. فحص Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ Python مثبت: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ خطأ: Python غير مثبت!" -ForegroundColor Red
    Write-Host "   يرجى تثبيت Python من: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "   أو استخدم: winget install Python.Python.3.12" -ForegroundColor Yellow
    exit 1
}

# 2. إنشاء البيئة الافتراضية
Write-Host ""
Write-Host "2. إعداد البيئة الافتراضية..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   البيئة الافتراضية موجودة مسبقاً" -ForegroundColor Gray
} else {
    Write-Host "   إنشاء البيئة الافتراضية..." -ForegroundColor Gray
    python -m venv venv
    Write-Host "   ✓ تم إنشاء البيئة الافتراضية" -ForegroundColor Green
}

# 3. تفعيل البيئة الافتراضية
Write-Host ""
Write-Host "3. تفعيل البيئة الافتراضية..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# 4. ترقية pip
Write-Host ""
Write-Host "4. ترقية pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "   ✓ تم ترقية pip" -ForegroundColor Green

# 5. تثبيت المكتبات
Write-Host ""
Write-Host "5. تثبيت مكتبات Python..." -ForegroundColor Yellow
Write-Host "   (قد يستغرق هذا عدة دقائق...)" -ForegroundColor Gray
python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ تم تثبيت جميع المكتبات بنجاح" -ForegroundColor Green
} else {
    Write-Host "   ⚠ حدثت بعض المشاكل أثناء التثبيت" -ForegroundColor Yellow
    Write-Host "   سيتم المتابعة على أي حال..." -ForegroundColor Gray
}

# 6. نسخ ملف البيئة
Write-Host ""
Write-Host "6. إعداد ملف البيئة..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.local") {
        Copy-Item ".env.local" ".env"
        Write-Host "   ✓ تم نسخ .env.local إلى .env" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ ملف .env غير موجود - سيتم استخدام الإعدادات الافتراضية" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ملف .env موجود مسبقاً" -ForegroundColor Gray
}

# 7. إعداد قاعدة البيانات
Write-Host ""
Write-Host "7. إعداد قاعدة البيانات..." -ForegroundColor Yellow
if (Test-Path "migrations") {
    Write-Host "   تشغيل migrations..." -ForegroundColor Gray
    $env:FLASK_APP = "app.py"
    python -m flask db upgrade 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ تم إعداد قاعدة البيانات" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ حدثت مشكلة في migrations - سيتم إنشاء قاعدة بيانات جديدة" -ForegroundColor Yellow
    }
} else {
    Write-Host "   مجلد migrations غير موجود - سيتم إنشاء قاعدة بيانات جديدة" -ForegroundColor Gray
}

# 8. تشغيل المشروع
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "✓ الإعداد اكتمل بنجاح!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "تشغيل المشروع..." -ForegroundColor Yellow
Write-Host ""
Write-Host "المشروع سيعمل على: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "اضغط Ctrl+C لإيقاف المشروع" -ForegroundColor Gray
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# تشغيل التطبيق
python app.py
