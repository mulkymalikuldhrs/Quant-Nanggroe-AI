@echo off
setlocal EnableDelayedExpansion
REM ═══════════════════════════════════════════════════════════════════════
REM  QNA v8.1.1 — Single Complete Launcher (WIB UTC+7)
REM  ONE BAT TO RULE THEM ALL — api/daemon/dashboard/test/status/all
REM ═══════════════════════════════════════════════════════════════════════
REM  Usage:
REM    launch.bat              → All-in-One (backend+dashboard+tray+browser)
REM    launch.bat all          → All-in-One
REM    launch.bat api          → FastAPI :8000 only
REM    launch.bat daemon       → CandleScheduler daemon only
REM    launch.bat dashboard    → Next.js :3000 only
REM    launch.bat test [args]  → pytest
REM    launch.bat status       → Health check
REM    launch.bat weekly-reset → Manual weekly PnL reset (WIB)
REM ═══════════════════════════════════════════════════════════════════════
set "PYTHONPATH="
set "QNA_ROOT=%~dp0"
cd /d "%QNA_ROOT%"
if not exist "%QNA_ROOT%logs" mkdir "%QNA_ROOT%logs" >nul 2>&1
if not exist "%QNA_ROOT%data" mkdir "%QNA_ROOT%data" >nul 2>&1
if not exist "%QNA_ROOT%data\persistence" mkdir "%QNA_ROOT%data\persistence" >nul 2>&1
set "PY=%QNA_ROOT%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=C:\Python314\python.exe"
if not exist "%PY%" set "PY=python"
REM Auto-generate .env if missing (WIB)
if not exist "%QNA_ROOT%.env" (
    echo [SETUP] Generating .env WIB ...
    "%PY%" -c "import secrets,pathlib; k=secrets.token_hex(32); a='qna-'+secrets.token_hex(16); pathlib.Path(r'%QNA_ROOT%.env').write_text(f'QNAI_JWT_SECRET={k}\nQNAI_API_KEY={a}\nQNA_ADMIN_API_KEY={a}\nQNA_LIVE_TRADING=1\nQNA_SCHEDULER_ENABLED=1\nQNA_LOG_LEVEL=INFO\nTZ=Asia/Jakarta\n', encoding='utf-8')" 2>nul
    echo [SETUP] .env created.
)
if "%~1"=="" goto :all
if /I "%~1"=="all" goto :all
if /I "%~1"=="api" goto :api
if /I "%~1"=="daemon" goto :daemon
if /I "%~1"=="dashboard" goto :dashboard
if /I "%~1"=="test" goto :test
if /I "%~1"=="status" goto :status
if /I "%~1"=="weekly-reset" goto :weekly_reset
if /I "%~1"=="logs" goto :logs
if /I "%~1"=="monitor" goto :monitor
if /I "%~1"=="verbose" goto :verbose
goto :usage

:api
echo [QNA] API :8000 ...
start "QNA-API" /B "%PY%" qna.py api
goto :eof

:daemon
echo [QNA] Daemon WIB ...
if /I "%~2"=="--verbose" set "QNA_LOG_LEVEL=DEBUG"
if /I "%~2"=="verbose" set "QNA_LOG_LEVEL=DEBUG"
if /I "%QNA_LOG_LEVEL%"=="DEBUG" (
    echo  Verbose DEBUG mode — realtime color log
    "%PY%" qna.py daemon --log-level DEBUG
) else (
    "%PY%" qna.py daemon
)
goto :eof

:dashboard
echo [QNA] Dashboard :3000 ...
if not exist "%QNA_ROOT%dashboard\node_modules" (
    echo   npm install ...
    pushd "%QNA_ROOT%dashboard"
    call npm install --no-audit --no-fund >> "%QNA_ROOT%logs\npm-install.log" 2>&1
    popd
)
cd /d "%QNA_ROOT%dashboard"
start "QNA-DASHBOARD" /B cmd /c "npm run dev 2>&1"
cd /d "%QNA_ROOT%"
echo Dashboard http://localhost:3000
goto :eof

:test
echo [QNA] Tests ...
if "%~2"=="" (
    "%PY%" -m pytest tests/ -v
) else (
    REM %%* is not updated by SHIFT in cmd.exe, so it previously forwarded the
    REM literal subcommand "test" to pytest. Forward only arguments after it.
    "%PY%" -m pytest %2 %3 %4 %5 %6 %7 %8 %9 -v
)
goto :eof

:status
echo [QNA] Status WIB Asia/Jakarta ...
echo  Python: %PY%
echo  PYTHONPATH: [CLEARED]
echo  Time WIB: %date% %time%
"%PY%" -c "import sys; print(f'  sys.path[0]: {sys.path[0]}'); print(f'  Python: {sys.version}')"
"%PY%" -c "import MetaTrader5 as mt5; mt5.initialize(timeout=5000); i=mt5.account_info(); print(f'  MT5: {i.login if i else \"not connected\"} BAL {i.balance if i else \"-\"} EQ {i.equity if i else \"-\"}'); mt5.shutdown()" 2>nul
if exist "data\weekly_override.json" echo  Weekly override: data\weekly_override.json
if exist "data\persistence\risk_COLON_weekly_pnl.json" type "data\persistence\risk_COLON_weekly_pnl.json"
goto :eof

:weekly_reset
echo [QNA] Weekly reset WIB manual (owner override) ...
"%PY%" -c "import json,pathlib; p=pathlib.Path('data/weekly_override.json'); p.write_text(json.dumps({'weekly_pnl':0.0,'until':'2026-09-01T00:00:00+07:00','reason':'owner override weekly reset via launch.bat weekly-reset','created_at':'2026-08-28T10:30:00+07:00'},indent=2),encoding='utf-8'); print('  weekly_override.json -> 0 until 2026-09-01 WIB')" 2>nul
powershell -Command "Set-Content 'data\persistence\risk_COLON_weekly_pnl.json' '{\"value\": 0.0, \"updated_at\": \"2026-08-28T10:30:00+07:00\"}' -NoNewline; Set-Content 'data\persistence\risk_COLON_daily_pnl.json' '{\"value\": 0.0, \"updated_at\": \"2026-08-28T10:30:00+07:00\"}' -NoNewline; Write-Host '  persistence weekly/daily -> 0 WIB'" 2>nul
echo  Done. Restart daemon: launch.bat daemon
goto :eof

:logs
echo [QNA] Logs WIB realtime ...
echo  Daemon: logs\daemon*.log  Backend: logs\backend.log  Dashboard: logs\dashboard.log
echo  Press Ctrl+C to stop.
powershell -Command "Get-Content 'logs\daemon*.log','logs\backend.log' -Tail 50 -Wait 2>&1 | ForEach-Object { $c='Gray'; if($_ -match 'CRITICAL|BLOCKED|VETOED|KILL'){ $c='Red' } elseif($_ -match 'BUY|SELL'){ $c='Green' } elseif($_ -match 'heartbeat'){ $c='Cyan' } Write-Host $_ -ForegroundColor $c }"
goto :eof

:monitor
echo [QNA] Monitor WIB verbose realtime ...
echo  Daemon + Risk + Signals + MT5
powershell -Command "$host.UI.RawUI.WindowTitle='QNA-Monitor WIB'; Get-Content 'logs\daemon*.log' -Tail 100 -Wait 2>&1 | ForEach-Object { $c='Gray'; if($_ -match 'CRITICAL|BLOCKED|VETOED|KILL|ERROR'){ $c='Red' } elseif($_ -match 'BUY|SELL|signal=buy|signal=sell'){ $c='Green' } elseif($_ -match 'heartbeat|CPCV|Regime'){ $c='Cyan' } elseif($_ -match 'MT5|BAL|weekly_override'){ $c='Yellow' } Write-Host (\"[\" + (Get-Date -Format 'HH:mm:ss WIB') + \"] \" + $_) -ForegroundColor $c }"
goto :eof

:verbose
echo [QNA] Verbose daemon WIB DEBUG ...
set "QNA_LOG_LEVEL=DEBUG"
set "PYTHONPATH="
echo  QNA_LOG_LEVEL=DEBUG  WIB UTC+7
"%PY%" qna.py daemon --log-level DEBUG 2>&1 | powershell -Command "$input | ForEach-Object { $c='Gray'; if($_ -match 'CRITICAL|VETOED|KILL'){ $c='Red' } elseif($_ -match 'BUY|SELL'){ $c='Green' } elseif($_ -match 'heartbeat'){ $c='Cyan' } Write-Host $_ -ForegroundColor $c }"
goto :eof

:all
title QNA v8.1.1 — Autonomous Hedge Fund (WIB)
color 0A
echo.
echo  ╔════════════════════════════════════════════╗
echo  ║   Quant-Nanggroe-AI v8.1.1 WIB            ║
echo  ║   Autonomous Quant Hedge Fund              ║
echo  ║   FX / Commodity MT5  |  WIB UTC+7         ║
echo  ╚════════════════════════════════════════════╝
echo.
echo [1/4] Backend :8000 ...
start "QNA-Backend" /min /D "%QNA_ROOT%" cmd /c "%PY%" qna.py api ^> logs\backend.log 2^>^&1
timeout /t 5 /nobreak >nul
echo      Backend launched.
echo [2/4] Dashboard :3000 ...
if not exist "%QNA_ROOT%dashboard\node_modules" (
    echo      node_modules missing — npm install...
    pushd "%QNA_ROOT%dashboard"
    call npm install --no-audit --no-fund >> "%QNA_ROOT%logs\npm-install.log" 2>&1
    popd
)
start "QNA-Dashboard" /min /D "%QNA_ROOT%dashboard" cmd /c npm run dev ^> ..\logs\dashboard.log 2^>^&1
timeout /t 8 /nobreak >nul
echo      Dashboard launched.
echo [3/4] Tray ...
if exist "%QNA_ROOT%scripts\qna_tray.py" (
    if exist "%QNA_ROOT%.venv\Scripts\pythonw.exe" (
        start "" "%QNA_ROOT%.venv\Scripts\pythonw.exe" "%QNA_ROOT%scripts\qna_tray.py"
    ) else (
        start "" "%QNA_ROOT%.venv\Scripts\python.exe" "%QNA_ROOT%scripts\qna_tray.py"
    )
    timeout /t 2 /nobreak >nul
    echo      Tray launched.
) else (
    echo      Tray skipped (scripts\qna_tray.py not found).
)
echo [4/4] Browser ...
start http://localhost:3000
echo.
echo  ══════════════════════════════════════════════
echo   ALL SERVICES RUNNING (WIB)
echo   Backend:    http://localhost:8000/docs
echo   Dashboard:  http://localhost:3000
echo   Logs:       logs\backend.log / logs\dashboard.log / logs\daemon*.log
echo   Monitor:    launch.bat logs      ^(tail color^)
echo               launch.bat monitor   ^(verbose WIB^)
echo               launch.bat verbose   ^(daemon DEBUG^)
echo   Weekly:     launch.bat weekly-reset  ^(manual WIB^)
echo   Status:     launch.bat status
echo  ══════════════════════════════════════════════
echo.
pause
goto :eof

:usage
echo QNA v8.1.1 — Single Launcher WIB
echo.
echo Usage:
echo   launch.bat              All-in-One
echo   launch.bat all          All-in-One
echo   launch.bat api          FastAPI :8000
echo   launch.bat daemon       Daemon WIB
echo   launch.bat daemon --verbose  Daemon DEBUG verbose
echo   launch.bat dashboard    Next.js :3000
echo   launch.bat test [args]  pytest
echo   launch.bat status       Health check WIB
echo   launch.bat weekly-reset Manual weekly PnL reset WIB
echo   launch.bat logs         Tail logs realtime color
echo   launch.bat monitor      Verbose monitor realtime WIB
echo   launch.bat verbose      Daemon DEBUG verbose foreground
echo.
echo All commands use PYTHONPATH="" ^(no Hermes contamination^) WIB UTC+7
echo Logs: logs\daemon*.log ^| Backend: logs\backend.log ^| Dashboard: logs\dashboard.log
goto :eof
