@echo off
chcp 65001 >nul
title Manager ServerPal — Setup

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   Manager ServerPal v1.0.0 by MityTinDev — Cài Đặt     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Chuyển về thư mục chứa file .bat ──────────────────────────────────────
cd /d "%~dp0"

:: ══════════════════════════════════════════════════════════════════════════
:: [1] KIỂM TRA PYTHON
:: ══════════════════════════════════════════════════════════════════════════
echo  [1/4] Kiểm tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [LỖI] Python chưa được cài hoặc chưa có trong PATH!
    echo.
    echo  Tải Python tại: https://www.python.org/downloads/
    echo  ✔ Nhớ tick "Add Python to PATH" khi cài!
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo         %%v [OK]

:: ══════════════════════════════════════════════════════════════════════════
:: [2] CÀI PYTHON PACKAGES
:: ══════════════════════════════════════════════════════════════════════════
echo.
echo  [2/4] Cài Python packages (requirements.txt)...
pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  [LỖI] pip install thất bại — kiểm tra internet/pip/venv rồi chạy lại.
    pause & exit /b 1
)
echo         requests, psutil, Pillow, discord.py, py7zr, rarfile [OK]

:: ══════════════════════════════════════════════════════════════════════════
:: [3] KIỂM TRA NODE.JS + CÀI PACKAGE LIVE MAP
:: ══════════════════════════════════════════════════════════════════════════
echo.
echo  [3/4] Kiểm tra Node.js (Live Map)...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo         [CẢNH BÁO] Node.js chưa cài — Live Map sẽ không hoạt động.
    echo         Tải Node.js tại: https://nodejs.org/  ^(LTS^)
    echo         Sau khi cài xong, chạy lại install.bat để hoàn tất.
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo         Node.js %%v [OK]
    if exist "palserver-online-map-main\package.json" (
        echo         Cài Node packages cho Live Map...
        pushd palserver-online-map-main
        npm install --silent
        if %errorlevel% neq 0 (
            echo  [LỖI] npm install thất bại.
        ) else (
            echo         express, cors, axios [OK]
        )
        popd
    ) else (
        echo         [CẢNH BÁO] Không tìm thấy palserver-online-map-main\package.json
    )
)

:: ══════════════════════════════════════════════════════════════════════════
:: [4] KIỂM TRA CONFIG
:: ══════════════════════════════════════════════════════════════════════════
echo.
echo  [4/4] Kiểm tra manager_config.json...
python -c "import json,sys; c=json.load(open('manager_config.json','r',encoding='utf-8')); keys=[k for k in c if not k.startswith('/')and k!='_']; print('        ',len(keys),'config keys [OK]')" 2>nul
if %errorlevel% neq 0 (
    echo  [LỖI] manager_config.json bị lỗi cú pháp JSON!
    pause & exit /b 1
)

:: ══════════════════════════════════════════════════════════════════════════
:: HOÀN TẤT
:: ══════════════════════════════════════════════════════════════════════════
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                   CÀI ĐẶT HOÀN TẤT!                    ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║  Bước tiếp theo:                                        ║
echo  ║  1. Mở manager_config.json và điền thông tin server     ║
echo  ║  2. Chạy: python serverpal.py                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
