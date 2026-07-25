"""SelfFineTuner — real parameter fine-tuning for QNA strategies.

Phase D: replaces the missing/inert SelfFineTuner import that autonomous.py
expected. This is NOT LLM training (no GPU needed) — it is parameter-level
fine-tuning: mutate strategy params -> validate via real backtest -> promote
if improved. Thin wrapper over StrategyEvolver with a grid-search sweep.

Ponytail: no new deps, reuse StrategyEvolver + real backtest. ~80 lines.
"""
from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FineTuneConfig:
    """Config for self fine-tuning sweep."""
    metric: str = "profit_factor"
    min_improvement_pct: float = 3.0
    grid_steps: int = 3  # steps per param axis
    history_path: str = "data/finetune_history.json"


@dataclass
class FineTuneResult:
    strategy_name: str
    baseline_params: Dict[str, Any]
    best_params: Dict[str, Any]
    baseline_metric: float
    best_metric: float
    improved: bool
    reason: str


class SelfFineTuner:
    """Fine-tunes a strategy's parameters via grid search + real backtest gate.

    Usage:
        ft = SelfFineTuner()
        res = ft.optimize("DhaherSystem", {"lookback": 20, "atr_mult": 1.2},
                          {"lookback": [15, 20, 25], "atr_mult": [1.0, 1.2, 1.5]})
        if res.improved:
            # promote res.best_params
    """

    def __init__(self, config: Optional[FineTuneConfig] = None):
        self.config = config or FineTuneConfig()
        # Reuse the same real-backtest gate as StrategyEvolver
        from quant_nanggroe.engine.strategies.strategy_evolver import StrategyEvolver
        self._evolver = StrategyEvolver()

    def optimize(
        self,
        strategy_name: str,
        baseline_params: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
    ) -> FineTuneResult:
        """Grid-search param combinations, keep best by real-backtest metric."""
        keys = list(param_grid.keys())
        combos = list(itertools.product(*[param_grid[k] for k in keys]))
        if not combos:
            return FineTuneResult(strategy_name, baseline_params, baseline_params,
                                  0.0, 0.0, False, "empty grid")

        best_params = dict(baseline_params)
        best_val = self._metric(strategy_name, baseline_params)
        baseline_val = best_val

        for combo in combos:
            cand = dict(baseline_params)
            cand.update(dict(zip(keys, combo)))
            val = self._metric(strategy_name, cand)
            if val is None:
                continue
            if val > best_val:
                best_val = val
                best_params = cand

        improved = best_val > baseline_val * (1 + self.config.min_improvement_pct / 100.0)
        reason = (
            f"{self.config.metric}: {baseline_val:.4f} → {best_val:.4f} "
            f"({'IMPROVED' if improved else 'no gain'})"
        )
        logger.info(f"SelfFineTuner {strategy_name}: {reason}")
        return FineTuneResult(
            strategy_name=strategy_name,
            baseline_params=baseline_params,
            best_params=best_params,
            baseline_metric=baseline_val or 0.0,
            best_metric=best_val or 0.0,
            improved=improved,
            reason=reason,
        )

    def _metric(self, name: str, params: Dict[str, Any]) -> Optional[float]:
        """Run real backtest, return primary metric (fail-closed: None on error)."""
        metrics = self._evolver._real_backtest(name, params)
        if metrics is None:
            return None
        return metrics.get(self.config.metric, 0.0)
