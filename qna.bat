@echo off
REM qna.bat — PYTHONPATH-clean launcher for Quant Nanggroe AI
REM Fixes Hermes venv leakage into .venv
SETLOCAL
SET "PYTHONPATH="
"%~dp0.venv\Scripts\python.exe" "%~dp0qna.py" %*
ENDLOCAL
