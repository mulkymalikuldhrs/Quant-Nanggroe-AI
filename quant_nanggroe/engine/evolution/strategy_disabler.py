"""StrategyDisabler — evaluate performance results and disable underperformers.

Delegates to StrategyRegistry for lifecycle-aware disabling. Underperformers
are not instantiated for future trading cycles.

Regime-aware: strategies with strong performance in a specific market regime
are flagged as regime-dependent rather than disabled outright.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)

REGIME_MIN_WIN_RATE = 0.62
REGIME_MIN_TRADES = 5
REGIME_DIMENSIONS = ["vix_bucket", "fear_greed_bucket", "regime_label", "killzone"]


class StrategyDisabler:
    """Evaluate strategy performance and recommend disabling.

    Supports regime-aware gating: strategies with a specific regime edge
    are preserved as regime-dependent rather than fully disabled.
    """

    def __init__(
        self,
        min_sharpe: float = 0.5,
        min_win_rate: float = 0.40,
        min_trades: int = 10,
        max_drawdown: float = 15.0,
        journal: Optional[EvolutionJournal] = None,
    ) -> None:
        self.min_sharpe = min_sharpe
        self.min_win_rate = min_win_rate
        self.min_trades = min_trades
        self.max_drawdown = max_drawdown
        self._journal = journal

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

    def evaluate_with_regime(
        self, performance_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extend evaluate() with regime-aware gating.

        Returns:
            to_disable: list of strategies with no regime edge (safe to disable)
            regime_dependent: list of strategies that underperform globally but
                              have strong regime-specific edge (preserved)
        """
        candidates = self.evaluate(performance_results)
        to_disable: list[dict[str, Any]] = []
        regime_dependent: list[dict[str, Any]] = []

        for candidate in candidates:
            name = candidate["strategy_name"]

            if self._journal is not None and self._has_regime_edge(name):
                regime_dependent.append({
                    "strategy_name": name,
                    "reason": candidate["reason"],
                    "regime_edge": self._find_best_regime(name),
                    "metrics": candidate["metrics"],
                })
                logger.info(
                    "Regime gate saved '%s' — global %.1f%% WR but regime edge detected",
                    name,
                    candidate["metrics"].get("win_rate", 0.0) * 100,
                )
            else:
                to_disable.append(candidate)

        return {
            "to_disable": to_disable,
            "regime_dependent": regime_dependent,
        }

    def _has_regime_edge(self, strategy_name: str) -> bool:
        """Check if strategy has any regime bucket with win_rate >= threshold."""
        best = self._find_best_regime(strategy_name)
        if best is None:
            return False
        return best["win_rate"] >= REGIME_MIN_WIN_RATE

    def _find_best_regime(self, strategy_name: str) -> dict[str, Any] | None:
        """Return the best regime bucket for a strategy, or None."""
        if self._journal is None:
            return None

        from quant_nanggroe.engine.evolution.performance_scanner import (
            PerformanceScanner,
        )

        scanner = PerformanceScanner(self._journal)
        best: dict[str, Any] | None = None

        for dim in REGIME_DIMENSIONS:
            buckets = scanner.scan_by_regime(strategy_name, dimension=dim)
            for b in buckets:
                if b["trade_count"] < REGIME_MIN_TRADES:
                    continue
                if best is None or b["win_rate"] > best["win_rate"]:
                    best = {
                        "dimension": dim,
                        "bucket": b["bucket"],
                        "win_rate": b["win_rate"],
                        "sharpe": b["sharpe"],
                        "trade_count": b["trade_count"],
                        "avg_r": b["avg_r"],
                    }

        return best

    def report_regime_specialists(
        self, strategy_names: list[str]
    ) -> list[dict[str, Any]]:
        """List strategies with strong regime-specific performance.

        Returns entries sorted by best regime win_rate descending.
        """
        specialists: list[dict[str, Any]] = []

        for name in strategy_names:
            best = self._find_best_regime(name)
            if best is not None and best["win_rate"] >= REGIME_MIN_WIN_RATE:
                specialists.append({
                    "strategy_name": name,
                    "best_regime": best["bucket"],
                    "regime_dim": best["dimension"],
                    "regime_win_rate": best["win_rate"],
                    "regime_sharpe": best["sharpe"],
                    "regime_trades": best["trade_count"],
                    "regime_avg_r": best["avg_r"],
                })

        return sorted(specialists, key=lambda r: r["regime_win_rate"], reverse=True)

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
