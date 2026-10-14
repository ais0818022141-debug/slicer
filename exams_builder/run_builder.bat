@echo off
chcp 65001 >nul
title TealMED - بناء وتجميع ملفات دورات الامتحان الطبي الموحد
cls
echo ===================================================================
echo   TealMED - مولد ملفات دورات الامتحان الطبي الموحد (السنوات الكاملة)
echo ===================================================================
echo.
echo [1] إعادة بناء الدورات من لقطة العمل الحالية (input_snapshot)
echo [2] مزامنة أحدث التعديلات والملفات من final ثم إعادة البناء الشامل
echo [3] فتح لوحة التحكم والفهرس (index.html) في المتصفح
echo [4] خروج
echo.
set /p choice="اختر رقم العملية (1-4) [الافتراضي: 2]: "

if "%choice%"=="" set choice=2
if "%choice%"=="1" goto build_current
if "%choice%"=="2" goto sync_and_build
if "%choice%"=="3" goto open_catalog
if "%choice%"=="4" goto exit_app

:build_current
echo.
echo [*] جاري بناء ملفات الدورات من input_snapshot...
python build_exam_sessions.py
goto finish_build

:sync_and_build
echo.
echo [*] جاري مزامنة أحدث الملفات من final وبناء الدورات...
python build_exam_sessions.py --sync
goto finish_build

:open_catalog
echo.
echo [*] فتح الفهرس ولوحة التحكم في المتصفح...
start "" "output\index.html"
goto exit_app

:finish_build
echo.
echo ===================================================================
echo [✓] تم الانتهاء بنجاح! تم إنشاء ملفات JSON و CSV و HTML لكل دورة.
echo ===================================================================
echo.
set /p open_now="هل تريد فتح لوحة التحكم والفهرس الشامل الآن؟ (y/n) [y]: "
if "%open_now%"=="" set open_now=y
if /i "%open_now%"=="y" start "" "output\index.html"

:exit_app
pause
