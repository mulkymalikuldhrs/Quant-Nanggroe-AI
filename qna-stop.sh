#!/usr/bin/env bash
# qna-stop.sh — Graceful stop of paper trading daemon
set -e

PID_FILE="paper_state/daemon.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Daemon may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Stale PID $PID — cleaning up."
    rm -f "$PID_FILE"
    exit 0
fi

echo "Stopping daemon (PID: $PID)..."
kill -TERM "$PID"

# ponytail: simple 10s loop, no exponential backoff
for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        rm -f "$PID_FILE"
        echo "Daemon stopped."
        exit 0
    fi
    sleep 1
done

echo "Daemon did not stop after 10s — sending SIGKILL."
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "Daemon stopped."
