"""
Tests for Market State Engine — Regime Detection
==================================================
Test PANIC, RISK_OFF, TRENDING_UP/DOWN, NO_TRADE override,
and volatility/liquidity classification.
"""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.engine.market_state import MarketStateEngine, MarketStateResult
from quant_nanggroe_ai.types import MarketRegime, VolatilityLevel, LiquidityLevel


class TestPanicDetection:
    """Test PANIC regime detection (> 5% drop in 5 days)."""

    def test_panic_on_extreme_drop(self, market_engine: MarketStateEngine) -> None:
        """5-day drop > 5% should trigger PANIC regime."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-6.0,
        )
        assert result.base_regime == MarketRegime.PANIC
        # PANIC always triggers NO_TRADE override
        assert result.regime == MarketRegime.NO_TRADE
        assert not result.trade_allowed

    def test_panic_overrides_trending(self, market_engine: MarketStateEngine) -> None:
        """PANIC should override even with strong ADX."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-5.5,
            adx=40.0,
        )
        assert result.base_regime == MarketRegime.PANIC


class TestRiskOffDetection:
    """Test RISK_OFF regime detection (> 2% drop in 5 days)."""

    def test_risk_off_on_significant_decline(self, market_engine: MarketStateEngine) -> None:
        """5-day drop > 2% (but < 5%) should trigger RISK_OFF."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-3.0,
        )
        assert result.base_regime == MarketRegime.RISK_OFF
        assert not result.trade_allowed

    def test_risk_off_boundary(self, market_engine: MarketStateEngine) -> None:
        """5-day drop at exactly -2% should NOT trigger RISK_OFF (needs < -2%)."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-2.0,
        )
        # -2.0 is NOT < -2.0, so it falls through to next check
        assert result.base_regime != MarketRegime.RISK_OFF

    def test_risk_off_just_past_threshold(self, market_engine: MarketStateEngine) -> None:
        """5-day drop just past -2% should trigger RISK_OFF."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-2.01,
        )
        assert result.base_regime == MarketRegime.RISK_OFF


class TestTrendingRegimes:
    """Test TRENDING_UP and TRENDING_DOWN detection."""

    def test_trending_up_with_bullish_ema(self, market_engine: MarketStateEngine) -> None:
        """ADX > 25 + bullish EMA should be TRENDING_UP."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=1.0,
            adx=30.0,
            ema_trend="bullish",
        )
        assert result.regime == MarketRegime.TRENDING_UP
        assert result.trade_allowed

    def test_trending_up_with_positive_daily(self, market_engine: MarketStateEngine) -> None:
        """ADX > 25 + positive 1d change > 0.5% should be TRENDING_UP."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=0.0,
            price_change_1d=1.0,
            adx=30.0,
        )
        assert result.regime == MarketRegime.TRENDING_UP

    def test_trending_down_with_bearish_ema(self, market_engine: MarketStateEngine) -> None:
        """ADX > 25 + bearish EMA should be TRENDING_DOWN."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=0.0,
            adx=30.0,
            ema_trend="bearish",
        )
        assert result.regime == MarketRegime.TRENDING_DOWN
        assert result.trade_allowed

    def test_trending_down_with_negative_daily(self, market_engine: MarketStateEngine) -> None:
        """ADX > 25 + negative 1d change < -0.5% should be TRENDING_DOWN."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=0.0,
            price_change_1d=-1.0,
            adx=30.0,
        )
        assert result.regime == MarketRegime.TRENDING_DOWN

    def test_trending_neutral_direction(self, market_engine: MarketStateEngine) -> None:
        """ADX > 25 + neutral EMA and small daily change should be TRENDING."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=0.0,
            price_change_1d=0.1,
            adx=28.0,
            ema_trend="neutral",
        )
        assert result.regime == MarketRegime.TRENDING


class TestNoTradeOverride:
    """Test NO_TRADE override conditions."""

    def test_no_trade_on_panic(self, market_engine: MarketStateEngine) -> None:
        """PANIC regime should always override to NO_TRADE."""
        result = market_engine.detect_regime(
            symbol="SPY",
            price_change_5d=-10.0,
        )
        assert result.regime == MarketRegime.NO_TRADE
        assert "Panic regime" in result.no_trade_reasons[0]
        assert result.trade_allowed is False

    def test_no_trade_high_vol_thin_liquidity(self, market_engine: MarketStateEngine) -> None:
        """High volatility + thin liquidity should trigger NO_TRADE."""
        result = market_engine.detect_regime(
            symbol="XAUUSD",
            price_change_5d=0.0,
            atr_pct=3.0,        # > 2.5% = HIGH volatility
            volume_ratio=0.3,   # < 0.4 = THIN liquidity
        )
        assert result.regime == MarketRegime.NO_TRADE
        assert any("thin liquidity" in r.lower() for r in result.no_trade_reasons)

    def test_no_trade_extremely_low_volume(self, market_engine: MarketStateEngine) -> None:
        """Volume ratio < 0.2 should trigger NO_TRADE."""
        result = market_engine.detect_regime(
            symbol="XAUUSD",
            price_change_5d=0.0,
            atr_pct=1.0,        # NORMAL volatility
            volume_ratio=0.15,  # < 0.2 = extremely low
        )
        assert result.regime == MarketRegime.NO_TRADE
        assert any("low volume" in r.lower() for r in result.no_trade_reasons)

    def test_no_override_when_conditions_safe(self, market_engine: MarketStateEngine) -> None:
        """Normal conditions should NOT trigger NO_TRADE override."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            price_change_5d=0.5,
            adx=30.0,
            atr_pct=1.0,
            volume_ratio=1.0,
            ema_trend="bullish",
        )
        assert result.regime != MarketRegime.NO_TRADE
        assert result.trade_allowed is True
        assert len(result.no_trade_reasons) == 0


class TestVolatilityClassification:
    """Test volatility level classification."""

    def test_high_volatility(self, market_engine: MarketStateEngine) -> None:
        """ATR > 2.5% of price should be HIGH volatility."""
        result = market_engine.detect_regime(
            symbol="XAUUSD",
            atr_pct=3.0,
        )
        assert result.volatility == VolatilityLevel.HIGH

    def test_low_volatility(self, market_engine: MarketStateEngine) -> None:
        """ATR < 0.5% of price should be LOW volatility."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            atr_pct=0.3,
        )
        assert result.volatility == VolatilityLevel.LOW

    def test_normal_volatility(self, market_engine: MarketStateEngine) -> None:
        """ATR between 0.5% and 2.5% should be NORMAL volatility."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            atr_pct=1.2,
        )
        assert result.volatility == VolatilityLevel.NORMAL


class TestLiquidityClassification:
    """Test liquidity level classification."""

    def test_thin_liquidity(self, market_engine: MarketStateEngine) -> None:
        """Volume ratio < 0.4 should be THIN liquidity."""
        result = market_engine.detect_regime(
            symbol="XAUUSD",
            volume_ratio=0.3,
        )
        assert result.liquidity == LiquidityLevel.THIN

    def test_deep_liquidity(self, market_engine: MarketStateEngine) -> None:
        """Volume ratio > 1.8 should be DEEP liquidity."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            volume_ratio=2.0,
        )
        assert result.liquidity == LiquidityLevel.DEEP

    def test_normal_liquidity(self, market_engine: MarketStateEngine) -> None:
        """Volume ratio between 0.4 and 1.8 should be NORMAL liquidity."""
        result = market_engine.detect_regime(
            symbol="EURUSD",
            volume_ratio=1.0,
        )
        assert result.liquidity == LiquidityLevel.NORMAL


class TestMarketStateHistory:
    """Test regime history tracking."""

    def test_regime_history_tracks(self, market_engine: MarketStateEngine) -> None:
        """Engine should track regime history."""
        market_engine.detect_regime(symbol="EURUSD", price_change_5d=0.5, adx=30.0, ema_trend="bullish")
        market_engine.detect_regime(symbol="EURUSD", price_change_5d=-3.0)
        assert len(market_engine.regime_history) == 2

    def test_regime_history_capped_at_100(self, market_engine: MarketStateEngine) -> None:
        """Regime history should not exceed 100 entries."""
        for i in range(110):
            market_engine.detect_regime(symbol="EURUSD", price_change_5d=float(i % 10 - 5))
        assert len(market_engine.regime_history) <= 100

    def test_get_regime_returns_current(self, market_engine: MarketStateEngine) -> None:
        """get_regime should return the most recent regime."""
        market_engine.detect_regime(symbol="EURUSD", price_change_5d=-6.0)
        assert market_engine.get_regime() == MarketRegime.NO_TRADE

    def test_result_contains_inputs(self, market_engine: MarketStateEngine) -> None:
        """MarketStateResult should record all input parameters."""
        result = market_engine.detect_regime(
            symbol="XAUUSD",
            price_change_5d=2.0,
            price_change_1d=0.5,
            adx=35.0,
            rsi=65.0,
            atr_pct=1.5,
            volume_ratio=1.2,
            ema_trend="bullish",
        )
        assert "price_change_5d" in result.inputs
        assert "adx" in result.inputs
        assert result.inputs["ema_trend"] == "bullish"
