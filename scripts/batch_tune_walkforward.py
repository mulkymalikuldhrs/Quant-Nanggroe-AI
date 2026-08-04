"""Batch tune + walk-forward ALL engine strategies (fixed 2026-08-04).

Runs in the repaired .venv (PYTHONPATH must be cleared of hermes-agent pollution).
For each of the 81 strategies:
  - Walk-forward validation (rolling, 2y data) -> OOS sharpe per fold
  - Grid param tuning (small default grid) -> top params by sharpe
Results persisted to D:/qna_audit_artifacts/tune_wf_results.json (incremental).
Resilient: per-strategy try/except; records errors, never crashes the batch.
"""
from __future__ import annotations
import json, logging, time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("batch_tune_wf")

OUT = Path("D:/qna_audit_artifacts/tune_wf_results.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

import pandas as pd
import yfinance as yf
from quant_nanggroe.engine.strategies import list_strategies as _list
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
from quant_nanggroe.engine.backtest.auto_tune import AutoTuner, ParameterGrid
from quant_nanggroe.engine.strategies import create_strategy

SYMBOLS = ["EURUSD=X", "BTC-USD", "GBPUSD=X", "ETH-USD"]
PERIOD = "2y"

def fetch(sym):
    try:
        df = yf.Ticker(sym).history(period=PERIOD)
        if df is None or len(df) < 150:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        log.warning("fetch %s failed: %s", sym, e)
        return None

def main():
    names = _list()
    log.info("TOTAL strategies: %d", len(names))
    results = {}
    for name in names:
        rec = {"walk_forward": None, "tune": None, "error": None}
        try:
            strat = create_strategy(name)
            if strat is None:
                rec["error"] = "create_strategy returned None"
                results[name] = rec
                continue
            df = None
            used = None
            for s in SYMBOLS:
                d = fetch(s)
                if d is not None and len(d) >= 200:
                    df, used = d, s
                    break
            if df is None:
                rec["error"] = "no data (yfinance thin/rate-limited)"
                results[name] = rec
                continue
            bpy = 252
            eng = BacktestEngine(BacktestConfig(initial_capital=10000.0, commission_rate=0.001, slippage_bps=5.0, bars_per_year=bpy))
            # WALK FORWARD
            try:
                tw, twt = 120, 60
                if len(df) < tw + twt + 30:
                    tw, twt = 80, 40
                ana = WalkForwardAnalyzer(engine=eng, train_window=tw, test_window=twt, mode="rolling", purge_gap=5, embargo=3)
                wfr = ana.analyze_strategy(prices=df, strategy_class=type(strat), strategy_params={})
                wins = wfr.get("windows", [])
                rec["walk_forward"] = {
                    "symbol": used, "n_folds": len(wins),
                    "oos_sharpe_mean": round(sum(w.out_of_sample_sharpe for w in wins)/len(wins), 4) if wins else None,
                    "is_sharpe_mean": round(sum(w.in_sample_sharpe for w in wins)/len(wins), 4) if wins else None,
                }
            except Exception as e:
                rec["walk_forward"] = {"error": str(e)[:200]}
            # TUNE (small grid on fast/slow periods if strategy accepts them)
            try:
                grid = ParameterGrid({
                    "fast_period": [10, 20, 30],
                    "slow_period": [30, 50, 100],
                })
                tuner = AutoTuner(strategy_name=name, param_grid=grid, data=df, n_windows=3)
                res = tuner.tune(top_n=3, verbose=False)
                if res:
                    rec["tune"] = [
                        {"params": r.params, "sharpe": round(r.sharpe, 4), "num_trades": r.num_trades}
                        for r in res
                    ]
            except Exception as e:
                rec["tune"] = {"error": str(e)[:200]}
            log.info("DONE %s wf_folds=%s oos=%s tune=%s", name,
                     rec["walk_forward"].get("n_folds") if isinstance(rec["walk_forward"], dict) else "err",
                     rec["walk_forward"].get("oos_sharpe_mean") if isinstance(rec["walk_forward"], dict) else "-",
                     "ok" if rec["tune"] and not isinstance(rec["tune"], dict) else "err")
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            log.error("STRATEGY %s FAILED: %s", name, rec["error"])
        results[name] = rec
        OUT.write_text(json.dumps(results, indent=2, default=str))
    n_wf = sum(1 for r in results.values() if isinstance(r.get("walk_forward"), dict) and r["walk_forward"].get("n_folds"))
    n_oos = sum(1 for r in results.values() if isinstance(r.get("walk_forward"), dict) and r["walk_forward"].get("oos_sharpe_mean") not in (None, 0.0))
    log.info("ALL DONE. %d strategies. wf_with_folds=%d, wf_with_positive_oos=%d", len(results), n_wf, n_oos)

if __name__ == "__main__":
    main()
