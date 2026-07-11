"""
Kelly Criterion — Legacy Shim
==============================
Backward-compatible wrapper that delegates to the ``engine/kelly/`` package.

All new development should use ``quant_nanggroe.engine.kelly`` directly.
This module re-exports the legacy ``KellyCriterion`` class and enums
for existing callers.

Usage (legacy)::

    from quant_nanggroe.engine.risk.kelly import KellyCriterion, KellyResult

Usage (preferred)::

    from quant_nanggroe.engine.kelly import BaseKelly, KellyParameters, KellyResult
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from quant_nanggroe.engine.kelly import (
    AdaptiveKelly,
    BaseKelly,
    FractionalKelly,
    FullKelly,
    MultiAssetKelly,
)
from quant_nanggroe.engine.kelly import (
    KellyMethod as NewKellyMethod,
)
from quant_nanggroe.engine.kelly import (
    KellyParameters as NewKellyParameters,
)
from quant_nanggroe.engine.kelly import (
    KellyResult as NewKellyResult,
)


class KellyMethod(Enum):
    """Legacy Kelly method names mapped to new engine/kelly/ package."""

    FULL_KELLY = "FULL_KELLY"
    HALF_KELLY = "HALF_KELLY"
    QUARTER_KELLY = "QUARTER_KELLY"
    FRACTIONAL_KELLY = "FRACTIONAL_KELLY"
    ADAPTIVE_KELLY = "ADAPTIVE_KELLY"

    def to_new(self) -> NewKellyMethod:
        mapping = {
            self.FULL_KELLY: NewKellyMethod.FULL,
            self.HALF_KELLY: NewKellyMethod.HALF,
            self.QUARTER_KELLY: NewKellyMethod.QUARTER,
            self.FRACTIONAL_KELLY: NewKellyMethod.FRACTIONAL,
            self.ADAPTIVE_KELLY: NewKellyMethod.ADAPTIVE,
        }
        return mapping.get(self, NewKellyMethod.HALF)


@dataclass
class KellyParameters:
    """Legacy Kelly parameters — delegates to engine/kelly/ backend."""

    win_rate: float
    avg_win: float
    avg_loss: float
    max_loss: Optional[float] = None
    confidence: float = 0.5
    volatility: Optional[float] = None

    def to_new(self) -> NewKellyParameters:
        return NewKellyParameters(
            win_rate=self.win_rate,
            avg_win=self.avg_win,
            avg_loss=self.avg_loss,
            volatility=self.volatility,
            risk_free_rate=0.0,
            leverage_max=1.0,
            regime_multiplier=self.confidence,
        )


@dataclass
class KellyResult:
    """Legacy Kelly result — wraps engine/kelly/ result."""

    optimal_fraction: float
    expected_growth: float
    expected_value: float
    risk_of_ruin: float
    adjusted_fraction: float
    recommendation: str
    confidence: float

    @classmethod
    def from_new(cls, new: NewKellyResult) -> KellyResult:
        return cls(
            optimal_fraction=new.f_star,
            expected_growth=new.growth_rate,
            expected_value=0.0,
            risk_of_ruin=0.0,
            adjusted_fraction=new.f_star,
            recommendation=cls._recommendation(new),
            confidence=1.0,
        )

    @staticmethod
    def _recommendation(new: NewKellyResult) -> str:
        f = new.f_star
        if f <= 0:
            return "NO POSITION - No edge detected"
        if f >= 0.20:
            return f"MAX POSITION - Strong edge ({new.method.value})"
        if f >= 0.15:
            return f"LARGE POSITION - Good edge ({new.method.value})"
        if f >= 0.10:
            return f"MEDIUM POSITION - Moderate edge ({new.method.value})"
        if new.warnings:
            return f"CAUTION: {'; '.join(new.warnings)}"
        return f"SMALL POSITION - Weak edge ({new.method.value})"


class KellyCriterion:
    """Legacy Kelly Criterion — delegates to engine/kelly/ package.

    Maintains full backward compatibility while routing computation
    to the new ``engine/kelly/`` implementations.

    Config parameters:
        max_position: Maximum position size (default: 0.20).
        min_position: Minimum position size (default: 0.01).
    """

    def __init__(
        self,
        max_position: float = 0.20,
        min_position: float = 0.01,
        ruin_threshold: float = 0.05,
        volatility_penalty: float = 0.5,
        confidence_weight: float = 0.3,
    ) -> None:
        self.max_position = max_position
        self.min_position = min_position
        self.ruin_threshold = ruin_threshold
        self.volatility_penalty = volatility_penalty
        self.confidence_weight = confidence_weight
        self._history: List[Dict] = []

    def calculate_kelly(
        self,
        params: KellyParameters,
        method: Optional[KellyMethod] = None,
    ) -> KellyResult:
        """Calculate Kelly Criterion via delegation to engine/kelly/.

        Args:
            params: Legacy Kelly parameters.
            method: Legacy Kelly method enum.

        Returns:
            Legacy KellyResult wrapping the new engine result.
        """
        if method is None:
            method = KellyMethod.HALF_KELLY

        new_params = params.to_new()
        new_method = method.to_new()

        impl = self._get_implementation(new_method)
        new_result = impl.compute(new_params)

        result = KellyResult.from_new(new_result)

        self._history.append({
            "timestamp": datetime.now(),
            "params": params,
            "result": result,
            "method": method,
        })

        return result

    def _get_implementation(self, method: NewKellyMethod) -> BaseKelly:
        if method == NewKellyMethod.FULL:
            return FullKelly()  # ponytail: was falling to else→Fractional(0.5), broke f*
        elif method == NewKellyMethod.ADAPTIVE:
            return AdaptiveKelly(
                max_position=self.max_position,
                min_position=self.min_position,
            )
        elif method in (NewKellyMethod.FRACTIONAL, NewKellyMethod.HALF, NewKellyMethod.QUARTER):
            frac = {NewKellyMethod.HALF: 0.5, NewKellyMethod.QUARTER: 0.25}.get(method, 0.5)
            return FractionalKelly(fraction=frac)
        else:
            return AdaptiveKelly(max_position=self.max_position, min_position=self.min_position)

    def calculate_continuous_kelly(
        self,
        mean_return: float,
        variance: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """Continuous-time Kelly: f* = (mu - r) / sigma^2."""
        if variance <= 0:
            return 0.0
        return (mean_return - risk_free_rate) / variance

    def calculate_multi_asset_kelly(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_free_rate: float = 0.0,
    ) -> np.ndarray:
        """Multi-asset Kelly via engine/kelly/ delegation."""
        macro = MultiAssetKelly(
            max_leverage=self.max_position,
        )
        params = NewKellyParameters(
            win_rate=0.5,
            avg_win=1.0,
            avg_loss=1.0,
            mean_returns=expected_returns.tolist() if hasattr(expected_returns, 'tolist') else list(expected_returns),
            cov_matrix=cov_matrix,
            risk_free_rate=risk_free_rate,
        )
        result = macro.compute(params)
        return np.array([result.f_star])

    def get_optimal_position_size(
        self,
        account_value: float,
        params: KellyParameters,
        method: Optional[KellyMethod] = None,
    ) -> float:
        """Get position size in monetary terms."""
        result = self.calculate_kelly(params, method)
        return account_value * result.adjusted_fraction

    def get_summary_statistics(self) -> Dict[str, Any]:
        if not self._history:
            return {"total_calculations": 0}
        total = len(self._history)
        avg_fraction = np.mean([h["result"].adjusted_fraction for h in self._history])
        avg_growth = np.mean([h["result"].expected_growth for h in self._history])
        positive = sum(1 for h in self._history if h["result"].expected_growth > 0)
        return {
            "total_calculations": total,
            "average_fraction": round(float(avg_fraction), 4),
            "average_expected_growth": round(float(avg_growth), 6),
            "positive_growth_rate": round(positive / total, 4),
        }
