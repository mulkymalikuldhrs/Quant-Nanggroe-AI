"""
SelfFineTuner — Parameter Auto-Optimization Engine for QNA Strategies.

Wraps StrategyEvolver with grid search / random search to find optimal
parameter sets for any registered strategy. Validates improvements via
the evolver's real backtest gate before accepting changes.

Replaces the missing self_finetune.py that autonomous.py was trying to import.
"""

from __future__ import annotations

import itertools
import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from quant_nanggroe.engine.strategies.strategy_evolver import (
    StrategyEvolver,
    EvolveAttempt,
    EvolveConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class FineTuneResult:
    """Result of a single fine-tune run."""
    strategy_name: str
    best_params: Dict[str, Any]
    best_metrics: Dict[str, float]
    attempts: int
    accepted: int
    duration_seconds: float
    improvement_pct: float
    history: List[EvolveAttempt] = field(default_factory=list)


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning."""
    method: str = "grid"            # "grid" | "random" | "bayesian"
    max_attempts: int = 20          # max param sets to try
    max_consecutive_fails: int = 5  # stop if N consecutive fails
    min_improvement_pct: float = 5.0  # must beat baseline by this %
    param_ranges: Dict[str, List[Any]] = field(default_factory=lambda: {
        "lookback": [10, 15, 20, 25, 30],
        "atr_mult": [1.0, 1.2, 1.5, 2.0],
        "fast": [5, 10, 15],
        "slow": [20, 30, 40],
        "threshold": [20, 25, 30],
        "std_dev": [1.5, 2.0, 2.5],
        "period": [10, 14, 20, 30],
    })
    history_path: str = "data/fine_tune_history.json"


class SelfFineTuner:
    """Parameter auto-optimization engine.

    Takes a strategy, explores its parameter space via grid/random search,
    validates each mutation through StrategyEvolver's real backtest gate,
    and returns the best-validated parameter set.

    Usage:
        tuner = SelfFineTuner()
        result = tuner.fine_tune("MeanReversion", {"lookback": 20, "std_dev": 2.0})
        if result and result.accepted > 0:
            # apply best_params to the strategy
            deploy_params(result.best_params)
    """

    def __init__(self, config: Optional[FineTuneConfig] = None):
        self.config = config or FineTuneConfig()
        self._evolver = StrategyEvolver(EvolveConfig(
            min_improvement_pct=self.config.min_improvement_pct,
        ))
        self._history: List[FineTuneResult] = []
        self._load_history()

    # ── Public API ────────────────────────────────────────────────

    def fine_tune(
        self,
        strategy_name: str,
        baseline_params: Dict[str, Any],
        *,
        param_ranges: Optional[Dict[str, List[Any]]] = None,
        backtest_fn: Optional[Callable] = None,
    ) -> Optional[FineTuneResult]:
        """Run parameter optimization for a strategy.

        Args:
            strategy_name: Name of the strategy to fine-tune.
            baseline_params: Current active parameters (baseline).
            param_ranges: Optional custom param ranges (overrides config).
            backtest_fn: Optional custom backtest function.
                         If None, uses StrategyEvolver's real backtest.

        Returns:
            FineTuneResult with best params found, or None if all attempts fail.
        """
        start_time = time.time()
        ranges = param_ranges or self._infer_ranges(baseline_params)
        candidates = self._generate_candidates(baseline_params, ranges)

        logger.info(
            "FineTune %s: %d candidates from %d param dimensions",
            strategy_name, len(candidates), len(ranges),
        )

        best_val = float("-inf")
        best_params = dict(baseline_params)
        best_metrics = {}
        attempts = 0
        accepted_count = 0
        consecutive_fails = 0
        history: List[EvolveAttempt] = []

        for mutated_params in candidates:
            if attempts >= self.config.max_attempts:
                logger.info("FineTune %s: max_attempts (%d) reached", strategy_name, self.config.max_attempts)
                break

            attempt = self._evolver.evaluate(
                strategy_name=strategy_name,
                baseline_params=baseline_params,
                mutated_params=mutated_params,
                backtest_fn=backtest_fn,
            )
            history.append(attempt)
            attempts += 1

            if attempt.accepted:
                accepted_count += 1
                consecutive_fails = 0
                metric_val = attempt.mutated_value
                if metric_val > best_val:
                    best_val = metric_val
                    best_params = dict(mutated_params)
                    best_metrics = {
                        "profit_factor": attempt.mutated_value,
                        "sharpe": attempt.mutated_value,
                        "metric": attempt.metric,
                        "baseline": attempt.baseline_value,
                        "improvement_pct": (
                            ((attempt.mutated_value - attempt.baseline_value)
                             / abs(attempt.baseline_value)) * 100
                            if attempt.baseline_value != 0 else 0.0
                        ),
                    }
                logger.info(
                    "  ✅ ACCEPTED %s: %s → %.4f",
                    attempt.strategy_name, attempt.reason, attempt.mutated_value,
                )
            else:
                consecutive_fails += 1
                logger.debug("  ❌ REJECTED %s: %s", attempt.strategy_name, attempt.reason)

            if consecutive_fails >= self.config.max_consecutive_fails:
                logger.warning(
                    "FineTune %s: %d consecutive fails — stopping early",
                    strategy_name, consecutive_fails,
                )
                break

        elapsed = time.time() - start_time

        improvement_pct = 0.0
        if best_metrics.get("baseline", 0) != 0:
            improvement_pct = ((best_val - best_metrics["baseline"])
                               / abs(best_metrics["baseline"])) * 100

        result = FineTuneResult(
            strategy_name=strategy_name,
            best_params=best_params,
            best_metrics=best_metrics,
            attempts=attempts,
            accepted=accepted_count,
            duration_seconds=round(elapsed, 2),
            improvement_pct=round(improvement_pct, 2),
            history=history,
        )

        self._history.append(result)
        self._persist_history(result)

        logger.info(
            "FineTune %s: %d/%d accepted, best improvement %.1f%%, took %.1fs",
            strategy_name, accepted_count, attempts, improvement_pct, elapsed,
        )

        return result

    def get_history(self, strategy_name: Optional[str] = None) -> List[FineTuneResult]:
        if strategy_name:
            return [r for r in self._history if r.strategy_name == strategy_name]
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        total_accepted = sum(r.accepted for r in self._history)
        total_attempts = sum(r.attempts for r in self._history)
        return {
            "strategies_tuned": total,
            "total_attempts": total_attempts,
            "total_accepted": total_accepted,
            "accept_rate_pct": round(total_accepted / total_attempts * 100, 1) if total_attempts else 0.0,
            "avg_duration_seconds": round(
                sum(r.duration_seconds for r in self._history) / total, 1
            ) if total else 0.0,
        }

    # ── Internal ──────────────────────────────────────────────────

    def _infer_ranges(self, params: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Infer parameter ranges from a strategy's existing params."""
        ranges = {}
        for key, val in params.items():
            if key in self.config.param_ranges:
                ranges[key] = self.config.param_ranges[key]
            elif isinstance(val, (int, float)):
                # Auto-infer range: ±50% around current value
                delta = max(abs(val) * 0.5, 1.0)
                low = val - delta
                high = val + delta
                if isinstance(val, int):
                    ranges[key] = list(range(int(low), int(high) + 1, max(1, int(delta // 2))))
                else:
                    steps = 3
                    ranges[key] = [round(low + i * (high - low) / (steps - 1), 1) for i in range(steps)]
        return ranges

    def _generate_candidates(
        self,
        baseline: Dict[str, Any],
        ranges: Dict[str, List[Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidate param sets via grid or random search."""
        if self.config.method == "grid":
            return self._grid_search(baseline, ranges)
        else:
            return self._random_search(baseline, ranges)

    def _grid_search(
        self,
        baseline: Dict[str, Any],
        ranges: Dict[str, List[Any]],
    ) -> List[Dict[str, Any]]:
        """Grid search: Cartesian product of all parameter ranges."""
        keys = list(ranges.keys())
        values = list(ranges.values())
        candidates = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            # Skip if identical to baseline
            if params == baseline:
                continue
            candidates.append(params)
        # Limit to max_attempts
        return candidates[:self.config.max_attempts]

    def _random_search(
        self,
        baseline: Dict[str, Any],
        ranges: Dict[str, List[Any]],
    ) -> List[Dict[str, Any]]:
        """Random search: sample random combinations from ranges."""
        keys = list(ranges.keys())
        candidates = []
        seen = set()
        while len(candidates) < self.config.max_attempts:
            params = {}
            for k in keys:
                params[k] = random.choice(ranges[k])
            key = str(sorted(params.items()))
            if key in seen or params == baseline:
                continue
            seen.add(key)
            candidates.append(params)
        return candidates

    def _persist_history(self, result: FineTuneResult) -> None:
        path = Path(self.config.history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = json.loads(path.read_text()) if path.exists() else []
            existing.append(asdict(result))
            path.write_text(json.dumps(existing, indent=2, default=str))
        except Exception:
            pass

    def _load_history(self) -> None:
        path = Path(self.config.history_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for entry in data:
                self._history.append(FineTuneResult(**entry))
        except Exception:
            pass
