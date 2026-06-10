"""Tests for Backtesting Engine.

Tests cover:
- Portfolio (position tracking, P&L)
- Execution Simulator (slippage, commission)
- Performance Metrics (Sharpe, Sortino, Max DD)
- Backtest Engine (end-to-end)
- Walk-Forward Analysis
- Monte Carlo Simulation
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_prices():
    """Generate sample price DataFrame."""
    np.random.seed(42)
    n = 252  # 1 year of daily data
    dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
    
    symbols = ["AAPL", "GOOGL"]
    data = {}
    for sym in symbols:
        returns = np.random.normal(0.0005, 0.02, n)
        data[sym] = 100 * np.cumprod(1 + returns)
    
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_signals(sample_prices):
    """Generate sample signal DataFrame."""
    n = len(sample_prices)
    signals = pd.DataFrame(
        np.random.choice([-1, 0, 1], size=(n, len(sample_prices.columns))),
        index=sample_prices.index,
        columns=sample_prices.columns,
    ).astype(float) * 0.1  # Small position sizes
    return signals


# ─── Portfolio Tests ──────────────────────────────────────────────────────────

class TestPortfolio:
    """Test Portfolio state management."""

    def test_portfolio_initialization(self):
        from quant_nanggroe.engine.backtest.portfolio import Portfolio
        portfolio = Portfolio(initial_capital=500000)
        assert portfolio.equity == 500000
        assert portfolio.cash == 500000
        assert portfolio.position_count == 0

    def test_portfolio_open_position(self):
        from quant_nanggroe.engine.backtest.portfolio import Portfolio
        portfolio = Portfolio(initial_capital=1_000_000)
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", 1, 100, 150.0, ts, 1.0)
        assert portfolio.position_count == 1
        assert "AAPL" in portfolio.positions

    def test_portfolio_close_position(self):
        from quant_nanggroe.engine.backtest.portfolio import Portfolio
        portfolio = Portfolio(initial_capital=1_000_000)
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", 1, 100, 150.0, ts, 1.0)
        trade = portfolio.close_position("AAPL", 160.0, ts + pd.Timedelta(days=5), "signal")
        assert trade is not None
        assert trade.pnl > 0  # Long position, price went up
        assert portfolio.position_count == 0

    def test_portfolio_equity_tracking(self):
        from quant_nanggroe.engine.backtest.portfolio import Portfolio
        portfolio = Portfolio(initial_capital=1_000_000)
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", 1, 100, 150.0, ts, 1.0)
        # Mark to market with updated prices
        price_row = pd.Series({"AAPL": 160.0, "GOOGL": 100.0})
        portfolio.mark_to_market(price_row)
        # Equity should reflect unrealized P&L
        assert portfolio.equity > 0

    def test_portfolio_max_positions(self):
        from quant_nanggroe.engine.backtest.portfolio import Portfolio
        portfolio = Portfolio(initial_capital=1_000_000, max_positions=2)
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", 1, 100, 50.0, ts, 1.0)
        portfolio.open_position("GOOGL", 1, 100, 50.0, ts, 1.0)
        # Third position should be rejected
        assert not portfolio.can_open_position(50.0, 100, 1.0)


# ─── Execution Simulator Tests ───────────────────────────────────────────────

class TestExecutionSimulator:
    """Test execution simulation."""

    def test_slippage_buy(self):
        from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig
        sim = ExecutionSimulator(ExecutionConfig(slippage_bps=10.0))
        slipped = sim.apply_slippage(100.0, 1)  # Buying
        assert slipped > 100.0  # Buying → price increases

    def test_slippage_sell(self):
        from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig
        sim = ExecutionSimulator(ExecutionConfig(slippage_bps=10.0))
        slipped = sim.apply_slippage(100.0, -1)  # Selling
        assert slipped < 100.0  # Selling → price decreases

    def test_commission(self):
        from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig
        sim = ExecutionSimulator(ExecutionConfig(commission_rate=0.001))
        comm = sim.calc_commission(100, 50.0)
        assert comm == 5.0  # 0.1% of 5000

    def test_simulate_fill(self):
        from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig
        sim = ExecutionSimulator(ExecutionConfig(commission_rate=0.001, slippage_bps=5.0))
        result = sim.simulate_fill(100.0, 1, 100)
        assert "fill_price" in result
        assert "commission" in result
        assert result["commission"] > 0


# ─── Performance Metrics Tests ───────────────────────────────────────────────

class TestPerformanceMetrics:
    """Test performance metrics calculation."""

    def test_basic_metrics(self):
        from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
        metrics = PerformanceMetrics(bars_per_year=252)
        
        # Create a simple equity curve
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        equity = pd.Series(1_000_000 * np.cumprod(1 + returns))
        
        result = metrics.calculate(equity, [], 1_000_000)
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "sortino_ratio" in result
        assert "calmar_ratio" in result

    def test_metrics_with_positive_returns(self):
        from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
        metrics = PerformanceMetrics(bars_per_year=252)
        
        # Monotonically increasing equity
        equity = pd.Series(range(1000, 2000), dtype=float)
        result = metrics.calculate(equity, [], 1000)
        assert result["total_return"] > 0
        assert result["max_drawdown"] == 0  # No drawdown

    def test_empty_equity_curve(self):
        from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
        metrics = PerformanceMetrics(bars_per_year=252)
        equity = pd.Series([], dtype=float)
        result = metrics.calculate(equity, [], 1_000_000)
        assert result["total_return"] == 0

    def test_bars_per_year(self):
        from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
        # Equity market
        assert PerformanceMetrics.calc_bars_per_year("1D", "equity") == 252
        # Crypto market
        assert PerformanceMetrics.calc_bars_per_year("1D", "crypto") == 365
        # Hourly equity
        assert PerformanceMetrics.calc_bars_per_year("1H", "equity") > 1000


# ─── Backtest Engine Tests ───────────────────────────────────────────────────

class TestBacktestEngine:
    """Test the main backtest engine."""

    def test_basic_backtest(self, sample_prices, sample_signals):
        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
        engine = BacktestEngine(BacktestConfig(initial_capital=1_000_000))
        results = engine.run(sample_prices, sample_signals)
        
        assert "metrics" in results
        assert "equity_curve" in results
        assert "trades" in results
        assert len(results["equity_curve"]) > 0

    def test_backtest_with_benchmark(self, sample_prices, sample_signals):
        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
        engine = BacktestEngine(BacktestConfig(initial_capital=1_000_000))
        results = engine.run(sample_prices, sample_signals)
        
        metrics = results["metrics"]
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics

    def test_backtest_no_short(self, sample_prices):
        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
        engine = BacktestEngine(BacktestConfig(
            initial_capital=1_000_000,
            short_enabled=False,
        ))
        # All negative signals should be ignored
        signals = pd.DataFrame(
            -0.5, index=sample_prices.index, columns=sample_prices.columns
        )
        results = engine.run(sample_prices, signals)
        # Should have no trades since shorts are disabled
        assert results["total_trades"] == 0


# ─── Walk-Forward Tests ──────────────────────────────────────────────────────

class TestWalkForward:
    """Test Walk-Forward Analysis."""

    def test_walk_forward_basic(self, sample_prices, sample_signals):
        from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
        from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
        
        engine = BacktestEngine(BacktestConfig(initial_capital=1_000_000))
        analyzer = WalkForwardAnalyzer(
            engine=engine,
            train_window=120,
            test_window=30,
        )
        results = analyzer.analyze(sample_prices, sample_signals)
        
        assert "windows" in results
        assert "aggregate" in results
        assert "degradation_stats" in results
        if len(results["windows"]) > 0:
            assert results["aggregate"]["num_windows"] > 0


# ─── Monte Carlo Tests ──────────────────────────────────────────────────────

class TestMonteCarlo:
    """Test Monte Carlo Simulation."""

    def test_trade_shuffle(self):
        from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
        simulator = MonteCarloSimulator(num_simulations=100, random_seed=42)
        trades_pnl = [100, -50, 200, -30, 150, -80, 50, -20, 300, -100]
        result = simulator.simulate_trade_shuffle(trades_pnl, 1_000_000)
        
        assert result.num_simulations == 100
        assert result.original_value != 0
        assert result.p5 < result.p95
        assert result.confidence_95[0] < result.confidence_95[1]

    def test_return_resample(self):
        from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
        simulator = MonteCarloSimulator(num_simulations=100, random_seed=42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        result = simulator.simulate_return_resample(returns, 1_000_000)
        
        assert result.num_simulations == 100
        assert result.probability_of_loss >= 0
        assert result.probability_of_loss <= 1

    def test_price_path(self):
        from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
        simulator = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = simulator.simulate_price_path(0.001, 0.02, 252, 1_000_000)
        
        assert result.num_simulations == 100
        assert result.mean_value != 0


# ─── Report Tests ────────────────────────────────────────────────────────────

class TestBacktestReport:
    """Test backtest report generation."""

    def test_json_report(self):
        from quant_nanggroe.engine.backtest.report import BacktestReport
        from quant_nanggroe.engine.backtest.portfolio import TradeRecord
        
        metrics = {"total_return": 0.15, "sharpe_ratio": 1.5, "max_drawdown": -0.05}
        equity = pd.Series([1_000_000, 1_050_000, 1_100_000, 1_150_000])
        trades = []
        
        report = BacktestReport.generate(metrics, equity, trades, format="json")
        assert isinstance(report, str)
        assert "total_return" in report

    def test_text_report(self):
        from quant_nanggroe.engine.backtest.report import BacktestReport
        from quant_nanggroe.engine.backtest.portfolio import TradeRecord
        
        metrics = {"total_return": 0.15, "sharpe_ratio": 1.5, "max_drawdown": -0.05}
        equity = pd.Series([1_000_000, 1_050_000, 1_100_000, 1_150_000])
        trades = []
        
        report = BacktestReport.generate(metrics, equity, trades, format="text")
        assert isinstance(report, str)
        assert "QUANT-NANGGROE-AI" in report
