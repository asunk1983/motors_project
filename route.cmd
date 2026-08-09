@echo off
:: Check admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Run as Administrator!
    pause
    exit /b
)
route add 192.168.1.0 mask 255.255.255.0 192.168.1.140 -p
echo Route to motors server added. Done.
pause