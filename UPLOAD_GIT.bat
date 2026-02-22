@echo off
REM Add Git to PATH
set PATH=%PATH%;C:\Program Files (x86)\Git\bin

REM Change to project directory
cd /d D:\nuzm

REM Configure Git
git config --global user.name "NUZUM System"
git config --global user.email "admin@nuzum.local"

REM Initialize Git repository
echo Initializing Git repository...
git init
git add .
echo Committing files...
git commit -m "Initial commit: NUZUM Attendance System - Production Ready"

echo.
echo ========================================================
echo Git repository initialized and committed!
echo ========================================================
echo.
echo Next steps to upload to GitHub:
echo.
echo 1. Go to https://github.com/new
echo 2. Create a new repository named: NUZUM
echo 3. Copy the HTTPS URL from GitHub
echo 4. Run this command in PowerShell:
echo.
echo    git remote add origin [YOUR_GITHUB_URL]
echo    git branch -M main
echo    git push -u origin main
echo.
echo ========================================================
echo.

pause
