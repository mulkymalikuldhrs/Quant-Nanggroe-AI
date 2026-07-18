"""Smoke test — backtest walk-forward pipeline runs headless on synthetic data.

Proves the walk-forward engine is wired and produces OOS results WITHOUT any
network/yfinance dependency. Synthetic OHLCV is generated in-process and a real
BaseStrategy subclass (correct contract) drives signal generation.

Run:
    PYTHONPATH="" python -m pytest tests/test_backtest/test_walkforward_smoke.py -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import unittest

from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType
from quant_nanggroe.types.signals import SignalStrength  # noqa: F401  (kept for clarity)


class _MaCrossStrategy(BaseStrategy):
    """Deterministic synthetic strategy: long when short-MA > long-MA, else short."""

    def __init__(self, name: str = "ma_cross", params: dict | None = None) -> None:
        super().__init__(name=name, params=params or {"short": 3, "long": 8})
        self.short = int(self.params.get("short", 3))
        self.long = int(self.params.get("long", 8))

    def generate_signal(self, data: pd.DataFrame):  # type: ignore[override]
        close = data["close"]
        if len(close) < self.long:
            return None
        ma_s = close.iloc[-self.short :].mean()
        ma_l = close.iloc[-self.long :].mean()
        if ma_s > ma_l:
            return Signal(signal_type=SignalType.BUY, strength=None)
        if ma_s < ma_l:
            return Signal(signal_type=SignalType.SELL, strength=None)
        return None

    def required_columns(self) -> list[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.long


class TestWalkForwardSmoke(unittest.TestCase):
    def _make_prices(self, n: int = 400, seed: int = 7) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        idx = pd.date_range("2023-01-01", periods=n, freq="D")
        rets = rng.normal(0.0005, 0.02, n)
        close = 100 * np.cumprod(1 + rets)
        return pd.DataFrame(
            {
                "open": close * (1 + rng.normal(0, 0.001, n)),
                "high": close * (1 + np.abs(rng.normal(0, 0.003, n))),
                "low": close * (1 - np.abs(rng.normal(0, 0.003, n))),
                "close": close,
                "volume": rng.integers(1_000, 10_000, n).astype(float),
            },
            index=idx,
        )

    def test_analyze_strategy_produces_oos(self) -> None:
        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig

        prices = self._make_prices()
        engine = BacktestEngine(BacktestConfig(initial_capital=100_000))
        wf = WalkForwardAnalyzer(engine, train_window=120, test_window=30, mode="rolling")
        result = wf.analyze_strategy(
            prices, _MaCrossStrategy, strategy_params={}, purge_gap=5, embargo=2
        )
        self.assertIn("windows", result)
        self.assertIn("aggregate", result)
        self.assertGreater(len(result["windows"]), 0, "no walk-forward folds produced")
        oos = result.get("oos_equity_curve")
        self.assertIsInstance(oos, pd.Series)
        self.assertGreater(len(oos), 0, "OOS equity curve empty")


if __name__ == "__main__":
    unittest.main()
