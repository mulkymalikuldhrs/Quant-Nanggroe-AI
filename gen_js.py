import pathlib

PART1 = '''"""MT5 -> Journal Sync - closes the feedback loop."""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("QNA.JournalSync")
_JOURNAL_DB = Path(__file__).resolve().parents[1] / "data" / "qna_trade_journal.db"
_LAST_SYNC_KEY = "last_sync_ts"
_DEAL_TYPE_BUY = 0
_DEAL_ENTRY_IN = 0
_DEAL_ENTRY_OUT = 1

_MAGIC_MAP = {888888: "ensemble"}
_KNOWN = [
    "aroon", "smc", "ensemble", "amdx", "kaufman", "mean_rev",
    "multi_timeframe", "trend_follow", "momentum", "scalp",
    "day", "swing", "trailing_stop", "ict", "algebra",
]


def _get_db() -> Path:
    p = Path(__file__).resolve().parents[1] / "data" / "qna_trade_journal.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _ensure_schema(db_path):
    con = sqlite3.connect(str(db_path))
    con.execute(
        "CREATE TABLE IF NOT EXISTS _sync_meta"
        " (key TEXT PRIMARY KEY, value TEXT)")
    con.commit()
    con.close()


def _read_last_sync(con):
    try:
        r = con.execute(
            "SELECT value FROM _sync_meta WHERE key=?",
            (_LAST_SYNC_KEY,)).fetchone()
        return float(r[0]) if r else 0.0
    except Exception:
        return 0.0


def _write_last_sync(con, ts):
    con.execute(
        "INSERT OR REPLACE INTO _sync_meta VALUES (?,?)",
        (_LAST_SYNC_KEY, str(ts)))
    con.commit()


def _classify_outcome(pnl):
    if pnl > 0:
        return "win"
    if pnl < 0:
        return "loss"
    return "breakeven"


def _detect_hit_type(close_reason, pnl):
    cr = close_reason.lower()
    if "take_profit" in cr or "[tp]" in cr:
        return "tp"
    if "stop_loss" in cr or "[sl]" in cr:
        return "sl"
    if "trailing" in cr:
        return "trail"
    if pnl > 0:
        return "tp"
    if pnl < 0:
        return "sl"
    return "unknown"


def _attribute_strategy(magic, comment, symbol):
    if magic in _MAGIC_MAP:
        return _MAGIC_MAP[magic]
    if comment and len(comment) > 2:
        c = comment.strip().lower()
        for k in _KNOWN:
            if k in c:
                return k
    try:
        from quant_nanggroe.engine.strategy_allocation import (
            admitted_for_symbol,
        )
        admitted = admitted_for_symbol(symbol)
        if admitted and len(admitted) == 1:
            return admitted[0]
    except Exception:
        pass
    return "unknown"

'''

js = pathlib.Path(__file__).resolve().parents[0] / ".." / ".." / "quant_nanggroe" / "engine" / "journal_sync.py"
js = js.resolve()
old = js.read_text(encoding="utf-8", errors="ignore") if js.exists() else ""
lines = old.splitlines()
start = next((i for i, l in enumerate(lines) if "def sync_mt5_deals" in l), None)
if start is None:
    print("ERROR: sync_mt5_deals not found in existing file")
else:
    body = "\n".join(lines[start:])
    full = PART1 + "\n\n" + body + "\n"
    js.write_text(full, encoding="utf-8")
    print(f"written: {len(full.splitlines())} lines to {js}")
