#!/usr/bin/env bash
# Quant Nanggroe — Live Trading Activation
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
QNA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGINE="$QNA_DIR/quant_nanggroe/live_engine.py"
LOG_DIR="$QNA_DIR/logs"
DATA_DIR="$QNA_DIR/data"

mkdir -p "$LOG_DIR" "$DATA_DIR"
unset PYTHONPATH

echo "═══ QUANT NANGGROE — ACTIVATION ═══"
echo ""

echo "[1/3] Testing exchange connection..."
cd "$QNA_DIR"
python3 -c "
from quant_nanggroe.live_engine import BinanceConnector
c = BinanceConnector()
t = c.get_ticker()
print(f'  BTC: \${float(t[\"lastPrice\"]):,.2f}')
print(f'  ✅ Exchange connected')
"

echo ""
echo "[2/3] Starting live engine..."
cd "$QNA_DIR"
nohup python3 -c "
import sys
sys.path.insert(0, '$QNA_DIR')
from quant_nanggroe.live_engine import LiveEngine
LiveEngine().start()
" > "$LOG_DIR/live-engine.log" 2>&1 &
ENGINE_PID=$!
echo "  ✅ Engine started (PID: $ENGINE_PID)"
sleep 2

echo ""
echo "[3/3] Verification..."
cd "$QNA_DIR" && python3 -c "
import sys; sys.path.insert(0, '$QNA_DIR')
from quant_nanggroe.live_engine import LiveEngine
LiveEngine().status()
"

echo ""
echo "═══ QNA ACTIVATED ═══"
echo "  PID: $ENGINE_PID"
echo "  Logs: $LOG_DIR/live-engine.log"
echo "  Dashboard: cd $QNA_DIR && python3 -c 'import sys; sys.path.insert(0, \".\"); from quant_nanggroe.live_engine import LiveEngine; import json; print(json.dumps(LiveEngine().dashboard(), indent=2))'"