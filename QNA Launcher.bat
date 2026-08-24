@echo off
rem ══════════════════════════════════════════════════════
rem  QNA v8.0.2 All-in-One Launcher
rem  Backend (FastAPI :8000) + Dashboard (Next.js :3000) + Tray + Browser
rem  Double-click to start everything.
rem ══════════════════════════════════════════════════════
title QNA v8.0.2 — Autonomous Hedge Fund
color 0A

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║   Quant-Nanggroe-AI v8.0.2                 ║
echo  ║   Autonomous Quant Hedge Fund              ║
echo  ║   FX / Commodity on MT5                    ║
echo  ╚════════════════════════════════════════════╝
echo.

set "PYTHONPATH="
set "ROOT=%~dp0"

rem Ensure logs directory exists
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

rem Auto-generate .env with JWT secret if missing
if not exist "%ROOT%.env" (
    echo  [SETUP] Generating .env with fresh JWT secret...
    C:\Python314\python.exe -c "import secrets,pathlib;k=secrets.token_hex(32);a='qna-'+secrets.token_hex(16);pathlib.Path(r'%ROOT%.env').write_text('QNAI_JWT_SECRET=%k%\nQNAI_API_KEY=%a%\nQNA_ADMIN_API_KEY=%a%\nQNA_LIVE_TRADING=1\nQNA_SCHEDULER_ENABLED=1\nQNA_LOG_LEVEL=INFO\n')"
    echo  [SETUP] .env created.
)

rem ── 1. Backend ─────────────────────────────────────
echo [1/4] Starting FastAPI backend on :8000 ...
start "QNA-Backend" /min /D "%ROOT%" cmd /c C:\Python314\python.exe qna.py api ^> logs\backend.log 2^>^&1
timeout /t 5 /nobreak >nul
echo      Backend launched.

rem ── 2. Dashboard ───────────────────────────────────
echo [2/4] Starting Dashboard on :3000 ...
if not exist "%ROOT%dashboard\node_modules" (
    echo      node_modules missing — running npm install...
    pushd "%ROOT%dashboard"
    call npm install --no-audit --no-fund >> "%ROOT%logs\npm-install.log" 2>&1
    popd
)
start "QNA-Dashboard" /min /D "%ROOT%dashboard" cmd /c npm run dev ^> ..\logs\dashboard.log 2^>^&1
timeout /t 8 /nobreak >nul
echo      Dashboard launched.

rem ── 3. System Tray ─────────────────────────────────
echo [3/4] Starting System Tray...
if exist "C:\Python314\pythonw.exe" (
    start "" "C:\Python314\pythonw.exe" "%ROOT%scripts\qna_tray.py"
) else (
    start "" "C:\Python314\python.exe" "%ROOT%scripts\qna_tray.py"
)
timeout /t 2 /nobreak >nul

rem ── 4. Browser ─────────────────────────────────────
echo [4/4] Opening Dashboard in browser...
start http://localhost:3000

echo.
echo  ══════════════════════════════════════════════
echo   ALL SERVICES RUNNING
echo   ────────────────────────────────────────────
echo   Backend:    http://localhost:8000/docs
echo   Dashboard:  http://localhost:3000
echo   Logs:       logs\backend.log
echo               logs\dashboard.log
echo   Tray:       System tray icon (bottom right)
echo   ────────────────────────────────────────────
echo   Close this window does NOT stop services.
echo   Use tray ^> Exit, or kill via Task Manager.
echo  ══════════════════════════════════════════════
echo.
pause
