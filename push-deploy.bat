@echo off
REM push-deploy.bat - push + deploy одной командой, для cmd.exe
REM Запуск из корня репозитория: push-deploy.bat

set SERVER_USER=kipia
set SERVER_HOST=192.168.1.140
set SERVER_PROJECT_DIR=/home/kipia/motors_project

echo === git push (production) ===
git push production main
if errorlevel 1 (
    echo git push production FAILED - deploy отменён
    exit /b 1
)

echo.
echo === Деплой на сервере (%SERVER_HOST%) ===
ssh -t %SERVER_USER%@%SERVER_HOST% "cd %SERVER_PROJECT_DIR% && ./deploy.sh"
