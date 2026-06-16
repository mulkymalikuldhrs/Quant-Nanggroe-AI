from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np


class KellyMethod(Enum):
    FULL = "full"
    HALF = "half"
    QUARTER = "quarter"
    FRACTIONAL = "fractional"
    BAYESIAN = "bayesian"
    DRAWDOWN_CONTROLLED = "drawdown_controlled"
    CORRELATION_AWARE = "correlation_aware"
    ADAPTIVE = "adaptive"
    MULTI_ASSET = "multi_asset"
    OPTIMAL_F = "optimal_f"


@dataclass
class KellyParameters:
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 1.0
    fraction: float = 1.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    volatility: Optional[float] = None
    risk_free_rate: float = 0.0
    leverage_max: float = 1.0
    regime_multiplier: float = 1.0
    trade_history: Optional[list[float]] = None
    correlation_matrix: Optional[np.ndarray] = None
    cov_matrix: Optional[np.ndarray] = None
    mean_returns: Optional[list[float]] = None
    num_bets: Optional[int] = None


@dataclass
class KellyResult:
    f_star: float
    method: KellyMethod
    growth_rate: float
    parameters: KellyParameters
    warnings: list[str] = field(default_factory=list)


class BaseKelly:
    def compute(self, params: KellyParameters) -> KellyResult:
        raise NotImplementedError

    @staticmethod
    def _validate_probability(p: float) -> bool:
        return 0 < p < 1

    @staticmethod
    def _growth_rate(f: float, p: float, b: float) -> float:
        if f <= 0 or f >= 1:
            return -np.inf
        g = p * np.log(1 + f * b) + (1 - p) * np.log(1 - f)
        return g if not np.isnan(g) else -np.inf
