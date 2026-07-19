@echo off
title Dhaher Labs — Hedge Fund + Dashboard
color 0A
cd /d E:\trading

echo ==========================================
echo   Dhaher Labs Hedge Fund System
echo   Starting MT5 + Dashboard...
echo ==========================================
echo.

:: Check if MT5 is already running
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [✅] MT5 already running
) else (
    echo [⏳] Starting MT5...
    start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
    echo [✅] MT5 launched
)

:: Wait for MT5 to initialize
echo [⏳] Waiting for MT5 to connect...
timeout /t 10 /nobreak >nul

:: Start the dashboard
echo [⏳] Starting Hedge Fund Dashboard...
start "" /B "C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\uvicorn" dashboard:app --host 127.0.0.1 --port 5050 --reload
echo [✅] Dashboard on http://localhost:5050

:: Start market context updater (background)
echo [⏳] Starting Market Context...
start "" /B "C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python" market_context.py --daemon
echo [✅] Market context active

echo.
echo ==========================================
echo   SYSTEM READY
echo   Dashboard: http://localhost:5050
echo   MT5: %date% %time%
echo   Close this window to stop everything
echo ==========================================
echo.

:: Keep window alive so closing it kills everything
pause
taskkill /F /FI "WINDOWTITLE eq Hedge Fund Dashboard*" >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq Market Context*" >nul 2>nul
echo All services stopped.