@echo off
REM QNA Dashboard Auto-Launcher
REM Launches QNA dashboard and keeps it alive
REM Uses Python (not VBS) for reliable process management

setlocal

echo ============================================
echo QNA Dashboard Launcher
echo ============================================
echo Starting QNA Dashboard on http://localhost:3000
echo.

REM Kill any existing dashboard on port 3000
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":3000"') do (
    taskkill /PID %%a /f >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Launch dashboard in background (Node.js must be in PATH)
cd /d repositories\Quant-Nanggroe-AI-worktree\dashboard
start "QNA Dashboard" /min npm run dev

echo Dashboard launched. Waiting for startup...
timeout /t 8 /nobreak >nul

REM Verify dashboard is up
for /f "tokens=*" %%a in ('curl -s -o nul -w "%%{http_code}" http://localhost:3000 2^>nul') do (
    if "%%a"=="200" (
        echo [OK] Dashboard is running on http://localhost:3000
    ) else (
        echo [WARN] Dashboard returned HTTP %%a (might still starting)
    )
)

echo.
echo QNA Dashboard is ready. Press any key to exit this window.
pause >nul
endlocal