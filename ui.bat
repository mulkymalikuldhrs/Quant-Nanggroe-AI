@echo off
title Dhaher Crypto Trading UI
echo.
echo ===== DHAHER CRYPTO TRADING UI =====
echo.
echo Starting Web UI at: http://localhost:8080
echo Username: dhaher
echo Password: trading2026
echo.
echo Press Ctrl+C to stop
echo ====================================
cd /d E:\trading
start "" http://localhost:8080
cd /d E:\freqtrade
.venv\Scripts\freqtrade webserver --config E:\trading\config\freqtrade.json
pause
