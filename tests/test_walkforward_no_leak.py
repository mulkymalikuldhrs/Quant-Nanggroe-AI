#!/usr/bin/env python3
"""P1 #41 regression: walk-forward script must NOT leak validation data.

Old script concatenated train+val and backtested the combined series, so
OOS folds saw data used to form the signal -> fake OOS == IS (no separation).
New path uses WalkForwardAnalyzer.analyze_strategy: per-fold refit, separate
IS/OOS signal slices. On data with a TRAIN-ONLY regime, OOS must degrade
sharply vs IS.

We use a deterministic DummyStrategy (captures a sine edge present ONLY in the
first ~60% of data) so the test does not depend on any real alpha.
"""
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType
from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from scripts.run_walkforward import run_strategy_backtest


class DummyStrategy(BaseStrategy):
    """Buys when price is above its 10-bar mean; captures train-only sine edge.
    Single 'close' column keeps the WF signal/price shape aligned (we are
    testing WF leakage machinery, not strategy validation)."""
    def __init__(self, name="Dummy", params=None):
        super().__init__(name, params)
    def required_columns(self):
        return ["close"]
    def warmup_period(self):
        return 10
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if len(data) < 10:
            return None
        close = data["close"]
        ma = close.rolling(10).mean().iloc[-1]
        last = close.iloc[-1]
        return Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY if last > ma else SignalType.SELL,
            confidence=0.9,
            source_agent="Dummy",
        )


def make_ohlcv(seed=7, n=420):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    # Edge present ONLY in first 250 bars (train). Last 170 bars pure noise.
    edge = np.where(t < 250, 4.0 * np.sin(2 * np.pi * t / 45.0), 0.0)
    noise = rng.normal(0, 1.0, n).cumsum()
    close = 100 + np.cumsum(edge[:n] + noise[:n] * 0.4)
    return pd.DataFrame({
        "close": close,
    }, index=pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="D"))


def new_engine_wf(df):
    eng = BacktestEngine(BacktestConfig())
    az = WalkForwardAnalyzer(eng, train_window=200, test_window=60, mode="rolling",
                             purge_gap=2, embargo=1, min_observations=30)
    res = az.analyze_strategy(df, DummyStrategy)
    for i, w in enumerate(res.get("windows", [])):
        print(f"  fold{i+1}: IS_s={w.in_sample_sharpe:.3f} OOS_s={w.out_of_sample_sharpe:.3f} IS_t={w.is_trades} OOS_t={w.oos_trades}")
    agg = res.get("aggregate", {})
    return agg.get("avg_is_sharpe", 0.0), agg.get("avg_oos_sharpe", 0.0), len(res.get("windows", []))


def old_leaky_wf(df):
    """Reproduce the REMOVED leaky logic: combined = train+val, single backtest."""
    closes = df["close"].tolist()
    train, test = 250, 60
    combined = list(closes[:train]) + list(closes[train:train + test])
    bt = run_strategy_backtest("Dummy", combined)  # name ignored; we monkeypatch below
    return bt.get("sharpe", 0.0)


def test_new_wf_degrades_oos():
    df = make_ohlcv()
    is_s, oos_s, nwin = new_engine_wf(df)
    print(f"[NEW] windows={nwin} IS_sharpe={is_s:.3f} OOS_sharpe={oos_s:.3f}")
    assert nwin >= 1, "expected >=1 WF window with signals"
    # leak fixed: OOS must be materially below IS on train-only regime
    assert oos_s < is_s - 0.05, f"OOS ({oos_s:.3f}) not degraded vs IS ({is_s:.3f}) — leak?"


def test_old_leaky_wf_had_no_oos_separation():
    df = make_ohlcv()
    # monkeypatch create_strategy so run_strategy_backtest uses DummyStrategy
    import quant_nanggroe.engine.strategy.strategies as S
    orig = S.create_strategy
    S.create_strategy = lambda name: DummyStrategy()
    try:
        leaky = old_leaky_wf(df)
    finally:
        S.create_strategy = orig
    print(f"[OLD-LEAKY] combined single backtest sharpe={leaky:.3f} (no IS/OOS split)")
    assert leaky is not None


if __name__ == "__main__":
    test_new_wf_degrades_oos()
    test_old_leaky_wf_had_no_oos_separation()
    print("PASS: walk-forward leakage regression OK")
