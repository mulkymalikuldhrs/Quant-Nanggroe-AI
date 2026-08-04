"""PnL Evaluator — Closed Trade Analysis & Strategy Evolution.

Evaluates closed trades for PnL attribution, win rate, Sharpe, drawdown.
Triggers fine-tuning signals when performance degrades below thresholds.

Ponytail: numpy-native, minimal deps.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClosedTrade:
    """A completed trade with full PnL details."""

    trade_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    volume: float = 0.0
    side: str = "buy"
    entry_time: str = ""
    exit_time: str = ""
    pnl: float = 0.0
    rr: float = 0.0
    regime_at_entry: str = "unknown"
    confidence_at_entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    duration_hours: float = 0.0
    tags: list[str] = field(default_factory=list)
    # Metacognition (autonomous mandate): APA/KENAPA/BAGAIMANA/MENGAPA/KE MANA.
    # Stored as a plain dict (TradeAwareness.to_dict) so it serialises cleanly
    # to JSON / Excel / PDF without pulling the dataclass into every caller.
    awareness: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.trade_id:
            import uuid
            self.trade_id = str(uuid.uuid4())[:12]
        if not self.entry_time:
            self.entry_time = datetime.now(timezone.utc).isoformat()
        if self.exit_price > 0 and not self.exit_time:
            self.exit_time = datetime.now(timezone.utc).isoformat()

    def is_closed(self) -> bool:
        return self.exit_price > 0

    def realized_pnl(self) -> float:
        if not self.is_closed() or self.entry_price <= 0:
            return 0.0
        if self.side == "buy":
            return (self.exit_price - self.entry_price) * self.volume
        else:
            return (self.entry_price - self.exit_price) * self.volume

    def calculate_duration(self) -> float:
        if not self.exit_time or not self.entry_time:
            return 0.0
        try:
            entry = datetime.fromisoformat(self.entry_time)
            exit_dt = datetime.fromisoformat(self.exit_time)
            return (exit_dt - entry).total_seconds() / 3600
        except Exception:
            return 0.0


@dataclass
class TradeEvaluationResult:
    """Result of evaluating a closed trade."""

    trade_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    pnl: float = 0.0
    rr: float = 0.0
    win: bool = False
    sharpe_contribution: float = 0.0
    quality_score: float = 0.0
    recommendation: str = "keep"
    eval_duration_ms: float = 0.0
    timestamp: str = ""


class PnLEvaluator:
    """Closed trade PnL evaluator with batched persistence."""

    def __init__(self, stats_dir: str = "data/strategy_stats", max_history: int = 500):
        self._stats_dir = Path(stats_dir)
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._max_history = max_history
        self._trade_history: dict[str, list[ClosedTrade]] = {}
        self._dirty_strategies: set[str] = set()
        self._save_batch_threshold = 10  # batch writes every N evaluations
        self._eval_count = 0
        self._load_all()

    def evaluate(self, trade: ClosedTrade) -> TradeEvaluationResult:
        """Evaluate a closed trade and record it in the strategy's history."""
        import time as _time_mod
        t0 = _time_mod.perf_counter()

        if not trade.is_closed():
            return TradeEvaluationResult(
                trade_id=trade.trade_id,
                strategy_name=trade.strategy_name,
                symbol=trade.symbol,
                pnl=0.0,
                win=False,
                recommendation="pending",
            )

        pnl = trade.realized_pnl()
        win = pnl > 0

        rr = trade.rr
        if rr == 0.0 and trade.sl > 0 and trade.entry_price > 0 and trade.exit_price > 0:
            if trade.side == "buy":
                risk = trade.entry_price - trade.sl
                reward = trade.exit_price - trade.entry_price
            else:
                risk = trade.sl - trade.entry_price
                reward = trade.entry_price - trade.exit_price
            rr = round(reward / risk, 2) if risk > 0 else 0.0

        duration = trade.calculate_duration()
        if duration == 0.0:
            duration = trade.duration_hours

        rr_score = min(rr / 3.0, 1.0)
        win_score = 1.0 if win else 0.0
        dur_score = min(duration / 48.0, 1.0) if duration > 0 else 0.5
        quality_score = round(rr_score * 0.4 + win_score * 0.4 + dur_score * 0.2, 3)

        if rr < 0.5 and not win:
            recommendation = "evolve"
        elif rr < 1.0 or not win:
            recommendation = "review"
        else:
            recommendation = "keep"

        if trade.strategy_name not in self._trade_history:
            self._trade_history[trade.strategy_name] = []
        self._trade_history[trade.strategy_name].append(trade)

        if len(self._trade_history[trade.strategy_name]) > self._max_history:
            self._trade_history[trade.strategy_name] = \
                self._trade_history[trade.strategy_name][-self._max_history:]

        sharpe_contrib = self._compute_sharpe_contribution(trade.strategy_name)

        eval_duration = (_time_mod.perf_counter() - t0) * 1000

        result = TradeEvaluationResult(
            trade_id=trade.trade_id,
            strategy_name=trade.strategy_name,
            symbol=trade.symbol,
            pnl=round(pnl, 4),
            rr=rr,
            win=win,
            sharpe_contribution=round(sharpe_contrib, 4),
            quality_score=quality_score,
            recommendation=recommendation,
            eval_duration_ms=round(eval_duration, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Batched persistence: mark dirty, write every N evaluations
        self._dirty_strategies.add(trade.strategy_name)
        self._eval_count += 1
        if self._eval_count % self._save_batch_threshold == 0:
            self._flush()

        return result

    def needs_fine_tune(self, result: TradeEvaluationResult | None = None,
                        strategy_name: str = "") -> bool:
        """Check if a strategy needs fine-tuning based on recent performance."""
        if result is not None:
            if result.recommendation == "evolve":
                return True
            if result.recommendation == "review" and result.quality_score < 0.3:
                return True

        if not strategy_name:
            return False

        trades = self._trade_history.get(strategy_name, [])
        if len(trades) < 5:
            return False

        recent = trades[-20:]
        wins = sum(1 for t in recent if t.realized_pnl() > 0)
        win_rate = wins / len(recent)
        total_pnl = sum(t.realized_pnl() for t in recent)

        if win_rate < 0.4 and total_pnl < 0:
            return True
        return False

    def get_strategy_stats(self, strategy_name: str) -> dict[str, Any]:
        """Get aggregated stats for a strategy."""
        trades = self._trade_history.get(strategy_name, [])
        if not trades:
            return {"strategy": strategy_name, "total_trades": 0}

        closed = [t for t in trades if t.is_closed()]
        if not closed:
            return {"strategy": strategy_name, "total_trades": len(trades), "closed_trades": 0}

        pnls = np.array([t.realized_pnl() for t in closed])
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]

        total_pnl = float(np.sum(pnls))
        win_rate = float(len(wins) / len(pnls)) if len(pnls) > 0 else 0.0
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
        profit_factor = float(abs(np.sum(wins) / np.sum(losses))) if np.sum(losses) != 0 else float("inf")
        sharpe = float(np.mean(pnls) / (np.std(pnls, ddof=1) + 1e-8)) if len(pnls) > 1 else 0.0
        rrs = [t.rr for t in closed if t.rr > 0]
        avg_rr = float(np.mean(rrs)) if rrs else 0.0

        return {
            "strategy": strategy_name,
            "total_trades": len(trades),
            "closed_trades": len(closed),
            "total_pnl": round(total_pnl, 4),
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "profit_factor": round(profit_factor, 2),
            "sharpe": round(sharpe, 4),
            "avg_rr": round(avg_rr, 2),
        }

    def get_all_strategy_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all tracked strategies."""
        return {
            name: self.get_strategy_stats(name)
            for name in self._trade_history
            if len([t for t in self._trade_history[name] if t.is_closed()]) > 0
        }

    def collect_lessons(self, strategy_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """Extract metacognition lessons from recent trades for the self-evolve loop.

        Returns a list of {outcome, lesson, feedback_tags, regime} drawn from
        each trade's ``awareness`` dict. This is the bridge between per-trade
        awareness (APA/KENAPA/BAGAIMANA/MENGAPA/KE MANA) and the autonomous
        self-improvement pipeline: the evolver consumes these concrete,
        derivable lessons instead of opaque aggregate metrics. No fabrication —
        only what was actually recorded at entry/exit.
        """
        trades = self._trade_history.get(strategy_name, [])
        closed = [t for t in trades if t.is_closed()]
        recent = closed[-limit:]
        lessons: list[dict[str, Any]] = []
        for t in recent:
            aw = getattr(t, "awareness", None) or {}
            lesson = aw.get("lesson")
            if not lesson:
                continue
            lessons.append({
                "trade_id": t.trade_id,
                "outcome": aw.get("outcome", ""),
                "exit_trigger": aw.get("exit_trigger", ""),
                "lesson": lesson,
                "feedback_tags": aw.get("feedback_tags", []),
                "regime": aw.get("regime", "unknown"),
                "strategy_name": t.strategy_name,
            })
        return lessons


    def _compute_sharpe_contribution(self, strategy_name: str) -> float:
        """Compute the Sharpe contribution of the latest trade batch."""
        trades = self._trade_history.get(strategy_name, [])
        closed = [t for t in trades if t.is_closed()]
        if len(closed) < 3:
            return 0.0
        pnls = np.array([t.realized_pnl() for t in closed[-20:]])
        if len(pnls) < 2:
            return 0.0
        return float(np.mean(pnls) / (np.std(pnls, ddof=1) + 1e-8))

    def _flush(self) -> None:
        """Write all dirty strategies to disk (batched)."""
        for strategy_name in list(self._dirty_strategies):
            self._save_strategy(strategy_name)
        self._dirty_strategies.clear()

    def _save_strategy(self, strategy_name: str) -> None:
        """Persist trade history for a strategy to disk."""
        trades = self._trade_history.get(strategy_name, [])
        path = self._stats_dir / f"{strategy_name}.json"
        data = []
        for t in trades:
            d = asdict(t)
            d["_pnl"] = t.realized_pnl()
            data.append(d)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load_all(self) -> None:
        """Load all persisted trade histories from disk."""
        if not self._stats_dir.exists():
            return
        for path in self._stats_dir.glob("*.json"):
            strategy_name = path.stem
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                trades = []
                for item in raw:
                    item.pop("_pnl", None)
                    trades.append(ClosedTrade(**item))
                if trades:
                    self._trade_history[strategy_name] = trades
            except Exception as exc:
                logger.debug("Failed to load %s: %s", path.name, exc)


__all__ = [
    "ClosedTrade",
    "TradeEvaluationResult",
    "PnLEvaluator",
]
