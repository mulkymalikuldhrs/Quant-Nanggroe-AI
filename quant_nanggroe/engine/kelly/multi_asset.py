from quant_nanggroe.engine.kelly.base import BaseKelly, KellyParameters, KellyResult, KellyMethod
import numpy as np


class MultiAssetKelly(BaseKelly):
    def __init__(self, shrinkage: float = 0.1):
        self.shrinkage = shrinkage

    def compute(self, params: KellyParameters) -> KellyResult:
        if params.cov_matrix is None or params.mean_returns is None:
            return self._fallback(params)
        sigma = params.cov_matrix
        mu = np.array(params.mean_returns) - params.risk_free_rate
        n = sigma.shape[0]
        target = np.eye(n) * np.diag(sigma).mean()
        sigma_shrunk = (1 - self.shrinkage) * sigma + self.shrinkage * target
        sigma_inv = np.linalg.inv(sigma_shrunk)
        f_raw = sigma_inv @ mu
        max_lever = params.leverage_max
        f_lever_sum = np.sum(np.abs(f_raw))
        if f_lever_sum > max_lever:
            f_scaled = f_raw * max_lever / f_lever_sum
        else:
            f_scaled = f_raw
        f_star = float(np.max(f_scaled)) if len(f_scaled) > 0 else 0
        g = float(mu.T @ f_scaled - 0.5 * f_scaled.T @ sigma @ f_scaled) if len(f_scaled) > 0 else -np.inf
        return KellyResult(f_star=f_star, method=KellyMethod.MULTI_ASSET, growth_rate=g, parameters=params)

    def _fallback(self, params: KellyParameters) -> KellyResult:
        from quant_nanggroe.engine.kelly.fractional import FractionalKelly
        return FractionalKelly(0.5).compute(params)
