@echo off
chcp 65001 >nul
title TealMED - بناء بنك الأسئلة من ملف Markdown إلى مجلد final الكامل
cls
echo ===================================================================
echo   TealMED - مولد مجلد المادة الكامل من قالب Markdown إلى final/
echo ===================================================================
echo.

if "%~1"=="" goto pick_file
python build_subject_from_md.py "%~1"
goto finish

:pick_file
echo [*] لم يتم تحديد ملف، جاري فتح نافذة اختيار ملف Markdown...
python build_subject_from_md.py
goto finish

:finish
echo.
echo ===================================================================
pause
