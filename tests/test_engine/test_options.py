"""Tests for Options Analyzer Module (engine/options/analyzer.py)."""

from __future__ import annotations

import math

import pytest

from quant_nanggroe.engine.options.analyzer import (
    BlackScholes,
    ImpliedVolatilityResult,
    OptionGreeks,
    OptionType,
    OptionsAnalyzer,
)


class TestBlackScholes:
    def test_call_price_atm(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        price = bs.price(OptionType.CALL)
        assert price > 0
        assert 3 < price < 15

    def test_put_price_atm(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        price = bs.price(OptionType.PUT)
        assert price > 0
        assert 3 < price < 15

    def test_call_put_parity(self):
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.3
        bs = BlackScholes(S=S, K=K, T=T, r=r, sigma=sigma)
        parity = bs.price(OptionType.CALL) - bs.price(OptionType.PUT)
        expected = S - K * math.exp(-r * T)
        assert abs(parity - expected) < 0.01

    def test_itm_call_pricier_than_atm(self):
        bs_itm = BlackScholes(S=110, K=100, T=0.25, r=0.02, sigma=0.3)
        bs_atm = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert bs_itm.price(OptionType.CALL) > bs_atm.price(OptionType.CALL)

    def test_expired_option(self):
        bs = BlackScholes(S=110, K=100, T=0, r=0.02, sigma=0.3)
        assert bs.price(OptionType.CALL) == 10.0
        assert bs.price(OptionType.PUT) == 0.0


class TestGreeks:
    def test_call_delta_positive(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert 0 < bs.greeks().delta < 1

    def test_put_delta_negative(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert -1 < bs.greeks(OptionType.PUT).delta < 0

    def test_gamma_positive_and_symmetric(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        cg, pg = bs.greeks().gamma, bs.greeks(OptionType.PUT).gamma
        assert cg > 0 and pg > 0
        assert abs(cg - pg) < 1e-10

    def test_theta_negative(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert bs.greeks().theta < 0

    def test_vega_positive(self):
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert bs.greeks().vega > 0

    def test_expired_greeks_zero(self):
        bs = BlackScholes(S=110, K=100, T=0, r=0.02, sigma=0.3)
        g = bs.greeks()
        assert g.gamma == 0.0 and g.theta == 0.0


class TestOptionsAnalyzer:
    def test_calculate_iv_roundtrip(self):
        # Price at known vol, recover it via Newton-Raphson
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.3
        price = BlackScholes(S, K, T, r, sigma).price(OptionType.CALL)
        res = OptionsAnalyzer().calculate_iv(S, K, T, r, price, OptionType.CALL)
        assert isinstance(res, ImpliedVolatilityResult)
        assert res.converged
        assert abs(res.iv - sigma) < 1e-3

    def test_calculate_iv_invalid_price(self):
        res = OptionsAnalyzer().calculate_iv(100, 100, 0.25, 0.02, 0.0, OptionType.CALL)
        assert not res.converged

    def test_analyze(self):
        out = OptionsAnalyzer().analyze(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert "call_price" in out and "put_price" in out
        assert isinstance(out["greeks"], OptionGreeks)
