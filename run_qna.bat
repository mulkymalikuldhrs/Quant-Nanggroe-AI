@echo off
REM QNA Launcher — cleans PYTHONPATH pollution (Hermes agent venv leak) and uses local .venv
setlocal
REM Strip Hermes-contaminated PYTHONPATH so .venv resolves its OWN deps
set "PYTHONPATH="
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [QNA] ERROR: .venv not found. Run setup first.
    exit /b 1
)
".venv\Scripts\python.exe" qna.py %*
endlocal
