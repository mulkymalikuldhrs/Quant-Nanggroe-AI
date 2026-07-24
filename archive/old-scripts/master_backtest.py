"""
Master Backtest — ALL strategies dari registry + risk module
Backtest → Walk-Forward → Risk Score → Ranking
"""
import sys, json, logging, csv
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

SRC = Path(r'E:/trading')
RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SRC))
from strategy_registry import list_strategies, get_strategy
from risk_module import kelly_fraction, monte_carlo_simulation, performance_metrics, strategy_score
from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('master')

def test_all(symbol="EURUSD", days=365, tf="M15"):
    log.info(f"═══ Master Backtest: {symbol} {tf} {days}d ═══")
    
    df = get_historical(symbol, days, tf)
    if df is None:
        log.error("No data"); return
    
    log.info(f"Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")
    
    results = []
    for name in list_strategies():
        log.info(f"\n📊 Testing {name}...")
        try:
            strat = get_strategy(name)
            bt, trades, eq = backtest(df, strat)
            wf = walk_forward(df, strat, folds=5)
            gate = gate_decision(wf)
            risk = strategy_score(bt, wf)
            
            # Metrics
            perf = performance_metrics(eq)
            mc = monte_carlo_simulation(trades, simulations=1000)
            kelly = kelly_fraction(bt['win_rate']/100, 
                                  max(1, bt.get('return_pct',1)/max(bt.get('closed_trades',1),1)),
                                  max(1, -bt.get('max_drawdown',-10)/max(bt.get('closed_trades',1),1)))
            
            entry = {
                "strategy": name,
                "backtest": bt,
                "walkforward": wf,
                "gate": gate,
                "score": risk,
                "performance": perf,
                "monte_carlo": mc,
                "kelly_fraction": round(kelly, 4),
                "trades": len(trades),
            }
            results.append(entry)
            
            status = "✅" if gate['pass'] else "❌"
            log.info(f"   {status} Ret={bt['return_pct']}% SR={bt['sharpe']} WF={wf['avg_return_pct']}% Score={risk['composite_score']}")
        except Exception as e:
            log.warning(f"   ❌ {name} error: {e}")
    
    return results

def report(results):
    if not results:
        print("\n❌ No results")
        return
    
    # Sort by composite score
    ranked = sorted(results, key=lambda r: r.get('score',{}).get('composite_score',0), reverse=True)
    
    print(f"\n{'='*70}")
    print(f"🏆 STRATEGY RANKING")
    print(f"{'='*70}")
    print(f"{'Rank':<6} {'Strategy':<20} {'Ret%':<8} {'Sharpe':<8} {'WF%':<8} {'Score':<8} {'Gate':<6}")
    print(f"{'-'*70}")
    
    for i, r in enumerate(ranked, 1):
        bt = r['backtest']
        wf = r['walkforward']
        sc = r['score']
        gate = "✅" if r['gate']['pass'] else "❌"
        print(f"{i:<6} {r['strategy']:<20} {bt['return_pct']:<8} {bt['sharpe']:<8} {wf['avg_return_pct']:<8} {sc['composite_score']:<8} {gate:<6}")
    
    print(f"{'='*70}")
    
    # Save
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    file = RESULT / f"master_backtest_{ts}.json"
    # Convert non-serializable
    clean = json.loads(json.dumps(ranked, default=str))
    file.write_text(json.dumps(clean, indent=2))
    print(f"\nSaved: {file}")
    
    # Gate passing strategies
    passing = [r for r in ranked if r['gate']['pass']]
    if passing:
        print(f"\n✅ STRATEGI LOLOS GATE ({len(passing)}):")
        for r in passing:
            print(f"   {r['strategy']}: Score={r['score']['composite_score']} SR={r['backtest']['sharpe']}")
    else:
        print(f"\n❌ TIDAK ADA strategi lolos gate")
        print(f"   Best: {ranked[0]['strategy']} Score={ranked[0]['score']['composite_score']}")

if __name__ == "__main__":
    results = test_all()
    if results:
        report(results)
