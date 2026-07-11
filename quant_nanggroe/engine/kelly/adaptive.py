from collections import deque

import numpy as np

from quant_nanggroe.engine.kelly.base import BaseKelly, KellyMethod, KellyParameters, KellyResult


class AdaptiveKelly(BaseKelly):
    def __init__(self, base_fraction: float = 0.5, window: int = 60):
        self.base_fraction = base_fraction
        self.window = window
        self.performance_history: deque[float] = deque(maxlen=window)

    def compute(self, params: KellyParameters) -> KellyResult:
        b = params.avg_win / params.avg_loss if params.avg_loss != 0 else 0
        p = params.win_rate
        q = 1 - p
        f_full = (b * p - q) / b if b > 0 else 0
        perf_multiplier = self._get_performance_multiplier()
        fraction = self.base_fraction * perf_multiplier * params.regime_multiplier
        fraction = max(0.1, min(1.0, fraction))
        f_star = max(0, f_full * fraction)
        f_star = min(f_star, params.leverage_max)
        g = self._growth_rate(f_star, p, b)
        return KellyResult(f_star=f_star, method=KellyMethod.ADAPTIVE, growth_rate=g, parameters=params)

    def _get_performance_multiplier(self) -> float:
        if not self.performance_history:
            return 1.0
        recent_sharpe = np.mean(self.performance_history) / max(0.01, np.std(self.performance_history))
        base_sharpe = 0.5
        return min(2.0, max(0.5, recent_sharpe / max(0.01, base_sharpe)))

    def update(self, return_value: float):
        self.performance_history.append(return_value)
