#!/usr/bin/env bash
# QNA Heartbeat — cron-friendly health check (every 5 minutes)
# If engine dies, restart it automatically

QNA_DIR="/sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree"
ENGINE="$QNA_DIR/quant_nanggroe/live_engine.py"
PID_FILE="$QNA_DIR/data/qna.pid"
LOG="$QNA_DIR/logs/heartbeat.log"
DATA_DIR="$QNA_DIR/data"

mkdir -p "$QNA_DIR/logs" "$DATA_DIR"
export PYTHONPATH="$QNA_DIR:$PYTHONPATH"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] QNA heartbeat check..." >> "$LOG"

# Check if engine is alive
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE" 2>/dev/null)
  if kill -0 "$PID" 2>/dev/null; then
    echo "  Alive (PID: $PID)" >> "$LOG"
    exit 0
  fi
fi

# Engine is dead — restart
echo "  Engine down. Restarting..." >> "$LOG"
rm -f "$PID_FILE"
cd "$QNA_DIR" && nohup python3 -c "
import sys; sys.path.insert(0, '$QNA_DIR')
from quant_nanggroe.live_engine import LiveEngine
LiveEngine().start()
" > "$QNA_DIR/logs/live-engine.log" 2>&1 &
echo "  Restarted at $(date)" >> "$LOG"
echo "[$(date)] 🔄 QNA auto-restarted" >> "$QNA_DIR/logs/live-engine.log"