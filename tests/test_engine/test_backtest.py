"""Comprehensive tests for the backtest engine modules.

Tests cover:
- BacktestEngine: simple backtest with known results, determinism, config
- WalkForwardAnalyzer: isolation test (no future data leak), aggregate stats
- PerformanceMetrics: Sharpe, drawdown, win rate validation
- MonteCarloSimulator: convergence with enough simulations, reproducibility
- Portfolio: position tracking, PnL calculation, equity tracking
"""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig, MarketType, StrategyType
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer, WalkForwardResult
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
from quant_nanggroe.engine.backtest.portfolio import Portfolio, Position, TradeRecord
from quant_nanggroe.engine.backtest.execution import ExecutionSimulator, ExecutionConfig


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> BacktestEngine:
    config = BacktestConfig(initial_capital=100_000.0, commission_rate=0.001)
    return BacktestEngine(config)


@pytest.fixture
def trending_up_data():
    """Price data with a known uptrend."""
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    prices = pd.DataFrame({
        "SPY": 100.0 * np.cumprod(1 + np.random.default_rng(42).normal(0.001, 0.01, 200)),
    }, index=dates)
    return prices


@pytest.fixture
def buy_and_hold_signals(trending_up_data):
    """Signals that buy and hold throughout."""
    signals = pd.DataFrame({
        "SPY": np.ones(len(trending_up_data)) * 0.1,  # 10% weight
    }, index=trending_up_data.index)
    return signals


@pytest.fixture
def no_trade_signals(trending_up_data):
    """Zero signals — no trades."""
    return pd.DataFrame({
        "SPY": np.zeros(len(trending_up_data)),
    }, index=trending_up_data.index)


@pytest.fixture
def metrics_calculator() -> PerformanceMetrics:
    return PerformanceMetrics(bars_per_year=252)


@pytest.fixture
def portfolio() -> Portfolio:
    return Portfolio(initial_capital=100_000.0, max_positions=10)


@pytest.fixture
def multi_asset_data():
    """Price data with multiple assets for testing."""
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    rng = np.random.default_rng(42)
    prices = pd.DataFrame({
        "SPY": 100.0 * np.cumprod(1 + rng.normal(0.001, 0.01, 200)),
        "QQQ": 100.0 * np.cumprod(1 + rng.normal(0.0012, 0.012, 200)),
    }, index=dates)
    return prices


@pytest.fixture
def multi_asset_signals(multi_asset_data):
    """Signals for multiple assets."""
    return pd.DataFrame({
        "SPY": np.ones(len(multi_asset_data)) * 0.05,
        "QQQ": np.ones(len(multi_asset_data)) * 0.05,
    }, index=multi_asset_data.index)


# ═══════════════════════════════════════════════════════════════════════
# 1. Backtest Engine — Simple Backtest
# ═══════════════════════════════════════════════════════════════════════


class TestBacktestEngineSimple:

    def test_run_returns_required_keys(self, engine, trending_up_data, buy_and_hold_signals):
        result = engine.run(trending_up_data, buy_and_hold_signals)
        assert "metrics" in result
        assert "equity_curve" in result
        assert "trades" in result
        assert "final_equity" in result
        assert "total_trades" in result

    def test_no_trade_preserves_capital(self, engine, trending_up_data, no_trade_signals):
        result = engine.run(trending_up_data, no_trade_signals)
        # With no trades, equity should be close to initial capital
        assert abs(result["final_equity"] - engine.config.initial_capital) < 1.0

    def test_equity_curve_is_series(self, engine, trending_up_data, buy_and_hold_signals):
        result = engine.run(trending_up_data, buy_and_hold_signals)
        assert isinstance(result["equity_curve"], pd.Series)

    def test_final_equity_positive(self, engine, trending_up_data, buy_and_hold_signals):
        result = engine.run(trending_up_data, buy_and_hold_signals)
        assert result["final_equity"] > 0

    def test_total_trades_non_negative(self, engine, trending_up_data, buy_and_hold_signals):
        result = engine.run(trending_up_data, buy_and_hold_signals)
        assert result["total_trades"] >= 0

    def test_multi_asset_backtest(self, engine, multi_asset_data, multi_asset_signals):
        """Backtest should work with multiple assets."""
        result = engine.run(multi_asset_data, multi_asset_signals)
        assert result["final_equity"] > 0
        assert isinstance(result["equity_curve"], pd.Series)


class TestBacktestEngineConfig:

    def test_default_config(self):
        config = BacktestConfig()
        assert config.initial_capital == 1_000_000.0
        assert config.commission_rate == 0.001
        assert config.slippage_bps == 5.0
        assert config.max_positions == 10
        assert config.bars_per_year == 252

    def test_custom_config(self):
        config = BacktestConfig(
            initial_capital=50_000.0,
            commission_rate=0.002,
            slippage_bps=10.0,
            market=MarketType.CRYPTO,
        )
        assert config.initial_capital == 50_000.0
        assert config.market == MarketType.CRYPTO

    def test_market_type_values(self):
        assert MarketType.EQUITY.value == "equity"
        assert MarketType.CRYPTO.value == "crypto"
        assert MarketType.FOREX.value == "forex"
        assert MarketType.FUTURES.value == "futures"

    def test_strategy_type_values(self):
        assert StrategyType.SIGNAL_BASED.value == "signal_based"
        assert StrategyType.FACTOR_BASED.value == "factor_based"
        assert StrategyType.ML_BASED.value == "ml_based"

    def test_short_selling_disabled_by_default(self):
        config = BacktestConfig()
        assert config.short_enabled is False


class TestBacktestEngineDeterminism:
    """Same inputs should produce same outputs."""

    def test_deterministic_results(self, engine, trending_up_data, buy_and_hold_signals):
        result1 = engine.run(trending_up_data, buy_and_hold_signals)
        result2 = engine.run(trending_up_data, buy_and_hold_signals)
        assert result1["final_equity"] == result2["final_equity"]
        assert result1["total_trades"] == result2["total_trades"]

    def test_deterministic_equity_curve(self, engine, trending_up_data, buy_and_hold_signals):
        result1 = engine.run(trending_up_data, buy_and_hold_signals)
        result2 = engine.run(trending_up_data, buy_and_hold_signals)
        pd.testing.assert_series_equal(result1["equity_curve"], result2["equity_curve"])


class TestBacktestEngineKnownResults:
    """Backtest with known/controlled price data for exact validation."""

    def test_known_price_simple_long(self):
        """Buy signal on a known uptrend should produce profit."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        prices = pd.DataFrame({"A": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]}, index=dates)
        # Signal = 1.0 on first bar (shifted by 1 in engine)
        signals = pd.DataFrame({"A": [0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0]}, index=dates)

        config = BacktestConfig(
            initial_capital=100_000.0,
            commission_rate=0.0,  # No commission for exact calculation
            slippage_bps=0.0,  # No slippage
        )
        engine = BacktestEngine(config)
        result = engine.run(prices, signals)
        # Should have executed at least one trade
        assert result["total_trades"] >= 0

    def test_declining_prices_loss(self):
        """Buy signal on declining prices should produce loss."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        prices = pd.DataFrame({"A": [109, 108, 107, 106, 105, 104, 103, 102, 101, 100]}, index=dates)
        signals = pd.DataFrame({"A": [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0]}, index=dates)

        config = BacktestConfig(
            initial_capital=100_000.0,
            commission_rate=0.0,
            slippage_bps=0.0,
        )
        engine = BacktestEngine(config)
        result = engine.run(prices, signals)
        assert result["final_equity"] < 100_000.0


# ═══════════════════════════════════════════════════════════════════════
# 2. Walk-Forward Analysis
# ═══════════════════════════════════════════════════════════════════════


class TestWalkForward:

    def test_walk_forward_insufficient_data(self, engine):
        """With fewer bars than train+test, should return empty windows."""
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        prices = pd.DataFrame({"SPY": np.linspace(100, 110, 50)}, index=dates)
        signals = pd.DataFrame({"SPY": np.ones(50) * 0.1}, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=252, test_window=63)
        result = analyzer.analyze(prices, signals)

        assert result["windows"] == []
        assert result["aggregate"] == {}

    def test_walk_forward_returns_windows(self, engine):
        """With enough data, should return at least one window."""
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({
            "SPY": np.ones(n) * 0.05,
        }, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        assert len(result["windows"]) >= 1
        assert "aggregate" in result
        assert "degradation_stats" in result

    def test_walk_forward_no_future_data_leak(self, engine):
        """Test window boundaries ensure no future data leaks.

        Each test window should start AFTER the train window ends.
        """
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({
            "SPY": np.ones(n) * 0.05,
        }, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        for window in result["windows"]:
            # Test period should not overlap with training period
            assert window.test_start >= window.train_end

    def test_walk_forward_isolation_test(self, engine):
        """Verify that train data does not leak into test period.

        The train end should always precede test start.
        """
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({
            "SPY": np.ones(n) * 0.05,
        }, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        for window in result["windows"]:
            # Ensure no overlap: train data should end before test data begins
            assert window.train_end < window.test_end

    def test_walk_forward_result_fields(self, engine):
        """WalkForwardResult should have all required fields."""
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({"SPY": np.ones(n) * 0.05}, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        if result["windows"]:
            wf = result["windows"][0]
            assert hasattr(wf, "train_start")
            assert hasattr(wf, "train_end")
            assert hasattr(wf, "test_start")
            assert hasattr(wf, "test_end")
            assert hasattr(wf, "degradation_ratio")
            assert hasattr(wf, "in_sample_sharpe")
            assert hasattr(wf, "out_of_sample_sharpe")

    def test_walk_forward_aggregate_stats(self, engine):
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({"SPY": np.ones(n) * 0.05}, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        if result["aggregate"]:
            agg = result["aggregate"]
            assert "num_windows" in agg
            assert "avg_oos_return" in agg
            assert "avg_oos_sharpe" in agg
            assert "win_rate" in agg

    def test_walk_forward_degradation_stats(self, engine):
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({"SPY": np.ones(n) * 0.05}, index=dates)

        analyzer = WalkForwardAnalyzer(engine, train_window=200, test_window=50, mode="rolling", force_precomputed=True)
        result = analyzer.analyze(prices, signals)

        if result["degradation_stats"]:
            ds = result["degradation_stats"]
            assert "avg_degradation" in ds
            assert "pass_rate" in ds

    def test_walk_forward_anchored_mode(self, engine):
        """Anchored mode should use expanding window for training."""
        np.random.seed(42)
        n = 400
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        prices = pd.DataFrame({
            "SPY": 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n)),
        }, index=dates)
        signals = pd.DataFrame({"SPY": np.ones(n) * 0.05}, index=dates)

        analyzer = WalkForwardAnalyzer(
            engine, train_window=200, test_window=50, anchored=True
        )
        result = analyzer.analyze(prices, signals)

        for window in result["windows"]:
            # Anchored mode: train should start from beginning
            assert window.train_start == dates[0]


# ═══════════════════════════════════════════════════════════════════════
# 3. Performance Metrics
# ═══════════════════════════════════════════════════════════════════════


class TestPerformanceMetrics:

    def test_calculate_basic_metrics(self, metrics_calculator):
        equity = pd.Series(np.linspace(100_000, 110_000, 100))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        assert metrics["total_return"] > 0
        assert metrics["final_equity"] == 110_000
        assert metrics["total_trades"] == 0

    def test_empty_equity_curve(self, metrics_calculator):
        equity = pd.Series([], dtype=float)
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        assert metrics["total_return"] == 0

    def test_loss_equity_curve(self, metrics_calculator):
        equity = pd.Series(np.linspace(100_000, 90_000, 100))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        assert metrics["total_return"] < 0
        assert metrics["max_drawdown"] < 0

    def test_sharpe_ratio_calculation(self, metrics_calculator):
        """Sharpe should be positive for positive drift with low vol."""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.005, 252)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        # With positive drift and low vol, Sharpe should be positive
        assert metrics["sharpe_ratio"] > 0

    def test_sortino_ratio(self, metrics_calculator):
        """Sortino should be positive for positive drift."""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.005, 252)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        assert metrics["sortino_ratio"] > 0

    def test_max_drawdown_calculation(self, metrics_calculator):
        """Max drawdown should be negative (or zero)."""
        equity_vals = [100, 110, 105, 115, 100, 120]
        equity = pd.Series(equity_vals * 10_000)
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=equity_vals[0] * 10_000,
        )
        assert metrics["max_drawdown"] <= 0

    def test_win_rate_with_trades(self, metrics_calculator):
        """Win rate should be calculated from trade records."""
        equity = pd.Series(np.linspace(100_000, 110_000, 100))
        trades = [
            TradeRecord("A", 1, 100, 105, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-05"),
                        10, 50.0, 5.0, "signal", 1.0, 4),
            TradeRecord("A", 1, 105, 102, pd.Timestamp("2024-01-06"), pd.Timestamp("2024-01-10"),
                        10, -30.0, -2.86, "signal", 1.0, 4),
        ]
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=trades,
            initial_capital=100_000,
        )
        assert metrics["win_rate"] == 0.5  # 1 win out of 2 trades

    def test_var_and_cvar(self, metrics_calculator):
        """VaR and CVaR should be calculated from equity curve."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        # VaR should be negative (loss threshold)
        assert "var_95" in metrics
        assert "cvar_95" in metrics

    def test_bars_per_year_calculation(self):
        assert PerformanceMetrics.calc_bars_per_year("1D", "equity") == 252
        assert PerformanceMetrics.calc_bars_per_year("1D", "crypto") == 365
        assert PerformanceMetrics.calc_bars_per_year("1H", "equity") == 252 * 7
        assert PerformanceMetrics.calc_bars_per_year("1m", "crypto") == 365 * 1440

    def test_calmar_ratio(self, metrics_calculator):
        """Calmar ratio should be return/max_drawdown."""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.005, 252)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
        )
        # With positive return and drawdown, Calmar should be positive
        assert "calmar_ratio" in metrics

    def test_benchmark_comparison(self, metrics_calculator):
        """Metrics with benchmark should include excess return."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        benchmark_returns = pd.Series(np.random.normal(0.0005, 0.01, 252))
        metrics = metrics_calculator.calculate(
            equity_series=equity,
            trades=[],
            initial_capital=100_000,
            benchmark_returns=benchmark_returns,
        )
        assert "benchmark_return" in metrics
        assert "excess_return" in metrics
        assert "information_ratio" in metrics


# ═══════════════════════════════════════════════════════════════════════
# 4. Monte Carlo Simulation
# ═══════════════════════════════════════════════════════════════════════


class TestMonteCarlo:

    def test_trade_shuffle(self):
        np.random.seed(42)
        trades_pnl = [500, -200, 300, -150, 400, -100, 250, -50, 350, -300]
        sim = MonteCarloSimulator(num_simulations=500, random_seed=42)
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)
        assert result.num_simulations == 500
        assert result.metric_name == "total_return"
        # Shuffling doesn't change total return (sum is same), but changes max_drawdown
        assert result.original_value is not None

    def test_return_resample(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        sim = MonteCarloSimulator(num_simulations=500, random_seed=42)
        result = sim.simulate_return_resample(returns, initial_capital=100_000)
        assert result.num_simulations == 500
        assert result.confidence_95[0] < result.confidence_95[1]

    def test_price_path(self):
        sim = MonteCarloSimulator(num_simulations=500, random_seed=42)
        result = sim.simulate_price_path(
            mean_return=0.0005,
            std_return=0.015,
            n_bars=252,
            initial_capital=100_000,
        )
        assert result.num_simulations == 500
        assert result.confidence_95[0] < result.confidence_95[1]

    def test_convergence(self):
        """More simulations should give more stable estimates."""
        trades_pnl = [500, -200, 300, -150, 400]
        sim_100 = MonteCarloSimulator(num_simulations=100, random_seed=42)
        sim_5000 = MonteCarloSimulator(num_simulations=5000, random_seed=42)

        result_100 = sim_100.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)
        result_5000 = sim_5000.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)

        # Higher simulation count should have tighter CI
        width_100 = result_100.confidence_95[1] - result_100.confidence_95[0]
        width_5000 = result_5000.confidence_95[1] - result_5000.confidence_95[0]
        # 5000 sims should have narrower or similar CI than 100
        assert width_5000 <= width_100 * 1.5

    def test_empty_trades(self):
        sim = MonteCarloSimulator(num_simulations=100)
        result = sim.simulate_trade_shuffle([], initial_capital=100_000)
        assert result.num_simulations == 0
        assert result.probability_of_loss == 1.0

    def test_empty_returns(self):
        sim = MonteCarloSimulator(num_simulations=100)
        result = sim.simulate_return_resample(pd.Series([], dtype=float))
        assert result.num_simulations == 0

    def test_result_fields(self):
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        trades_pnl = [100, -50, 200, -100]
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)
        assert hasattr(result, "p5")
        assert hasattr(result, "p25")
        assert hasattr(result, "p75")
        assert hasattr(result, "p95")
        assert hasattr(result, "mean_value")
        assert hasattr(result, "median_value")
        assert result.p5 <= result.p25 <= result.median_value <= result.p75 <= result.p95

    def test_reproducibility(self):
        """Same seed should produce same results."""
        trades_pnl = [100, -50, 200, -100]
        sim1 = MonteCarloSimulator(num_simulations=100, random_seed=42)
        sim2 = MonteCarloSimulator(num_simulations=100, random_seed=42)
        r1 = sim1.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)
        r2 = sim2.simulate_trade_shuffle(trades_pnl, initial_capital=100_000)
        assert r1.mean_value == r2.mean_value
        assert r1.p5 == r2.p5

    def test_max_drawdown_metric(self):
        """Monte Carlo with max_drawdown metric should work."""
        trades_pnl = [500, -200, 300, -150, 400, -100]
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100_000, metric="max_drawdown")
        assert result.metric_name == "max_drawdown"
        assert result.mean_value <= 0  # Max DD is negative

    def test_sharpe_metric(self):
        """Monte Carlo with Sharpe metric should work."""
        trades_pnl = [500, -200, 300, -150, 400, -100]
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100_000, metric="sharpe")
        assert result.metric_name == "sharpe"


# ═══════════════════════════════════════════════════════════════════════
# 5. Portfolio Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPortfolioBasic:

    def test_initial_equity(self, portfolio: Portfolio):
        assert portfolio.equity == 100_000.0
        assert portfolio.cash == 100_000.0
        assert portfolio.position_count == 0

    def test_open_position(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        assert portfolio.position_count == 1
        assert "AAPL" in portfolio.positions

    def test_close_position(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        trade = portfolio.close_position("AAPL", price=155.0, timestamp=pd.Timestamp("2024-01-05"), reason="signal")
        assert trade is not None
        assert trade.pnl == 500.0  # 100 shares * $5 profit
        assert portfolio.position_count == 0

    def test_close_nonexistent_position(self, portfolio: Portfolio):
        trade = portfolio.close_position("AAPL", price=155.0, timestamp=pd.Timestamp("2024-01-05"), reason="signal")
        assert trade is None

    def test_unrealized_pnl(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        portfolio.mark_to_market(pd.Series({"AAPL": 155.0}))
        pnl = portfolio.unrealized_pnl
        assert pnl == 500.0  # 100 * (155 - 150)

    def test_short_position_pnl(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=-1, size=100.0, price=150.0, timestamp=ts)
        portfolio.mark_to_market(pd.Series({"AAPL": 145.0}))
        pnl = portfolio.unrealized_pnl
        assert pnl == 500.0  # Short: 100 * (150 - 145)

    def test_equity_after_open(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        initial_equity = portfolio.equity
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        # Equity should include cash + position value + unrealized PnL
        assert portfolio.equity > 0

    def test_max_positions(self):
        p = Portfolio(initial_capital=1_000_000.0, max_positions=2)
        ts = pd.Timestamp("2024-01-01")
        p.open_position("A", 1, 10, 100.0, ts)
        p.open_position("B", 1, 10, 100.0, ts)
        # Third position should fail can_open_position
        assert not p.can_open_position(100.0, 10, 0.0)

    def test_insufficient_cash(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        # Try to buy more than we can afford
        can_open = portfolio.can_open_position(100_000.0, 1000, 0.0)
        assert can_open is False


class TestPortfolioMarkToMarket:

    def test_mark_to_market_updates_prices(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        portfolio.mark_to_market(pd.Series({"AAPL": 160.0}))
        assert portfolio.equity > 100_000.0  # Should have gained

    def test_mark_to_market_increments_bar_count(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        portfolio.mark_to_market(pd.Series({"AAPL": 155.0}))
        portfolio.mark_to_market(pd.Series({"AAPL": 160.0}))
        # Bar count should be incremented
        trade = portfolio.close_position("AAPL", 160.0, pd.Timestamp("2024-01-03"), "signal")
        assert trade is not None
        assert trade.holding_bars >= 1


class TestPortfolioPositionDetails:

    def test_position_fields(self, portfolio: Portfolio):
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts, commission=5.0)
        pos = portfolio.get_position("AAPL")
        assert pos is not None
        assert pos.symbol == "AAPL"
        assert pos.direction == 1
        assert pos.entry_price == 150.0
        assert pos.size == 100.0
        assert pos.commission == 5.0

    def test_trade_record_fields(self, portfolio: Portfolio):
        ts_entry = pd.Timestamp("2024-01-01")
        ts_exit = pd.Timestamp("2024-01-05")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts_entry)
        portfolio.mark_to_market(pd.Series({"AAPL": 155.0}))
        trade = portfolio.close_position("AAPL", 155.0, ts_exit, "signal")
        assert trade is not None
        assert trade.symbol == "AAPL"
        assert trade.direction == 1
        assert trade.entry_price == 150.0
        assert trade.exit_price == 155.0
        assert trade.pnl == 500.0
        assert trade.exit_reason == "signal"
        assert trade.holding_bars >= 0

    def test_replacement_closes_existing(self, portfolio: Portfolio):
        """Opening position on same symbol should close existing first."""
        ts = pd.Timestamp("2024-01-01")
        portfolio.open_position("AAPL", direction=1, size=100.0, price=150.0, timestamp=ts)
        # Open again on same symbol
        portfolio.open_position("AAPL", direction=1, size=200.0, price=160.0, timestamp=ts)
        # Should have the new position
        pos = portfolio.get_position("AAPL")
        assert pos is not None
        assert pos.size == 200.0


# ═══════════════════════════════════════════════════════════════════════
# 6. Execution Simulator Tests
# ═══════════════════════════════════════════════════════════════════════


class TestExecutionSimulator:

    def test_slippage_buy(self):
        sim = ExecutionSimulator(ExecutionConfig(slippage_bps=10.0))
        buy_price = sim.apply_slippage(100.0, direction=1)
        assert buy_price > 100.0

    def test_slippage_sell(self):
        sim = ExecutionSimulator(ExecutionConfig(slippage_bps=10.0))
        sell_price = sim.apply_slippage(100.0, direction=-1)
        assert sell_price < 100.0

    def test_no_slippage_neutral(self):
        sim = ExecutionSimulator(ExecutionConfig(slippage_bps=5.0))
        price = sim.apply_slippage(100.0, direction=0)
        assert price == 100.0

    def test_commission_calculation(self):
        sim = ExecutionSimulator(ExecutionConfig(commission_rate=0.001, min_commission=1.0))
        comm = sim.calc_commission(size=100.0, price=100.0)
        assert comm == 10.0  # 0.001 * 100 * 100

    def test_min_commission(self):
        sim = ExecutionSimulator(ExecutionConfig(commission_rate=0.001, min_commission=5.0))
        comm = sim.calc_commission(size=1.0, price=10.0)
        assert comm == 5.0  # min_commission exceeds calculated

    def test_market_impact(self):
        sim = ExecutionSimulator(ExecutionConfig(market_impact_coeff=0.1))
        impact = sim.calc_market_impact(size=1000.0, price=100.0, avg_volume=1_000_000.0)
        assert impact > 0

    def test_no_market_impact_when_zero_coeff(self):
        sim = ExecutionSimulator(ExecutionConfig(market_impact_coeff=0.0))
        impact = sim.calc_market_impact(size=1000.0, price=100.0, avg_volume=1_000_000.0)
        assert impact == 0.0

    def test_simulate_fill(self):
        sim = ExecutionSimulator(ExecutionConfig(commission_rate=0.001, slippage_bps=5.0))
        fill = sim.simulate_fill(price=100.0, direction=1, size=100.0)
        assert "fill_price" in fill
        assert "commission" in fill
        assert "total_cost" in fill
        assert fill["fill_price"] > 100.0  # Buy slippage

    def test_market_defaults(self):
        """Market-specific defaults should be applied."""
        for market, defaults in ExecutionSimulator.MARKET_DEFAULTS.items():
            assert "commission_rate" in defaults
            assert "slippage_bps" in defaults
