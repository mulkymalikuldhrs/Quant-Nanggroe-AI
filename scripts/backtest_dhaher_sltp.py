#!/usr/bin/env python3
"""QNA WAR PLAN Phase 2 — Real Backtest Validation (Dhaher SL/TP gate).

Reuses the canonical QNA backtest framework (quant_nanggroe/backtest/*):
  - StrategyFactory  -> generates strategy variants (templates + param grids)
  - Backtester        -> pure-python Sharpe/Return/MaxDD engine
  - DataFetcher       -> REAL market data (CoinGecko OHLC, cached on disk)

Walks forward folds per coin, gates each strategy:
  Sharpe > 0.5  AND  total_return > 0%  AND  max_drawdown > -25%
Writes results/gate_status.json. Prints "Backtest: X/200 pass gate".

Ponytail: minimal. RTK: real data, File:line. No synthetic candles.
"""
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKTEST = REPO / "quant_nanggroe" / "backtest"


def _load(modname, fname):
    spec = importlib.util.spec_from_file_location(
        "qna_bt_" + modname, BACKTEST / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bf = _load("backtester", "backtester.py")
sf = _load("factory", "strategy_factory.py")
Backtester, DataFetcher = bf.Backtester, bf.DataFetcher
StrategyFactory = sf.StrategyFactory

N_VARIANTS = 200
GATE = {"sharpe": 0.5, "return": 0.0, "dd": -0.25}
COINS = ["bitcoin", "ethereum", "solana", "binancecoin"]
DAYS = 365
MIN_FOLD_SIZE = 30

# Use only coins with REAL cached OHLC on disk (no network dependency in cron).
_CACHE = REPO / "data" / "hist_cache"
COINS = [c for c in COINS if (_CACHE / f"{c}_{DAYS}d.json").exists()]


def five_folds(candles):
    """Adaptive folds: try N=5,3,2 based on data size."""
    n = len(candles)
    for nf in [5, 3, 2]:
        if n >= nf * MIN_FOLD_SIZE:
            step = n // nf
            folds = [candles[i * step:(i + 1) * step] for i in range(nf)]
            return [f for f in folds if len(f) >= MIN_FOLD_SIZE]
    # Last resort: single fold
    return [candles] if len(candles) >= MIN_FOLD_SIZE else []


def main():
    factory = StrategyFactory()
    variants = factory.generate(max_variants=N_VARIANTS)
    total = len(variants)

    fetcher = DataFetcher()
    coin_data = {}
    for coin in COINS:
        try:
            candles = fetcher.fetch_historical(coin, DAYS)
            if candles and len(candles) >= MIN_FOLD_SIZE:
                coin_data[coin] = candles
                print(f"[data] {coin}: {len(candles)} REAL candles", file=sys.stderr)
        except Exception as e:
            print(f"[data] {coin}: skip ({e})", file=sys.stderr)

    if not coin_data:
        print(f"Backtest: 0/{total} pass gate (NO REAL DATA)")
        return

    bt = Backtester()
    fold_results = {i: [] for i in range(total)}
    for coin, candles in coin_data.items():
        folds = five_folds(candles)
        print(f"[folds] {coin}: {len(folds)} folds from {len(candles)} candles", file=sys.stderr)
        for fold in folds:
            for i, r in enumerate(bt.run_batch(variants, fold)):
                fold_results[i].append(r)

    strategies = []
    passed = 0
    for i, res_list in fold_results.items():
        v = variants[i]
        if not res_list:
            strategies.append({"name": v.name, "template": v.template_name,
                               "sharpe": 0.0, "return": 0.0, "dd": 0.0, "pass": False})
            continue
        mean_sharpe = sum(r.sharpe for r in res_list) / len(res_list)
        mean_ret = sum(r.total_return for r in res_list) / len(res_list)
        min_dd = min(r.max_drawdown for r in res_list)
        ok = (mean_sharpe > GATE["sharpe"] and mean_ret > GATE["return"]
              and min_dd > GATE["dd"])
        passed += 1 if ok else 0
        strategies.append({
            "name": v.name, "template": v.template_name,
            "sharpe": round(mean_sharpe, 4), "return": round(mean_ret, 4),
            "dd": round(min_dd, 4), "pass": ok,
        })

    out = {
        "timestamp": datetime.now().isoformat(),
        "total": total, "passed": passed,
        "gate": {"sharpe_gt": GATE["sharpe"], "return_gt": GATE["return"],
                 "dd_gt": GATE["dd"]},
        "data_source": "coingecko_real_ohlc",
        "coins": list(coin_data.keys()),
        "strategies": strategies,
    }
    res_dir = REPO / "results"
    res_dir.mkdir(exist_ok=True)
    (res_dir / "gate_status.json").write_text(json.dumps(out, indent=2))
    print(f"Backtest: {passed}/{total} pass gate")


if __name__ == "__main__":
    main()