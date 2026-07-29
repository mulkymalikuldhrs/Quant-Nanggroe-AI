"""StrategyDisabler — evaluate performance results and disable underperformers.

Delegates to StrategyRegistry for lifecycle-aware disabling. Underperformers
are not instantiated for future trading cycles.
"""

from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class StrategyDisabler:
    """Evaluate strategy performance and recommend disabling."""

    def __init__(
        self,
        min_sharpe: float = 0.5,
        min_win_rate: float = 0.40,
        min_trades: int = 10,
        max_drawdown: float = 15.0,
    ) -> None:
        self.min_sharpe = min_sharpe
        self.min_win_rate = min_win_rate
        self.min_trades = min_trades
        self.max_drawdown = max_drawdown

    def evaluate(
        self, performance_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return list of strategies to disable with reasons.

        Each entry: {strategy_name, reason, metrics_snapshot}
        Only strategies below thresholds with sufficient trade count qualify.
        """
        to_disable: list[dict[str, Any]] = []

        for result in performance_results:
            name: str = result.get("strategy_name", "")
            trade_count: int = result.get("trade_count", 0)

            if trade_count < self.min_trades:
                continue  # insufficient data

            reasons: list[str] = []

            sharpe = result.get("sharpe", 0.0)
            if sharpe < self.min_sharpe:
                reasons.append(f"sharpe {sharpe:.3f} < {self.min_sharpe}")

            win_rate = result.get("win_rate", 0.0)
            if win_rate < self.min_win_rate:
                reasons.append(f"win_rate {win_rate:.2%} < {self.min_win_rate:.0%}")

            max_dd = result.get("max_drawdown", 0.0)
            if self.max_drawdown > 0 and max_dd > self.max_drawdown:
                reasons.append(f"max_drawdown {max_dd:.1%} > {self.max_drawdown:.0%}")

            if reasons:
                to_disable.append({
                    "strategy_name": name,
                    "reason": "; ".join(reasons),
                    "metrics": result,
                })

        return to_disable

    def disable(self, strategy_name: str) -> bool:
        """Mark a strategy as disabled via StrategyRegistry.

        This uses the lifecycle approach: updates evolved params with
        a '__disabled__' sentinel. StrategyRegistry.create() will skip
        strategies whose lifecycle state isn't ACTIVE.

        Returns True if acknowledged.
        """
        # Persist a disabled marker via update_params so future create()
        # can check it.  The StrategyLifecycleManager is the canonical
        # place for lifecycle transitions; we record intent here.
        existing = StrategyRegistry.get_evolved_params(strategy_name)
        existing["__disabled__"] = True
        StrategyRegistry.update_params(strategy_name, existing)
        logger.warning("Strategy '%s' marked disabled", strategy_name)
        return True

    def enable(self, strategy_name: str) -> bool:
        """Re-enable a previously disabled strategy."""
        existing = StrategyRegistry.get_evolved_params(strategy_name)
        existing.pop("__disabled__", None)
        StrategyRegistry.update_params(strategy_name, existing)
        logger.info("Strategy '%s' re-enabled", strategy_name)
        return True

    def is_disabled(self, strategy_name: str) -> bool:
        """Check if a strategy has the disabled marker."""
        return StrategyRegistry.get_evolved_params(strategy_name).get(
            "__disabled__", False
        )
