@echo off
chcp 65001 > nul
title TealMED Master CSV-to-All Synchronizer
echo =================================================================
echo       TealMED Master CSV-to-All Synchronizer
echo       تحديث ملفات JSON و AI.md و HTML تلقائياً من ملف CSV
echo =================================================================
echo.
cd /d "%~dp0"
python sync_from_csv.py %*
echo.
pause
