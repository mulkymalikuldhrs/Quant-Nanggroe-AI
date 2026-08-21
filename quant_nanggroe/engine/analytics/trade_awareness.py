"""Trade Awareness — deterministic 'what/why/how/lesson' per closed trade.

GATE-3 (user mandate): QNA must have awareness — what happened, why it
happened, how it happened, what to learn — for every closed trade / SL hit /
TP hit. Pure math/rules (no LLM dependency), part of the evaluate→evolve loop.

Output shape per deal:
    {
      "ticket": ..., "strategy": ..., "symbol": ...,
      "what":  "WIN +40.00 USD on XAUUSD.vx",
      "why":   "TP hit: price reached take-profit target",
      "how":   "Entry 2000 -> Exit 2040 (+2.0%) over 1d 2h",
      "lesson":"Positive expectancy contribution; keep current sizing",
      "severity": "good" | "bad" | "neutral"
    }
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

_JOURNAL_DB_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "quant_nanggroe" / "data" / "qna_trade_journal.db",
    Path(__file__).resolve().parents[3] / "data" / "qna_trade_journal.db",
]

_HIT_WHYS = {
    "tp": ("TP hit", "price reached the take-profit target"),
    "sl": ("SL hit", "price reached the protective stop-loss"),
    "trail": ("Trailing stop hit",
              "price retraced past the trailed stop after profit run-up"),
    "be": ("Breakeven exit", "stop had been ratcheted to entry; scratch trade"),
    "manual": ("Manual close", "operator intervened"),
    "time": ("Time stop", "position exceeded its maximum holding window"),
}


def explain_deal(
    ticket: str,
    strategy: str,
    symbol: str,
    side: str,
    entry: Optional[float],
    exit_price: Optional[float],
    pnl: float,
    close_reason: str = "",
    hit_type: str = "",
    holding_hours: Optional[float] = None,
) -> dict:
    key = (hit_type or close_reason or "").strip().lower()
    short = next((v for k, v in _HIT_WHYS.items() if k in key), None)
    if short is None:
        if pnl > 0:
            short = ("Closed profitable", "exit rule or end-of-window close in profit")
        elif pnl < 0:
            short = ("Closed at loss", "exit rule triggered while position was adverse")
        else:
            short = ("Scratch close", "flat exit, no material P&L")

    title, why = short
    pct = ""
    if entry and exit_price and entry != 0:
        move = (exit_price - entry) / entry * (1 if side.lower().startswith("b") else -1)
        pct = f" ({move:+.2%})"
    hold = ""
    if holding_hours is not None:
        hold = f" over {holding_hours:.0f}h"
    what = f"{'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'FLAT')} {pnl:+.2f} USD on {symbol}"
    how = f"Entry {entry} -> Exit {exit_price}{pct}{hold}"

    severity = "good" if pnl > 0 else ("bad" if pnl < 0 else "neutral")
    if severity == "good":
        lesson = ("Positive expectancy contribution; keep strategy active at "
                  "current sizing tier")
        if "sl" in key and pnl > 0:
            lesson = "Profitable despite SL-tag — verify hit_type labeling integrity"
    elif "sl" in key or "trail" in key:
        lesson = ("Loss protected by risk framework; check whether entry timing "
                  "or ATR stop distance needs widening")
    elif "tp" in key and pnl < 0:
        lesson = "TP-tagged but negative PnL — data anomaly, investigate journaling"
    else:
        lesson = "Negative expectancy contribution; lifecycle will tune or kill"

    return {
        "ticket": ticket, "strategy": strategy, "symbol": symbol,
        "what": what, "why": f"{title}: {why}", "how": how,
        "lesson": lesson, "severity": severity,
    }


def explain_journal(date_from: Optional[str] = None,
                    date_to: Optional[str] = None,
                    strategy: Optional[str] = None,
                    limit: int = 500) -> List[dict]:
    """Generate awareness narratives for closed trades in the journal."""
    db = next((p for p in _JOURNAL_DB_CANDIDATES if p.exists()), None)
    if db is None:
        return []
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        sql = "SELECT * FROM trades WHERE close_time IS NOT NULL AND close_time != ''"
        params: list = []
        if date_from:
            sql += " AND date(close_time) >= date(?)"
            params.append(date_from)
        if date_to:
            sql += " AND date(close_time) <= date(?)"
            params.append(date_to)
        if strategy:
            sql += " AND strategy = ?"
            params.append(strategy)
        sql += " ORDER BY close_time DESC LIMIT ?"
        params.append(limit)
        out = []
        for r in con.execute(sql, params):
            d = dict(r)
            out.append(explain_deal(
                ticket=d.get("ticket"), strategy=d.get("strategy") or "",
                symbol=d.get("symbol") or "", side=d.get("side") or "",
                entry=d.get("entry"), exit_price=d.get("exit_price"),
                pnl=float(d.get("pnl") or 0),
                close_reason=d.get("close_reason") or "",
                hit_type=d.get("hit_type") or "",
                holding_hours=None,
            ))
        return out
    finally:
        con.close()
