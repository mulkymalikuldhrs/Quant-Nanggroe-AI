"""Test stress testing module"""
import sys; sys.path.insert(0, '..')
import numpy as np; import pandas as pd
from quant_nanggroe.engine.stress_testing.monte_carlo import MonteCarloSimulator
from quant_nanggroe.engine.stress_testing.ewhs import EWHSVARCalculator
from quant_nanggroe.engine.stress_testing.historical import HistoricalScenarioAnalyzer

prices = pd.Series(100 * np.exp(np.cumsum(np.random.randn(252) * 0.02)))
sim = MonteCarloSimulator()
result = sim.simulate_gbm(prices, n_simulations=1000, n_days=252)
print(f"MC: VaR95={result.var_95:.4f}, VaR99={result.var_99:.4f}")

returns = np.random.randn(500) * 0.02
ewhs = EWHSVARCalculator()
r = ewhs.compute(pd.Series(returns))
print(f"EWHS: VaR95={r.var_95:.4f}, CVaR95={r.cvar_95:.4f}")

hsa = HistoricalScenarioAnalyzer()
scenarios = hsa.analyze_portfolio({"SPY": 1.0}, {"SPY": pd.Series(np.random.randn(252) * 0.015)})
for s in scenarios:
    print(f"Historical: {s.scenario[:30]}... impact={s.portfolio_impact:.4f}")

print("TEST PASSED")
