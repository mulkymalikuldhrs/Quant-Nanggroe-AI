"""Council follow-up: measure OOS expectancy for top-firing strategies (shadow, no capital).

Runs real WalkForwardAnalyzer.analyze_strategy on yfinance 1h BTC/ETH/SOL, extracts
the v4.5.9 significance-gated aggregate (total_oos_trades, under_sampled, avg_oos_return,
avg_oos_sharpe). Outputs JSON for orchestrator review. No live capital, no orders.

Ponytail: top-15 by firing count only — sufficient to prove edge exists or not.
"""
from __future__ import annotations

import json
import sys
import traceback
import warnings
from pathlib import Path

import yfinance as yf

warnings.filterwarnings("ignore")  # ponytail: silence NaN std noise from pandas, not signal
import glob
import importlib
import os

from quant_nanggroe.engine.backtest.engine import BacktestEngine
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer

TOP = [
    "VortexStrategy", "KalmanFilterStrategy", "MarketMakingStrategy", "HullMAStrategy",
    "ParticleFilterStrategy", "T3Strategy", "EntropyStrategy", "MacroFXStrategy",
    "PCAStrategy", "KaufmanAMAStrategy", "DEMAStrategy", "RiskParityStrategy",
    "DrawdownRegimeStrategy", "TEMAStrategy", "CommodityTrendStrategy",
]
ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]

def load_strategy(cls_name):
    for m in glob.glob("quant_nanggroe/engine/strategy/strategies/*.py"):
        name = os.path.basename(m)[:-3]
        if name in ("base_strategy", "__init__"):
            continue
        mod = importlib.import_module(f"quant_nanggroe.engine.strategy.strategies.{name}")
        if hasattr(mod, cls_name):
            return getattr(mod, cls_name)
    return None

def main():
    eng = BacktestEngine()
    ana = WalkForwardAnalyzer(engine=eng, train_window=300, test_window=200,
                              purge_gap=5, embargo=2, mode="rolling")
    results = {}
    for cls_name in TOP:
        cls = load_strategy(cls_name)
        if cls is None:
            results[cls_name] = {"error": "not found"}
            continue
        per_asset = {}
        for sym in ASSETS:
            try:
                px = yf.download(sym, period="2y", interval="1h",
                                 auto_adjust=True, progress=False)
                px = px[["Open", "High", "Low", "Close", "Volume"]]
                px.columns = [c[0] if isinstance(c, tuple) else c for c in px.columns]
                res = ana.analyze_strategy(px, cls)
                agg = res["aggregate"]
                deg = res.get("degradation_stats", {})
                per_asset[sym] = {
                    "windows": res["n_folds"],
                    "total_oos_trades": agg.get("total_oos_trades", 0),
                    "under_sampled": agg.get("under_sampled", True),
                    # expectancy proxy: avg return PER TRADE (not sum-of-trades fold mean)
                    "avg_oos_return_per_trade": round(agg.get("avg_oos_return_per_trade", 0.0), 5),
                    "avg_oos_sharpe": round(agg.get("avg_oos_sharpe", 0.0), 4),
                    # OOS/IS Sharpe ratio >0.5 pass-rate: separates edge from beta drift
                    "degradation_pass_rate": round(deg.get("pass_rate", 0.0), 3),
                }
            except Exception as e:
                per_asset[sym] = {"error": repr(e)}
        results[cls_name] = per_asset
        print(f"{cls_name}: {json.dumps(per_asset)}", flush=True)
    out = Path("data/council_expectancy.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print("WROTE", out)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
