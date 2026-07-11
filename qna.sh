#!/usr/bin/env bash
# =============================================================================
# QNA Portable Launcher — Auto-detect OS, paths, Python; start/stop/status
# Works on: Linux, macOS, Windows (Git Bash/WSL), Termux/Android
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# ── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── Auto-detect OS ─────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
IS_TERMUX=false
IS_WSL=false

if echo "$HOME" | grep -qi "termux" || [ -n "${TERMUX_VERSION:-}" ]; then
    IS_TERMUX=true
fi
if uname -r | grep -qi "microsoft\|wsl"; then
    IS_WSL=true
fi

# ── Auto-detect Python ────────────────────────────────────────────────────
PYTHON=""
for p in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$p" &>/dev/null; then
        PY_VER=$("$p" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        MAJOR=${PY_VER%.*}
        MINOR=${PY_VER#*.}
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON="$p"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.10+ not found. Install Python 3.10 or later."
fi

info "Platform: $OS / $ARCH"
info "Python: $PYTHON ($PY_VER)"
if $IS_TERMUX; then info "Environment: Termux/Android"; fi
if $IS_WSL; then info "Environment: WSL"; fi

# ── PID file ───────────────────────────────────────────────────────────────
PID_FILE="$PROJECT_ROOT/data/engine.pid"
mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"

# ── Commands ───────────────────────────────────────────────────────────────
cmd="${1:-status}"

case "$cmd" in
    start)
        if [ -f "$PID_FILE" ]; then
            OLD_PID=$(cat "$PID_FILE")
            if kill -0 "$OLD_PID" 2>/dev/null; then
                fail "Engine already running (PID $OLD_PID). Use '$0 stop' first."
            fi
            rm -f "$PID_FILE"
        fi

        info "Starting QNA engine..."

        # Detach properly for each platform
        if $IS_TERMUX; then
            # Termux: nohup works, Android doesn't kill bg on TTY detach
            nohup "$PYTHON" -m quant_nanggroe.live_engine start \
                > "$PROJECT_ROOT/logs/engine.log" 2>&1 &
            ENGINE_PID=$!
        elif [ "$OS" = "Darwin" ]; then
            # macOS: use nohup + disown
            nohup "$PYTHON" -m quant_nanggroe.live_engine start \
                > "$PROJECT_ROOT/logs/engine.log" 2>&1 &
            ENGINE_PID=$!
            disown "$ENGINE_PID" 2>/dev/null || true
        elif [ "$OS" = "Linux" ] && command -v setsid &>/dev/null; then
            # Linux: setsid creates new session (survives TTY detach)
            setsid "$PYTHON" -m quant_nanggroe.live_engine start \
                > "$PROJECT_ROOT/logs/engine.log" 2>&1 &
            ENGINE_PID=$!
        else
            # Windows / fallback: nohup
            nohup "$PYTHON" -m quant_nanggroe.live_engine start \
                > "$PROJECT_ROOT/logs/engine.log" 2>&1 &
            ENGINE_PID=$!
        fi

        echo "$ENGINE_PID" > "$PID_FILE"
        success "Engine started (PID $ENGINE_PID)"
        echo ""
        echo "  Logs:    tail -f $PROJECT_ROOT/logs/engine.log"
        echo "  Status:  $0 status"
        echo "  Stop:    $0 stop"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            warn "No PID file found. Engine may not be running."
            # Try to find and kill
            PID=$(pgrep -f "quant_nanggroe.live_engine" 2>/dev/null || true)
            if [ -n "$PID" ]; then
                kill "$PID" 2>/dev/null && success "Engine stopped (PID $PID)" || warn "Could not stop PID $PID"
            fi
            exit 0
        fi
        ENGINE_PID=$(cat "$PID_FILE")
        if kill -0 "$ENGINE_PID" 2>/dev/null; then
            kill "$ENGINE_PID" 2>/dev/null
            sleep 2
            if kill -0 "$ENGINE_PID" 2>/dev/null; then
                kill -9 "$ENGINE_PID" 2>/dev/null || true
            fi
            success "Engine stopped (PID $ENGINE_PID)"
        else
            warn "Engine not running (PID $ENGINE_PID)"
        fi
        rm -f "$PID_FILE"
        ;;

    status)
        ENGINE_PID=""
        if [ -f "$PID_FILE" ]; then
            ENGINE_PID=$(cat "$PID_FILE")
        fi
        if [ -n "$ENGINE_PID" ] && kill -0 "$ENGINE_PID" 2>/dev/null; then
            UPTIME=$(ps -o etime= -p "$ENGINE_PID" 2>/dev/null | xargs || echo "?")
            LOG_LINES=$(wc -l < "$PROJECT_ROOT/logs/engine.log" 2>/dev/null || echo 0)
            success "Engine RUNNING (PID $ENGINE_PID, up $UPTIME, $LOG_LINES log lines)"
        else
            # Fallback: check pgrep
            FALLBACK_PID=$(pgrep -f "quant_nanggroe.live_engine" 2>/dev/null | head -1 || true)
            if [ -n "$FALLBACK_PID" ]; then
                warn "Engine running without PID file (PID $FALLBACK_PID)"
                echo "$FALLBACK_PID" > "$PID_FILE"
            else
                warn "Engine NOT running"
            fi
        fi

        # Show dashboard if engine is running
        if [ -n "$ENGINE_PID" ] && kill -0 "$ENGINE_PID" 2>/dev/null; then
            echo ""
            info "Quick dashboard:"
            "$PYTHON" -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
try:
    from quant_nanggroe.live_engine import LiveEngine
    eng = LiveEngine()
    d = eng.dashboard()
    print(f'  Balance: \${d.get(\"balance\",0):.2f}')
    print(f'  Cycles: {d.get(\"cycle_count\",0)}')
    print(f'  Positions: {len(d.get(\"open_positions\",[]))}')
    print(f'  Sharpe: {d.get(\"sharpe_ratio\",0):.2f}')
    print(f'  Drawdown: {d.get(\"drawdown\",\"0%\")}')
except Exception as e:
    print(f'  Dashboard error: {e}')
" 2>/dev/null || warn "Dashboard unavailable"
        fi
        ;;

    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;

    health)
        "$PYTHON" -m quant_nanggroe.live_engine health
        ;;

    dashboard)
        "$PYTHON" -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
from quant_nanggroe.live_engine import LiveEngine
import json
eng = LiveEngine()
print(json.dumps(eng.dashboard(), indent=2))
" 2>/dev/null || fail "Dashboard failed (engine not running?)"
        ;;

    backtest)
        shift
        DAYS="${1:-30}"
        MAX="${2:-200}"
        info "Running backtest (${DAYS}d, max ${MAX} variants)..."
        "$PYTHON" -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
import json, time
from pathlib import Path
from quant_nanggroe.backtest.strategy_factory import StrategyFactory
from quant_nanggroe.backtest.backtester import Backtester

factory = StrategyFactory()
all_variants = factory.generate(max_variants=$MAX)
backtester = Backtester()
CACHE = Path('$PROJECT_ROOT') / 'data' / 'hist_cache'
all_results = {}

for coin_id in ['bitcoin', 'ethereum', 'solana', 'binancecoin', 'avalanche-2']:
    cf = CACHE / f'{coin_id}_365d.json'
    if not cf.exists(): continue
    candles = json.loads(cf.read_text())
    results = backtester.run_batch(all_variants, candles, max_strategies=$MAX)
    filtered = backtester.rank(results, min_sharpe=0.3, max_dd=0.50, min_trades=5, top_n=10)
    all_results[coin_id] = {'tested': len(results), 'passed': len(filtered), 'strategies': [r.to_dict() for r in filtered]}

output = {'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'coins': all_results, 'total_variants': len(all_variants)}
Path('$PROJECT_ROOT/data/backtest_results.json').write_text(json.dumps(output, indent=2))

all_s = []
for c,d in all_results.items():
    for r in d['strategies']:
        r['coin_id'] = c; all_s.append(r)
all_s.sort(key=lambda r: r.get('sharpe',0), reverse=True)
Path('$PROJECT_ROOT/data/deployed_strategies.json').write_text(json.dumps({'timestamp':output['timestamp'],'strategies':all_s[:50]}, indent=2))
print(f'Done: {len(all_results)} coins, {sum(d[\"tested\"] for d in all_results.values())} tested, {sum(d[\"passed\"] for d in all_results.values())} passed')
" 2>/dev/null || fail "Backtest failed"
        ;;

    setup)
        info "Running WARP setup..."
        bash "$PROJECT_ROOT/scripts/setup_warp.sh" 2>/dev/null || warn "WARP setup skipped"
        info "Creating data directories..."
        mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"
        info "Copying .env.example if needed..."
        if [ ! -f "$PROJECT_ROOT/.env" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            success "Created .env — edit with your API keys"
        fi
        success "Setup complete"
        ;;

    *)
        echo ""
        echo -e "${CYAN}QNA Portable Launcher${NC}"
        echo ""
        echo "  Usage: $0 <command>"
        echo ""
        echo "  Commands:"
        echo "    start          Start engine (daemon mode)"
        echo "    stop           Stop engine"
        echo "    status         Check engine status"
        echo "    health         Run readiness checks"
        echo "    restart        Restart engine"
        echo "    dashboard      Show full dashboard JSON"
        echo "    backtest [d] [n]  Run backtest (days, max variants)"
        echo "    setup          First-time setup (WARP + dirs)"
        echo ""
        echo "  Examples:"
        echo "    $0 start"
        echo "    $0 backtest 365 500"
        echo "    $0 dashboard"
        echo ""
        ;;
esac
