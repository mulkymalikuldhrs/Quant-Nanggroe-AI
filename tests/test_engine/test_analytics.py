"""Unit tests for performance analytics (engine/analytics)."""

from __future__ import annotations

import numpy as np
import pytest

from quant_nanggroe.engine.analytics import compute_metrics, rolling_sharpe, PerformanceMetrics


class TestComputeMetrics:
    def test_basic_returns(self):
        returns = [0.01, -0.005, 0.02, 0.015]
        m = compute_metrics(returns, periods_per_year=252)
        assert isinstance(m, PerformanceMetrics)
        assert m.sharpe != 0.0
        assert m.max_drawdown <= 0.0

    def test_constant_returns(self):
        returns = [0.001] * 100
        m = compute_metrics(returns)
        assert m.annualized_vol < 0.001  # near zero vol

    def test_with_benchmark(self):
        returns = np.array([0.01, -0.01, 0.02, -0.005, 0.015])
        bm = np.array([0.008, -0.009, 0.018, -0.004, 0.012])
        m = compute_metrics(returns, benchmark_returns=bm)
        assert m.alpha is not None
        assert m.beta is not None

    def test_with_trades(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}]
        returns = [0.01, -0.005, 0.02]
        m = compute_metrics(returns, trades=trades)
        assert m.win_rate == 2 / 3
        assert m.profit_factor > 0


class TestRollingSharpe:
    def test_basic(self):
        returns = np.random.randn(300) * 0.02
        rs = rolling_sharpe(returns, window=252)
        assert len(rs) == 49  # 300 - 252 + 1
        assert np.all(np.isfinite(rs))

    def test_too_short(self):
        returns = np.array([0.01] * 10)
        rs = rolling_sharpe(returns, window=252)
        assert len(rs) == 0
