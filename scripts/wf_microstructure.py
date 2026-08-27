"""Walk-forward harness for the 10 implanted microstructure strategies.

Ponytail: reuses WalkForwardAnalyzer.analyze_strategy (real engine, no TradingView MCP).
Fetches real OHLCV via yfinance_loader (free, no key). One pass = deploy decision per strategy.
"""
from __future__ import annotations

import os
import sys

# ponytail: repo root on sys.path (PYTHONPATH="" strips it for clean subprocess)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta  # noqa: E402

import pandas as pd  # noqa: E402  (used in __main__ + _real_ohlcv)

from quant_nanggroe.engine.backtest.engine import BacktestEngine  # noqa: E402
from quant_nanggroe.engine.backtest.loaders.yfinance_loader import YFinanceLoader  # noqa: E402
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer  # noqa: E402
from quant_nanggroe.engine.strategy.strategies import new_proposals as np_mod  # noqa: E402

# (symbol, yfinance_interval, train_bars, test_bars)
CONFIGS = [
    ("BTC-USD", "1h", 400, 80),
    ("ETH-USD", "1h", 400, 80),
    ("SOL-USD", "1h", 400, 80),
]

# every concrete Strategy subclass from new_proposals (skip abstract BaseStrategy)
STRATS = [getattr(np_mod, n) for n in dir(np_mod)
           if isinstance(getattr(np_mod, n), type)
           and n.endswith("Strategy")
           and getattr(np_mod, n) is not np_mod.BaseStrategy
           and not getattr(np_mod, n, object).__abstractmethods__]


def _real_ohlcv(symbol: str, interval: str) -> object:
    end = datetime.now()
    start = end - timedelta(days=400)
    loader = YFinanceLoader()
    data = loader.fetch([symbol], start.strftime("%Y-%m-%d"),
                        end.strftime("%Y-%m-%d"), interval=interval)
    df = data.get(symbol)
    if df is None or getattr(df, "empty", True):
        return None
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    return df


def main() -> int:
    engine = BacktestEngine()
    for sym, interval, tw, tew in CONFIGS:
        prices = _real_ohlcv(sym, interval)
        if prices is None:
            print(f"SKIP {sym}: no data")
            continue
        analyzer = WalkForwardAnalyzer(engine, train_window=tw, test_window=tew,
                                       mode="rolling", purge_gap=5, embargo=2)
        print(f"\n=== {sym} ({interval}) | {len(prices)} bars ===")
        for cls in STRATS:
            try:
                res = analyzer.analyze_strategy(prices, cls)
            except Exception as exc:  # ponytail: one bad strat must not kill the loop
                print(f"  {cls.__name__:28s} ERROR {exc!r}")
                continue
            agg = res.get("aggregate", {}) or {}
            oos_ret = agg.get("avg_oos_return") or 0.0
            oos_sh = agg.get("avg_oos_sharpe") or 0.0
            verdict = "KEEP" if oos_ret > 0 and oos_sh > 0 else "DROP"
            print(f"  {cls.__name__:28s} OOS_ret={oos_ret:+.2%} "
                  f"OOS_sharpe={oos_sh:+.2f} -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
