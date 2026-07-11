from quant_nanggroe.engine.kelly.base import BaseKelly, KellyMethod, KellyParameters, KellyResult


class FractionalKelly(BaseKelly):
    def __init__(self, fraction: float = 0.5):
        self.fraction = max(0.01, min(1.0, fraction))

    def compute(self, params: KellyParameters) -> KellyResult:
        b = params.avg_win / params.avg_loss if params.avg_loss != 0 else 0
        p = params.win_rate
        q = 1 - p
        f_full = (b * p - q) / b if b > 0 else 0
        f_star = max(0, f_full * self.fraction * params.regime_multiplier)
        f_star = min(f_star, params.leverage_max)
        g = self._growth_rate(f_star, p, b)
        return KellyResult(f_star=f_star, method=KellyMethod.FRACTIONAL, growth_rate=g, parameters=params)
