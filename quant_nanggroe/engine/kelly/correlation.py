from quant_nanggroe.engine.kelly.base import BaseKelly, KellyParameters, KellyResult, KellyMethod
import numpy as np


class CorrelationAwareKelly(BaseKelly):
    def __init__(self, base_fraction: float = 0.5):
        self.base_fraction = base_fraction

    def compute(self, params: KellyParameters) -> KellyResult:
        if params.correlation_matrix is None or params.num_bets is None:
            return self._single_asset_kelly(params)
        rho = params.correlation_matrix.mean()
        n = params.num_bets
        diversity = 1.0 / (1.0 + (n - 1) * rho) if rho > 0 else 1.0
        b = params.avg_win / params.avg_loss if params.avg_loss != 0 else 0
        p = params.win_rate
        q = 1 - p
        f_single = (b * p - q) / b if b > 0 else 0
        f_star = max(0, f_single * self.base_fraction * diversity * params.regime_multiplier)
        f_star = min(f_star, params.leverage_max)
        g = self._growth_rate(f_star, p, b)
        return KellyResult(f_star=f_star, method=KellyMethod.CORRELATION_AWARE, growth_rate=g, parameters=params)

    def _single_asset_kelly(self, params: KellyParameters) -> KellyResult:
        from quant_nanggroe.engine.kelly.fractional import FractionalKelly
        return FractionalKelly(self.base_fraction).compute(params)
