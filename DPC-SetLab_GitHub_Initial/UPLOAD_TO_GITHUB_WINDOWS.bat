@echo off
setlocal
cd /d "%~dp0"

git --version >nul 2>&1
if errorlevel 1 (
  echo Git is not installed. Install Git for Windows first.
  pause
  exit /b 1
)

if not exist .git (
  git init
)

git branch -M main
git add .
git commit -m "Initial release: DPC SetLab v2.3.2"
git remote remove origin >nul 2>&1
git remote add origin https://github.com/lms4038-web/DPC-SetLab.git
git push -u origin main

if errorlevel 1 (
  echo.
  echo Upload failed. Check GitHub sign-in or repository permissions.
) else (
  echo.
  echo Upload completed successfully.
)
pause
