@echo off
chcp 65001 > nul
title Dubbing Video Plus+ - Backup to GitHub
echo ========================================================
echo   🚀 DUBBING VIDEO PLUS+ — BACKUP TO GITHUB
echo ========================================================
echo.
..\venv\Scripts\python.exe backup_to_github.py
echo.
pause
