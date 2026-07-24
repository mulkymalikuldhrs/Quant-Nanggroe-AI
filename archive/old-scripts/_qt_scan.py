import sys, time
sys.path.insert(0, 'E:/trading')
from strategy_fixes import apply_fixes
apply_fixes()
from backtest_pipeline import get_historical
from strategy_registry import get_strategy

t0 = time.time()
df = get_historical('EURUSD', days=365, tf='M15')
print(f'{len(df)} bars loaded in {time.time()-t0:.1f}s')

# Pass 1: Scan signal counts only
combos = []
for fe in [5, 8, 10, 12, 15]:
    for se in [13, 21, 30, 50]:
        if fe >= se:
            continue
        for rp in [16, 24, 32]:
            lb = max(8, rp - 4)
            strat = get_strategy('QuarterlyTheoryStrategy', lookback=lb, range_period=rp, fast_ema=fe, slow_ema=se, volume_mult=1.3)
            result = strat.generate_signals(df)
            n = (result['entry'] != 0).sum()
            buys = (result['entry'] == 1).sum()
            if n >= 10:
                combos.append((rp, fe, se, n, buys, n-buys))

print(f'\nCombos with >=10 entries: {len(combos)}')
for rp, fe, se, n, b, s in combos:
    print(f'  rp={rp} fe={fe} se={se}: entries={n} (b={b} s={s})')
