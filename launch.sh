#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  QNA v8.1.1 — Single Complete Launcher (Linux/macOS)
#  Mirror of launch.bat — WIB UTC+7, PYTHONPATH cleared (no Hermes leak)
#  Usage:
#    ./launch.sh              → All-in-One (backend+daemon+dashboard)
#    ./launch.sh all          → All-in-One
#    ./launch.sh api          → FastAPI :8000 only
#    ./launch.sh daemon       → CandleScheduler daemon only
#    ./launch.sh dashboard    → Next.js :3000 only
#    ./launch.sh test [args]  → pytest
#    ./launch.sh status       → Health check
#    ./launch.sh weekly-reset → Manual weekly PnL reset (WIB)
# ═══════════════════════════════════════════════════════════════════════
set -u

export PYTHONPATH=""
export TZ="Asia/Jakarta"
QNA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$QNA_ROOT" || exit 1

mkdir -p logs data data/persistence

PY="${QNA_ROOT}/.venv/bin/python"
if [ ! -x "$PY" ]; then PY="$(command -v python3 || command -v python)"; fi

# Auto-generate .env if missing (WIB)
if [ ! -f "${QNA_ROOT}/.env" ]; then
  echo "[SETUP] Generating .env (WIB) ..."
  "$PY" - <<'PYEOF'
import secrets, pathlib
k = secrets.token_hex(32)
a = 'qna-' + secrets.token_hex(16)
pathlib.Path('.env').write_text(
    f'QNAI_JWT_SECRET={k}\nQNAI_API_KEY={a}\nQNA_ADMIN_API_KEY={a}\n'
    f'QNA_LIVE_TRADING=1\nQNA_SCHEDULER_ENABLED=1\nQNA_LOG_LEVEL=INFO\nTZ=Asia/Jakarta\n',
    encoding='utf-8')
PYEOF
  echo "[SETUP] .env created."
fi

CMD="${1:-all}"
case "$CMD" in
  api)
    echo "[QNA] API :8000 ..."
    "$PY" qna.py api
    ;;
  daemon)
    echo "[QNA] Daemon WIB ..."
    if [ "${2:-}" = "--verbose" ] || [ "${2:-}" = "verbose" ]; then
      export QNA_LOG_LEVEL=DEBUG
      "$PY" qna.py daemon --log-level DEBUG
    else
      "$PY" qna.py daemon
    fi
    ;;
  dashboard)
    echo "[QNA] Dashboard :3000 ..."
    [ -d dashboard/node_modules ] || (cd dashboard && npm install --no-audit --no-fund)
    (cd dashboard && npm run dev)
    ;;
  test)
    shift
    echo "[QNA] Tests ..."
    "$PY" -m pytest "$@" -v
    ;;
  status)
    echo "[QNA] Status WIB Asia/Jakarta ..."
    echo "  Python: $PY"
    echo "  PYTHONPATH: [CLEARED]"
    date
    "$PY" -c "import MetaTrader5 as mt5; mt5.initialize(timeout=5000); i=mt5.account_info(); print(f'  MT5: {i.login if i else \"not connected\"} BAL {i.balance if i else \"-\"} EQ {i.equity if i else \"-\"}'); mt5.shutdown()" 2>/dev/null
    [ -f data/weekly_override.json ] && echo "  Weekly override: data/weekly_override.json"
    [ -f data/persistence/risk_COLON_weekly_pnl.json ] && cat data/persistence/risk_COLON_weekly_pnl.json
    ;;
  weekly-reset)
    echo "[QNA] Weekly reset WIB manual (owner override) ..."
    "$PY" - <<'PYEOF'
import json, pathlib
p = pathlib.Path('data/weekly_override.json')
p.write_text(json.dumps({
    'weekly_pnl': 0.0, 'until': '2026-09-01T00:00:00+07:00',
    'reason': 'owner override weekly reset via launch.sh weekly-reset',
    'created_at': '2026-08-28T10:30:00+07:00'}, indent=2), encoding='utf-8')
print('  weekly_override.json -> 0 until 2026-09-01 WIB')
PYEOF
    printf '{"value": 0.0, "updated_at": "2026-08-28T10:30:00+07:00"}' > data/persistence/risk_COLON_weekly_pnl.json
    printf '{"value": 0.0, "updated_at": "2026-08-28T10:30:00+07:00"}' > data/persistence/risk_COLON_daily_pnl.json
    echo "  persistence weekly/daily -> 0 WIB"
    ;;
  all)
    echo "╔════════════════════════════════════════════╗"
    echo "║   Quant-Nanggroe-AI v8.1.1 WIB            ║"
    echo "║   Autonomous Quant Hedge Fund              ║"
    echo "╚════════════════════════════════════════════╝"
    echo "[1/4] Backend :8000 ..."
    nohup "$PY" qna.py api > logs/backend.log 2>&1 &
    sleep 5
    echo "[2/4] Dashboard :3000 ..."
    [ -d dashboard/node_modules ] || (cd dashboard && npm install --no-audit --no-fund)
    nohup bash -c 'cd dashboard && npm run dev' > logs/dashboard.log 2>&1 &
    sleep 8
    echo "[3/4] Daemon WIB ..."
    nohup "$PY" qna.py daemon > logs/daemon.log 2>&1 &
    echo "[4/4] Done. Backend http://localhost:8000/docs  Dashboard http://localhost:3000"
    echo "  Logs: logs/backend.log | logs/dashboard.log | logs/daemon.log"
    echo "  Status: ./launch.sh status   Weekly: ./launch.sh weekly-reset"
    ;;
  *)
    echo "QNA v8.1.1 — Single Launcher WIB"
    echo "Usage:"
    echo "  ./launch.sh              All-in-One"
    echo "  ./launch.sh api          FastAPI :8000"
    echo "  ./launch.sh daemon       Daemon WIB"
    echo "  ./launch.sh dashboard    Next.js :3000"
    echo "  ./launch.sh test [args]  pytest"
    echo "  ./launch.sh status       Health check WIB"
    echo "  ./launch.sh weekly-reset Manual weekly PnL reset WIB"
    echo "All commands use PYTHONPATH='' (no Hermes contamination) WIB UTC+7"
    ;;
esac
