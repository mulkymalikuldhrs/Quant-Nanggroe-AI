import numpy as np

class SensitivityAnalyzer:
    def __init__(self, shock_sizes: list[float] = [-0.05, -0.01, 0.01, 0.05]):
        self.shock_sizes = shock_sizes

    def analyze(self, portfolio_value: float, exposures: dict[str, float], factor_correlations: dict[str, dict[str, float]]) -> dict:
        results = {}
        for factor, shock in [("equities", -0.10), ("rates", 0.01), ("credit", -0.05), ("vol", 0.20), ("fx", -0.05)]:
            impacted = {}
            for asset_class, exposure in exposures.items():
                corr = factor_correlations.get(asset_class, {}).get(factor, 0)
                impact = exposure * shock * corr
                impacted[asset_class] = impact
            results[factor] = {"shock": shock, "total_impact": sum(impacted.values()), "details": impacted}
        return results
