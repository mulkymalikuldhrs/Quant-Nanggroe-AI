from quant_nanggroe.engine.kelly.base import BaseKelly, KellyParameters, KellyResult, KellyMethod


class DrawdownControlledKelly(BaseKelly):
    def __init__(self, base_fraction: float = 0.5, max_drawdown_threshold: float = 0.25):
        self.base_fraction = base_fraction
        self.max_dd_threshold = max_drawdown_threshold

    def compute(self, params: KellyParameters) -> KellyResult:
        b = params.avg_win / params.avg_loss if params.avg_loss != 0 else 0
        p = params.win_rate
        q = 1 - p
        f_full = (b * p - q) / b if b > 0 else 0
        dd_ratio = min(1.0, max(0.0, params.current_drawdown / max(0.01, self.max_dd_threshold)))
        dd_multiplier = 1.0 - dd_ratio
        f_star = max(0, f_full * self.base_fraction * dd_multiplier * params.regime_multiplier)
        f_star = min(f_star, params.leverage_max)
        g = self._growth_rate(f_star, p, b)
        return KellyResult(f_star=f_star, method=KellyMethod.DRAWDOWN_CONTROLLED, growth_rate=g, parameters=params)
