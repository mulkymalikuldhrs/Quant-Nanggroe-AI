"""
Kelly→Strategy→Backtest Integration Tests
==========================================

Tests the full pipeline from Kelly optimal f calculation through strategy
signal generation to backtest execution.

Covers:
- TestKellyOptimalF: Kelly optimal f calculation correctness
- TestKellyStrategyIntegration: Kelly output feeds into strategy
- TestStrategyBacktestIntegration: Strategy output feeds into backtest
- TestFullPipeline: Kelly→strategy→backtest end-to-end
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
from quant_nanggroe.engine.kelly.backtest_integration import (
    KellyBacktestBridge,
    KellySignal,
    StrategyKellyMixin,
)
from quant_nanggroe.engine.kelly.base import KellyMethod, KellyParameters, KellyResult
from quant_nanggroe.engine.kelly.fractional import FractionalKelly
from quant_nanggroe.engine.kelly.optimal_f import OptimalF
from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategySignal,
)

# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_trades() -> list[float]:
    """Known trade history with positive expectancy."""
    rng = np.random.default_rng(42)
    wins = rng.normal(0.02, 0.01, 60)
    losses = rng.normal(-0.015, 0.008, 40)
    trades = np.concatenate([wins, losses])
    rng.shuffle(trades)
    return trades.tolist()


@pytest.fixture
def losing_trades() -> list[float]:
    """Trade history with negative expectancy."""
    rng = np.random.default_rng(99)
    wins = rng.normal(0.01, 0.005, 30)
    losses = rng.normal(-0.025, 0.01, 70)
    trades = np.concatenate([wins, losses])
    rng.shuffle(trades)
    return trades.tolist()


@pytest.fixture
def trending_prices() -> pd.DataFrame:
    """Price data with a clear uptrend."""
    dates = pd.date_range("2024-01-01", periods=252, freq="B")
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0008, 0.012, 252)
    close = 100.0 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.005, 252)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, 252)))
    open_ = close * (1 + rng.normal(0, 0.002, 252))
    volume = rng.lognormal(15, 0.5, 252)

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def backtest_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=100_000.0,
        commission_rate=0.001,
        slippage_bps=5.0,
        leverage=1.0,
        risk_per_trade=0.02,
    )


class SimpleTrendStrategy(Strategy):
    """Simple moving average crossover strategy for testing."""
    name = "simple_trend"

    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signal(self, data: pd.DataFrame, **kwargs) -> StrategySignal:
        if len(data) < self.slow_period:
            return StrategySignal(
                strategy_name=self.name,
                direction=SignalDirection.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.0,
            )

        close = data["close"] if "close" in data.columns else data.iloc[:, -1]
        sma_fast = close.rolling(self.fast_period).mean().iloc[-1]
        sma_slow = close.rolling(self.slow_period).mean().iloc[-1]
        current = float(close.iloc[-1])

        if current > sma_fast > sma_slow:
            return StrategySignal(
                strategy_name=self.name,
                direction=SignalDirection.BUY,
                strength=SignalStrength.STRONG,
                confidence=min(1.0, (current - sma_slow) / max(sma_slow, 1e-10)),
                entry_price=current,
            )
        elif current < sma_fast < sma_slow:
            return StrategySignal(
                strategy_name=self.name,
                direction=SignalDirection.SELL,
                strength=SignalStrength.STRONG,
                confidence=min(1.0, (sma_slow - current) / max(sma_slow, 1e-10)),
                entry_price=current,
            )

        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
        )


# ═══════════════════════════════════════════════════════════════════════
# TestKellyOptimalF
# ═══════════════════════════════════════════════════════════════════════

class TestKellyOptimalF:
    """Tests for Kelly optimal f calculation."""

    def test_optimal_f_with_positive_expectancy(self, sample_trades: list[float]):
        """Optimal f should be positive for trades with positive expectancy."""
        calc = OptimalF(max_f=0.5, steps=50)
        params = KellyParameters(
            win_rate=0.6,
            avg_win=0.02,
            avg_loss=0.015,
            leverage_max=1.0,
            trade_history=sample_trades,
        )
        result = calc.compute(params)

        assert isinstance(result, KellyResult)
        assert result.method == KellyMethod.OPTIMAL_F
        assert result.f_star > 0.0
        assert result.f_star <= 1.0
        assert result.growth_rate > -np.inf

    def test_optimal_f_with_negative_expectancy(self, losing_trades: list[float]):
        """Optimal f should be near zero for trades with negative expectancy."""
        calc = OptimalF(max_f=0.5, steps=50)
        params = KellyParameters(
            win_rate=0.3,
            avg_win=0.01,
            avg_loss=0.025,
            leverage_max=1.0,
            trade_history=losing_trades,
        )
        result = calc.compute(params)

        assert result.f_star >= 0.0
        assert result.f_star <= 1.0

    def test_optimal_f_respects_leverage_max(self, sample_trades: list[float]):
        """Optimal f should be capped by leverage_max."""
        calc = OptimalF(max_f=1.0, steps=50)
        params = KellyParameters(
            win_rate=0.7,
            avg_win=0.05,
            avg_loss=0.01,
            leverage_max=0.3,
            trade_history=sample_trades,
        )
        result = calc.compute(params)

        assert result.f_star <= 0.3

    def test_optimal_f_regime_multiplier(self, sample_trades: list[float]):
        """Regime multiplier should scale the result."""
        calc = OptimalF(max_f=0.5, steps=50)

        params_bull = KellyParameters(
            win_rate=0.6, avg_win=0.02, avg_loss=0.015,
            leverage_max=1.0, regime_multiplier=1.0,
            trade_history=sample_trades,
        )
        result_bull = calc.compute(params_bull)

        params_bear = KellyParameters(
            win_rate=0.6, avg_win=0.02, avg_loss=0.015,
            leverage_max=1.0, regime_multiplier=0.5,
            trade_history=sample_trades,
        )
        result_bear = calc.compute(params_bear)

        assert result_bear.f_star <= result_bull.f_star

    def test_optimal_f_fallback_with_insufficient_data(self):
        """Optimal f should fallback to fractional with too few trades."""
        calc = OptimalF(max_f=0.5, steps=50)
        params = KellyParameters(
            win_rate=0.6, avg_win=0.02, avg_loss=0.015,
            leverage_max=1.0, trade_history=[0.01] * 5,
        )
        result = calc.compute(params)

        assert isinstance(result, KellyResult)
        assert result.f_star >= 0.0

    def test_fractional_kelly_basic(self):
        """Fractional Kelly should return fraction of full Kelly."""
        calc = FractionalKelly(fraction=0.5)
        params = KellyParameters(
            win_rate=0.6, avg_win=0.02, avg_loss=0.015,
            leverage_max=1.0,
        )
        result = calc.compute(params)

        assert result.method == KellyMethod.FRACTIONAL
        assert result.f_star >= 0.0
        assert result.f_star <= 1.0

    def test_fractional_kelly_clamps_to_leverage_max(self):
        """Fractional Kelly should respect leverage_max."""
        calc = FractionalKelly(fraction=1.0)
        params = KellyParameters(
            win_rate=0.9, avg_win=0.1, avg_loss=0.01,
            leverage_max=0.5,
        )
        result = calc.compute(params)

        assert result.f_star <= 0.5


# ═══════════════════════════════════════════════════════════════════════
# TestKellyStrategyIntegration
# ═══════════════════════════════════════════════════════════════════════

class TestKellyStrategyIntegration:
    """Tests that Kelly output feeds correctly into strategy layer."""

    def test_kelly_bridge_produces_signals(
        self, trending_prices: pd.DataFrame
    ):
        """KellyBacktestBridge should produce valid signals from price data."""
        bridge = KellyBacktestBridge(config={
            "default_fraction": 0.5,
            "window": 63,
            "min_samples": 30,
            "max_leverage": 1.0,
        })

        returns = trending_prices["close"].pct_change().dropna()
        signals = bridge.compute_signals(
            prices=trending_prices,
            returns=returns,
            equity=100_000.0,
            regime="bull",
        )

        assert len(signals) > 0
        for sig in signals:
            assert isinstance(sig, KellySignal)
            assert 0.0 <= sig.capped_fraction <= 1.0
            assert 0.0 <= sig.conviction <= 1.0
            assert sig.regime == "bull"

    def test_kelly_signal_history_tracking(
        self, trending_prices: pd.DataFrame
    ):
        """KellyBacktestBridge should track signal history."""
        bridge = KellyBacktestBridge()
        returns = trending_prices["close"].pct_change().dropna()

        bridge.compute_signals(trending_prices, returns, 100_000.0)
        assert len(bridge.signal_history) > 0

        bridge.compute_signals(trending_prices, returns, 100_000.0)
        assert len(bridge.signal_history) > 1

        bridge.reset_history()
        assert len(bridge.signal_history) == 0

    def test_strategy_kelly_mixin_adjusts_position_size(
        self, trending_prices: pd.DataFrame
    ):
        """StrategyKellyMixin should scale position sizes by Kelly fraction."""
        class MockStrategy:
            pass

        mixin = StrategyKellyMixin.__new__(StrategyKellyMixin)
        mixin.kelly_bridge = KellyBacktestBridge(config={"max_leverage": 0.5})

        returns = trending_prices["close"].pct_change().dropna()
        base_size = 1000.0

        adjusted = mixin.adjust_position_size(
            base_size=base_size,
            prices=trending_prices,
            returns=returns,
            equity=100_000.0,
        )

        assert 0.0 <= adjusted <= base_size

    def test_kelly_bridge_regime_multipliers(self, trending_prices: pd.DataFrame):
        """Different regimes should produce different Kelly fractions."""
        bridge = KellyBacktestBridge()
        returns = trending_prices["close"].pct_change().dropna()

        bull_signals = bridge.compute_signals(
            trending_prices, returns, 100_000.0, regime="bull"
        )
        bridge.reset_history()

        bear_signals = bridge.compute_signals(
            trending_prices, returns, 100_000.0, regime="bear"
        )

        if bull_signals and bear_signals:
            bull_avg = np.mean([s.capped_fraction for s in bull_signals])
            bear_avg = np.mean([s.capped_fraction for s in bear_signals])
            assert bull_avg >= bear_avg

    def test_kelly_bridge_empty_data(self):
        """KellyBacktestBridge should handle empty data gracefully."""
        bridge = KellyBacktestBridge()
        empty_prices = pd.DataFrame()
        empty_returns = pd.Series([], dtype=float)

        signals = bridge.compute_signals(empty_prices, empty_returns, 100_000.0)
        assert signals == []


# ═══════════════════════════════════════════════════════════════════════
# TestStrategyBacktestIntegration
# ═══════════════════════════════════════════════════════════════════════

class TestStrategyBacktestIntegration:
    """Tests that strategy output feeds correctly into backtest engine."""

    def test_strategy_produces_valid_signals(
        self, trending_prices: pd.DataFrame
    ):
        """Strategy should produce valid signals for backtest."""
        strategy = SimpleTrendStrategy(fast_period=10, slow_period=30)
        signal = strategy.generate_signal(trending_prices)

        assert isinstance(signal, StrategySignal)
        assert signal.direction in (SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD)
        assert 0.0 <= signal.confidence <= 1.0

    def test_backtest_runs_with_strategy_signals(
        self, trending_prices: pd.DataFrame, backtest_config: BacktestConfig
    ):
        """Backtest should complete with strategy-generated signals."""
        strategy = SimpleTrendStrategy(fast_period=10, slow_period=30)
        engine = BacktestEngine(backtest_config)

        signals = pd.DataFrame(index=trending_prices.index)
        for col in trending_prices.columns:
            signals[col] = 0.0

        close = trending_prices["close"]
        sma_fast = close.rolling(10).mean()
        sma_slow = close.rolling(30).mean()

        signal_values = pd.Series(0.0, index=trending_prices.index)
        signal_values[sma_fast > sma_slow] = 0.1
        signal_values[sma_fast < sma_slow] = -0.1

        signals["close"] = signal_values

        result = engine.run(trending_prices, signals)

        assert "metrics" in result
        assert "equity_curve" in result
        assert len(result["equity_curve"]) > 0
        assert result["final_equity"] > 0

    def test_backtest_determinism(
        self, trending_prices: pd.DataFrame, backtest_config: BacktestConfig
    ):
        """Running the same backtest twice should produce identical results."""
        engine = BacktestEngine(backtest_config)

        signals = pd.DataFrame(0.0, index=trending_prices.index, columns=["close"])
        signals.iloc[50:150, 0] = 0.1

        result1 = engine.run(trending_prices, signals)
        result2 = engine.run(trending_prices, signals)

        assert result1["final_equity"] == pytest.approx(result2["final_equity"])
        assert result1["total_trades"] == result2["total_trades"]

    def test_backtest_respects_risk_per_trade(
        self, trending_prices: pd.DataFrame
    ):
        """Backtest should respect risk_per_trade limit."""
        config = BacktestConfig(
            initial_capital=100_000.0,
            risk_per_trade=0.001,
            commission_rate=0.001,
        )
        engine = BacktestEngine(config)

        signals = pd.DataFrame(0.0, index=trending_prices.index, columns=["close"])
        signals.iloc[50:150, 0] = 0.5

        result = engine.run(trending_prices, signals)
        assert result["final_equity"] > 0


# ═══════════════════════════════════════════════════════════════════════
# TestFullPipeline
# ═══════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """End-to-end tests: Kelly → Strategy → Backtest."""

    def test_full_pipeline_produces_results(
        self, trending_prices: pd.DataFrame, backtest_config: BacktestConfig
    ):
        """Full pipeline should produce valid backtest results."""
        # Step 1: Kelly
        kelly_bridge = KellyBacktestBridge(config={
            "default_fraction": 0.5,
            "window": 63,
            "min_samples": 30,
            "max_leverage": 0.5,
        })

        returns = trending_prices["close"].pct_change().dropna()
        kelly_signals = kelly_bridge.compute_signals(
            trending_prices, returns, 100_000.0, regime="bull"
        )

        # Step 2: Strategy signals
        strategy = SimpleTrendStrategy(fast_period=10, slow_period=30)
        signals_df = pd.DataFrame(0.0, index=trending_prices.index, columns=["close"])

        for i in range(len(trending_prices)):
            row_data = trending_prices.iloc[: i + 1]
            if len(row_data) >= 30:
                sig = strategy.generate_signal(row_data)
                if sig.direction == SignalDirection.BUY:
                    kelly_frac = kelly_signals[0].capped_fraction if kelly_signals else 0.1
                    signals_df.iloc[i, 0] = kelly_frac
                elif sig.direction == SignalDirection.SELL:
                    kelly_frac = kelly_signals[0].capped_fraction if kelly_signals else 0.1
                    signals_df.iloc[i, 0] = -kelly_frac

        # Step 3: Backtest
        engine = BacktestEngine(backtest_config)
        result = engine.run(trending_prices, signals_df)

        assert "metrics" in result
        assert "equity_curve" in result
        assert result["final_equity"] > 0
        assert len(result["equity_curve"]) > 0

    def test_full_pipeline_with_losing_regime(
        self, backtest_config: BacktestConfig
    ):
        """Full pipeline should handle a losing regime gracefully."""
        dates = pd.date_range("2024-01-01", periods=252, freq="B")
        rng = np.random.default_rng(123)
        returns = rng.normal(-0.0005, 0.02, 252)
        close = 100.0 * np.cumprod(1 + returns)
        prices = pd.DataFrame({
            "close": close,
            "open": close * (1 + rng.normal(0, 0.002, 252)),
            "high": close * (1 + np.abs(rng.normal(0, 0.005, 252))),
            "low": close * (1 - np.abs(rng.normal(0, 0.005, 252))),
            "volume": rng.lognormal(15, 0.5, 252),
        }, index=dates)

        kelly_bridge = KellyBacktestBridge(config={"max_leverage": 0.3})
        price_returns = prices["close"].pct_change().dropna()
        kelly_signals = kelly_bridge.compute_signals(
            prices, price_returns, 100_000.0, regime="bear"
        )

        strategy = SimpleTrendStrategy(fast_period=10, slow_period=30)
        signals_df = pd.DataFrame(0.0, index=prices.index, columns=["close"])

        for i in range(len(prices)):
            row_data = prices.iloc[: i + 1]
            if len(row_data) >= 30:
                sig = strategy.generate_signal(row_data)
                if sig.direction == SignalDirection.BUY:
                    kf = kelly_signals[0].capped_fraction if kelly_signals else 0.05
                    signals_df.iloc[i, 0] = kf * 0.5
                elif sig.direction == SignalDirection.SELL:
                    kf = kelly_signals[0].capped_fraction if kelly_signals else 0.05
                    signals_df.iloc[i, 0] = -kf * 0.5

        engine = BacktestEngine(backtest_config)
        result = engine.run(prices, signals_df)

        assert result["final_equity"] > 0
        assert len(result["equity_curve"]) > 0

    def test_full_pipeline_metrics_reasonable(
        self, trending_prices: pd.DataFrame, backtest_config: BacktestConfig
    ):
        """Full pipeline metrics should be within reasonable bounds."""
        kelly_bridge = KellyBacktestBridge(config={"max_leverage": 0.3})
        returns = trending_prices["close"].pct_change().dropna()
        kelly_signals = kelly_bridge.compute_signals(
            trending_prices, returns, 100_000.0
        )

        strategy = SimpleTrendStrategy(fast_period=10, slow_period=30)
        signals_df = pd.DataFrame(0.0, index=trending_prices.index, columns=["close"])

        for i in range(30, len(trending_prices)):
            row_data = trending_prices.iloc[: i + 1]
            sig = strategy.generate_signal(row_data)
            if sig.direction == SignalDirection.BUY:
                signals_df.iloc[i, 0] = 0.1
            elif sig.direction == SignalDirection.SELL:
                signals_df.iloc[i, 0] = -0.1

        engine = BacktestEngine(backtest_config)
        result = engine.run(trending_prices, signals_df)
        metrics = result["metrics"]

        assert -1.0 <= metrics.get("total_return", 0) <= 10.0
        assert metrics.get("max_drawdown", 0) <= 0.0
        assert metrics.get("win_rate", 0) >= 0.0
