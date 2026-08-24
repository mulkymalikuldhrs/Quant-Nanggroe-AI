#!/bin/bash
# ══════════════════════════════════════════════════════
#  QNA v8.0 All-in-One Launcher (Linux/Mac)
# ══════════════════════════════════════════════════════

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH=""

echo ""
echo "  ╔════════════════════════════════════════════╗"
echo "  ║   Quant-Nanggroe-AI v8.0.2                 ║"
echo "  ║   Autonomous Quant Hedge Fund              ║"
echo "  ╚════════════════════════════════════════════╝"
echo ""

cleanup() {
    echo -e "\n[SHUTDOWN] Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "[1/3] Starting FastAPI backend (port 8000)..."
mkdir -p logs
python "$ROOT/qna.py" api > "$ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!

echo "[2/3] Starting Dashboard (port 3000)..."
cd "$ROOT/dashboard"
npm run dev -- --port 3000 &
DASHBOARD_PID=$!
cd "$ROOT"

sleep 8
echo "[3/3] Opening Dashboard in browser..."
if command -v xdg-open &>/dev/null; then xdg-open http://localhost:3000
elif command -v open &>/dev/null; then open http://localhost:3000; fi

echo ""
echo "  ══════════════════════════════════════════════"
echo "   ALL SERVICES RUNNING (PID: backend=$BACKEND_PID dash=$DASHBOARD_PID)"
echo "   Dashboard: http://localhost:3000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Press Ctrl+C to stop all."
echo "  ══════════════════════════════════════════════"
echo ""

wait
