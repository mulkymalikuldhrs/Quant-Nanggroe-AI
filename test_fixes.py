"""
Focused test harness for fixed strategies.
Tests each strategy on EURUSD M15 365d with multiple param configs.
"""
import sys, json, logging
from pathlib import Path

SRC = Path(r'E:/trading')
sys.path.insert(0, str(SRC))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('test_fixes')

from strategy_fixes import apply_fixes
apply_fixes()

from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision
from strategy_registry import get_strategy

log.info("📥 Loading EURUSD M15 365d from MT5...")
df = get_historical("EURUSD", days=365, tf="M15")
if df is None:
    log.error("❌ Cannot load data — MT5 not available!")
    sys.exit(1)
log.info(f"✅ Loaded {len(df)} bars")

# ── MSNRStrategy ──
log.info(f"\n{'='*60}")
log.info("📊 MSNRStrategy — S/R reaction with RSI")

msnr_params = [
    {"lookback": 16, "rsi_period": 10, "rsi_low": 30, "rsi_high": 70, "trend_ema": 80},
    {"lookback": 48, "rsi_period": 21, "rsi_low": 40, "rsi_high": 60, "trend_ema": 200},
]

best_msnr = None
for params in msnr_params:
    strat = get_strategy('MSNRStrategy', **params)
    bt, trades, equity = backtest(df, strat, initial_capital=1000)
    wf = walk_forward(df, strat, folds=5)
    gate = gate_decision(wf)
    log.info(f"\n  {params}")
    log.info(f"  BT:  Ret={bt['return_pct']:+.2f}% SR={bt['sharpe']:.3f} DD={bt['max_drawdown']:.2f}%")
    log.info(f"  WF:  Ret={wf['avg_return_pct']:+.2f}% SR={wf['avg_sharpe']:.3f} DD={wf['avg_max_dd_pct']:.2f}%")
    log.info(f"  Gate: {'✅ PASS' if gate['pass'] else '❌ FAIL'} — {gate['reason']}")
    if gate['pass'] and (best_msnr is None or wf['avg_sharpe'] > best_msnr['sharpe']):
        best_msnr = {"params": params, "sharpe": wf['avg_sharpe'], "ret": wf['avg_return_pct'], "dd": wf['avg_max_dd_pct']}

if best_msnr:
    log.info(f"\n  🏆 MSNR: Params={best_msnr['params']} — SR={best_msnr['sharpe']:.3f} Ret={best_msnr['ret']:+.2f}% DD={best_msnr['dd']:.2f}%")
else:
    log.info("\n  ❌ No MSNR config passes gate")

# ── SMCStrategy ──
log.info(f"\n{'='*60}")
log.info("📊 SMCStrategy — swing, BOS/CHoCH, OB, FVG")

smc_params = [
    {"swing_period": 7, "bos_confirmation_bars": 2, "ob_lookback": 15},
]

best_smc = None
for params in smc_params:
    strat = get_strategy('SMCStrategy', **params)
    bt, trades, equity = backtest(df, strat, initial_capital=1000)
    wf = walk_forward(df, strat, folds=5)
    gate = gate_decision(wf)
    log.info(f"\n  {params}")
    log.info(f"  BT:  Ret={bt['return_pct']:+.2f}% SR={bt['sharpe']:.3f} DD={bt['max_drawdown']:.2f}%")
    log.info(f"  WF:  Ret={wf['avg_return_pct']:+.2f}% SR={wf['avg_sharpe']:.3f} DD={wf['avg_max_dd_pct']:.2f}%")
    log.info(f"  Gate: {'✅ PASS' if gate['pass'] else '❌ FAIL'} — {gate['reason']}")
    if gate['pass'] and (best_smc is None or wf['avg_sharpe'] > best_smc['sharpe']):
        best_smc = {"params": params, "sharpe": wf['avg_sharpe'], "ret": wf['avg_return_pct'], "dd": wf['avg_max_dd_pct']}

if best_smc:
    log.info(f"\n  🏆 SMC: Params={best_smc['params']} — SR={best_smc['sharpe']:.3f} Ret={best_smc['ret']:+.2f}% DD={best_smc['dd']:.2f}%")
else:
    log.info("\n  ❌ No SMC config passes gate")

# ── QuarterlyTheoryStrategy ──
log.info(f"\n{'='*60}")
log.info("📊 QuarterlyTheoryStrategy — session momentum + ADX")

qt_params = [
    {"lookback": 10, "range_period": 16, "trend_ema": 50, "atr_mult": 0.5},
    {"lookback": 15, "range_period": 20, "trend_ema": 75, "atr_mult": 0.8},
    {"lookback": 20, "range_period": 24, "trend_ema": 100, "atr_mult": 1.0},
    {"lookback": 25, "range_period": 30, "trend_ema": 150, "atr_mult": 1.2},
    {"lookback": 30, "range_period": 36, "trend_ema": 200, "atr_mult": 1.5},
    {"lookback": 40, "range_period": 48, "trend_ema": 200, "atr_mult": 2.0},
]

best_qt = None
for params in qt_params:
    strat = get_strategy('QuarterlyTheoryStrategy', **params)
    bt, trades, equity = backtest(df, strat, initial_capital=1000)
    wf = walk_forward(df, strat, folds=5)
    gate = gate_decision(wf)
    log.info(f"\n  {params}")
    log.info(f"  BT:  Ret={bt['return_pct']:+.2f}% SR={bt['sharpe']:.3f} DD={bt['max_drawdown']:.2f}%")
    log.info(f"  WF:  Ret={wf['avg_return_pct']:+.2f}% SR={wf['avg_sharpe']:.3f} DD={wf['avg_max_dd_pct']:.2f}%")
    log.info(f"  Gate: {'✅ PASS' if gate['pass'] else '❌ FAIL'} — {gate['reason']}")
    if gate['pass'] and (best_qt is None or wf['avg_sharpe'] > best_qt['sharpe']):
        best_qt = {"params": params, "sharpe": wf['avg_sharpe'], "ret": wf['avg_return_pct'], "dd": wf['avg_max_dd_pct']}

if best_qt:
    log.info(f"\n  🏆 QT: Params={best_qt['params']} — SR={best_qt['sharpe']:.3f} Ret={best_qt['ret']:+.2f}% DD={best_qt['dd']:.2f}%")
else:
    log.info("\n  ❌ No Quarterly config passes gate")

# ── FINAL SUMMARY ──
log.info(f"\n{'='*60}")
log.info("📋 FINAL RESULTS")
log.info('='*60)

all_pass = True
for name, best in [("MSNRStrategy", best_msnr), ("SMCStrategy", best_smc), ("QuarterlyTheoryStrategy", best_qt)]:
    if best:
        log.info(f"  ✅ {name}: Sharpe={best['sharpe']:.3f} Ret={best['ret']:+.2f}% DD={best['dd']:.2f}%")
    else:
        log.info(f"  ❌ {name}: Failed gate")
        all_pass = False

log.info(f"\n{'='*60}")
log.info(f"Overall: {'✅ ALL 3 PASS' if all_pass else '❌ SOME FAILED'}")
log.info('='*60)

results = {
    "MSNRStrategy": best_msnr,
    "SMCStrategy": best_smc,
    "QuarterlyTheoryStrategy": best_qt,
    "all_pass": all_pass
}
result_file = SRC / "results" / "fixes_test_result.json"
result_file.write_text(json.dumps(results, indent=2, default=str))
log.info(f"\nResults saved to {result_file}")
log.info("🏁 Done")
