@echo off
chcp 65001 > nul
title Dubbing Video Plus+
echo ========================================================
echo   🎬 ĐANG KHỞI CHẠY DUBBING VIDEO PLUS+...
echo ========================================================
echo.

if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe main.py
) else if exist ..\venv\Scripts\python.exe (
    ..\venv\Scripts\python.exe main.py
) else (
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Ứng dụng đã dừng lại với mã lỗi %ERRORLEVEL%.
    pause
)
