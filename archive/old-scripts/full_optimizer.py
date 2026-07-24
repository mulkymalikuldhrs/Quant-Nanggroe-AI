"""
Full Optimizer — optimize & test SEMUA strategi di SEMUA style
MSNR, SMC, MeanRev, Fibo, EMAADX, Wyckoff — cari parameter terbaik
"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from strategy_registry import list_strategies, get_strategy
from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision
import MetaTrader5 as mt5

log = logging.getLogger('optimizer')

# Parameter grids untuk setiap strategi
PARAM_GRIDS = {
    "MSNRStrategy": [
        {"lookback": l, "breakout_mult": m}
        for l in [10, 15, 20, 30, 40, 50]
        for m in [1.2, 1.5, 2.0]
    ],
    "SMCStrategy": [
        {"bos_period": p}
        for p in [5, 8, 10, 15, 20, 30]
    ],
    "MeanReversionStrategy": [
        {"k_period": k, "d_period": d, "oversold": os, "overbought": ob}
        for k in [10, 14, 20]
        for d in [3, 5]
        for os, ob in [(20,80), (25,75), (30,70)]
    ],
    "FiboStrategy": [
        {"lookback": l}
        for l in [10, 20, 30, 50]
    ],
    "EMAADXStrategy": [
        {"fast": f, "slow": s, "adx_threshold": t}
        for f, s in [(5,13), (8,21), (12,26), (20,50)]
        for t in [20, 25, 30]
    ],
    "AlgebraStrategy": [
        {"window": w, "entry_z": z}
        for w in [10, 20, 30, 50]
        for z in [1.5, 2.0, 2.5, 3.0]
    ],
    "QuarterlyTheoryStrategy": [{}],  # no params, just test
    "AMDXStrategy": [
        {"lookback": l}
        for l in [5, 8, 13, 21]
    ],
    "WyckoffStrategy": [
        {"lookback": l, "volume_mult": v}
        for l in [30, 40, 50]
        for v in [1.2, 1.3, 1.5]
    ],
}

def optimize_strategy(name, df):
    """Cari parameter terbaik untuk 1 strategi"""
    params_list = PARAM_GRIDS.get(name, [{}])
    best = None
    
    for idx, params in enumerate(params_list):
        try:
            strat = get_strategy(name, **params)
            bt, _, _ = backtest(df, strat)
            wf = walk_forward(df, strat, folds=5)
            gate = gate_decision(wf)
            
            # Score: weighted by Sharpe + return, with gate bonus
            score = bt['sharpe'] * 10 + bt['return_pct'] * 0.1
            if gate['pass']: score += 50  # big bonus for passing gate
            
            if best is None or score > best['score']:
                best = {
                    "params": params, "score": round(score, 1),
                    "bt_ret": bt['return_pct'], "bt_sr": bt['sharpe'],
                    "wf_ret": wf['avg_return_pct'], "wf_sr": wf['avg_sharpe'],
                    "gate": gate['pass'], "dd": bt['max_drawdown'],
                }
            log.info(f"  [{idx+1}/{len(params_list)}] {name} {params}: SR={bt['sharpe']:.2f} Ret={bt['return_pct']:.1f}% Gate={'✅' if gate['pass'] else '❌'} Score={score:.0f}")
        except Exception as e:
            log.warning(f"  [{idx+1}/{len(params_list)}] {name} {params}: ERROR {e}")
    
    return best

def main():
    log.info("═══ FULL OPTIMIZER — ALL STRATEGIES ═══")
    
    df = get_historical("EURUSD", 365, "M15")
    if df is None: log.error("No data"); return
    log.info(f"Data: {len(df)} bars")
    
    all_best = {}
    for name in list_strategies():
        log.info(f"\n📊 Optimizing {name}...")
        best = optimize_strategy(name, df)
        all_best[name] = best
        if best:
            status = "✅" if best['gate'] else "❌"
            log.info(f"   BEST: {status} Score={best['score']} SR={best['bt_sr']:.2f} Ret={best['bt_ret']:.1f}% Params={best['params']}")
    
    print("\n" + "="*70)
    print("🏆 STRATEGY RANKING (Optimized)")
    print("="*70)
    print(f"{'Strategy':<20} {'Score':<8} {'Sharpe':<8} {'Ret%':<8} {'Gate':<6} {'Params'}")
    print("-"*70)
    ranked = sorted(all_best.items(), key=lambda x: x[1]['score'] if x[1] else 0, reverse=True)
    for name, b in ranked:
        if b:
            print(f"{name:<20} {b['score']:<8} {b['bt_sr']:<8} {b['bt_ret']:<8} {'✅' if b['gate'] else '❌':<6} {str(list(b['params'].values())[:3])}")
    print("="*70)
    
    # Yang lolos gate
    passing = [(n,b) for n,b in ranked if b and b['gate']]
    if passing:
        print(f"\n✅ STRATEGI LOLOS GATE ({len(passing)}):")
        for n,b in passing:
            print(f"   {n}: params={b['params']} Sharpe={b['bt_sr']:.2f} WF={b['wf_ret']:.1f}%")
    else:
        print("\n❌ TIDAK ADA lolos gate — perlu fine-tuning lebih lanjut")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    main()
