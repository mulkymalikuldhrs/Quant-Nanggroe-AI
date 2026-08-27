"""Strategy Evaluator — Rolling backtest + live signal tracking + auto-disable."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger("QNA.StrategyEvaluator")

_JOURNAL = Path(__file__).resolve().parents[3] / "data" / "qna_trade_journal.db"
_EVAL_DB = Path(__file__).resolve().parents[3] / "data" / "strategy_eval.db"

MIN_SHARPE = 0.5
MIN_WIN_RATE = 0.35
MIN_TRADES = 5
REVIEW_WINDOW_DAYS = 30


@dataclass
class StrategyStats:
    strategy: str
    symbol: str = ""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    sharpe: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    enabled: bool = True
    disable_reason: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy, "symbol": self.symbol,
            "total_trades": self.total_trades, "wins": self.wins,
            "losses": self.losses, "win_rate": self.win_rate,
            "sharpe": self.sharpe, "profit_factor": self.profit_factor,
            "avg_win": self.avg_win, "avg_loss": self.avg_loss,
            "expectancy": self.expectancy, "enabled": self.enabled,
            "disable_reason": self.disable_reason,
            "last_updated": self.last_updated,
        }


class StrategyEvaluator:
    """Tracks per-strategy performance and auto-disables bad performers."""

    def __init__(self, journal_db: Path | None = None, eval_db: Path | None = None):
        self._journal = journal_db or _JOURNAL
        self._eval_db = eval_db or _EVAL_DB
        self._init_eval_db()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(str(self._eval_db), timeout=5)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_eval_db(self) -> None:
        with self._conn() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS strategy_stats (
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL DEFAULT '',
                    total_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    sharpe REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    expectancy REAL DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    disable_reason TEXT DEFAULT '',
                    last_updated TEXT,
                    PRIMARY KEY (strategy, symbol)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS signal_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    ticket INTEGER,
                    entry_price REAL,
                    exit_price REAL DEFAULT 0,
                    pnl REAL DEFAULT 0,
                    outcome TEXT DEFAULT 'open',
                    opened_at TEXT,
                    closed_at TEXT,
                    auto_disabled INTEGER DEFAULT 0
                )
            """)

    def record_signal(self, strategy: str, symbol: str, ticket: int,
                      entry_price: float, opened_at: str | None = None) -> None:
        try:
            with self._conn() as con:
                con.execute(
                    """INSERT INTO signal_outcomes
                       (strategy, symbol, ticket, entry_price, opened_at)
                       VALUES (?,?,?,?,?)""",
                    (strategy, symbol, ticket, entry_price,
                     opened_at or datetime.now(timezone.utc).isoformat()))
        except Exception as exc:
            logger.warning("record_signal failed: %s", exc)

    def record_outcome(self, ticket: int, exit_price: float, pnl: float) -> None:
        try:
            with self._conn() as con:
                outcome = "win" if pnl > 0 else ("loss" if pnl < 0 else "breakeven")
                con.execute(
                    """UPDATE signal_outcomes SET exit_price=?, pnl=?, outcome=?,
                       closed_at=? WHERE ticket=?""",
                    (exit_price, pnl, outcome,
                     datetime.now(timezone.utc).isoformat(), ticket))
        except Exception as exc:
            logger.warning("record_outcome failed: %s", exc)

    def compute_stats(self, strategy: str, symbol: str = "",
                      window_days: int = REVIEW_WINDOW_DAYS) -> StrategyStats:
        stats = StrategyStats(strategy=strategy, symbol=symbol)
        try:
            with self._conn() as con:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
                if symbol:
                    rows = con.execute(
                        """SELECT pnl, outcome FROM signal_outcomes
                           WHERE strategy=? AND symbol=? AND closed_at IS NOT NULL
                             AND closed_at >= ?
                           ORDER BY closed_at""",
                        (strategy, symbol, cutoff)).fetchall()
                else:
                    rows = con.execute(
                        """SELECT pnl, outcome FROM signal_outcomes
                           WHERE strategy=? AND closed_at IS NOT NULL
                             AND closed_at >= ?
                           ORDER BY closed_at""",
                        (strategy, cutoff)).fetchall()

                if not rows:
                    return stats

                pnls = [r[0] for r in rows]
                stats.total_trades = len(pnls)
                stats.wins = sum(1 for p in pnls if p > 0)
                stats.losses = sum(1 for p in pnls if p < 0)
                stats.win_rate = stats.wins / stats.total_trades if stats.total_trades > 0 else 0

                if len(pnls) > 1:
                    mean_ret = np.mean(pnls)
                    std_ret = np.std(pnls, ddof=1)
                    if std_ret > 0:
                        stats.sharpe = mean_ret / std_ret * np.sqrt(252)

                gross_profit = sum(p for p in pnls if p > 0)
                gross_loss = abs(sum(p for p in pnls if p < 0))
                stats.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

                avg_win = np.mean([p for p in pnls if p > 0]) if stats.wins > 0 else 0
                avg_loss = np.mean([p for p in pnls if p < 0]) if stats.losses > 0 else 0
                stats.avg_win = avg_win
                stats.avg_loss = avg_loss
                stats.expectancy = (stats.win_rate * avg_win + (1 - stats.win_rate) * avg_loss)

                if stats.total_trades >= MIN_TRADES:
                    if stats.sharpe < MIN_SHARPE:
                        stats.enabled = False
                        stats.disable_reason = f"Sharpe {stats.sharpe:.2f} < {MIN_SHARPE}"
                    elif stats.win_rate < MIN_WIN_RATE:
                        stats.enabled = False
                        stats.disable_reason = f"Win rate {stats.win_rate:.1%} < {MIN_WIN_RATE:.0%}"

                stats.last_updated = datetime.now(timezone.utc).isoformat()

                con.execute(
                    """INSERT OR REPLACE INTO strategy_stats
                       (strategy, symbol, total_trades, wins, losses, win_rate,
                        sharpe, profit_factor, avg_win, avg_loss, expectancy,
                        enabled, disable_reason, last_updated)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stats.strategy, stats.symbol, stats.total_trades,
                     stats.wins, stats.losses, stats.win_rate, stats.sharpe,
                     stats.profit_factor, stats.avg_win, stats.avg_loss,
                     stats.expectancy, int(stats.enabled), stats.disable_reason,
                     stats.last_updated))

        except Exception as exc:
            logger.warning("compute_stats failed for %s: %s", strategy, exc)

        return stats

    def is_strategy_enabled(self, strategy: str, symbol: str = "") -> bool:
        try:
            with self._conn() as con:
                row = con.execute(
                    "SELECT enabled FROM strategy_stats WHERE strategy=? AND symbol=?",
                    (strategy, symbol)).fetchone()
                if row:
                    return bool(row[0])
        except Exception:
            pass
        return True

    def get_all_stats(self, window_days: int = REVIEW_WINDOW_DAYS) -> list[dict]:
        try:
            with self._conn() as con:
                strategies = con.execute(
                    "SELECT DISTINCT strategy FROM signal_outcomes").fetchall()
                return [self.compute_stats(s[0], window_days=window_days).to_dict()
                        for s in strategies]
        except Exception:
            return []

    def review_all(self) -> list[dict]:
        report = []
        try:
            with self._conn() as con:
                strategies = con.execute(
                    "SELECT DISTINCT strategy FROM signal_outcomes").fetchall()

            for (strategy,) in strategies:
                stats = self.compute_stats(strategy)
                report.append(stats.to_dict())
                if not stats.enabled:
                    logger.warning(
                        "AUTO-DISABLED %s: %s (trades=%d, sharpe=%.2f, win_rate=%.1f%%)",
                        strategy, stats.disable_reason,
                        stats.total_trades, stats.sharpe, stats.win_rate * 100)

        except Exception as exc:
            logger.warning("review_all failed: %s", exc)

        return report
