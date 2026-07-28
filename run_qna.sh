#!/usr/bin/env bash
# run_qna.sh — clean launcher that neutralizes PYTHONPATH pollution
# (Hermes agent venv leaks PYTHONPATH globally; QNA .venv must resolve its own deps)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
# Strip contaminated PYTHONPATH
unset PYTHONPATH
if [ ! -x ".venv/bin/python" ]; then
    if [ -x ".venv/Scripts/python.exe" ]; then
        PY=".venv/Scripts/python.exe"
    else
        echo "[QNA] ERROR: .venv not found. Run setup first."
        exit 1
    fi
else
    PY=".venv/bin/python"
fi
exec "$PY" qna.py "$@"
