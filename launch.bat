@echo off
REM ============================================================================
REM  Quant-Nanggroe-AI — SINGLE LAUNCHER
REM  Boots backend (FastAPI :8000) + frontend (Next.js :3000) and opens browser.
REM  Usage: double-click launch.bat
REM ============================================================================
setlocal
set "ROOT=D:\repositories\Quant-Nanggroe-AI-worktree"
set "BE_VENV=C:\Users\Hi\.venv-backend"
set "FRONT=%ROOT%\dashboard"
set "PY=%BE_VENV%\Scripts\python.exe"
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
curl -s -o nul http://127.0.0.1:%API_PORT%/health
if %errorlevel%==0 ( goto be_up )
set /a tries+=1
if %tries% geq 40 (
  echo [X] backend did not come up. backend.log:
  type "%BE_LOG%" | tail -15
  goto :fail
) else ( ping -n 2 127.0.0.1 >nul & goto be_wait )
:be_up
echo [+] backend UP

REM ---- 2. FRONTEND ----
echo [^>] starting frontend on :%NODE_PORT% ...
start "QN-WEB" /min "%FE_HELPER%"

echo [..] waiting for frontend...
set "tries=0"
:fe_wait
curl -s -o nul http://127.0.0.1:%NODE_PORT%/
if %errorlevel%==0 ( goto fe_up )
set /a tries+=1
if %tries% geq 60 (
  echo [X] frontend did not come up. frontend.log:
  type "%FE_LOG%" | tail -15
  goto :fail
) else ( ping -n 2 127.0.0.1 >nul & goto fe_wait )
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
ping -n 3 127.0.0.1 >nul
goto waitloop

:fail
echo [X] launcher aborted.
:cleanup
echo [^>] shutting down...
taskkill /FI "WINDOWTITLE eq QN-API*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq QN-WEB*" >nul 2>&1
pause
exit /b 1
