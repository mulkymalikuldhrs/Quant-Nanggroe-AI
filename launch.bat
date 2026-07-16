@echo off
REM ============================================================================
REM  Quant-Nanggroe-AI — SINGLE LAUNCHER (fixed for Windows cmd.exe)
REM  Boots backend (FastAPI :8000) + frontend (Next.js :3000) and opens browser.
REM  Usage: double-click launch.bat
REM  FIX: health-check via powershell (no curl|tail bash-ism); PYTHONPATH=""
REM ============================================================================
setlocal EnableExtensions
set "ROOT=D:\repositories\Quant-Nanggroe-AI-worktree"
set "BE_VENV=%ROOT%\.venv"
if not exist "%BE_VENV%\Scripts\python.exe" set "BE_VENV=C:\Users\Hi\.venv-backend"
set "PY=%BE_VENV%\Scripts\python.exe"
set "FRONT=%ROOT%\dashboard"
set "NODE_PORT=3000"
set "API_PORT=8000"
set "BE_LOG=%ROOT%\backend.log"
set "FE_LOG=%ROOT%\frontend.log"
set "BE_HELPER=%TEMP%\qn_backend.bat"
set "FE_HELPER=%TEMP%\qn_frontend.bat"

cd /d "%ROOT%"

REM ---- sanity ----
if not exist "%PY%" (
  echo [!] backend venv missing: %BE_VENV%
  echo     run: python -m venv %BE_VENV% ^& %BE_VENV%\Scripts\pip install -e %ROOT%
  pause & exit /b 1
)
if not exist "%FRONT%\node_modules" (
  echo [!] dashboard node_modules missing. Run in dashboard: npm install
  pause & exit /b 1
)

REM ---- helpers (avoid nested-quote pain in start) ----
echo @echo off > "%BE_HELPER%"
echo set "PYTHONPATH=" >> "%BE_HELPER%"
echo cd /d "%ROOT%" >> "%BE_HELPER%"
echo "%PY%" -m uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port %API_PORT% ^> "%BE_LOG%" 2^>^&1 >> "%BE_HELPER%"

echo @echo off > "%FE_HELPER%"
echo set "PYTHONPATH=" >> "%FE_HELPER%"
echo cd /d "%FRONT%" >> "%FE_HELPER%"
if not exist "%FRONT%\.next" (
  echo npx next dev -p %NODE_PORT% ^> "%FE_LOG%" 2^>^&1 >> "%FE_HELPER%"
) else (
  echo npx next start -p %NODE_PORT% ^> "%FE_LOG%" 2^>^&1 >> "%FE_HELPER%"
)

REM ---- 1. BACKEND ----
echo [^>] starting backend on :%API_PORT% ...
start "QN-API" /min "%BE_HELPER%"

echo [..] waiting for backend health...
set "tries=0"
:be_wait
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:%API_PORT%/health' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { 0 }" | findstr /r "^200$" >nul && goto be_up
set /a tries+=1
if %tries% geq 40 (
  echo [X] backend did not come up. backend.log (last 15 lines):
  powershell -NoProfile -Command "Get-Content '%BE_LOG%' -Tail 15 -ErrorAction SilentlyContinue"
  goto :fail
) else ( timeout /t 2 >nul & goto be_wait )
:be_up
echo [+] backend UP

REM ---- 2. FRONTEND ----
echo [^>] starting frontend on :%NODE_PORT% ...
start "QN-WEB" /min "%FE_HELPER%"

echo [..] waiting for frontend...
set "tries=0"
:fe_wait
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:%NODE_PORT%/' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { 0 }" | findstr /r "^200$" >nul && goto fe_up
set /a tries+=1
if %tries% geq 60 (
  echo [X] frontend did not come up. frontend.log (last 15 lines):
  powershell -NoProfile -Command "Get-Content '%FE_LOG%' -Tail 15 -ErrorAction SilentlyContinue"
  goto :fail
) else ( timeout /t 2 >nul & goto fe_wait )
:fe_up
echo [+] frontend UP

REM ---- 3. OPEN BROWSER ----
echo [^>] opening browser -^> http://localhost:%NODE_PORT%/
start "" "http://localhost:%NODE_PORT%/"
echo.
echo [OK] Quant-Nanggroe-AI running. Close this window to stop all.
echo      backend : http://localhost:%API_PORT%/docs
echo      frontend: http://localhost:%NODE_PORT%/

:waitloop
timeout /t 3 >nul
goto waitloop

:fail
echo [X] launcher aborted.
:cleanup
echo [^>] shutting down...
taskkill /FI "WINDOWTITLE eq QN-API*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq QN-WEB*" >nul 2>&1
pause
exit /b 1
