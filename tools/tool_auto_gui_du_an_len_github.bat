@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo.
echo =========================================================
echo   TOOL AUTO GUI DU AN LEN GITHUB - Manager ServerPal
echo =========================================================
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay git trong PATH.
    echo Hay cai Git for Windows roi chay lai.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURRENT_BRANCH=%%i"
if "!CURRENT_BRANCH!"=="" (
    echo [LOI] Thu muc hien tai khong phai Git repository hop le.
    pause
    exit /b 1
)

echo Nhanh trang thai repository:
git status --short
echo.

set "COMMIT_MSG="
set /p COMMIT_MSG=Nhap noi dung commit (de trong de dung mac dinh): 
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=chore: auto upload project"

echo.
echo Dang add file...
git add -A
if %errorlevel% neq 0 (
    echo [LOI] Khong the git add.
    pause
    exit /b 1
)

git diff --cached --quiet
if %errorlevel% equ 0 (
    echo [INFO] Khong co thay doi nao de commit.
    echo Van se thu push nhanh branch !CURRENT_BRANCH!...
    git push origin !CURRENT_BRANCH!
    if %errorlevel% neq 0 (
        echo [LOI] Push that bai.
        pause
        exit /b 1
    )
    echo [OK] Push thanh cong.
    pause
    exit /b 0
)

echo Dang commit...
git commit -m "!COMMIT_MSG!"
if %errorlevel% neq 0 (
    echo [LOI] Commit that bai.
    pause
    exit /b 1
)

echo Dang push len origin/!CURRENT_BRANCH! ...
git push origin !CURRENT_BRANCH!
if %errorlevel% neq 0 (
    echo [LOI] Push that bai.
    pause
    exit /b 1
)

echo.
echo [OK] Da gui du an len GitHub thanh cong.
echo Nhanh commit gan nhat:
git log --oneline -1
echo.
pause
exit /b 0

