from dataclasses import dataclass

import numpy as np


@dataclass
class VaRResult:
    parametric_var_95: float
    parametric_var_99: float
    historical_var_95: float
    historical_var_99: float
    ewhs_var_95: float
    ewhs_var_99: float
    cvar_95: float
    cvar_99: float

class StressVaRCalculator:
    def __init__(self, lambda_factor: float = 0.94):
        self.lambda_factor = lambda_factor

    def compute(self, returns: np.ndarray, confidence: float = 0.95) -> VaRResult:
        mu = np.mean(returns)
        sigma = np.std(returns)
        parametric_var_95 = mu - 1.645 * sigma
        parametric_var_99 = mu - 2.326 * sigma
        historical_var_95 = float(np.percentile(returns, 5))
        historical_var_99 = float(np.percentile(returns, 1))
        weights = np.array([(1 - self.lambda_factor) * self.lambda_factor ** i for i in range(len(returns))])
        weights /= weights.sum()
        sorted_idx = np.argsort(returns)
        sorted_rets = returns[sorted_idx]
        sorted_w = weights[sorted_idx]
        cum_w = np.cumsum(sorted_w)
        ewhs_var_95 = float(sorted_rets[cum_w >= 0.05][0]) if np.any(cum_w >= 0.05) else historical_var_95
        ewhs_var_99 = float(sorted_rets[cum_w >= 0.01][0]) if np.any(cum_w >= 0.01) else historical_var_99
        tail_95 = returns[returns <= historical_var_95]
        cvar_95 = float(np.mean(tail_95)) if len(tail_95) > 0 else historical_var_95
        tail_99 = returns[returns <= historical_var_99]
        cvar_99 = float(np.mean(tail_99)) if len(tail_99) > 0 else historical_var_99
        return VaRResult(parametric_var_95, parametric_var_99, historical_var_95, historical_var_99, ewhs_var_95, ewhs_var_99, cvar_95, cvar_99)

    def compute_ewhs_var(self, returns: np.ndarray, lambda_factor: float = 0.94):
        self.lambda_factor = lambda_factor
        return self.compute(returns)
