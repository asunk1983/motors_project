@echo off
chcp 65001 >nul
cd /d "%~dp0"
 
python app.py
if errorlevel 1 (
    echo.
    echo Произошла ошибка при запуске app.py
    pause
)