"""Quick test: Kelly → Backtest integration"""
import sys

sys.path.insert(0, '..')

import numpy as np
import pandas as pd

from quant_nanggroe.engine.kelly.backtest_integration import (
    KellyBacktestBridge,
    StrategyKellyMixin,
)

np.random.seed(42)

# Simulate 252 daily returns (1 year)
returns = np.random.normal(0.001, 0.02, 252)
prices_series = 100 * np.exp(np.cumsum(returns))
prices = pd.DataFrame({"ASSET": prices_series}, index=pd.date_range("2024-01-01", periods=252, freq="D"))
returns_series = pd.Series(returns, index=prices.index)

bridge = KellyBacktestBridge(config={"default_fraction": 0.5})

# Test with regime
signals_bull = bridge.compute_signals(prices, returns_series, equity=10000.0, regime="bull")
print(f"Bull regime: generated {len(signals_bull)} Kelly signals")
if signals_bull:
    s = signals_bull[-1]
    print(f"  Raw={s.raw_kelly_fraction:.4f}, Capped={s.capped_fraction:.4f}, "
          f"Conviction={s.conviction:.4f}, Method={s.metadata.get('method')}")

# Test with drawdown regime
signals_dd = bridge.compute_signals(prices, returns_series, equity=10000.0, regime="drawdown")
print(f"Drawdown regime: generated {len(signals_dd)} Kelly signals")
if signals_dd:
    s = signals_dd[-1]
    print(f"  Raw={s.raw_kelly_fraction:.4f}, Capped={s.capped_fraction:.4f}, "
          f"Conviction={s.conviction:.4f}, Method={s.metadata.get('method')}")

# Test with few data points (Bayesian path)
few_prices = prices.iloc[:10]
few_returns = returns_series.iloc[:10]
signals_few = bridge.compute_signals(few_prices, few_returns, equity=10000.0)
print(f"Few samples: generated {len(signals_few)} Kelly signals")
if signals_few:
    s = signals_few[-1]
    print(f"  Raw={s.raw_kelly_fraction:.4f}, Capped={s.capped_fraction:.4f}, "
          f"Conviction={s.conviction:.4f}, Method={s.metadata.get('method')}")

# Test empty data
empty_signals = bridge.compute_signals(pd.DataFrame(), pd.Series(), equity=10000.0)
print(f"Empty data: {len(empty_signals)} signals")

# Test StrategyKellyMixin
class DummyStrategy(StrategyKellyMixin):
    def __init__(self, kelly_config=None):
        super().__init__(kelly_config=kelly_config)

strat = DummyStrategy(kelly_config={"default_fraction": 0.25})
adjusted = strat.adjust_position_size(100.0, prices, returns_series, 10000.0)
print(f"Mixin adjusted size: {adjusted:.2f} (base was 100.0)")

# Test signal_history and reset
print(f"Signal history length: {len(bridge.signal_history)}")
bridge.reset_history()
print(f"After reset: {len(bridge.signal_history)}")

print("\nTEST PASSED")
