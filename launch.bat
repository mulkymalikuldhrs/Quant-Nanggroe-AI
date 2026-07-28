@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM Quant Nanggroe AI — Clean Launcher
REM ═══════════════════════════════════════════════════════════════════════
REM
REM CRITICAL: PYTHONPATH must be EMPTY to avoid Hermes venv contamination.
REM Hermes venv has pydantic-core compiled for Python 3.11 ABI.
REM Our project .venv has Python 3.11. Running in Hermes context causes:
REM   ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
REM
REM Single entry point: PYTHONPATH="" + project .venv
REM ═══════════════════════════════════════════════════════════════════════

setlocal
set PYTHONPATH=
set QNA_ROOT=%~dp0
cd /d "%QNA_ROOT%"

if "%1"=="" goto :usage
if "%1"=="api" goto :api
if "%1"=="cli" goto :cli
if "%1"=="daemon" goto :daemon
if "%1"=="test" goto :test
if "%1"=="status" goto :status
goto :usage

:api
echo [QNA] Starting API server via qna.py (single entry point)...
echo [QNA] PYTHONPATH cleared — no venv contamination.
".venv\Scripts\python.exe" qna.py api
goto :eof

:cli
echo [QNA] Starting CLI shell...
".venv\Scripts\python.exe" qna.py cli
goto :eof

:daemon
echo [QNA] Starting background daemon...
".venv\Scripts\python.exe" qna.py daemon
goto :eof

:test
shift
echo [QNA] Running tests...
if "%1"=="" (
    ".venv\Scripts\python.exe" -m pytest tests/ -v
) else (
    ".venv\Scripts\python.exe" -m pytest %* -v
)
goto :eof

:status
echo [QNA] System check...
echo.
echo  Python:     ".venv\Scripts\python.exe"
echo  PYTHONPATH: [CLEARED]
echo.
".venv\Scripts\python.exe" -c "import sys; print(f'  sys.path[0]: {sys.path[0]}'); print(f'  Python: {sys.version}')"
echo.
echo  To start API:  launch.bat api
echo  To run CLI:    launch.bat cli
echo  To run tests:  launch.bat test [optional test path]
goto :eof

:usage
echo Quant Nanggroe AI — Clean Launcher
echo.
echo Usage:
echo   launch.bat api        Start API server (FastAPI, port 8000)
echo   launch.bat cli        Interactive CLI shell
echo   launch.bat daemon     Background agent daemon
echo   launch.bat test       Run test suite
echo   launch.bat status     System health check
echo.
echo All commands run with PYTHONPATH=="" (no venv contamination)
goto :eof
