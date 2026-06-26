#!/usr/bin/env bash
# qna-paper.sh — Start paper trading daemon
set -e

DAEMON="scripts/qna-paper-daemon.py"
PAPER_DIR="paper_state"
PID_FILE="$PAPER_DIR/daemon.pid"
LOG_FILE="$PAPER_DIR/daemon.log"
# ponytail: hardcoded defaults, argparse handles dedup of later --interval wins
DEFAULT_ARGS="--live-data --interval 3600"

FOREGROUND=false
ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--foreground" ]; then
        FOREGROUND=true
    else
        ARGS+=("$arg")
    fi
done

mkdir -p "$PAPER_DIR"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Daemon already running (PID: $OLD_PID)."
        exit 1
    fi
    # ponytail: stale PID cleanup, no extra validation
    rm -f "$PID_FILE"
fi

if [ "$FOREGROUND" = true ]; then
    exec python3 "$DAEMON" $DEFAULT_ARGS "${ARGS[@]}"
fi

nohup python3 "$DAEMON" $DEFAULT_ARGS "${ARGS[@]}" > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"
echo "Daemon started (PID: $PID). Log: $LOG_FILE"
