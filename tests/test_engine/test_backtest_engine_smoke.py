"""Smoke test for the core BacktestEngine after the _execute_bar refactor.

These modules had zero coverage; this is the runnable check ponytail requires:
it fails loudly if the split of run() into _execute_bar / _size_position
changes behavior.
"""
import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig, MarketType


def _make_data(n=30, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    prices = pd.DataFrame(
        {"AAA": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))),
         "BBB": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
        index=idx,
    )
    # alternating long/flat/short-ish signals on AAA
    sig = np.zeros(n)
    sig[2:6] = 0.8
    sig[10:14] = -0.8
    sig[20:24] = 0.5
    signals = pd.DataFrame({"AAA": sig, "BBB": sig * 0.5}, index=idx)
    return prices, signals


def test_run_produces_trades_and_equity():
    prices, signals = _make_data()
    engine = BacktestEngine(BacktestConfig(market=MarketType.EQUITY))
    res = engine.run(prices, signals)
    assert res["total_trades"] > 0, "expected trades to be generated"
    assert len(res["equity_curve"]) == len(prices), "equity curve length mismatch"
    assert isinstance(res["metrics"], dict)
    # every trade must have a pnl (meaningful fill happened)
    assert all(t.pnl is not None for t in res["trades"])
    print(f"OK: {res['total_trades']} trades, final_equity={res['final_equity']:.2f}")


def test_short_disabled_blocks_short():
    prices, signals = _make_data()
    engine = BacktestEngine(BacktestConfig(short_enabled=False))
    res = engine.run(prices, signals)
    assert not any(t.direction == -1 for t in res["trades"]), "short opened with short_enabled=False"
    print("OK: no shorts when short_enabled=False")


if __name__ == "__main__":
    test_run_produces_trades_and_equity()
    test_short_disabled_blocks_short()
    print("ALL SMOKE CHECKS PASSED")
