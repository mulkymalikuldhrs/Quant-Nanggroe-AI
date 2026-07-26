"""
Dhaher System v1.0 — Full Backtest Pipeline
Milestone 2: Walk-Forward 5-Fold + Gate Check
"""
import sys, json, logging
from pathlib import Path
from datetime import datetime

SRC = Path(r'E:/trading')
sys.path.insert(0, str(SRC))

RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('bt')

# ── Import pipeline components ──
from backtest_pipeline import get_historical, backtest, walk_forward, gate_decision

# ── Import DhaherSystem ──
sys.path.insert(0, str(SRC / 'strategies'))
import strategies.dhaher_system
from quant_nanggroe.engine.strategy.strategies import get_strategy

def run():
    log.info("═══════════════════════════════════════")
    log.info("  DHAHER SYSTEM v1.0 — FULL BACKTEST  ")
    log.info("═══════════════════════════════════════")

    symbol = "EURUSD"
    log.info(f"📡 Loading {symbol} data (365 days, M15)...")
    df = get_historical(symbol, days=365, tf="M15")
    if df is None:
        log.error("❌ Data unavailable")
        return None

    log.info(f"📊 Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")

    # ── Strategy instances ──
    strategies_to_test = [
        ("DhaherSystem (default)", get_strategy('DhaherSystem')),
        ("DhaherSystem (aggro)", get_strategy('DhaherSystem', lookback=15, atr_mult=1.2, rr_min=1.5)),
        ("DhaherSystem (conservative)", get_strategy('DhaherSystem', lookback=30, atr_mult=2.0, rr_min=3.0)),
    ]

    best = None
    all_results = []

    for name, strat in strategies_to_test:
        log.info(f"\n📊 Testing: {name}")
        
        # Full backtest
        bt, trades, equity = backtest(df, strat, initial_capital=1000)
        
        # Walk-forward 5-fold
        wf = walk_forward(df, strat, folds=5)
        
        # Gate evaluation
        gate = gate_decision(wf)
        
        entry = {
            "name": name,
            "backtest": bt,
            "walkforward": wf,
            "gate": gate,
            "trades_count": len(trades),
        }
        all_results.append(entry)

        status = "✅ LOLOS" if gate['pass'] else "❌ GAGAL"
        log.info(f"\n   {status}")
        log.info(f"   Return: {bt['return_pct']}% | Sharpe: {bt['sharpe']} | DD: {bt['max_drawdown']}%")
        log.info(f"   WF Avg Return: {wf['avg_return_pct']}% | WF Sharpe: {wf['avg_sharpe']} | WF DD: {wf['avg_max_dd_pct']}%")
        log.info(f"   Win Rate: {bt['win_rate']}% | Trades: {bt['total_trades']}")
        
        for check, msg in gate.get('checks', []):
            log.info(f"   Gate: {'✅' if check else '❌'} {msg}")
        
        if gate['pass'] and (best is None or wf['avg_sharpe'] > best['walkforward']['avg_sharpe']):
            best = {"name": name, "strategy": strat, "backtest": bt, "walkforward": wf, "gate": gate}

    # ── Summary ──
    log.info("\n" + "═" * 55)
    log.info("  BACKTEST SUMMARY")
    log.info("═" * 55)
    
    if best:
        log.info(f"🏆 BEST: {best['name']}")
        log.info(f"   Return: {best['backtest']['return_pct']}%")
        log.info(f"   Sharpe: {best['backtest']['sharpe']}")
        log.info(f"   WF Sharpe: {best['walkforward']['avg_sharpe']}")
        log.info(f"   Max DD: {best['backtest']['max_drawdown']}%")
        log.info(f"   Win Rate: {best['backtest']['win_rate']}%")
        log.info(f"   Gate: {'✅ LOLOS' if best['gate']['pass'] else '❌ GAGAL'}")
    else:
        log.info("❌ No strategy passed the gate")
        for r in all_results:
            log.info(f"   {r['name']}: Gate={'✅' if r['gate']['pass'] else '❌'}")

    # ── Save results ──
    report = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "strategies_tested": len(strategies_to_test),
        "all_results": all_results,
        "best": best,
    }
    report_file = RESULT / f"dhaher_backtest_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"📁 Report saved: {report_file}")

    return report

if __name__ == "__main__":
    report = run()
    if report:
        print("\n=== FINAL RESULT ===")
        best = report.get("best")
        if best:
            wf = best['walkforward']
            bt = best['backtest']
            print(f"🏆 Best config: {best['name']}")
            print(f"   Return: {bt['return_pct']}%")
            print(f"   Sharpe: {bt['sharpe']}")
            print(f"   WF Avg Sharpe: {wf['avg_sharpe']}")
            print(f"   Max DD: {bt['max_drawdown']}%")
            print(f"   Gate: {'✅ LOLOS — Siap wire ke Hedge Fund' if best['gate']['pass'] else '❌ GAGAL — Tidak lolos syarat'}")
        else:
            print("❌ Tidak ada strategi lolos")
