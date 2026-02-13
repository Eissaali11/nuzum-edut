# دفع المشروع إلى مستودع nuzum-edut على GitHub
# شغّل هذا الملف من PowerShell ثم أدخل بيانات الدخول عند الطلب.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "الريموت الحالي edut:" -ForegroundColor Cyan
git remote -v | Select-String "edut"
Write-Host ""

Write-Host "جاري الدفع إلى https://github.com/Eissaali11/nuzum-edut.git ..." -ForegroundColor Yellow
Write-Host "عند الطلب: استخدم اسم المستخدم Eissaali11 وكلمة المرور = Personal Access Token من GitHub." -ForegroundColor Gray
Write-Host ""

git push -u edut main

if ($LASTEXITCODE -eq 0) {
    Write-Host "تم رفع المشروع بنجاح إلى nuzum-edut." -ForegroundColor Green
} else {
    Write-Host "فشل الدفع. تحقق من الاتصال والمصادقة (Token من GitHub)." -ForegroundColor Red
}
