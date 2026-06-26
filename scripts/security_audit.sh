#!/usr/bin/env bash
set -uo pipefail

PYTHON=""
for candidate in python3 python python3.12; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[SECURITY AUDIT] ERROR: No Python interpreter found (tried python3, python, python3.12)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUDIT_SCRIPT="$SCRIPT_DIR/security_audit.py"

if [ ! -f "$AUDIT_SCRIPT" ]; then
    echo "[SECURITY AUDIT] ERROR: $AUDIT_SCRIPT not found"
    exit 1
fi

OUTPUT=$("$PYTHON" "$AUDIT_SCRIPT" "$@" 2>&1)
EXIT_CODE=$?
echo "$OUTPUT"

SCORE_LINE=$(echo "$OUTPUT" | grep -o 'Score: [0-9]*/100 ([A-Z]*)\?' | tail -1)
if [ -n "$SCORE_LINE" ]; then
    echo "[SECURITY AUDIT] $SCORE_LINE"
fi

exit $EXIT_CODE
