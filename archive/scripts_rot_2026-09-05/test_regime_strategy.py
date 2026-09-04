"""Test regime -> strategy integration"""
import sys

sys.path.insert(0, '..')
import numpy as np
import pandas as pd
from quant_nanggroe.engine.strategy.regime_strategy import RegimeAdaptiveStrategy

from quant_nanggroe.engine.regime.strategy_selector import (
    RegimeStrategySelector,
)

np.random.seed(42)
dates = pd.date_range('2023-01-01', periods=252, freq='D')
prices = 100 + np.cumsum(np.random.randn(252) * 0.5)
df = pd.DataFrame({
    'close': prices, 'high': prices * 1.02,
    'low': prices * 0.98, 'open': prices,
}, index=dates)

selector = RegimeStrategySelector()
result = selector.select_strategy("bull_trend", 0.8, [])
print(f"Bull trend: {result.primary_strategy.name}, risk={result.risk_multiplier}")

kelly = selector.adjust_kelly_for_regime(0.5, "high_volatility", 0.8)
print(f"Adjusted Kelly (high_vol): {kelly}")

import asyncio


async def test():
    strat = RegimeAdaptiveStrategy()
    result = await strat.analyze(df)
    print(f"Detected regime: {result['regime']}")
    print(f"Recommended: {result['recommended_strategy']}")
    print(f"Risk multiplier: {result['risk_multiplier']}")
    print(f"Kelly adjustment: {result['kelly_adjustment']}")

asyncio.run(test())
print("TEST PASSED")
