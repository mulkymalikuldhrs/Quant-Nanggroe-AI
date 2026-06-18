"""Tests for VolatilityArbitrageStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.volatility_arbitrage import (
    VolatilityArbitrageStrategy,
    GARCH11,
)
from quant_nanggroe.types.signals import Signal, SignalType


class TestGARCH11:
    """Test GARCH(1,1) model."""

    def test_fit(self):
        garch = GARCH11()
        returns = np.random.randn(100) * 0.02
        result = garch.fit(returns)
        assert result is garch
        assert garch._fitted is True

    def test_fit_insufficient_data(self):
        garch = GARCH11()
        returns = np.random.randn(5)
        garch.fit(returns)
        assert garch._fitted is False

    def test_forecast(self):
        garch = GARCH11()
        returns = np.random.randn(200) * 0.02
        garch.fit(returns)
        forecasts = garch.forecast(returns, horizon=5)
        assert len(forecasts) == 5
        assert all(f > 0 for f in forecasts)

    def test_half_life(self):
        garch = GARCH11()
        returns = np.random.randn(200) * 0.02
        garch.fit(returns)
        hl = garch.half_life
        if garch._fitted:
            assert hl > 0

    def test_parameters_bounded(self):
        garch = GARCH11()
        returns = np.random.randn(200) * 0.02
        garch.fit(returns)
        if garch._fitted:
            assert garch.omega > 0
            assert garch.alpha >= 0
            assert garch.beta >= 0
            assert garch.alpha + garch.beta < 1.0


class TestVolatilityArbitrageStrategy:
    """Test volatility arbitrage strategy."""

    def test_default_params(self):
        strategy = VolatilityArbitrageStrategy()
        assert strategy.name == "VolatilityArbitrage"
        assert strategy.lookback == 21
        assert strategy.entry_spread == 0.05

    def test_required_columns(self):
        strategy = VolatilityArbitrageStrategy()
        assert "close" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = VolatilityArbitrageStrategy()
        assert strategy.warmup_period() >= 60

    def test_compute_realized_vol(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy()
        vol = strategy.compute_realized_vol(random_ohlcv_data)
        assert vol > 0

    def test_compute_garch_forecast(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy()
        vol = strategy.compute_garch_forecast(random_ohlcv_data)
        assert vol > 0

    def test_compute_implied_vol(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy()
        vol = strategy.compute_implied_vol(random_ohlcv_data)
        assert vol > 0

    def test_compute_implied_vol_with_column(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy()
        data = random_ohlcv_data.copy()
        data["implied_vol"] = 0.3
        vol = strategy.compute_implied_vol(data)
        assert abs(vol - 0.3) < 1e-6

    def test_variance_risk_premium(self):
        strategy = VolatilityArbitrageStrategy()
        vrp = strategy.compute_variance_risk_premium(0.30, 0.20)
        expected = 0.30**2 - 0.20**2
        assert abs(vrp - expected) < 1e-6

    def test_generate_signal(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy(
            params={"entry_spread": 0.01, "symbol": "TEST"}
        )
        signal = strategy.generate_signal(random_ohlcv_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [
                SignalType.BUY, SignalType.SELL, SignalType.EXIT_ALL
            ]

    def test_delta_hedge_simulation(self, random_ohlcv_data):
        strategy = VolatilityArbitrageStrategy()
        result = strategy.simulate_delta_hedge(
            random_ohlcv_data, "short_vol", 0.25
        )
        assert "pnl" in result
        assert "hedge_cost" in result

    def test_insufficient_data(self):
        strategy = VolatilityArbitrageStrategy()
        data = pd.DataFrame({"close": [100, 101, 102]})
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_with_artificial_vol_spread(self, random_ohlcv_data):
        """Test with artificially high implied vol to trigger a signal."""
        strategy = VolatilityArbitrageStrategy(
            params={"entry_spread": 0.001, "symbol": "TEST"}
        )
        data = random_ohlcv_data.copy()
        # Set implied vol very high
        data["implied_vol"] = 5.0  # Unrealistically high
        signal = strategy.generate_signal(data)
        if signal is not None:
            assert isinstance(signal, Signal)
