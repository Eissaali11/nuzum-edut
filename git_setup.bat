@echo off
setlocal enabledelayedexpansion
cd /d D:\nuzm

echo ========================================
echo NUZUM - Git Upload Setup
echo ========================================
echo.

set GIT="C:\Program Files (x86)\Git\bin\git.exe"

echo Step 1: Configure Git...
%GIT% config --global user.name "NUZUM"
%GIT% config --global user.email "admin@nuzum.local"
echo Done.
echo.

echo Step 2: Initialize repository...
if exist .git (
    echo Repository already exists
) else (
    %GIT% init
)
echo.

echo Step 3: Add all files...
%GIT% add .
echo.

echo Step 4: Commit...
%GIT% commit -m "Initial commit: NUZUM System Production Ready"
echo.

echo Step 5: Show log...
%GIT% log --oneline -3
echo.

echo ========================================
echo Repository Ready!
echo ========================================
echo.
echo Next steps:
echo 1. Go to https://github.com/new
echo 2. Create NUZUM repository
echo 3. Run:
echo    git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git
echo    git branch -M main
echo    git push -u origin main
echo.
pause
