#!/usr/bin/env bash
# qna-status.sh — Show daemon status + latest P&L
set -e

PAPER_DIR="paper_state"
PID_FILE="$PAPER_DIR/daemon.pid"
PNL_FILE="$PAPER_DIR/pnl.csv"
STATE_FILE="$PAPER_DIR/state.json"

DAEMON_RUNNING=false
DAEMON_PID=""

if [ -f "$PID_FILE" ]; then
    DAEMON_PID=$(cat "$PID_FILE")
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        DAEMON_RUNNING=true
        echo "Daemon RUNNING (PID: $DAEMON_PID)"
    else
        echo "Daemon NOT running (stale PID $DAEMON_PID)"
    fi
else
    echo "Daemon NOT running"
fi
echo ""

# P&L summary
if [ -f "$PNL_FILE" ]; then
    LINE_COUNT=$(wc -l < "$PNL_FILE")
    if [ "$LINE_COUNT" -gt 1 ]; then
        LAST_LINE=$(tail -1 "$PNL_FILE")
        TOTAL_CYCLES=$(echo "$LAST_LINE" | cut -d, -f2)
        CURRENT_PNL=$(echo "$LAST_LINE" | cut -d, -f8)
        LATEST_DD=$(echo "$LAST_LINE" | cut -d, -f10)

        echo "=== Trading Summary ==="
        echo "  Total cycles:  $TOTAL_CYCLES"
        echo "  Current P&L:   $CURRENT_PNL"
        echo "  Latest drawdown: $LATEST_DD%"
        echo ""

        echo "=== Last 5 Cycles ==="
        echo "    Cycle | Signals | Cash     | Total Val | Unrealized | Realized  | Total PnL | Pos | Drawdown%"
        echo "    ------|---------|----------|-----------|------------|-----------|-----------|-----|----------"
        tail -5 "$PNL_FILE" | while IFS=',' read -r _ cycle sig cash tv upnl rpnl tpnl pos dd; do
            if [ "$cycle" != "cycle" ]; then
                printf "    %-5s | %-7s | %-8s | %-9s | %-10s | %-9s | %-9s | %-3s | %s\n" \
                    "$cycle" "$sig" "$cash" "$tv" "$upnl" "$rpnl" "$tpnl" "$pos" "$dd"
            fi
        done
    else
        echo "P&L file has header only — no trading data yet."
    fi
else
    echo "No P&L data yet (missing $PNL_FILE)."
fi
echo ""

# State summary
if [ -f "$STATE_FILE" ]; then
    echo "=== State ==="
    python3 -c "
import json
s = json.load(open('$STATE_FILE'))
print(f'  Capital:     {s.get(\"initial_capital\", \"N/A\")}')
print(f'  Peak:        {s.get(\"peak_capital\", \"N/A\")}')
print(f'  Cycle count: {s.get(\"cycle_count\", \"N/A\")}')
print(f'  Total P&L:   {s.get(\"total_pnl\", \"N/A\")}')
"
else
    echo "No state data yet (missing $STATE_FILE)."
fi
echo ""

# KillSwitch check
# ponytail: inline python, error handled with ||
echo "=== KillSwitch ==="
python3 -c "
import sys
sys.path.insert(0, '.')
from quant_nanggroe.engine.risk.kill_switch import KillSwitch
ks = KillSwitch()
print('  KillSwitch:', 'ACTIVE' if not ks.can_trade() else 'OK')
" 2>/dev/null || echo "  KillSwitch: could not import (package not installed?)"
