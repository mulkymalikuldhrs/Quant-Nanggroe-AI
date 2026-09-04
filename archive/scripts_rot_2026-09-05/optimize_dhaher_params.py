"""Grid search over DhaherSystem parameters to maximize Sharpe while passing gate.
Uses real EURUSD data via yfinance and DhaherSystem's built-in SL/TP.
"""
import itertools
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('opt_dhaher')

# Import real DhaherSystem from quant_nanggroe
from quant_nanggroe.engine.strategy.backtest_adapter import BacktestConfig, backtest

# Also import the pipeline gate
from quant_nanggroe.engine.strategies.dhaher_system import DhaherSystem


def run_grid():
    # Parameter grid
    lookbacks = [14, 17, 20, 23, 25, 28, 30]
    atr_mults = [1.0, 1.2, 1.3, 1.5, 1.8, 2.0]
    rr_mins = [2.0, 2.5, 3.0, 3.5]
    min_confluences = [2, 3, 4]

    configs = []
    for lb, am, rr, mc in itertools.product(lookbacks, atr_mults, rr_mins, min_confluences):
        configs.append((lb, am, rr, mc))

    log.info(f"Total configs: {len(configs)}")

    symbol = "EURUSD"
    log.info(f"Loading {symbol} data...")
    try:
        import yfinance as yf
        df = yf.download(symbol, period="720d", interval="15m", auto_adjust=False)
        if df.empty:
            log.error("No data from yfinance"); return None
        # Flatten multi-level columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
    except Exception as e:
        log.error(f"yfinance failed: {e}")
        # fallback: use backtest_pipeline's get_historical
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from backtest_pipeline import get_historical
            df = get_historical(symbol, days=365, tf="M15")
        except Exception as e2:
            log.error(f"Fallback also failed: {e2}"); return None

    log.info(f"Data: {len(df)} bars, {df.index[0]} to {df.index[-1]}")

    results = []
    for idx, (lb, am, rr, mc) in enumerate(configs):
        try:
            strat = DhaherSystem(
                parameters=None, lookback=lb, atr_mult=am, rr_min=rr,
                min_confluence=mc, use_adx_filter=True, adx_threshold=20,
            )
            bt_config = BacktestConfig(
                symbol=symbol, strategy=strat,
                initial_capital=1000.0,
                start_date=None, end_date=None,
            )
            result = backtest(bt_config)
            wf = result.get("walk_forward", {})
            sharpe = wf.get("avg_sharpe", result.get("sharpe", 0))
            ret = wf.get("avg_return_pct", result.get("return_pct", 0))
            dd = wf.get("avg_max_dd_pct", result.get("max_dd", 999))

            row = {
                "lookback": lb, "atr_mult": am, "rr_min": rr, "min_confluence": mc,
                "sharpe": round(sharpe, 3), "return_pct": round(ret, 2),
                "max_dd": round(dd, 2),
                "pass": sharpe > 0.5 and ret > 0 and dd > -25,
            }
            results.append(row)
            if idx % 50 == 0:
                log.info(f"  [{idx}/{len(configs)}] lb={lb} am={am} rr={rr} mc={mc} SR={sharpe:.3f} R={ret:+.2f}% DD={dd:.2f}%")
        except Exception as e:
            results.append({
                "lookback": lb, "atr_mult": am, "rr_min": rr, "min_confluence": mc,
                "sharpe": 0, "return_pct": 0, "max_dd": 0, "error": str(e),
            })

    # Sort by sharpe desc, keep passing configs
    passing = [r for r in results if r.get("pass")]
    passing.sort(key=lambda x: x["sharpe"], reverse=True)

    best = passing[0] if passing else max(results, key=lambda x: x.get("sharpe", 0))

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_configs": len(configs),
        "passing_count": len(passing),
        "best": best,
        "top_10": passing[:10] if len(passing) >= 10 else passing,
    }

    out = Path(__file__).parent.parent / "results" / f"dhaher_opt_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    log.info(f"Report saved to {out}")

    return report


if __name__ == "__main__":
    r = run_grid()
    if r:
        print(f"\nBEST: {r['best']}")
        print(f"PASSING: {r['passing_count']}/{r['total_configs']}")
