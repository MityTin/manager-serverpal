@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo.
echo ===================================================
echo   Build Manager_ServerPal_App.exe (serverpal.py)
echo ===================================================
echo.

set "PY_EXE=python"

echo [1/3] Kiem tra Python...
%PY_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python.
    pause
    exit /b 1
)

echo [2/3] Cai dat PyInstaller...
%PY_EXE% -m pip install --disable-pip-version-check --upgrade pyinstaller >nul
if %errorlevel% neq 0 (
    echo [LOI] Khong cai duoc PyInstaller.
    pause
    exit /b 1
)

echo [3/3] Build EXE serverpal...
%PY_EXE% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Manager_ServerPal_App" ^
  --icon "_ui_assets\app_icon.png" ^
  --add-data "_ui_assets;_ui_assets" ^
  --add-data "_datadb;_datadb" ^
  --add-data "_map_assets;_map_assets" ^
  --add-data "manager_config.json;." ^
  --add-data "PalWorldSettings.ini;." ^
  serverpal.py

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Build that bai.
    pause
    exit /b 1
)

echo.
echo [OK] Da tao: dist\Manager_ServerPal_App.exe
echo.
pause
exit /b 0

