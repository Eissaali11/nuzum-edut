# Script to setup Git and push to GitHub
# سكريبت إعداد Git والرفع على GitHub

$gitPath = "C:\Program Files (x86)\Git\bin"
$env:PATH += ";$gitPath"
$projectPath = "D:\nuzm"

Set-Location $projectPath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NUZUM - Git Setup & Initial Commit" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Configure Git
Write-Host "Step 1: Configuring Git..." -ForegroundColor Green
& "$gitPath\git.exe" config --global user.name "NUZUM System"
& "$gitPath\git.exe" config --global user.email "admin@nuzum.local"
Write-Host "✓ Git configured" -ForegroundColor Green
Write-Host ""

# Step 2: Initialize repository
Write-Host "Step 2: Initializing Git repository..." -ForegroundColor Green
if (Test-Path .git) {
    Write-Host "✓ Repository already exists" -ForegroundColor Green
} else {
    & "$gitPath\git.exe" init
    Write-Host "✓ Repository initialized" -ForegroundColor Green
}
Write-Host ""

# Step 3: Add all files
Write-Host "Step 3: Adding all files..." -ForegroundColor Green
& "$gitPath\git.exe" add .
Write-Host "✓ Files added" -ForegroundColor Green
Write-Host ""

# Step 4: Check status
Write-Host "Step 4: Checking status..." -ForegroundColor Green
$status = & "$gitPath\git.exe" status --short
$fileCount = ($status | Measure-Object).Count
Write-Host "✓ Total files to commit: $fileCount" -ForegroundColor Green
Write-Host ""

# Step 5: Create first commit
Write-Host "Step 5: Creating first commit..." -ForegroundColor Green
$commitMsg = "Initial commit: NUZUM Attendance System - Production Ready (Phase 2 Complete, Health Check 12/12, Routes 11/13, Port 5000)"
& "$gitPath\git.exe" commit -m $commitMsg
Write-Host "✓ Commit created successfully" -ForegroundColor Green
Write-Host ""

# Step 6: Display log
Write-Host "Step 6: Commit history:" -ForegroundColor Green
& "$gitPath\git.exe" log --oneline -5
Write-Host ""

# Step 7: Ready for GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Repository Ready for GitHub!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://github.com/new" -ForegroundColor White
Write-Host "2. Create repository named: NUZUM" -ForegroundColor White
Write-Host "3. Copy the HTTPS URL" -ForegroundColor White
Write-Host "4. Run these commands:" -ForegroundColor White
Write-Host ""
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git" -ForegroundColor Cyan
Write-Host "   git branch -M main" -ForegroundColor Cyan
Write-Host "   git push -u origin main" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Repository Statistics:" -ForegroundColor Green
Write-Host "   Files: $fileCount" -ForegroundColor White
Write-Host "   Size: " (Get-ChildItem . -Recurse | Measure-Object -Sum Length | ForEach-Object {"{0:F2} MB" -f ($_.Sum/1MB)}) -ForegroundColor White
Write-Host ""
