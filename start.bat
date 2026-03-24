@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Manager ServerPal — Launcher

:MENU
cls
echo.
echo  ===========================================================
echo    Manager ServerPal v1.0.2 by MityTinDev - Launcher
echo  ===========================================================
echo.
echo    [1] Run ServerPal (main app)
echo    [2] Open Setup / Config / Update
echo    [3] Dev only: install build environment
echo    [4] View guide
echo    [5] Exit
echo.
set /p CHOICE="  Select [1-5]: "

if "%CHOICE%"=="1" goto RUN_SERVERPAL
if "%CHOICE%"=="2" goto RUN_SETUP
if "%CHOICE%"=="3" goto RUN_INSTALL
if "%CHOICE%"=="4" goto SHOW_GUIDE
if "%CHOICE%"=="5" goto EXIT
goto MENU

:RUN_SERVERPAL
cls
if exist "dist\Manager_ServerPal_App.exe" (
    start "" "dist\Manager_ServerPal_App.exe"
    goto MENU
)
if exist "Manager_ServerPal_App.exe" (
    start "" "Manager_ServerPal_App.exe"
    goto MENU
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] App EXE not found and Python not installed.
    echo  Build EXE first with: _scripts\build_full_release.bat
    pause & goto MENU
)
pythonw serverpal.py
goto MENU

:RUN_SETUP
cls
if exist "dist\Manager_ServerPal.exe" (
    start "" "dist\Manager_ServerPal.exe"
    goto MENU
)
if exist "Manager_ServerPal.exe" (
    start "" "Manager_ServerPal.exe"
    goto MENU
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Setup EXE not found and Python not installed.
    echo  Build EXE first with: _scripts\build_full_release.bat
    pause & goto MENU
)
pythonw setup.py
goto MENU

:RUN_INSTALL
echo  [INFO] This option is for developers building from source only.
call "_scripts\install.bat"
goto MENU

:SHOW_GUIDE
cls
if exist "docs\HUONG_DAN.txt" (
    type "docs\HUONG_DAN.txt" | more
) else (
    echo  Guide file not found: docs\HUONG_DAN.txt
)
pause
goto MENU

:EXIT
exit /b 0

