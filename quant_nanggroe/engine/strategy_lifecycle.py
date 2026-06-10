"""
Darwinian Strategy Lifecycle
=============================
From HermesQuantOS — Strategy states: ACTIVE → HIBERNATING → KILLED.

Auto-kill strategies with negative expectancy after 20+ trades.
Survival of the fittest.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe.types.engine import StrategyStatus


class StrategyState(BaseModel):
    """State of a single strategy."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str = ""
    state: StrategyStatus = StrategyStatus.ACTIVE
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    expectancy: float = 0.0
    win_rate: float = 0.0
    registered_at: datetime = Field(default_factory=datetime.now)
    last_evaluated: datetime | None = None
    state_history: list[dict[str, Any]] = Field(default_factory=list)

    # Cumulative win/loss amounts for proper average calculation
    _cum_wins: float = 0.0
    _cum_losses: float = 0.0


class StrategyLifecycleManager:
    """
    Darwinian strategy evolution: survival of the fittest.

    Strategy states:
    - ACTIVE: Strategy is live and generating trades
    - HIBERNATING: Strategy paused due to excessive drawdown
    - KILLED: Strategy permanently disabled due to negative expectancy

    Auto-evaluation triggers:
    - After MIN_TRADES_FOR_EVALUATION trades
    - Negative expectancy → KILLED
    - Excessive drawdown → HIBERNATING
    - Recovery from hibernation → ACTIVE
    """

    MIN_TRADES_FOR_EVALUATION = 20
    HIBERNATE_MAX_DRAWDOWN = 0.15  # 15% max drawdown
    KILL_NEGATIVE_EXPECTANCY = True

    def __init__(self) -> None:
        self.strategies: dict[str, StrategyState] = {}

    def register_strategy(self, name: str, description: str = "") -> StrategyState:
        """Register a new strategy for lifecycle tracking.

        Args:
            name: Strategy name.
            description: Strategy description.

        Returns:
            The newly created StrategyState.
        """
        strategy = StrategyState(
            name=name,
            description=description,
            state_history=[{"state": StrategyStatus.ACTIVE, "timestamp": datetime.now().isoformat()}],
        )
        self.strategies[name] = strategy
        return strategy

    def update_strategy(
        self,
        name: str,
        pnl: float,
        is_win: bool,
        current_drawdown: float = 0.0,
    ) -> StrategyState:
        """
        Update strategy performance after a trade.

        Args:
            name: Strategy name
            pnl: Trade PnL
            is_win: Whether the trade was a win
            current_drawdown: Current drawdown percentage

        Returns:
            Updated strategy state
        """
        if name not in self.strategies:
            self.register_strategy(name)

        strategy = self.strategies[name]
        strategy.trades_count += 1
        strategy.total_pnl += pnl
        strategy.max_drawdown = max(strategy.max_drawdown, current_drawdown)

        # Track cumulative win/loss amounts for proper average calculation
        if is_win:
            strategy.wins += 1
            strategy._cum_wins += pnl
        else:
            strategy.losses += 1
            strategy._cum_losses += abs(pnl)

        # Calculate expectancy using proper average win/loss
        if strategy.trades_count > 0:
            strategy.win_rate = strategy.wins / strategy.trades_count
            avg_win = strategy._cum_wins / max(strategy.wins, 1)
            avg_loss = strategy._cum_losses / max(strategy.losses, 1) if strategy.losses > 0 else 0.0
            strategy.expectancy = strategy.win_rate * avg_win - (1 - strategy.win_rate) * avg_loss

        strategy.last_evaluated = datetime.now()

        # Guard: reject updates to KILLED strategies
        if strategy.state == StrategyStatus.KILLED:
            return strategy

        # Evaluate lifecycle
        self._evaluate_lifecycle(name)

        return strategy

    def _evaluate_lifecycle(self, name: str) -> None:
        """Evaluate strategy lifecycle state."""
        strategy = self.strategies[name]

        if strategy.trades_count < self.MIN_TRADES_FOR_EVALUATION:
            return

        # Kill condition: negative expectancy
        if self.KILL_NEGATIVE_EXPECTANCY and strategy.expectancy < 0:
            self._transition(name, StrategyStatus.KILLED, f"Negative expectancy after {strategy.trades_count} trades")
            return

        # Hibernate condition: max drawdown exceeded
        if strategy.max_drawdown > self.HIBERNATE_MAX_DRAWDOWN:
            self._transition(
                name,
                StrategyStatus.HIBERNATING,
                f"Max drawdown {strategy.max_drawdown:.2%} > {self.HIBERNATE_MAX_DRAWDOWN:.2%}",
            )
            return

        # If hibernating but recovered, reactivate
        if strategy.state == StrategyStatus.HIBERNATING and strategy.expectancy > 0:
            self._transition(name, StrategyStatus.ACTIVE, "Recovered — positive expectancy")

    def _transition(self, name: str, new_state: StrategyStatus, reason: str) -> None:
        """Transition strategy to new state.

        Args:
            name: Strategy name.
            new_state: Target StrategyStatus.
            reason: Reason for the transition.
        """
        strategy = self.strategies[name]
        old_state = strategy.state

        if old_state == new_state:
            return

        strategy.state = new_state
        strategy.state_history.append(
            {
                "state": new_state.value,
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
            }
        )

    def get_active_strategies(self) -> list[str]:
        """Get list of active strategy names."""
        return [name for name, s in self.strategies.items() if s.state == StrategyStatus.ACTIVE]

    def get_strategy_report(self) -> dict[str, Any]:
        """Get comprehensive strategy lifecycle report."""
        return {
            "total_strategies": len(self.strategies),
            "active": len([s for s in self.strategies.values() if s.state == StrategyStatus.ACTIVE]),
            "hibernating": len([s for s in self.strategies.values() if s.state == StrategyStatus.HIBERNATING]),
            "killed": len([s for s in self.strategies.values() if s.state == StrategyStatus.KILLED]),
            "strategies": {
                name: {
                    "state": s.state.value,
                    "trades": s.trades_count,
                    "win_rate": f"{s.win_rate:.1%}",
                    "expectancy": round(s.expectancy, 4),
                    "max_dd": f"{s.max_drawdown:.2%}",
                    "total_pnl": round(s.total_pnl, 2),
                }
                for name, s in self.strategies.items()
            },
        }
