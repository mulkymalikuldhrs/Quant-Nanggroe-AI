#!/usr/bin/env python3
"""Grid-search CPCV parameter tuning for top specialists.

For each strategy + symbol, sweeps the param grid, runs full CPCV per combo,
and reports the best params by combo-profit-share then avg OOS Sharpe.

Usage:
  C:\\Python314\\python.exe scripts/run_param_tuning.py --strategy archive_aroon
  C:\\Python314\\python.exe scripts/run_param_tuning.py --all
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
from quant_nanggroe.engine.strategies.registry import StrategyRegistry
from quant_nanggroe.engine.strategies.base import StrategyParameters
import quant_nanggroe.engine.strategies  # noqa: F401

PARAM_GRIDS = {
    "archive_aroon": {
        "period": [14, 21, 25, 35],
        "threshold": [55.0, 65.0, 70.0],
    },
    "archive_amdx": {
        "lookback": [5, 8, 12, 20],
    },
    "archive_ict_ote": {
        "ote_lower": [0.618, 0.65],
        "ote_upper": [0.786, 0.82],
    },
}

SYMBOLS = ["BTC-USD", "EURUSD=X", "GC=F"]


def fetch(sym):
    try:
        df = yf.download(sym, period="2y", interval="1d",
                         progress=False, auto_adjust=True)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    return df if len(df) >= 325 else None


def run_cpcv_once(analyzer, df, cls, params):
    try:
        sp = StrategyParameters(params=dict(params)) if params else None
        res = analyzer.analyze_strategy(prices=df, strategy_class=cls,
                                        strategy_params={"parameters": sp} if sp else {})
        wins = res.get("windows", [])
        sharpes = [float(w.out_of_sample_sharpe) for w in wins]
        n = len(sharpes)
        if not n:
            return {"profit_share": 0.0, "avg_sharpe": 0.0, "n": 0}
        pos = sum(1 for s in sharpes if s > 0)
        return {"profit_share": pos / n, "avg_sharpe": sum(sharpes) / n, "n": n}
    except Exception as e:
        return {"profit_share": 0.0, "avg_sharpe": 0.0, "n": 0, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", type=str, default="")
    ap.add_argument("--symbols", type=str, default=",".join(SYMBOLS))
    args = ap.parse_args()

    targets = [args.strategy] if args.strategy else list(PARAM_GRIDS.keys())
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    engine = BacktestEngine(BacktestConfig(initial_capital=10000, commission_rate=0.001))
    analyzer = WalkForwardAnalyzer(engine=engine, train_window=252, test_window=63,
                                   mode="cpcv", n_groups=6, n_test_groups=2,
                                   purge_gap=5, embargo=3)

    out_path = ROOT / "data" / "tuning_results.json"
    all_results: dict = {}
    if out_path.exists():
        try:
            all_results = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    for name in targets:
        grid = PARAM_GRIDS.get(name)
        if not grid:
            print(f"SKIP {name}: no param grid defined")
            continue
        cls = StrategyRegistry.get(name)
        if cls is None:
            print(f"SKIP {name}: not registered")
            continue

        keys = list(grid.keys())
        combos = list(itertools.product(*(grid[k] for k in keys)))
        total = len(combos) * len(symbols)
        print(f"\n{'='*72}\n{name}: {len(combos)} param sets x {len(symbols)} symbols "
              f"= {total} CPCV runs\n{'='*72}")

        all_results.setdefault(name, {})
        for sym in symbols:
            df = fetch(sym)
            if df is None:
                print(f"  {sym}: no data")
                continue
            print(f"  --- {sym} ---")
            sym_results = []
            for combo in combos:
                params = dict(zip(keys, combo))
                t0 = time.time()
                r = run_cpcv_once(analyzer, df, cls, params)
                r["params"] = params
                sym_results.append(r)
                ps = r["profit_share"]
                ash = r["avg_sharpe"]
                print(f"    {params} -> share={ps:.0%} sharpe={ash:+.3f} [{time.time()-t0:.1f}s]")

            # rank by profit_share desc then avg_sharpe desc
            sym_results.sort(key=lambda x: (x["profit_share"], x["avg_sharpe"]),
                             reverse=True)
            best = sym_results[0]
            baseline_params = {}
            # find baseline (defaults from source)
            defaults = {"archive_aroon": {"period": 25, "threshold": 70.0},
                        "archive_amdx": {"lookback": 8},
                        "archive_ict_ote": {"ote_lower": 0.618, "ote_upper": 0.786}}
            base_p = defaults.get(name, {})
            base_result = next((r for r in sym_results if r["params"] == base_p), None)

            all_results[name][sym] = {
                "best_params": best["params"],
                "best_profit_share": round(best["profit_share"], 4),
                "best_avg_sharpe": round(best["avg_sharpe"], 4),
                "baseline_params": base_p,
                "baseline_profit_share": round(base_result["profit_share"], 4) if base_result else None,
                "baseline_avg_sharpe": round(base_result["avg_sharpe"], 4) if base_result else None,
                "improved": (best["profit_share"] > (base_result["profit_share"] if base_result else 0)),
                "all_results": [{"params": r["params"],
                                  "share": round(r["profit_share"], 4),
                                  "sharpe": round(r["avg_sharpe"], 4)}
                                 for r in sym_results],
            }
            print(f"    BEST: {best['params']} share={best['profit_share']:.0%} "
                  f"sharpe={best['avg_sharpe']:+.3f}"
                  f" (baseline: {base_result['profit_share']:.0%}" +
                  f"/{base_result['avg_sharpe']:+.3f})" if base_result else ")")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
        print(f"  persisted -> {out_path}")

    # final summary
    print(f"\n=== TUNING SUMMARY ===")
    for name, per_sym in all_results.items():
        if name not in targets:
            continue
        for sym, d in per_sym.items():
            imp = d.get("improved")
            mark = "+" if imp else "="
            print(f"  {name} {sym}: best={d['best_params']} "
                  f"share={d['best_profit_share']:.0%} sharpe={d['best_avg_sharpe']:+.3f} "
                  f"[{mark}] baseline={d.get('baseline_profit_share')}%")


if __name__ == "__main__":
    main()
