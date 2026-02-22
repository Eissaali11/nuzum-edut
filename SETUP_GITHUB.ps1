# ============================================
# رفع المشروع على GitHub
# Push Project to GitHub
# ============================================

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  نظام نزوم - رفع على GitHub" -ForegroundColor Yellow
Write-Host "  NUZUM System - GitHub Upload" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# الخطوة 1: تهيئة Git (إذا لم يكن موجوداً)
Write-Host "📝 الخطوة 1: فحص Git Repository..." -ForegroundColor Green
if (!(Test-Path ".git")) {
    Write-Host "  • تهيئة Git repository جديد" -ForegroundColor Cyan
    git init
    git config user.name "نزوم نظام"
    git config user.email "admin@nuzum.local"
} else {
    Write-Host "  • Git repository موجود بالفعل ✓" -ForegroundColor Green
}

Write-Host ""

# الخطوة 2: إضافة .gitignore 
Write-Host "📝 الخطوة 2: التحقق من .gitignore..." -ForegroundColor Green
if (Test-Path ".gitignore") {
    Write-Host "  • .gitignore موجود ✓" -ForegroundColor Green
} else {
    Write-Host "  • تحذير: .gitignore غير موجود" -ForegroundColor Yellow
}

Write-Host ""

# الخطوة 3: حالة Git
Write-Host "📝 الخطوة 3: حالة المشروع الحالية:" -ForegroundColor Green
git status

Write-Host ""

# الخطوة 4: إضافة الملفات
Write-Host "📝 الخطوة 4: إضافة الملفات للـ staging..." -ForegroundColor Green
git add .
Write-Host "  • تم إضافة الملفات ✓" -ForegroundColor Green

Write-Host ""

# الخطوة 5: عمل Commit
Write-Host "📝 الخطوة 5: عمل commit أول..." -ForegroundColor Green
$commitMessage = "Initial commit: NUZUM Attendance System - Fully Modularized (Phase 2 Complete)"
git commit -m $commitMessage
Write-Host "  • Commit تم بنجاح ✓" -ForegroundColor Green

Write-Host ""

# الخطوة 6: معلومات الـ Remote
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  الخطوة التالية: الربط مع GitHub" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 للمتابعة، تحتاج إلى عمل الخطوات التالية يدويًا:" -ForegroundColor Magenta
Write-Host ""
Write-Host "1️⃣ اذهب إلى: https://github.com/new" -ForegroundColor Cyan
Write-Host "   وأنشئ repository جديد باسم: NUZUM" -ForegroundColor Cyan
Write-Host ""
Write-Host "2️⃣ بعد الإنشاء، شغّل أحد الأوامر التالية:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # الخيار الأول: HTTPS (أسهل)" -ForegroundColor Yellow
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "   # الخيار الثاني: SSH (أكثر أماناً)" -ForegroundColor Yellow
Write-Host "   git remote add origin git@github.com:YOUR_USERNAME/NUZUM.git" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  استبدل YOUR_USERNAME باسم حسابك على GitHub" -ForegroundColor Red
Write-Host ""

# عرض معلومات إضافية
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  معلومات المشروع" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 اسم المشروع: NUZUM" -ForegroundColor Cyan
Write-Host "📄 نوع المشروع: Flask Application" -ForegroundColor Cyan
Write-Host "🗂️  المجلد: $(Get-Location)" -ForegroundColor Cyan
Write-Host "📊 آخر commit:" -ForegroundColor Cyan
git log --oneline -1
Write-Host ""

Write-Host "✅ تم بنجاح! جاهز للرفع على GitHub" -ForegroundColor Green
Write-Host ""
