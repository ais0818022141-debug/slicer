@echo off
chcp 65001 > nul
title TealMED PDF/HTML Question Bank Generator
echo =================================================================
echo        TealMED PDF & HTML Question Bank Generator
echo =================================================================
echo.
cd /d "%~dp0"
python generator.py %*
echo.
pause
