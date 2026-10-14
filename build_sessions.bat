@echo off
chcp 65001 >nul
title TealMED - بناء وتجميع ملفات دورات الامتحان الطبي الموحد
cls
echo ===================================================================
echo   TealMED - مولد ملفات دورات الامتحان الطبي الموحد (السنوات الكاملة)
echo ===================================================================
echo.
echo [1] مزامنة أحدث التعديلات والملفات من final وبناء كافة الدورات (موصى به)
echo [2] بناء الدورات من لقطة العمل الحالية في exams_builder\input_snapshot
echo [3] فتح لوحة التحكم وفهرس الدورات (index.html) في المتصفح
echo [4] خروج
echo.
set /p choice="اختر رقم العملية (1-4) [الافتراضي: 1]: "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto sync_and_build
if "%choice%"=="2" goto build_current
if "%choice%"=="3" goto open_catalog
if "%choice%"=="4" goto exit_app

:sync_and_build
echo.
echo [*] جاري مزامنة أحدث الملفات من final وبناء كافة الدورات...
python exams_builder\build_exam_sessions.py --sync
goto finish_build

:build_current
echo.
echo [*] جاري بناء ملفات الدورات من exams_builder\input_snapshot...
python exams_builder\build_exam_sessions.py
goto finish_build

:open_catalog
echo.
echo [*] فتح الفهرس ولوحة التحكم في المتصفح...
start "" "exams_builder\output\index.html"
goto exit_app

:finish_build
echo.
echo ===================================================================
echo [✓] تم الانتهاء بنجاح! تم إنشاء ملفات JSON و CSV و HTML لكل دورة.
echo ===================================================================
echo.
set /p open_now="هل تريد فتح لوحة التحكم وفهرس الدورات الآن؟ (y/n) [y]: "
if "%open_now%"=="" set open_now=y
if /i "%open_now%"=="y" start "" "exams_builder\output\index.html"

:exit_app
pause
