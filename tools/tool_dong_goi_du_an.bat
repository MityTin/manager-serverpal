@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo.
echo =========================================================
echo   TOOL DONG GOI TOAN BO DU AN - Manager ServerPal
echo =========================================================
echo.
echo Tool nay se tu dong:
echo   1) Build Manager_ServerPal.exe (setup app)
echo   2) Build Manager_ServerPal_App.exe (main app)
echo   3) Dung Inno Setup 6 dong goi ra 1 file installer duy nhat
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo [0/4] Kiem tra Python...
%PY_EXE% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python.
    pause
    exit /b 1
)

echo [0/4] Cai dat PyInstaller...
%PY_EXE% -m pip install --disable-pip-version-check --upgrade pyinstaller >nul
if %errorlevel% neq 0 (
    echo [LOI] Khong cai duoc PyInstaller.
    pause
    exit /b 1
)

echo [1/4] Build setup app EXE...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "Manager_ServerPal.spec" del /f /q "Manager_ServerPal.spec"
%PY_EXE% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Manager_ServerPal" ^
  --icon "_ui_assets\app_icon.png" ^
  --add-data "_ui_assets;_ui_assets" ^
  --add-data "requirements.txt;." ^
  --add-data "HUONG_DAN.txt;." ^
  --add-data "PalWorldSettings.ini;." ^
  --add-data "manager_config.json;." ^
  setup.py
if %errorlevel% neq 0 (
    echo [LOI] Build Manager_ServerPal.exe that bai.
    pause
    exit /b 1
)

echo [2/4] Build server app EXE...
if exist "Manager_ServerPal_App.spec" del /f /q "Manager_ServerPal_App.spec"
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
    echo [LOI] Build Manager_ServerPal_App.exe that bai.
    pause
    exit /b 1
)

if not exist "release" mkdir "release"

echo [3/4] Tim Inno Setup 6 (ISCC.exe)...
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
    echo [LOI] Khong tim thay Inno Setup 6 ^(ISCC.exe^).
    echo Hay cai Inno Setup 6 roi chay lai tool nay.
    pause
    exit /b 1
)
echo [OK] ISCC: !ISCC_EXE!

echo [4/4] Dong goi installer bang Inno Setup 6...
"!ISCC_EXE!" "installer\Manager_ServerPal.iss"
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Build installer that bai.
    pause
    exit /b 1
)

set "LATEST_SETUP="
for /f "delims=" %%f in ('dir /b /a:-d /o:-d "release\Manager_ServerPal_Setup_v*.exe" 2^>nul') do (
    if not defined LATEST_SETUP set "LATEST_SETUP=%%f"
)

if not defined LATEST_SETUP (
    echo [LOI] Khong tim thay installer trong thu muc release.
    pause
    exit /b 1
)

copy /y "release\!LATEST_SETUP!" "release\Manager_ServerPal_Setup_Latest.exe" >nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tao duoc file release\Manager_ServerPal_Setup_Latest.exe
    pause
    exit /b 1
)

echo.
echo [OK] Dong goi thanh cong bang Inno Setup 6.
echo Thanh pham 1 file de gui cho nguoi dung:
echo   release\Manager_ServerPal_Setup_Latest.exe
echo.
echo (Ban goc theo version van duoc giu lai trong release\Manager_ServerPal_Setup_v*.exe)
echo.
pause
exit /b 0

