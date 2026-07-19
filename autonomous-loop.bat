@echo off
title DHAHER AUTONOMOUS ENGINE — DO NOT CLOSE
color 0D
cd /d E:\trading

echo ╔══════════════════════════════════════════════════════╗
echo ║     DHAHER AUTONOMOUS ENGINE — TMUX MODE           ║
echo ║     Self-prompting · Self-healing · Self-evolving   ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: ========== CYCLE 1: INIT ==========
echo [⏳] Phase 1: Initialize MT5 + Dashboard
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe" >NUL
if "%ERRORLEVEL%"=="0" ( echo [✅] MT5 running ) else (
    start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
    timeout /t 15 /nobreak >nul
    echo [✅] MT5 launched
)

:: Start dashboard
start "" /B "C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\uvicorn" dashboard:app --host 127.0.0.1 --port 5050
echo [✅] Dashboard: http://localhost:5050

:: Start market context
start "" /B "C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python" -c "from market_context import update_all; update_all(); print('Context updated')"
echo [✅] Market context loaded

:: ========== INFINITE LOOP ==========
echo.
echo [🔄] Entering autonomous cycle — press Ctrl+C to stop
echo.

:LOOP
echo.
echo ═══ CYCLE $(date) ═══

:: Step 1: Check MT5 connection
echo [1/5] Checking MT5...
"C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python" -c "
import sys; sys.path.insert(0,'E:/trading')
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        a = mt5.account_info()
        print(f'  MT5: {a.name} | Balance: \${a.balance:.0f} | Equity: \${a.equity:.0f}' if a else '  MT5: no account')
        mt5.shutdown()
    else:
        print('  MT5: disconnected')
except Exception as e:
    print(f'  MT5 error: {e}')
"

:: Step 2: Run hedge fund if market open
echo [2/5] Hedge Fund cycle...
"C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\python" -c "
import sys; sys.path.insert(0,'E:/trading')
try:
    from hedge_fund_mtf import run_mtf_cycle
    run_mtf_cycle()
    print('  Hedge fund cycle complete')
except Exception as e:
    print(f'  HF error: {e}')
"

:: Step 3: Sync to QNA
echo [3/5] Syncing to QNA...
xcopy /E /I /Y /Q "E:\trading\strategies\*.py" "D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\strategies\" >nul 2>nul
echo "  QNA strategies synced"

:: Step 4: Update vault
echo [4/5] Vault sync...
start /B /WAIT cmd /c "C:\Users\Hi\AppData\Local\hermes\scripts\vault-sync.bat" >nul 2>nul
echo "  Vault synced"

:: Step 5: Progress report
echo [5/5] Status report...
echo "  Dashboard: http://localhost:5050"
echo "  Next cycle in 10 minutes..."

:: Sleep 10 minutes
timeout /t 600 /nobreak >nul

:: Self-prompt: check if we need to do more
echo [🧠] Self-assessment: anything to optimize?
goto LOOP
