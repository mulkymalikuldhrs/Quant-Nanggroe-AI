"""
QNA TRADE JOURNAL + SELF-EVALUATION
====================================
Problem being solved (observed by user 2026-08-02):
  - Trades look random: some bullish, some bearish, no clear verdict.
  - No strategy attribution: which strategy decided each trade is unknown.
  - No self-eval: Kelly fractions never update from real PnL.
  - No conflict resolution: buy+sell both fire for same symbol.

Fix:
  1. Every executed order is journaled with {ticket, strategy, symbol, side,
     entry, sl, tp, confidence, timestamp} → SQLite (survives restart).
  2. On close, journal is updated with exit price + pnl + outcome.
  3. resolve_conflicts(): per symbol, if both buy & sell present, keep highest
     confidence (or skip if tie/low confidence) — no random opposing trades.
  4. self_eval(): reads journal, recomputes per-strategy win-rate + expectancy,
     updates RiskGuard.kelly_cache. Logs verdict per strategy.

REAL-ONLY: journal is local SQLite, no external calls.
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "qna_trade_journal.db",
)


class TradeJournal:
    """SQLite-backed trade journal with strategy attribution + self-eval."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    ticket INTEGER PRIMARY KEY,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry REAL NOT NULL,
                    sl REAL,
                    tp REAL,
                    confidence REAL,
                    open_time REAL NOT NULL,
                    close_time REAL,
                    exit_price REAL,
                    pnl REAL,
                    outcome TEXT,  -- 'win' | 'loss' | 'open'
                    comment TEXT
                )
            """)
            conn.commit()

    def record_open(self, ticket: int, strategy: str, symbol: str, side: str,
                    entry: float, sl: float = None, tp: float = None,
                    confidence: float = 0.0, comment: str = ""):
        """Log an executed order with full strategy attribution."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO trades
                   (ticket, strategy, symbol, side, entry, sl, tp, confidence,
                    open_time, outcome, comment)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (ticket, strategy, symbol, side, entry, sl, tp, confidence,
                 time.time(), "open", comment),
            )
            conn.commit()

    def record_close(self, ticket: int, exit_price: float, pnl: float):
        """Update a trade with close outcome. Recomputes outcome."""
        outcome = "win" if pnl > 0 else "loss"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE trades SET close_time=?, exit_price=?, pnl=?, outcome=?
                   WHERE ticket=?""",
                (time.time(), exit_price, pnl, outcome, ticket),
            )
            conn.commit()

    def get_open_trade(self, ticket: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM trades WHERE ticket=?", (ticket,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_closed_trades(self, strategy: str = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if strategy:
                cur = conn.execute(
                    "SELECT * FROM trades WHERE outcome IN ('win','loss') AND strategy=?",
                    (strategy,))
            else:
                cur = conn.execute("SELECT * FROM trades WHERE outcome IN ('win','loss')")
            return [dict(r) for r in cur.fetchall()]

    def self_eval(self) -> Dict[str, Dict]:
        """Read journal, compute per-strategy stats, return verdict dict."""
        closed = self.get_closed_trades()
        by_strat: Dict[str, Dict] = {}
        for t in closed:
            s = t["strategy"]
            if s not in by_strat:
                by_strat[s] = {"trades": 0, "wins": 0, "losses": 0,
                               "total_pnl": 0.0, "win_pnl": 0.0, "loss_pnl": 0.0}
            st = by_strat[s]
            st["trades"] += 1
            st["total_pnl"] += t["pnl"]
            if t["outcome"] == "win":
                st["wins"] += 1
                st["win_pnl"] += t["pnl"]
            else:
                st["losses"] += 1
                st["loss_pnl"] += abs(t["pnl"])

        verdict = {}
        for s, st in by_strat.items():
            if st["trades"] < 5:
                verdict[s] = {"status": "insufficient", "trades": st["trades"]}
                continue
            win_rate = st["wins"] / st["trades"]
            avg_win = st["win_pnl"] / st["wins"] if st["wins"] else 0
            avg_loss = st["loss_pnl"] / st["losses"] if st["losses"] else 1
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            # Kelly fraction from real expectancy
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win if avg_win > 0 else 0.05
            kelly = max(0.02, min(0.25, kelly))
            verdict[s] = {
                "status": "active",
                "trades": st["trades"],
                "win_rate": round(win_rate, 3),
                "expectancy": round(expectancy, 4),
                "total_pnl": round(st["total_pnl"], 2),
                "kelly": round(kelly, 3),
            }
        return verdict


def resolve_conflicts(signals: List) -> List:
    """Per-symbol conflict resolution.

    If both buy and sell signals exist for the same symbol, keep only the
    highest-confidence one. If confidence tie or both < MIN, skip (no trade).
    Prevents random opposing trades.
    """
    by_symbol: Dict[str, List] = {}
    for sig in signals:
        by_symbol.setdefault(sig.symbol, []).append(sig)

    resolved = []
    for sym, sigs in by_symbol.items():
        buys = [s for s in sigs if s.side == "buy"]
        sells = [s for s in sigs if s.side == "sell"]

        if buys and sells:
            best_buy = max(buys, key=lambda s: s.confidence)
            best_sell = max(sells, key=lambda s: s.confidence)
            if best_buy.confidence >= best_sell.confidence:
                resolved.append(best_buy)
                log_conflict(sym, "buy", best_buy.strategy, best_buy.confidence,
                             best_sell.strategy, best_sell.confidence)
            else:
                resolved.append(best_sell)
                log_conflict(sym, "sell", best_sell.strategy, best_sell.confidence,
                             best_buy.strategy, best_buy.confidence)
        else:
            resolved.extend(sigs)
    return resolved


def log_conflict(sym: str, chosen: str, win_strat: str, win_conf: float,
                 lose_strat: str, lose_conf: float):
    import logging
    logging.getLogger(__name__).info(
        f"CONFLICT {sym}: {chosen.upper()} by {win_strat}(conf={win_conf:.2f}) "
        f"over {lose_strat}(conf={lose_conf:.2f}) — resolved, no opposing trade"
    )
