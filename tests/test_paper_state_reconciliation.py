"""Paper state vs journal reconciliation — drift guard."""

import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOURNAL = PROJECT_ROOT / "quant_nanggroe" / "data" / "qna_trade_journal.db"
STATE = PROJECT_ROOT / "paper_state" / "state.json"
TRADES = PROJECT_ROOT / "paper_state" / "trades.json"

def test_state_total_value_matches_journal():
    """state.json total_value must equal sum(pnl) in journal db within $1."""
    assert JOURNAL.exists(), f"journal db missing: {JOURNAL}"
    assert STATE.exists(), f"state.json missing: {STATE}"
    conn = sqlite3.connect(str(JOURNAL))
    cur = conn.execute("SELECT SUM(pnl) FROM trades")
    journal_pnl = cur.fetchone()[0] or 0.0
    state = json.loads(STATE.read_text(encoding="utf-8"))
    total = state.get("total_value", 0)
    # journal stores cumulative pnl, state stores same as total_value per audit rebuild
    diff = abs(total - journal_pnl)
    assert diff < 1.0, f"DRIFT: state total_value {total} vs journal sum {journal_pnl} diff {diff} >= 1.0"

def test_trades_json_count_matches_journal():
    """trades.json length must match journal row count."""
    assert JOURNAL.exists()
    assert TRADES.exists()
    conn = sqlite3.connect(str(JOURNAL))
    cnt = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    trades = json.loads(TRADES.read_text(encoding="utf-8"))
    # trades.json is list
    assert isinstance(trades, list), "trades.json not a list"
    assert len(trades) == cnt, f"trades.json {len(trades)} vs journal {cnt}"

def test_state_not_unknown_when_regime_wired(tmp_path):
    """After regime fix, write_state should map unknown to ranging via stub."""
    from quant_nanggroe.engine.state_writer import PaperStateWriter
    w = PaperStateWriter(state_dir=tmp_path)
    w.write_state({"total_value": 100, "regime": "unknown"})
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data.get("regime") != "unknown", f"regime still unknown after stub: {data}"
