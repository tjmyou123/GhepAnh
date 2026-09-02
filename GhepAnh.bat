@echo off
rem Khoi dong giao dien Ghep anh thong minh
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m smart_collage.gui
) else (
    python -m smart_collage.gui
)
if errorlevel 1 pause
