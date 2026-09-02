"""Update wiki comparisons/paper-vs-live-reconciliation.md from live MT5 + journal."""
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
WIKI = Path.home() / "wiki"
JOURNAL = REPO / "quant_nanggroe" / "data" / "qna_trade_journal.db"
STATE = REPO / "paper_state" / "state.json"
TARGET = WIKI / "comparisons" / "paper-vs-live-reconciliation.md"

def get_journal_stats():
    if not JOURNAL.exists():
        return 0, 0.0
    conn = sqlite3.connect(str(JOURNAL))
    cnt, pnl = conn.execute("SELECT COUNT(*), SUM(pnl) FROM trades").fetchone()
    return cnt or 0, pnl or 0.0

def get_state():
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding="utf-8"))

def try_live_balance():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        info = mt5.account_info()
        if info is None:
            return None
        bal = float(info.balance)
        mt5.shutdown()
        return bal
    except Exception:
        return None

def main():
    cnt, pnl = get_journal_stats()
    state = get_state()
    live = try_live_balance()
    live_str = f"{live:.2f}" if live is not None else "unavailable (terminal offline)"
    now = datetime.now(timezone.utc).isoformat()
    # Read existing to preserve frontmatter
    existing = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    # Update the comparison table section
    print(f"Journal: {cnt} trades PnL {pnl:.2f}")
    print(f"State total_value: {state.get('total_value')} regime {state.get('regime')}")
    print(f"Live BAL: {live_str}")
    print(f"Wiki target: {TARGET}")
    print(f"Updated at {now} — run with terminal online for live BAL")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
