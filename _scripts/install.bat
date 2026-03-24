@echo off
chcp 65001 >nul
title Manager ServerPal - Setup
cd /d "%~dp0\.."

echo.
echo  ===========================================================
echo    Manager ServerPal v1.0.2 by MityTinDev - Setup
echo  ===========================================================
echo.

echo  [1/4] Check Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found in PATH.
    echo  Download: https://www.python.org/downloads/
    pause & exit /b 1
)

echo.
echo  [2/4] Install Python packages...
pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  [ERROR] pip install failed.
    pause & exit /b 1
)

echo.
echo  [3/4] Check Node.js (for Live Map)...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [WARN] Node.js not found. Live Map may not work.
) else (
    if exist "palserver-online-map-main\package.json" (
        pushd palserver-online-map-main
        npm install --silent
        popd
    )
)

echo.
echo  [4/4] Validate manager_config.json...
python -c "import json; json.load(open('manager_config.json','r',encoding='utf-8')); print('  config ok')"
if %errorlevel% neq 0 (
    echo  [ERROR] manager_config.json invalid.
    pause & exit /b 1
)

echo.
echo  Setup complete.
pause
exit /b 0

