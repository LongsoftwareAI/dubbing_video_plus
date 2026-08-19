@echo off
chcp 65001 > nul
title Dubbing Video Plus+ - Installer
echo ========================================================
echo   🚀 DUBBING VIDEO PLUS+ — CÀI ĐẶT THƯ VIỆN BẮT BUỘC
echo ========================================================
echo.

if not exist venv (
    echo [+] Đang tạo môi trường ảo Python (venv)...
    python -m venv venv
)

echo [+] Đang kích hoạt môi trường ảo và cài đặt thư viện...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================================
echo   🎉 CÀI ĐẶT HOÀN TẤT! BẠN CÓ THỂ CHẠY RUN_APP.BAT
echo ========================================================
echo.
pause
