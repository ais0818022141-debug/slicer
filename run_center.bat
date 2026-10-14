@echo off
title TealMED Studio - Control Center
cd /d "%~dp0"
start "" pythonw tealmed_center.py
if errorlevel 1 (
    python tealmed_center.py
    pause
)
