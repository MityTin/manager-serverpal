@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Manager ServerPal — Launcher

:MENU
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   Manager ServerPal v1.0.0 by MityTinDev — Launcher     ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║                                                          ║
echo  ║   [1]  🚀  Chạy ServerPal (App chính)                   ║
echo  ║   [2]  ⚙️   Mở Setup / Cấu hình / Update               ║
echo  ║   [3]  📦  Cài đặt môi trường (Python + Node.js)        ║
echo  ║   [4]  📄  Xem hướng dẫn cài đặt                        ║
echo  ║   [5]  ❌  Thoát                                         ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
set /p CHOICE="  Chọn [1-5]: "

if "%CHOICE%"=="1" goto RUN_SERVERPAL
if "%CHOICE%"=="2" goto RUN_SETUP
if "%CHOICE%"=="3" goto RUN_INSTALL
if "%CHOICE%"=="4" goto SHOW_GUIDE
if "%CHOICE%"=="5" goto EXIT
goto MENU

:RUN_SERVERPAL
cls
echo  Đang kiểm tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [LỖI] Python chưa cài! Chạy mục [3] để cài đặt.
    pause & goto MENU
)
echo  Đang khởi chạy ServerPal...
echo.
pythonw serverpal.py
goto MENU

:RUN_SETUP
cls
echo  Đang mở Setup...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [LỖI] Python chưa cài! Tải tại: https://www.python.org/downloads/
    pause & goto MENU
)
pythonw setup.py
goto MENU

:RUN_INSTALL
call install.bat
goto MENU

:SHOW_GUIDE
cls
if exist "HUONG_DAN.txt" (
    type HUONG_DAN.txt | more
) else (
    echo  Không tìm thấy HUONG_DAN.txt
)
pause
goto MENU

:EXIT
exit /b 0
