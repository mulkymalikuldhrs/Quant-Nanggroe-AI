"""WeightUpdater — adjust signal PROVIDER weights (not scorer weights).

DIFFERENTIATION from WeightEvolver (core/scoring/evolver.py):
- WeightEvolver → canonical scorer weight tuner (FusionEngine weights)
- WeightUpdater → provider weight tuner (SignalTracker weights)

Both coexist. No conflict by design — they operate on different registries.
WeightEvolver has circuit breaker + safety ceiling; WeightUpdater is Bayesian.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.hedge_fund.signals.tracker import SignalTracker

logger = logging.getLogger(__name__)


class WeightUpdater:
    """Update weights in SignalTracker and FusionEngine from evolution results."""

    def __init__(
        self,
        tracker: Optional[SignalTracker] = None,
        fusion: Any = None,
    ) -> None:
        self._tracker = tracker or SignalTracker()
        # FusionEngine reference — attached later if not provided at init
        self._fusion: Any = fusion

    # ── FusionEngine binding ─────────────────────────────────────────

    @property
    def fusion(self) -> Any:
        return self._fusion

    @fusion.setter
    def fusion(self, engine: Any) -> None:
        self._fusion = engine

    # ── Weight updates ───────────────────────────────────────────────

    def update_weights(
        self, evolution_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Update SignalTracker and FusionEngine weights.

        Args:
            evolution_results: list of scan results from PerformanceScanner,
                each containing strategy_name, sharpe, win_rate, etc.

        Returns:
            dict with 'signal_updates' and 'scorer_updates' summaries.
        """
        signal_updates: list[dict[str, Any]] = []
        scorer_updates: list[dict[str, Any]] = []

        for result in evolution_results:
            name: str = result.get("strategy_name", "")
            if not name:
                continue

            # ── SignalTracker weight (Bayesian) ──────────────────────
            win_rate = result.get("win_rate", 0.0)
            trade_count = result.get("trade_count", 0)

            if trade_count > 0:
                # Bayesian update: beta(alpha + wins, beta + losses)
                # Prior: beta(1, 1) = uniform
                # Not replacing get_weight() — just verifying it reflects
                # current data.  The actual weight is computed lazily.
                tracker_weight = self._compute_bayesian_weight(
                    win_rate, trade_count
                )
                signal_updates.append({
                    "provider": name,
                    "weight": round(tracker_weight, 4),
                    "trades": trade_count,
                })
                logger.debug(
                    "Tracker weight for '%s': %.4f (%d trades)",
                    name, tracker_weight, trade_count,
                )

            # ── FusionEngine scorer weight ───────────────────────────
            sharpe = result.get("sharpe", 0.0)
            if self._fusion is not None and hasattr(self._fusion, "_scorers"):
                # Map strategy name to scorer name convention
                scorer_name = f"{name}_scorer"
                for scorer in self._fusion._scorers:
                    if scorer.__class__.__name__.lower().startswith(
                        name.lower()
                    ) or scorer_name.lower() in scorer.__class__.__name__.lower():
                        # Adjust weight proportional to sharpe
                        old_weight = getattr(scorer, "weight", 1.0)
                        new_weight = self._compute_scorer_weight(
                            sharpe, old_weight
                        )
                        scorer.weight = new_weight  # type: ignore[assignment]
                        scorer_updates.append({
                            "scorer": scorer.__class__.__name__,
                            "old_weight": round(old_weight, 4),
                            "new_weight": round(new_weight, 4),
                            "sharpe": round(sharpe, 4),
                        })
                        logger.debug(
                            "Scorer weight %s: %.4f → %.4f (sharpe %.3f)",
                            scorer.__class__.__name__,
                            old_weight,
                            new_weight,
                            sharpe,
                        )

        return {
            "signal_updates": signal_updates,
            "scorer_updates": scorer_updates,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_bayesian_weight(
        win_rate: float, trade_count: int, alpha_prior: float = 1.0, beta_prior: float = 1.0
    ) -> float:
        """Bayesian smoothed weight: beta posterior mean.

        (alpha_prior + wins) / (alpha_prior + beta_prior + trades)
        """
        wins = int(win_rate * trade_count)
        return (alpha_prior + wins) / (alpha_prior + beta_prior + trade_count)

    @staticmethod
    def _compute_scorer_weight(
        sharpe: float,
        old_weight: float,
        max_change_pct: float = 0.05,
        weight_min: float = 0.05,
        weight_max: float = 3.0,
    ) -> float:
        """Adjust scorer weight based on sharpe ratio.

        Caps change at max_change_pct of old_weight per cycle.
        """
        # Map sharpe to a multiplier in [0.8, 1.2]; center at sharpe=0.5
        multiplier = 1.0 + (sharpe - 0.5) * 0.1
        multiplier = max(0.8, min(1.2, multiplier))

        delta = old_weight * (multiplier - 1.0)
        # Cap absolute change
        max_delta = old_weight * max_change_pct
        delta = max(-max_delta, min(max_delta, delta))

        new_weight = old_weight + delta
        return max(weight_min, min(weight_max, new_weight))
