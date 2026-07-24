import sys, time
sys.path.insert(0, 'E:/trading')
from strategy_fixes import apply_fixes
apply_fixes()
from backtest_pipeline import get_historical, backtest
from strategy_registry import get_strategy

df = get_historical('EURUSD', days=365, tf='M15')
print(f'{len(df)} bars loaded')

# Test diverse combos with just backtest
test_combos = [
    (16, 5, 13, 1.3),
    (16, 5, 21, 1.3),
    (24, 8, 21, 1.3),
    (24, 10, 30, 1.3),
    (32, 12, 30, 1.3),
    (32, 15, 50, 1.3),
]

for rp, fe, se, vm in test_combos:
    lb = max(8, rp-4)
    t0 = time.time()
    strat = get_strategy('QuarterlyTheoryStrategy', lookback=lb, range_period=rp, fast_ema=fe, slow_ema=se, volume_mult=vm)
    result = strat.generate_signals(df)
    n = (result['entry'] != 0).sum()
    bt, _, _ = backtest(df, strat)
    dt = time.time() - t0
    print(f'rp={rp:2d} fe={fe:2d} se={se:2d}: entries={n:4d} ret={bt["return_pct"]:+.2f}% SR={bt["sharpe"]:.3f} DD={bt["max_drawdown"]:.1f}% [{dt:.1f}s]')
