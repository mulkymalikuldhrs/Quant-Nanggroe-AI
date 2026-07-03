#!/usr/bin/env bash
set -e

# Quant-Nanggroe-AI One-Command Launcher
# Starts: API server + Dashboard

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$WORKSPACE/logs"
mkdir -p "$LOG_DIR"

echo "═══ Quant-Nanggroe-AI Launcher ═══"

# Start API
echo "Starting API server on port 8000..."
cd "$WORKSPACE"
nohup python3 -m uvicorn quant_nanggroe.api.app:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
echo $! > /tmp/qna-api.pid

# Wait for API
sleep 2
curl -s http://localhost:8000/health && echo " API OK" || echo " API starting..."

# Start Dashboard
echo "Starting Dashboard on port 3000..."
cd "$WORKSPACE/dashboard"
nohup npm run dev > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > /tmp/qna-dashboard.pid

echo "═══ All services launched ═══"
echo "API: http://localhost:8000"
echo "Dashboard: http://localhost:3000"