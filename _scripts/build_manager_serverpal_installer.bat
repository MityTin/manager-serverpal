@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo.
echo =========================================================
echo   Build Installer - Manager ServerPal (Inno Setup)
echo =========================================================
echo.

if not exist "dist\Manager_ServerPal.exe" (
    echo [LOI] Khong tim thay dist\Manager_ServerPal.exe
    echo Hay build EXE setup truoc bang:
    echo   _scripts\build_manager_serverpal_exe.bat
    echo.
    pause
    exit /b 1
)
if not exist "dist\Manager_ServerPal_App.exe" (
    echo [LOI] Khong tim thay dist\Manager_ServerPal_App.exe
    echo Hay build EXE serverpal truoc bang:
    echo   _scripts\build_manager_serverpal_app_exe.bat
    echo.
    pause
    exit /b 1
)

set "ISCC_EXE="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC_EXE!"=="" (
    for /f "delims=" %%i in ('where iscc 2^>nul') do (
        set "ISCC_EXE=%%i"
        goto :found_iscc
    )
)

:found_iscc
if "!ISCC_EXE!"=="" (
    echo [LOI] Khong tim thay Inno Setup Compiler (ISCC.exe)
    echo Cai Inno Setup 6 tai: https://jrsoftware.org/isdl.php
    echo Sau do chay lai file nay.
    echo.
    pause
    exit /b 1
)

if not exist "release" mkdir "release"

echo [1/1] Dang build installer...
"!ISCC_EXE!" "installer\Manager_ServerPal.iss"
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Build installer that bai.
    pause
    exit /b 1
)

echo.
echo [OK] Da tao installer tai:
echo   release\Manager_ServerPal_Setup_v1.0.2.exe
echo.
pause
exit /b 0

