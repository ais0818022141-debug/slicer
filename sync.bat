@echo off
chcp 65001 > nul
title TealMED File Synchronizer (JSON ^<^-^> CSV)
echo =================================================================
echo       TealMED File Synchronizer (JSON ^<^-^> CSV)
echo =================================================================
echo.
cd /d "%~dp0"
python file_syncer.py %*
echo.
pause
