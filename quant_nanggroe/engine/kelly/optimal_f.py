from quant_nanggroe.engine.kelly.base import BaseKelly, KellyParameters, KellyResult, KellyMethod
import numpy as np


class OptimalF(BaseKelly):
    def __init__(self, max_f: float = 1.0, steps: int = 100):
        self.max_f = max_f
        self.steps = steps

    def compute(self, params: KellyParameters) -> KellyResult:
        if params.trade_history is None or len(params.trade_history) < 10:
            return self._fallback(params)
        trades = np.array(params.trade_history)
        best_f = 0.0
        best_twr = -np.inf
        test_fs = np.linspace(0.01, self.max_f, self.steps)
        for f in test_fs:
            hprs = 1 + f * trades / max(0.01, np.max(np.abs(trades)))
            twr = np.prod(hprs)
            if twr > best_twr:
                best_twr = twr
                best_f = f
        f_star = min(best_f * params.regime_multiplier, params.leverage_max)
        g = self._growth_rate(f_star, params.win_rate, params.avg_win / max(0.01, params.avg_loss))
        return KellyResult(f_star=f_star, method=KellyMethod.OPTIMAL_F, growth_rate=g, parameters=params)

    def _fallback(self, params: KellyParameters) -> KellyResult:
        from quant_nanggroe.engine.kelly.fractional import FractionalKelly
        return FractionalKelly(0.5).compute(params)
