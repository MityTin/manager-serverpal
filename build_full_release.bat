@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo =========================================================
echo   Build Full Release (No Python/Node required on client)
echo =========================================================
echo.

call build_manager_serverpal_exe.bat
if %errorlevel% neq 0 exit /b 1

call build_manager_serverpal_app_exe.bat
if %errorlevel% neq 0 exit /b 1

call build_manager_serverpal_installer.bat
if %errorlevel% neq 0 exit /b 1

echo.
echo [OK] Full release ready:
echo   release\Manager_ServerPal_Setup_v1.0.0.exe
echo.
pause
exit /b 0

