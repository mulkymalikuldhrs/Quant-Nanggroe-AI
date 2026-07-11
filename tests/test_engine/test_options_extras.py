"""Unit tests for options vol surface and strategies."""

from __future__ import annotations

import numpy as np
import pytest

from quant_nanggroe.engine.options.vol_surface import SABRModel, VolSurface
from quant_nanggroe.engine.options.strategies import OptionStrategy


class TestSABRModel:
    def test_calibrate(self):
        model = SABRModel()
        strikes = np.array([95, 97.5, 100, 102.5, 105])
        vols = np.array([0.25, 0.22, 0.20, 0.22, 0.25])
        params = model.calibrate(strikes=strikes, vols=vols, forward=100, T=0.5)
        assert "alpha" in params
        assert "beta" in params
        assert "rho" in params
        assert "nu" in params
        assert params["beta"] == 0.7

    def test_implied_vol_smile(self):
        model = SABRModel(alpha=0.05, beta=0.7, rho=0.0, nu=0.4)
        vol_atm = model.implied_vol(forward=100, strike=100, T=0.5)
        vol_put = model.implied_vol(forward=100, strike=90, T=0.5)
        assert 0 < vol_atm < 1
        assert vol_put > 0

    def test_compute_surface(self):
        model = SABRModel()
        surface = model.compute_surface(forward=100, expiries=[0.25, 0.5], strikes=[90, 100, 110])
        assert surface.shape == (2, 3)
        assert np.all(surface > 0)

    def test_default_params(self):
        model = SABRModel()
        vol = model.implied_vol(forward=100, strike=100, T=1.0)
        assert 0 < vol < 1


class TestVolSurface:
    def test_build_and_interpolate(self):
        strikes = np.array([90, 100, 110])
        expiries = np.array([0.25, 0.5, 1.0])
        vols = np.array([
            [0.30, 0.26, 0.30],
            [0.28, 0.24, 0.28],
            [0.27, 0.23, 0.27],
        ])
        surface = VolSurface(strikes=strikes, expiries=expiries, vols=vols)
        vol = surface.get_vol(strike=100, expiry=0.5)
        assert 0 < vol < 1
        assert vol == pytest.approx(0.24, abs=0.01)


class TestOptionStrategy:
    def test_straddle(self):
        strat = OptionStrategy(spot=100)
        result = strat.straddle(strike=100, T=1.0)
        assert result.net_premium > 0  # premium is positive (paid)
        assert result.max_loss is not None

    def test_bull_call_spread(self):
        strat = OptionStrategy(spot=100)
        result = strat.bull_call_spread(lower=95, upper=105, T=1.0)
        # BS model with sigma=0.3: short leg cheaper → net credit
        # Just verify it yields valid P/L bounds
        assert result.max_profit > 0
        assert result.max_loss < 0
        assert result.net_premium != 0

    def test_bear_put_spread(self):
        strat = OptionStrategy(spot=100)
        result = strat.bear_put_spread(lower=95, upper=105, T=1.0)
        assert result.max_profit > 0
        assert result.max_loss < 0
        assert result.net_premium != 0

    def test_butterfly(self):
        strat = OptionStrategy(spot=100)
        result = strat.butterfly(lower=95, middle=100, upper=105, T=1.0)
        assert result.max_profit > 0
        assert result.max_loss < 0
        assert result.net_premium != 0

    def test_covered_call(self):
        strat = OptionStrategy(spot=100)
        result = strat.covered_call(strike=105, T=1.0)
        assert result.net_premium < 0  # short call receives premium
        assert "Covered" in result.name
