"""Tests for Options Analyzer Module."""

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


# ── Black-Scholes Tests ────────────────────────────────────────────────


class TestBlackScholes:
    def test_call_price_atm(self):
        """ATM call option pricing."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        price = bs.price(OptionType.CALL)
        assert price > 0
        # ATM call should be approximately 6-7 for these params
        assert 3 < price < 15

    def test_put_price_atm(self):
        """ATM put option pricing."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        price = bs.price(OptionType.PUT)
        assert price > 0
        assert 3 < price < 15

    def test_call_put_parity(self):
        """Call-put parity: C - P = S - K*exp(-rT)."""
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.3
        bs = BlackScholes(S=S, K=K, T=T, r=r, sigma=sigma)
        call = bs.price(OptionType.CALL)
        put = bs.price(OptionType.PUT)
        parity = call - put
        expected = S - K * math.exp(-r * T)
        assert abs(parity - expected) < 0.01

    def test_itm_call_price(self):
        """ITM call should be more expensive than ATM."""
        bs_itm = BlackScholes(S=110, K=100, T=0.25, r=0.02, sigma=0.3)
        bs_atm = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        assert bs_itm.price(OptionType.CALL) > bs_atm.price(OptionType.CALL)

    def test_expired_option(self):
        """At expiration, price should equal intrinsic value."""
        bs = BlackScholes(S=110, K=100, T=0, r=0.02, sigma=0.3)
        call = bs.price(OptionType.CALL)
        put = bs.price(OptionType.PUT)
        assert call == 10.0  # max(0, 110-100)
        assert put == 0.0  # max(0, 100-110)


class TestGreeks:
    def test_call_delta_positive(self):
        """Call delta should be positive (0 to 1)."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        greeks = bs.greeks(OptionType.CALL)
        assert 0 < greeks.delta < 1

    def test_put_delta_negative(self):
        """Put delta should be negative (-1 to 0)."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        greeks = bs.greeks(OptionType.PUT)
        assert -1 < greeks.delta < 0

    def test_gamma_positive(self):
        """Gamma should be positive for both calls and puts."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        call_greeks = bs.greeks(OptionType.CALL)
        put_greeks = bs.greeks(OptionType.PUT)
        assert call_greeks.gamma > 0
        assert put_greeks.gamma > 0
        # Gamma should be the same for calls and puts
        assert abs(call_greeks.gamma - put_greeks.gamma) < 1e-10

    def test_theta_negative(self):
        """Theta should be negative (time decay)."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        greeks = bs.greeks(OptionType.CALL)
        assert greeks.theta < 0

    def test_vega_positive(self):
        """Vega should be positive for both calls and puts."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        call_greeks = bs.greeks(OptionType.CALL)
        put_greeks = bs.greeks(OptionType.PUT)
        assert call_greeks.vega > 0
        assert put_greeks.vega > 0

    def test_expired_greeks(self):
        """Greeks at expiration should be zero or boundary values."""
        bs = BlackScholes(S=110, K=100, T=0, r=0.02, sigma=0.3)
        greeks = bs.greeks(OptionType.CALL)
        assert greeks.gamma == 0.0
        assert greeks.theta == 0.0


class TestImpliedVolatility:
    def test_iv_from_price(self):
        """Calculate IV from a known price."""
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.3
        bs = BlackScholes(S=S, K=K, T=T, r=r, sigma=sigma)
        call_price = bs.price(OptionType.CALL)

        iv_result = bs.implied_volatility(call_price, OptionType.CALL)
        assert iv_result.success
        # IV should be close to the original 30%
        assert abs(iv_result.iv - 30.0) < 1.0

    def test_iv_invalid_price(self):
        """IV should fail for zero or negative prices."""
        bs = BlackScholes(S=100, K=100, T=0.25, r=0.02, sigma=0.3)
        iv = bs.implied_volatility(0, OptionType.CALL)
        assert not iv.success

    def test_iv_below_intrinsic(self):
        """IV should fail if price is below intrinsic value."""
        S, K, T, r = 110, 100, 0.25, 0.02
        bs = BlackScholes(S=S, K=K, T=T, r=r, sigma=0.3)
        intrinsic = max(0, S - K * math.exp(-r * T))
        iv = bs.implied_volatility(intrinsic * 0.5, OptionType.CALL)
        assert not iv.success


# ── Options Analyzer Tests ─────────────────────────────────────────────


class TestOptionsAnalyzer:
    def test_price_option(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        price, greeks = analyzer.price_option(
            S=100, K=100, T=0.25, sigma=0.3, option_type=OptionType.CALL
        )
        assert price > 0
        assert isinstance(greeks, OptionGreeks)

    def test_analyze_chain(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        strikes = [90, 95, 100, 105, 110]
        chain = analyzer.analyze_chain(
            S=100, T=0.25, sigma=0.3, strikes=strikes, option_type=OptionType.CALL
        )
        assert len(chain) == len(strikes)
        for item in chain:
            assert "strike" in item
            assert "price" in item
            assert "delta" in item
            assert "moneyness" in item

    def test_analyze_straddle(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        result = analyzer.analyze_straddle(S=100, K=100, T=0.25, sigma=0.3)
        assert result["strategy"] == "Long Straddle"
        assert result["total_premium"] > 0
        assert result["upper_breakeven"] > 100
        assert result["lower_breakeven"] < 100

    def test_analyze_strangle(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        result = analyzer.analyze_strangle(
            S=100, K_call=110, K_put=90, T=0.25, sigma=0.3
        )
        assert result["strategy"] == "Long Strangle"
        assert result["total_premium"] > 0

    def test_analyze_butterfly(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        result = analyzer.analyze_butterfly(
            S=100, K_low=90, K_mid=100, K_high=110, T=0.25, sigma=0.3
        )
        assert result["strategy"] == "Long Butterfly"
        assert result["max_profit"] > 0
        assert result["max_loss"] > 0

    def test_calculate_iv(self):
        analyzer = OptionsAnalyzer(risk_free_rate=0.02)
        # Generate a price from known vol, then compute IV
        price, _ = analyzer.price_option(
            S=100, K=100, T=0.25, sigma=0.3, option_type=OptionType.CALL
        )
        iv_result = analyzer.calculate_implied_volatility(
            S=100, K=100, T=0.25, market_price=price, option_type=OptionType.CALL
        )
        assert iv_result.success
        assert abs(iv_result.iv - 30.0) < 1.0
