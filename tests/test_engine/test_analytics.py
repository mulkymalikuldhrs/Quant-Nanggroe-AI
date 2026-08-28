"""Unit tests for performance analytics (engine/analytics)."""

from __future__ import annotations

import numpy as np

from quant_nanggroe.engine.analytics import (
    PerformanceMetrics,
    compute_metrics,
    rolling_sharpe,
)
from quant_nanggroe.engine.analytics.metrics import (  # ponytail: not all funcs re-exported by package __init__
    benchmark_returns,
    strategy_comparison,
)


class TestComputeMetrics:
    def test_basic_returns(self):
        m = compute_metrics([0.01, -0.005, 0.02, 0.015], periods_per_year=252)
        assert isinstance(m, PerformanceMetrics)
        assert m.sharpe != 0.0
        assert m.max_drawdown <= 0.0
        assert m.total_return > 0

    def test_constant_returns(self):
        m = compute_metrics([0.001] * 100)
        assert m.annualized_vol < 0.001

    def test_too_few_returns(self):
        m = compute_metrics([0.01])
        assert isinstance(m, PerformanceMetrics)
        assert m.sharpe == 0.0

    def test_with_benchmark(self):
        returns = np.array([0.01, -0.01, 0.02, -0.005, 0.015])
        bm = np.array([0.008, -0.009, 0.018, -0.004, 0.012])
        m = compute_metrics(returns, benchmark_returns=bm)
        assert m.alpha is not None
        assert m.beta is not None
        assert m.information_ratio is not None

    def test_with_trades(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}]
        returns = [0.01, -0.005, 0.02]
        m = compute_metrics(returns, trades=trades)
        assert m.win_rate == 2 / 3
        assert m.profit_factor > 0
        assert m.count_trades == 3

    def test_to_dict_no_trades_key(self):
        m = compute_metrics([0.01, -0.005, 0.02], periods_per_year=252)
        d = m.to_dict()
        assert "trades" not in d
        assert isinstance(d["sharpe"], float)


class TestRollingSharpe:
    def test_basic(self):
        returns = np.random.randn(300) * 0.02
        rs = rolling_sharpe(returns, window=252)
        assert len(rs) == 49
        assert np.all(np.isfinite(rs))

    def test_too_short(self):
        rs = rolling_sharpe(np.array([0.01] * 10), window=252)
        assert len(rs) == 0


class TestStrategyComparison:
    def test_side_by_side(self):
        df = strategy_comparison(
            {"a": np.array([0.01, -0.005, 0.02]), "b": np.array([0.02, 0.0, -0.01])}
        )
        assert list(df.columns) == ["a", "b"]
        assert "sharpe" in df.index


class TestBenchmarkReturns:
    def test_unavailable_gracefully(self):
        # No network in CI — must return None, not raise
        assert benchmark_returns("SPY", "2099-01-01", "2099-02-01") is None
