@echo off
REM qna.bat — PYTHONPATH-clean launcher for Quant Nanggroe AI
REM Fixes Hermes venv leakage into .venv
SETLOCAL
SET "PYTHONPATH="
SET "FRED_API_KEY=%FRED_API_KEY%"
SET "QNAI_FRED_API_KEY=%FRED_API_KEY%"
"%~dp0.venv\Scripts\python.exe" "%~dp0qna.py" %*
ENDLOCAL
