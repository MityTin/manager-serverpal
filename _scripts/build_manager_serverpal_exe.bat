@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo.
echo ===============================================
echo   Build Manager_ServerPal.exe (PyInstaller)
echo ===============================================
echo.

set "PY_EXE=python"

echo [1/4] Kiem tra Python...
%PY_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python.
    echo Hay cai Python 3.10+ roi chay lai.
    pause
    exit /b 1
)

echo [2/4] Cai dat PyInstaller...
%PY_EXE% -m pip install --disable-pip-version-check --upgrade pyinstaller >nul
if %errorlevel% neq 0 (
    echo [LOI] Khong cai duoc PyInstaller.
    pause
    exit /b 1
)

echo [3/4] Don file build cu...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "Manager_ServerPal.spec" del /f /q "Manager_ServerPal.spec"

echo [4/4] Build EXE...
%PY_EXE% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Manager_ServerPal" ^
  --icon "_ui_assets\app_icon.png" ^
  --add-data "_ui_assets;_ui_assets" ^
  --add-data "requirements.txt;." ^
  --add-data "docs\HUONG_DAN.txt;docs" ^
  --add-data "PalWorldSettings.ini;." ^
  --add-data "manager_config.json;." ^
  setup.py

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Build that bai.
    pause
    exit /b 1
)

echo.
echo [OK] Da tao: dist\Manager_ServerPal.exe
echo Ban co the gui file EXE nay cho nguoi dung tai va chay truc tiep.
echo.
pause
exit /b 0

