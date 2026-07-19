"""
Wyckoff Optimizer — fine-tune parameter untuk Sharpe > 2.0
Testing: lookback 10-50, volume_mult 1.2-2.0
"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from strategy_registry import WyckoffStrategy
from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

df = get_historical("EURUSD", 365, "M15")
if df is None: exit()

best = None
for lb in [10, 15, 20, 25, 30, 40, 50]:
    for vm in [1.2, 1.3, 1.5, 1.8, 2.0]:
        strat = WyckoffStrategy(lookback=lb, volume_mult=vm)
        bt, _, _ = backtest(df, strat)
        wf = walk_forward(df, strat, folds=5)
        gate = gate_decision(wf)
        print(f"  lb={lb:2d} vm={vm:.1f} | Ret={bt['return_pct']:6.1f}% SR={bt['sharpe']:.3f} WF={wf['avg_return_pct']:6.1f}% WFSR={wf['avg_sharpe']:.3f} Gate={'✅' if gate['pass'] else '❌'}")
        if gate['pass'] and (best is None or wf['avg_sharpe'] > best['wf_sharpe']):
            best = {"lookback": lb, "volume_mult": vm, "bt_ret": bt['return_pct'], "bt_sr": bt['sharpe'], "wf_ret": wf['avg_return_pct'], "wf_sharpe": wf['avg_sharpe']}

if best:
    print(f"\n🏆 BEST: lb={best['lookback']} vm={best['volume_mult']} | Sharpe={best['wf_sharpe']:.3f} WFret={best['wf_ret']:.1f}%")
else:
    print("\n❌ No params pass gate")
