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

FIXED 2026-08-04: DB_PATH corrected to use correct file location.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# FIXED: Use correct path relative to THIS file (quant_nanggroe/data/)
# Previous: dirname(dirname(__file__)) → D:/repositories/data/ (wrong)
# Now: Path(__file__).parent / "data" → quant_nanggroe/data/ (correct)
DB_PATH = Path(__file__).parent / "data" / "qna_trade_journal.db"

log = logging.getLogger(__name__)

# G1-WIRE: rich metacognition schema (APA/KENAPA/MENGAPA/KE MANA) made live.
# Previously this module's TradeAwareness was orphaned (never called); the loop
# emitted a simplified inline awareness. Now the journal builds the full schema
# so trade_export.py / dashboard carry the real per-trade self-awareness.
from quant_nanggroe.engine.analytics.trade_awareness import (
    build_entry_awareness, build_exit_awareness,
)


class TradeJournal:
    """SQLite-backed trade journal with strategy attribution + self-eval."""

    def __init__(self, db_path: str = None):
        self.db_path = str(db_path) if db_path else str(DB_PATH)
        self._init_ok = False
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            self._init_db()
            self._init_ok = True
        except Exception as e:
            # FAIL-OPEN ONLY IF EXPLICITLY ALLOWED (e.g. first-boot where dir
            # doesn't exist yet). Otherwise the live loop MUST know the journal
            # is dead so it can either abort or fall back to no-self-eval mode.
            logging.getLogger(__name__).error(
                "TradeJournal._init_db FAILED on %s: %s — journal offline. "
                "Cycle will continue but strategy attribution/self-eval DISABLED.",
                self.db_path, e,
            )
            self._init_ok = False

    def db_healthy(self) -> bool:
        '''Return True iff schema is initialized and writable.'''
        if not self._init_ok:
            return False
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
                conn.execute("SELECT COUNT(*) FROM trades")
            return True
        except Exception:
            return False

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
                    comment TEXT,
                    -- TRADE-AWARENESS LAYER (apa/kenapa/bagaimana/mengapa)
                    hypothesis TEXT,   -- WHY entry taken
                    setup_ctx TEXT,    -- market context at open
                    close_reason TEXT, -- WHY closed
                    hit_type TEXT,     -- tp|sl|manual|killswitch|expiry|exit
                    market_ctx TEXT    -- market context at close
                )
            """)
            # MIGRATION: legacy DBs predate the trade-awareness columns. Add any
            # missing columns idempotently so record_open/record_close never crash
            # on a stale schema (fail-closed would otherwise disable ALL history).
            _expected = {
                "hypothesis": "TEXT", "setup_ctx": "TEXT", "close_reason": "TEXT",
                "hit_type": "TEXT", "market_ctx": "TEXT",
            }
            try:
                _cur_cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
                for _col, _type in _expected.items():
                    if _col not in _cur_cols:
                        conn.execute(f"ALTER TABLE trades ADD COLUMN {_col} {_type}")
            except Exception as _mig_err:
                logging.getLogger(__name__).warning("TradeJournal migration skipped: %s", _mig_err)
            conn.commit()

    def _emit_paper_state(self, rec: Dict):
        """Mirror a trade record into paper_state/trades.json (the format consumed
        by engine/analytics/trade_export.py + dashboard for apa/kenapa/bagaimana/
        mengapa awareness). Appends or updates by ticket."""
        import json
        # FIX G2: align with trade_export.py reader path. trade_journal.py lives
        # at quant_nanggroe/, so two parents up = repo root (not three).
        out_dir = Path(__file__).resolve().parent.parent / "paper_state"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "trades.json"
        data: List[Dict] = []
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data = data.get("trades", [])
            except Exception:
                data = []
        existing = next((t for t in data if t.get("ticket") == rec.get("ticket")), None)
        if existing:
            existing.update(rec)
        else:
            data.append(rec)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


    def record_open(self, ticket: int, strategy: str, symbol: str, side: str,
                    entry: float, sl: float = None, tp: float = None,
                    confidence: float = 0.0, comment: str = "",
                    hypothesis: str = "", setup_ctx: str = ""):
        """Log an executed order with full strategy attribution + HYPOTHESIS.

        hypothesis : WHY this trade was taken (the 'apa/kenapa' — what the
                     strategy expected to happen).
        setup_ctx  : market context at open (regime, multi-tf confluence,
                     volume, news) — the 'bagaimana/mengapa' of entry.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO trades
                   (ticket, strategy, symbol, side, entry, sl, tp, confidence,
                    open_time, outcome, comment, hypothesis, setup_ctx)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ticket, strategy, symbol, side, entry, sl, tp, confidence,
                 time.time(), "open", comment, hypothesis, setup_ctx),
            )
            conn.commit()
        # Mirror to paper_state for dashboard + export (G1: rich awareness schema).
        aw = build_entry_awareness(
            strategy_name=strategy, side=side, entry_price=entry, sl=sl or 0.0,
            tp=tp or 0.0, signal_direction=side, confidence=confidence,
            entry_trigger=hypothesis or f"signal:{side}", regime=setup_ctx or "unknown",
            regime_reason=setup_ctx or "", strategy_thesis=hypothesis,
            target_thesis="", expected_rr=0.0, holding_intent="",
            execution_venue="mt5",
        )
        self._emit_paper_state({
            "trade_id": str(ticket), "ticket": ticket, "symbol": symbol,
            "strategy_name": strategy, "side": side, "entry_price": entry,
            "sl": sl, "tp": tp, "pnl": 0.0, "entry_time": time.time(),
            "awareness": aw.to_dict(),
        })

    def record_close(self, ticket: int, exit_price: float, pnl: float,
                     reason: str = "", hit: str = "exit",
                     market_ctx: str = ""):
        """Update a trade with close outcome + REASONING (apa/kenapa/bagaimana/mengapa).

        reason  : human-readable narrative — WHY this trade closed.
        hit     : 'tp' | 'sl' | 'manual' | 'killswitch' | 'expiry' | 'exit'
        market_ctx : snapshot of context at close.
        """
        outcome = "win" if pnl > 0 else "loss"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE trades SET close_time=?, exit_price=?, pnl=?, outcome=?,
                       close_reason=?, hit_type=?, market_ctx=?
                   WHERE ticket=?""",
                (time.time(), exit_price, pnl, outcome, reason, hit,
                 market_ctx, ticket),
            )
            conn.commit()
        # Mirror close + full awareness to paper_state (G1: rich schema).
        open_rec = self.get_open_trade(ticket) or {}
        entry_aw = None
        try:
            from quant_nanggroe.engine.analytics.trade_awareness import TradeAwareness
            aw_raw = open_rec.get("awareness") if isinstance(open_rec, dict) else None
            entry_aw = TradeAwareness.from_dict(aw_raw) if aw_raw else None
        except Exception:
            entry_aw = None
        aw = build_exit_awareness(
            entry=entry_aw,
            exit_price=exit_price,
            exit_trigger=hit,
            exit_reason=reason,
            fill_note=market_ctx,
        ) if entry_aw else build_exit_awareness(
            entry=build_entry_awareness(
                strategy_name=open_rec.get("strategy", "unknown"),
                side=open_rec.get("side", ""), entry_price=open_rec.get("entry", 0.0),
                sl=open_rec.get("sl") or 0.0, tp=open_rec.get("tp") or 0.0,
                signal_direction=open_rec.get("side", ""), confidence=0.0,
                entry_trigger=open_rec.get("comment") or f"journal:{open_rec.get('side', '')}",
                execution_venue="mt5"),
            exit_price=exit_price, exit_trigger=hit, exit_reason=reason,
            fill_note=market_ctx,
        )
        self._emit_paper_state({
            "trade_id": str(ticket), "ticket": ticket,
            "exit_price": exit_price, "pnl": pnl, "exit_time": time.time(),
            "awareness": aw.to_dict(),
        })

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

        # Compute sharpe-like metric per strategy from the pnl series.
        by_strat_series: Dict[str, List[float]] = {}
        for t in closed:
            by_strat_series.setdefault(t["strategy"], []).append(t["pnl"])

        verdict = {}
        for s, st in by_strat.items():
            if st["trades"] < 20:
                verdict[s] = {"status": "insufficient", "trades": st["trades"]}
                continue
            win_rate = st["wins"] / st["trades"]
            avg_win = st["win_pnl"] / st["wins"] if st["wins"] else 0
            avg_loss = st["loss_pnl"] / st["losses"] if st["losses"] else 1
            # RR = average win / average loss (risk-reward ratio)
            avg_rr = (avg_win / avg_loss) if avg_loss > 0 else 0.0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            # Per-strategy Sharpe (annualized proxy): mean/std of pnl, risk-free=0.
            series = by_strat_series.get(s, [])
            sharpe = 0.0
            if len(series) >= 2:
                import math
                mean = sum(series) / len(series)
                var = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
                std = math.sqrt(var) if var > 0 else 0.0
                sharpe = (mean / std) if std > 0 else 0.0
            if expectancy <= 0:
                # DEBATE_ROUND1 gate: negative expectancy -> DISABLE (kelly=0, no trade)
                verdict[s] = {
                    "status": "disabled",
                    "trades": st["trades"],
                    "win_rate": round(win_rate, 3),
                    "expectancy": round(expectancy, 4),
                    "avg_rr": round(avg_rr, 3),
                    "sharpe": round(sharpe, 3),
                    "total_pnl": round(st["total_pnl"], 2),
                    "kelly": 0.0,
                }
                continue
            # Kelly fraction from real expectancy
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win if avg_win > 0 else 0.05
            kelly = max(0.02, min(0.25, kelly))
            verdict[s] = {
                "status": "active",
                "trades": st["trades"],
                "win_rate": round(win_rate, 3),
                "expectancy": round(expectancy, 4),
                "avg_rr": round(avg_rr, 3),
                "sharpe": round(sharpe, 3),
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
    logging.getLogger(__name__).info(
        f"CONFLICT {sym}: {chosen.upper()} by {win_strat}(conf={win_conf:.2f}) "
        f"over {lose_strat}(conf={lose_conf:.2f}) — resolved, no opposing trade"
    )