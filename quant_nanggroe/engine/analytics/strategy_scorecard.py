"""Strategy Scorecard — compute REAL per-strategy metrics from synced journal.

Reads from qna_trade_journal.db (populated by journal_sync from MT5),
computes expectancy / profit_factor / Sharpe / WR / max_drawdown /
t-statistic per strategy, and produces a KEEP/TUNE/KILL verdict.

This is the bridge between raw MT5 deals and the self-evolve loop.
Without this, lifecycle decisions are blind.

Usage:
    from quant_nanggroe.engine.analytics.strategy_scorecard import (
        compute_all_strategies,
    )
    scores = compute_all_strategies()
"""
from __future__ import annotations

import logging
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_JOURNAL_DB = Path(__file__).resolve().parents[2] / "data" / "qna_trade_journal.db"


def _read_trades(db_path: Path = None) -> List[Dict]:
    db = db_path or _JOURNAL_DB
    if not db.exists():
        return []
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """SELECT strategy, symbol, pnl, outcome,
               open_time, close_time, exit_price, entry,
               sl, tp, confidence, hit_type
               FROM trades
               WHERE close_time IS NOT NULL AND pnl IS NOT NULL AND pnl != 0.0"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def _sharpe(returns: List[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    # annualize assuming ~252 trading days, ~1 trade/day avg
    return round(mean / std * math.sqrt(min(len(returns), 252)), 4)


def _t_statistic(values: List[float]) -> float:
    n = len(values)
    if n < 3:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return round(mean / (std / math.sqrt(n)), 4)


def _max_drawdown(pnl_series: List[float]) -> float:
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnl_series:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd and peak > 0:
            max_dd = dd
    return round(max_dd / max(abs(peak), 1), 4) if peak > 0 else 0.0


def compute_scorecard(strategy: str, trades: List[Dict]) -> Dict[str, Any]:
    """Compute full scorecard for one strategy from its closed trades."""
    pnls = [float(t["pnl"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    n = len(trades)
    total_pnl = round(sum(pnls), 2)
    win_rate = round(len(wins) / n, 4) if n else 0.0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0.0
    avg_loss = round(abs(sum(losses) / len(losses)), 2) if losses else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else (
        999.0 if gross_profit > 0 else 0.0)

    expectancy = round(
        win_rate * avg_win - (1 - win_rate) * avg_loss, 4
    ) if n else 0.0

    sharpe = _sharpe(pnls)
    max_dd = _max_drawdown(pnls)
    t_stat = _t_statistic(pnls)
    kelly = round(win_rate - (1 - win_rate) / max(profit_factor, 0.01), 4) if profit_factor > 0 else 0.0

    # R-multiple (reward:risk) — derived from each trade's real sl/entry/exit.
    # Direction is inferred from the sign of (exit - entry); risk is |entry - sl|.
    rrs = []
    for t in trades:
        try:
            sl = float(t.get("sl") or 0)
            entry = float(t.get("entry") or 0)
            exit_px = float(t.get("exit_price") or 0)
        except (TypeError, ValueError):
            continue
        if sl > 0 and entry > 0:
            risk = abs(entry - sl)
            if risk > 0:
                rrs.append(abs(exit_px - entry) / risk)
    avg_rr = round(sum(rrs) / len(rrs), 3) if rrs else 0.0

    # Verdict — institutional criteria
    if n < 10:
        verdict = "INSUFFICIENT_DATA"
    elif (expectancy > 0 and profit_factor > 1.3 and sharpe > 0.3
          and win_rate > 0.35 and max_dd < 0.15):
        verdict = "PROVEN_GOOD"
    elif expectancy > 0:
        verdict = "MARGINAL_POSITIVE"
    elif expectancy < 0 and n >= 20:
        verdict = "NEGATIVE_EDGE"
    else:
        verdict = "NEUTRAL"

    return {
        "strategy": strategy,
        "n_trades": n,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_rr": avg_rr,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "t_statistic": t_stat,
        "kelly_fraction": kelly,
        "statistically_significant": abs(t_stat) > 2.0 and n >= 20,
        "verdict": verdict,
    }


def compute_all_strategies() -> Dict[str, Any]:
    """Compute scorecards for ALL strategies in the journal."""
    trades = _read_trades()
    by_strategy: Dict[str, List[Dict]] = {}
    for t in trades:
        s = t.get("strategy", "unknown")
        by_strategy.setdefault(s, []).append(t)

    results: Dict[str, Any] = {}
    for strat, trades_list in sorted(by_strategy.items()):
        results[strat] = compute_scorecard(strat, trades_list)

    # Portfolio-level summary
    all_pnls = [float(t["pnl"]) for t in trades]
    portfolio_pnl = round(sum(all_pnls), 2)

    proven = [s for s, d in results.items() if d["verdict"] == "PROVEN_GOOD"]
    negative = [s for s, d in results.items() if d["verdict"] == "NEGATIVE_EDGE"]

    return {
        "strategies": results,
        "portfolio": {
            "total_trades": len(trades),
            "total_pnl": portfolio_pnl,
            "proven_good": proven,
            "negative_edge": negative,
            "n_proven": len(proven),
            "n_negative": len(negative),
            "n_unknown_attr": results.get("unknown", {}).get("n_trades", 0),
        },
        "timestamp": "",
    }
