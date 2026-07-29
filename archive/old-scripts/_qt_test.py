import sys, logging, time
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, 'E:/trading')
from strategy_fixes import apply_fixes
apply_fixes()
from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision
from strategy_registry import get_strategy

df = get_historical('EURUSD', days=365, tf='M15')
print(f'Bars: {len(df)}')

# Quick scan: test all combos with just backtest (no walkforward)
results = []
for rp in [16, 24, 32, 48]:
    for fe in [8, 10, 12]:
        for se in [21, 30, 50]:
            if fe >= se:
                continue
            strat = get_strategy('QuarterlyTheoryStrategy', lookback=rp-4, range_period=rp, fast_ema=fe, slow_ema=se, volume_mult=1.2)
            result = strat.generate_signals(df)
            n = (result['entry'] != 0).sum()
            if n > 20:  # Only test strategies with enough signals
                bt, _, _ = backtest(df, strat)
                results.append((rp, fe, se, n, bt['return_pct'], bt['sharpe'], bt['max_drawdown']))
                print(f'rp={rp:2d} fe={fe:2d} se={se:2d}: entries={n:4d} ret={bt["return_pct"]:+.2f}% SR={bt["sharpe"]:.3f} DD={bt["max_drawdown"]:.1f}%')

# Sort by Sharpe
results.sort(key=lambda x: x[5], reverse=True)
print(f'\n{"="*60}')
print(f'Top 5 by Sharpe:')
for rp, fe, se, n, ret, sr, dd in results[:5]:
    print(f'  rp={rp} fe={fe} se={se}: SR={sr:.3f} Ret={ret:+.2f}% DD={dd:.1f}% entries={n}')

# Test top 3 with walkforward
print(f'\n{"="*60}')
print(f'Testing top 3 with walkforward...')
for rp, fe, se, n, ret, sr, dd in results[:3]:
    strat = get_strategy('QuarterlyTheoryStrategy', lookback=rp-4, range_period=rp, fast_ema=fe, slow_ema=se, volume_mult=1.2)
    wf = walk_forward(df, strat, folds=5)
    gate = gate_decision(wf)
    status = '✅' if gate['pass'] else '❌'
    print(f'{status} rp={rp} fe={fe} se={se}: WF_ret={wf["avg_return_pct"]:+.2f}% WF_SR={wf["avg_sharpe"]:.3f} DD={wf["avg_max_dd_pct"]:.1f}% — {gate["reason"]}')
