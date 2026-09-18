@echo off
chcp 65001 >nul
setlocal
cd /d C:\motors_project

for /f "delims=" %%i in ('.venv\Scripts\python.exe -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'))"') do set TS=%%i
set OUTFILE=docs\test_results_%TS%.md

rem Дальше для лога нужен именно PowerShell 7 (pwsh): Tee-Object в Windows
rem PowerShell 5.1 не имеет -Encoding и пишет файл в UTF-16LE. Из-за этого в
rem одном md смешивались UTF-8-строки echo и UTF-16-тело pytest, и лог не
rem читался ни одним редактором. Проверка ниже - чтобы не получить молча
rem сломанный лог на машине без pwsh.
where pwsh >nul 2>nul
if errorlevel 1 (
  echo [ОШИБКА] не найден pwsh - для записи лога в UTF-8 нужна PowerShell 7.
  echo Установка: winget install Microsoft.PowerShell
  if not defined NO_PAUSE pause
  exit /b 1
)
set PYTEST_PS=pwsh

echo # Прогон тестов: %TS%>"%OUTFILE%"
echo.>>"%OUTFILE%"

echo ================================================
echo   UNIT / ROUTE ТЕСТЫ (tests, без e2e)
echo ================================================
echo ## Unit/route (tests, без e2e)>>"%OUTFILE%"
echo ```>>"%OUTFILE%"
%PYTEST_PS% -NoProfile -Command "$env:PYTHONUTF8='1'; & '.venv\Scripts\python.exe' -m pytest tests -v --ignore=tests/e2e 2>&1 | Tee-Object -FilePath '%OUTFILE%' -Append -Encoding utf8"
echo ```>>"%OUTFILE%"
echo.>>"%OUTFILE%"

echo.
echo ================================================
echo   E2E ТЕСТЫ (tests/e2e)
echo ================================================
echo ## E2E (tests/e2e)>>"%OUTFILE%"
echo ```>>"%OUTFILE%"
%PYTEST_PS% -NoProfile -Command "$env:PYTHONUTF8='1'; & '.venv\Scripts\python.exe' -m pytest tests/e2e -v 2>&1 | Tee-Object -FilePath '%OUTFILE%' -Append -Encoding utf8"
echo ```>>"%OUTFILE%"

echo.
echo ================================================
echo   Готово: %OUTFILE%
echo ================================================
rem pause только в интерактивном запуске: при NO_PAUSE=1 батник не висит.
if not defined NO_PAUSE pause