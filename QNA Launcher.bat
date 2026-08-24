@echo off
rem ══════════════════════════════════════════════════════
rem  QNA v8.0 All-in-One Launcher — Backend + Dashboard + Tray + Browser
rem  Double-click this file to start everything.
rem ══════════════════════════════════════════════════════
title QNA v8.0 — Autonomous Hedge Fund
color 0A

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║   Quant-Nanggroe-AI v8.0                   ║
echo  ║   Autonomous Quant Hedge Fund              ║
echo  ║   FX / Commodity / Indices on MT5          ║
echo  ╚════════════════════════════════════════════╝
echo.

set "PYTHONPATH="
set "ROOT=%~dp0"

echo [1/4] Starting FastAPI backend (port 8000)...
start "QNA-Backend" /min cmd /c "cd /d "%ROOT%" && C:\Python314\python.exe qna.py api > logs\backend.log 2>&1"
timeout /t 5 /nobreak >nul

echo [2/4] Starting Dashboard (port 3000)...
start "QNA-Dashboard" /min cmd /c "cd /d "%ROOT%dashboard" && npm run dev > ..\logs\dashboard.log 2>&1"
timeout /t 8 /nobreak >nul

echo [3/4] Starting System Tray...
if exist "C:\Python314\pythonw.exe" (
    start "" "C:\Python314\pythonw.exe" "%ROOT%scripts\qna_tray.py"
) else (
    start "" "C:\Python314\python.exe" "%ROOT%scripts\qna_tray.py"
)
timeout /t 2 /nobreak >nul

echo [4/4] Opening Dashboard in browser...
start http://localhost:3000

echo.
echo  ══════════════════════════════════════════════
echo   ALL SERVICES RUNNING
echo   ────────────────────────────────────────────
echo   Backend:    http://localhost:8000/docs
echo   Dashboard:  http://localhost:3000
echo   API Docs:   http://localhost:8000/docs
echo   Tray:       System tray icon (bottom right)
echo   ────────────────────────────────────────────
echo   Press Ctrl+C in each window to stop,
echo   or use tray icon → Exit.
echo  ══════════════════════════════════════════════
echo.
pause
