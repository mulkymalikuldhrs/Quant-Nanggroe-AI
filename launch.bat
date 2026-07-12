@echo off
REM ============================================================================
REM  Quant-Nanggroe-AI — SINGLE LAUNCHER
REM  Boots backend (FastAPI :8000) + frontend (Next.js :3000) and opens browser.
REM  Usage: double-click launch.bat  (or: launch.bat)
REM ============================================================================
setlocal
set "ROOT=D:\repositories\Quant-Nanggroe-AI-worktree"
set "BE_VENV=C:\Users\Hi\.venv-backend"
set "FRONT=%ROOT%\dashboard"
set "PY=%BE_VENV%\Scripts\python.exe"
set "NODE_PORT=3000"
set "API_PORT=8000"

REM ---- sanity ----
if not exist "%PY%" ( echo [!] backend venv missing: %BE_VENV% && echo     run: python -m venv %BE_VENV% ^& pip install -e %ROOT% && pause & exit /b 1 )
if not exist "%FRONT%\node_modules" ( echo [!] dashboard node_modules missing. Run in dashboard: npm install && pause & exit /b 1 )

REM ---- 1. BACKEND ----
echo [>] starting backend on :%API_PORT% ...
start "QN-API" /min "%PY%" -m uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port %API_PORT%
set "BE_PID="

echo [..] waiting for backend health...
set "tries=0"
:be_wait
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:%API_PORT%/health >nul 2>&1
if %errorlevel%==0 ( goto be_up )
set /a tries+=1
if %tries% geq 40 ( echo [X] backend did not come up && goto :fail ) else ( timeout /t 1 >nul & goto be_wait )
:be_up
echo [+] backend UP

REM ---- 2. FRONTEND ----
echo [>] starting frontend on :%NODE_PORT% ...
pushd "%FRONT%"
if not exist ".next" ( echo [..] no build cache, running dev server && start "QN-WEB" /min cmd /c "npx next dev -p %NODE_PORT%" ) else ( start "QN-WEB" /min cmd /c "npx next start -p %NODE_PORT%" )
popd

echo [..] waiting for frontend...
set "tries=0"
:fe_wait
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:%NODE_PORT%/ >nul 2>&1
if %errorlevel%==0 ( goto fe_up )
set /a tries+=1
if %tries% geq 40 ( echo [X] frontend did not come up && goto :fail ) else ( timeout /t 1 >nul & goto fe_wait )
:fe_up
echo [+] frontend UP

REM ---- 3. OPEN BROWSER ----
echo [>] opening browser -> http://localhost:%NODE_PORT%/
start "" "http://localhost:%NODE_PORT%/"
echo.
echo [OK] Quant-Nanggroe-AI running.  Close this window or press Ctrl+C to stop all.
echo      backend : http://localhost:%API_PORT%/docs
echo      frontend: http://localhost:%NODE_PORT%/
echo.

:waitloop
timeout /t 2 >nul
goto waitloop

:fail
echo [X] launcher aborted.
:cleanup
echo [>] shutting down...
taskkill /FI "WINDOWTITLE eq QN-API*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq QN-WEB*" >nul 2>&1
pause
exit /b 1
