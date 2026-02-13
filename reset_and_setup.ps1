# سكريبت إعادة تهيئة قاعدة البيانات وإنشاء حساب المدير
# Reset Database and Create Admin Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "إعادة تهيئة قاعدة البيانات" -ForegroundColor Cyan
Write-Host "Reset Database & Create Admin" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. التأكد من البيئة الافتراضية
Write-Host "1. تفعيل البيئة الافتراضية..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Host "   ✓ تم تفعيل venv" -ForegroundColor Green
} else {
    Write-Host "   ✗ البيئة الافتراضية غير موجودة!" -ForegroundColor Red
    Write-Host "   قم بتشغيل: py -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 2. إيقاف أي سيرفر يعمل على المنفذ 5000
Write-Host ""
Write-Host "2. إيقاف السيرفر إن كان يعمل..." -ForegroundColor Yellow
$flaskProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*venv*"}
if ($flaskProcess) {
    Stop-Process -Id $flaskProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "   ✓ تم إيقاف السيرفر" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "   لا يوجد سيرفر يعمل" -ForegroundColor Gray
}

# 3. حذف قواعد البيانات القديمة
Write-Host ""
Write-Host "3. حذف قواعد البيانات القديمة..." -ForegroundColor Yellow

$dbFiles = @(
    "nuzum_local.db",
    "nuzum_local.db-shm",
    "nuzum_local.db-wal",
    "database\nuzum.db",
    "database\nuzum.db-shm",
    "database\nuzum.db-wal",
    "instance\nuzum.db",
    "instance\nuzum.db-shm",
    "instance\nuzum.db-wal"
)

foreach ($file in $dbFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ حذف: $file" -ForegroundColor Green
    }
}

Write-Host "   ✓ تم حذف قواعد البيانات القديمة" -ForegroundColor Green

# 4. إنشاء الجداول وحساب المدير
Write-Host ""
Write-Host "4. إنشاء حساب المدير..." -ForegroundColor Yellow
Write-Host ""
Write-Host "   استخدم البيانات الافتراضية (اضغط Enter لكل سؤال):" -ForegroundColor Cyan
Write-Host "   - اسم المستخدم: admin" -ForegroundColor Gray
Write-Host "   - كلمة المرور: admin123" -ForegroundColor Gray
Write-Host ""

python create_admin.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ تم الإعداد بنجاح!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "الآن شغّل المشروع بالأمر:" -ForegroundColor Yellow
Write-Host "   python app.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "ثم افتح المتصفح على:" -ForegroundColor Yellow
Write-Host "   http://127.0.0.1:5000/auth/login" -ForegroundColor Cyan
Write-Host ""
Write-Host "بيانات الدخول:" -ForegroundColor Yellow
Write-Host "   اسم المستخدم: admin" -ForegroundColor White
Write-Host "   كلمة المرور: admin123" -ForegroundColor White
Write-Host ""
