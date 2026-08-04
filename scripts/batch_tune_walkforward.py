"""Batch tune + walk-forward ALL engine strategies (robust, per-strategy timeout).

Each strategy runs in a separate multiprocessing worker with a hard timeout
(120s) so one slow/broken strategy (e.g. dhaher_system) cannot block the
other 80. Results persisted incrementally to
D:/qna_audit_artifacts/tune_wf_results.json.
"""
from __future__ import annotations
import json, logging, os, time, traceback
from pathlib import Path
from multiprocessing import Process, Queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("batch_tune_wf")

OUT = Path("D:/qna_audit_artifacts/tune_wf_results.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
TIMEOUT = 120  # seconds per strategy

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
        return None

def worker(name: str, q: Queue):
    rec = {"walk_forward": None, "tune": None, "error": None}
    try:
        strat = create_strategy(name)
        if strat is None:
            rec["error"] = "create_strategy returned None"
            q.put(rec); return
        df = None; used = None
        for s in SYMBOLS:
            d = fetch(s)
            if d is not None and len(d) >= 200:
                df, used = d, s; break
        if df is None:
            rec["error"] = "no data"
            q.put(rec); return
        bpy = 252
        eng = BacktestEngine(BacktestConfig(initial_capital=10000.0, commission_rate=0.001, slippage_bps=5.0, bars_per_year=bpy))
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
        try:
            grid = ParameterGrid({"fast_period": [10, 20, 30], "slow_period": [30, 50, 100]})
            tuner = AutoTuner(strategy_name=name, param_grid=grid, data=df, n_windows=3)
            res = tuner.tune(top_n=3, verbose=False)
            if res:
                rec["tune"] = [{"params": r.params, "sharpe": round(r.sharpe, 4), "num_trades": r.num_trades} for r in res]
        except Exception as e:
            rec["tune"] = {"error": str(e)[:200]}
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    q.put(rec)

def main():
    names = _list()
    log.info("TOTAL strategies: %d", len(names))
    results = {}
    for name in names:
        q = Queue()
        p = Process(target=worker, args=(name, q))
        p.start()
        p.join(TIMEOUT)
        if p.is_alive():
            p.terminate(); p.join(5)
            results[name] = {"walk_forward": None, "tune": None, "error": f"timeout >{TIMEOUT}s"}
            log.warning("TIMEOUT %s", name)
        else:
            try:
                results[name] = q.get_nowait()
            except Exception:
                results[name] = {"error": "no result from worker"}
        log.info("DONE %s wf=%s oos=%s tune=%s", name,
                 (results[name].get("walk_forward") or {}).get("n_folds") if isinstance(results[name].get("walk_forward"), dict) else "err",
                 (results[name].get("walk_forward") or {}).get("oos_sharpe_mean") if isinstance(results[name].get("walk_forward"), dict) else "-",
                 "ok" if results[name].get("tune") and not isinstance(results[name].get("tune"), dict) else "err")
        OUT.write_text(json.dumps(results, indent=2, default=str))
    n_wf = sum(1 for r in results.values() if isinstance(r.get("walk_forward"), dict) and r["walk_forward"].get("n_folds"))
    n_oos = sum(1 for r in results.values() if isinstance(r.get("walk_forward"), dict) and r["walk_forward"].get("oos_sharpe_mean") not in (None, 0.0))
    log.info("ALL DONE. %d strategies. wf_with_folds=%d, wf_with_positive_oos=%d", len(results), n_wf, n_oos)

if __name__ == "__main__":
    main()
