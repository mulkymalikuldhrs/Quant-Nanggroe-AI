@echo off
REM ===========================================================================
REM QNA Autonomous Trading — Launcher
REM "isi saldo dan mulai autonomous trading"
REM ===========================================================================
title QNA Trading Engine

REM ── SET YOUR CREDENTIALS ────────────────────────────────────────────────
REM Copy this file to start_trading_local.bat (never commit passwords)
if "%VALETAX_PASSWORD%"=="" (
    echo.
    echo ⚠️  VALETAX_PASSWORD not set!
    echo    Edit this file or set the env var before starting.
    echo    Example: set VALETAX_PASSWORD=your_mt5_password
    echo.
)

REM ── MODE: paper = 0, live = 1 ───────────────────────────────────────────
set QNA_LIVE_TRADING=1

REM ── OPTIONAL: bypass auth for local dev ─────────────────────────────────
set QNAI_ALLOW_INSECURE_DEV=true

REM ── START BACKEND ──────────────────────────────────────────────────────
echo.
echo ════════════════════════════════════════════════════════
echo  Starting Quant-Nanggroe AI — Autonomous Trading Engine
echo ════════════════════════════════════════════════════════
echo  Host: http://localhost:8000
echo  Docs: http://localhost:8000/docs
echo  Pipeline: POST /api/autonomous/pipeline/run
echo.

cd /d "%~dp0"
python run_server.py
