@echo off
setlocal
cd /d "%~dp0.."

set "PORT_DASH=8080"

where python >nul 2>&1
if errorlevel 1 echo Python not found in PATH. & pause & exit /b 1

echo [QNAv4] Seeding state files...
python scripts\seed_paper_state.py >nul 2>&1

echo [QNAv4] Starting paper daemon...
powershell -WindowStyle Hidden -Command "Start-Process python -ArgumentList 'scripts\qna-paper-daemon.py', '--interval', '3600' -WindowStyle Hidden"

echo [QNAv4] Creating desktop shortcut...
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Quant Nanggroe AI.lnk'); $s.TargetPath='%~dp0launch_qna.bat'; $s.WorkingDirectory='%~dp0..'; $s.Save()" >nul

echo [QNAv4] Starting Dashboard...
powershell -WindowStyle Hidden -Command "Start-Process python -ArgumentList 'scripts\dashboard_server.py' -WindowStyle Hidden"

echo [QNAv4] Opening browser...
timeout /t 3 /nobreak >nul
start "" "http://localhost:%PORT_DASH%"

echo [QNAv4] Launcher done.
timeout /t 2 /nobreak >nul
exit 0
