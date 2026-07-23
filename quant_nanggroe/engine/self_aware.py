"""Self-Aware module for QNA autonomous hedge fund.

This is the MISSING capability the user demanded ("mesin uang autonomous ... self aware").
It gives the pipeline introspection: it reflects on its own state, detects anomalies
in its own performance, and produces human-readable "I am X because Y" reasoning.

It is intentionally dependency-light (stdlib only) so it cannot break the pipeline
import graph. The pipeline instantiates ``SelfAware(state_provider)`` and calls
``.reflect()`` after each run to get a structured self-assessment.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SelfState:
    """Snapshot of the pipeline's own internal state."""
    equity: float = 0.0
    peak_equity: float = 0.0
    daily_pnl: float = 0.0
    total_trades: int = 0
    open_positions: int = 0
    veto_count: int = 0
    approval_count: int = 0
    losing_streak: int = 0
    winning_streak: int = 0
    last_strategy: str = ""
    last_symbol: str = ""
    last_run_ts: float = 0.0
    strategy_last_evolved_ts: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reflection:
    """A structured self-assessment."""
    verdict: str  # HEALTHY | CAUTION | DEGRADED | CRITICAL
    statements: List[str]  # "I am X because Y"
    metrics: Dict[str, Any]
    anomalies: List[str]


class SelfAware:
    """Introspection layer. Given a callable that returns the current SelfState,
    it can reflect on performance and surface anomalies autonomously."""

    def __init__(self, state_provider: Callable[[], SelfState] | None = None):
        self._provider = state_provider
        self._history: List[SelfState] = []
        self._max_history = 200

    def set_state_provider(self, provider: Callable[[], SelfState]) -> None:
        self._provider = provider

    def _snapshot(self) -> SelfState:
        if self._provider is None:
            return SelfState()
        s = self._provider()
        self._history.append(s)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        return s

    def reflect(self) -> Reflection:
        s = self._snapshot()
        statements: List[str] = []
        anomalies: List[str] = []

        # Drawdown
        drawdown = 0.0
        if s.peak_equity > 0:
            drawdown = max(0.0, (s.peak_equity - s.equity) / s.peak_equity)
        if drawdown > 0.20:
            anomalies.append(f"drawdown {drawdown:.1%} exceeds 20% comfort threshold")
            statements.append(f"I am DEGRADED because my drawdown is {drawdown:.1%} from peak.")
        elif drawdown > 0.10:
            statements.append(f"I am in CAUTION because drawdown is {drawdown:.1%}.")

        # Losing streak
        if s.losing_streak >= 5:
            anomalies.append(f"losing streak {s.losing_streak} consecutive trades")
            statements.append(
                f"I am underperforming because I lost {s.losing_streak} trades in a row — "
                f"my current regime/signal filter may be misaligned."
            )
        elif s.losing_streak >= 3:
            statements.append(f"I am cautious: {s.losing_streak} consecutive losses.")

        # Veto ratio (risk guard engagement)
        total_decisions = s.veto_count + s.approval_count
        veto_ratio = (s.veto_count / total_decisions) if total_decisions else 0.0
        if veto_ratio > 0.5 and total_decisions >= 5:
            anomalies.append(f"risk veto ratio {veto_ratio:.1%} — over half of trades blocked")
            statements.append(
                f"I am heavily constrained: risk guard vetoed {veto_ratio:.1%} of attempts — "
                f"either market regime is hostile or my signal quality is poor."
            )

        # Stale evolution
        if s.strategy_last_evolved_ts:
            stale_days = (time.time() - s.strategy_last_evolved_ts) / 86400.0
            if stale_days > 7:
                anomalies.append(f"strategies not evolved in {stale_days:.0f} days")
                statements.append(
                    f"I am stale: my strategies last evolved {stale_days:.0f} days ago — "
                    f"I should trigger self-evolve to adapt."
                )

        # Positive reflection
        if not anomalies:
            statements.append(
                f"I am HEALTHY: equity {s.equity:,.0f}, daily P&L {s.daily_pnl:,.0f}, "
                f"{s.open_positions} open positions, last strategy {s.last_strategy or 'none'}."
            )

        verdict = "HEALTHY"
        if any("DEGRADED" in st or "CRITICAL" in st for st in statements):
            verdict = "DEGRADED"
        elif anomalies:
            verdict = "CAUTION"

        return Reflection(
            verdict=verdict,
            statements=statements,
            metrics={
                "equity": s.equity,
                "peak_equity": s.peak_equity,
                "drawdown": round(drawdown, 4),
                "daily_pnl": s.daily_pnl,
                "total_trades": s.total_trades,
                "open_positions": s.open_positions,
                "veto_ratio": round(veto_ratio, 4),
                "losing_streak": s.losing_streak,
            },
            anomalies=anomalies,
        )

    def last_state(self) -> Optional[SelfState]:
        return self._history[-1] if self._history else None
