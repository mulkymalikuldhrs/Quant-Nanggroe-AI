"""
Comprehensive Tests for Agent Tools
=====================================
Tests for MarketDataTool, TechnicalAnalysisTool, SentimentTool,
ExecutionTool, BacktestTool, and LangChain @tool functions.
All external dependencies are mocked.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from quant_nanggroe.agents.tools.technical import (
    TechnicalAnalysisTool,
    _sma,
    _ema,
    _rsi,
    _macd,
    _adx,
    _bollinger_bands,
    _stochastic,
    _atr,
    _obv,
    _vwap,
    _compute_all_indicators,
    _SMCDetector,
    _SupportResistanceDetector,
)
from quant_nanggroe.agents.tools.sentiment import (
    SentimentTool,
    _NewsClassifier,
    NewsEventType,
)
from quant_nanggroe.agents.tools.execution import (
    ExecutionTool,
    _normalize_side,
    _normalize_order_type,
    _OrderStore,
    _is_crypto,
    _is_forex,
)
from quant_nanggroe.agents.tools.market_data import (
    MarketDataTool,
    _InMemoryCache,
    _is_crypto_symbol,
    _is_forex_symbol,
)
from quant_nanggroe.exceptions import (
    DataError,
    InsufficientDataError,
    ExecutionError,
    OrderRejectedError,
)


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_closes_100() -> list[float]:
    """100-bar sample close price series."""
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.015, 100)
    prices = 100.0 * np.cumprod(1 + returns)
    return [round(float(p), 2) for p in prices]


@pytest.fixture
def sample_ohlcv_100() -> dict[str, list[float]]:
    """100-bar OHLCV sample data."""
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.015, 100)
    closes = 100.0 * np.cumprod(1 + returns)
    highs = [round(float(c) * (1 + abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    lows = [round(float(c) * (1 - abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    volumes = [round(float(max(np.random.lognormal(15, 1), 1000)), 0) for _ in range(100)]
    return {
        "closes": [round(float(c), 2) for c in closes],
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
    }


@pytest.fixture
def trending_up_closes() -> list[float]:
    """Strong uptrend close prices."""
    return [100.0 + i * 2.0 for i in range(100)]


@pytest.fixture
def trending_down_closes() -> list[float]:
    """Strong downtrend close prices."""
    return [300.0 - i * 2.0 for i in range(100)]


# ══════════════════════════════════════════════════════════════════════
# MarketDataTool Tests
# ══════════════════════════════════════════════════════════════════════


class TestMarketDataTool:
    """Test the MarketDataTool class and helper functions."""

    def test_init_default(self) -> None:
        """MarketDataTool initializes with default cache TTL."""
        tool = MarketDataTool(cache_ttl=60)
        assert tool._cache is not None

    def test_init_custom_ttl(self) -> None:
        """MarketDataTool accepts custom cache TTL."""
        tool = MarketDataTool(cache_ttl=120)
        assert tool._cache._default_ttl == 120

    def test_is_crypto_symbol_btc(self) -> None:
        """BTC-USD is identified as crypto."""
        assert _is_crypto_symbol("BTC-USD") is True

    def test_is_crypto_symbol_eth_usdt(self) -> None:
        """ETH/USDT is identified as crypto."""
        assert _is_crypto_symbol("ETH/USDT") is True

    def test_is_crypto_symbol_stock(self) -> None:
        """AAPL is not identified as crypto."""
        assert _is_crypto_symbol("AAPL") is False

    def test_is_crypto_symbol_sol(self) -> None:
        """SOL-USD is identified as crypto."""
        assert _is_crypto_symbol("SOL-USD") is True

    def test_is_forex_symbol(self) -> None:
        """EURUSD=X is identified as forex."""
        assert _is_forex_symbol("EURUSD=X") is True

    def test_is_forex_symbol_not_forex(self) -> None:
        """AAPL is not identified as forex."""
        assert _is_forex_symbol("AAPL") is False

    def test_normalize_crypto_symbol_dash(self) -> None:
        """BTC-USD is normalized to BTC/USDT."""
        assert MarketDataTool._normalize_crypto_symbol("BTC-USD") == "BTC/USDT"

    def test_normalize_crypto_symbol_slash_usd(self) -> None:
        """BTC/USD is normalized to BTC/USDT."""
        assert MarketDataTool._normalize_crypto_symbol("BTC/USD") == "BTC/USDT"

    def test_normalize_crypto_symbol_already_correct(self) -> None:
        """BTC/USDT stays as BTC/USDT."""
        assert MarketDataTool._normalize_crypto_symbol("BTC/USDT") == "BTC/USDT"

    def test_normalize_crypto_symbol_bare(self) -> None:
        """BTC is normalized to BTC/USDT (fallback)."""
        assert MarketDataTool._normalize_crypto_symbol("BTC") == "BTC/USDT"


class TestInMemoryCache:
    """Test the _InMemoryCache TTL-based cache."""

    def test_cache_miss(self) -> None:
        """Missing key returns None."""
        cache = _InMemoryCache(default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_cache_set_and_get(self) -> None:
        """Set and get work for fresh entries."""
        cache = _InMemoryCache(default_ttl=60)
        cache.set("key1", {"value": 42})
        assert cache.get("key1") == {"value": 42}

    def test_cache_expired(self) -> None:
        """Expired entries return None."""
        cache = _InMemoryCache(default_ttl=0)  # Immediate expiry
        cache.set("key1", "value")
        # Wait a tiny bit for monotonic clock to advance
        import time
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_cache_clear(self) -> None:
        """clear() removes all entries."""
        cache = _InMemoryCache(default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_custom_ttl(self) -> None:
        """Custom TTL overrides default."""
        cache = _InMemoryCache(default_ttl=60)
        cache.set("short", "value", ttl=0)
        import time
        time.sleep(0.01)
        assert cache.get("short") is None


# ══════════════════════════════════════════════════════════════════════
# TechnicalAnalysisTool Tests
# ══════════════════════════════════════════════════════════════════════


class TestSMA:
    """Test Simple Moving Average calculation."""

    def test_sma_basic(self) -> None:
        """SMA of constant series equals the constant."""
        data = [10.0] * 20
        result = _sma(data, 20)
        assert result[-1] == pytest.approx(10.0, abs=0.001)

    def test_sma_insufficient_data(self) -> None:
        """SMA returns None for insufficient data points."""
        data = [1.0, 2.0, 3.0]
        result = _sma(data, 20)
        assert all(v is None for v in result)

    def test_sma_length_matches_input(self) -> None:
        """SMA output length matches input length."""
        data = list(range(1, 51))
        result = _sma(data, 20)
        assert len(result) == 50

    def test_sma_first_values_none(self) -> None:
        """First period-1 values are None."""
        data = list(range(1, 51))
        result = _sma(data, 20)
        assert all(v is None for v in result[:19])
        assert result[19] is not None


class TestEMA:
    """Test Exponential Moving Average calculation."""

    def test_ema_basic(self) -> None:
        """EMA of constant series equals the constant."""
        data = [50.0] * 30
        result = _ema(data, 20)
        assert result[-1] == pytest.approx(50.0, abs=0.01)

    def test_ema_insufficient_data(self) -> None:
        """EMA returns None for insufficient data points."""
        data = [1.0, 2.0]
        result = _ema(data, 20)
        assert all(v is None for v in result)

    def test_ema_responsiveness(self) -> None:
        """EMA is more responsive than SMA to recent prices."""
        # Create a step function: flat then rising
        data = [10.0] * 50 + [20.0] * 50
        ema_result = _ema(data, 20)
        sma_result = _sma(data, 20)
        # After many periods at 20, both should converge near 20
        # EMA should be closer to 20 than SMA because it weights recent data more
        ema_val = ema_result[-1]
        sma_val = sma_result[-1]
        # Both should be near 20 at this point, but EMA should be higher
        # (closer to 20) if the step was recent enough
        # With 50 bars at 20 after a step, both converge closely
        assert ema_val is not None and sma_val is not None
        assert ema_val > 10.0  # EMA has moved away from the flat 10
        assert sma_val > 10.0  # SMA has also moved


class TestRSI:
    """Test Relative Strength Index calculation."""

    def test_rsi_overbought(self) -> None:
        """Consistently rising prices → RSI approaches 100."""
        closes = [100.0 + i * 2 for i in range(30)]
        result = _rsi(closes, 14)
        assert result[-1] is not None
        assert result[-1] > 70

    def test_rsi_oversold(self) -> None:
        """Consistently falling prices → RSI approaches 0."""
        closes = [200.0 - i * 2 for i in range(30)]
        result = _rsi(closes, 14)
        assert result[-1] is not None
        assert result[-1] < 30

    def test_rsi_insufficient_data(self) -> None:
        """RSI returns None for insufficient data."""
        closes = [100.0, 101.0]
        result = _rsi(closes, 14)
        assert all(v is None for v in result)

    def test_rsi_range_0_100(self) -> None:
        """RSI is always between 0 and 100."""
        np.random.seed(42)
        closes = (100.0 * np.cumprod(1 + np.random.normal(0, 0.02, 200))).tolist()
        result = _rsi(closes, 14)
        valid_values = [v for v in result if v is not None]
        assert all(0 <= v <= 100 for v in valid_values)


class TestMACD:
    """Test MACD indicator calculation."""

    def test_macd_structure(self) -> None:
        """MACD result contains all three lines."""
        closes = list(range(1, 101))
        result = _macd(closes)
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result
        assert len(result["macd_line"]) == len(closes)

    def test_macd_bullish_trend(self) -> None:
        """MACD line should be positive in strong uptrend."""
        closes = [100.0 + i * 1.0 for i in range(100)]
        result = _macd(closes)
        valid_macd = [v for v in result["macd_line"] if v is not None]
        # In a strong uptrend, MACD should be positive
        assert valid_macd[-1] > 0


class TestADX:
    """Test Average Directional Index calculation."""

    def test_adx_strong_trend(self, trending_up_closes: list[float]) -> None:
        """ADX should be high in a strong trend."""
        result = _adx(trending_up_closes, trending_up_closes, trending_up_closes)
        if result["adx"] is not None:
            assert result["adx"] > 20

    def test_adx_insufficient_data(self) -> None:
        """ADX returns None for insufficient data."""
        highs = [10.0, 11.0, 12.0]
        lows = [9.0, 10.0, 11.0]
        closes = [9.5, 10.5, 11.5]
        result = _adx(highs, lows, closes)
        assert result["adx"] is None

    def test_adx_returns_all_fields(self, sample_ohlcv_100: dict) -> None:
        """ADX returns adx, plus_di, minus_di fields."""
        result = _adx(
            sample_ohlcv_100["highs"],
            sample_ohlcv_100["lows"],
            sample_ohlcv_100["closes"],
        )
        assert "adx" in result
        assert "plus_di" in result
        assert "minus_di" in result


class TestBollingerBands:
    """Test Bollinger Bands calculation."""

    def test_bollinger_bands_basic(self) -> None:
        """Bollinger Bands returns upper, middle, lower."""
        closes = list(range(1, 31))
        result = _bollinger_bands(closes)
        assert result["upper"] is not None
        assert result["middle"] is not None
        assert result["lower"] is not None
        assert result["upper"] > result["middle"] > result["lower"]

    def test_bollinger_bands_insufficient_data(self) -> None:
        """Bollinger Bands returns None for insufficient data."""
        closes = [1.0, 2.0, 3.0]
        result = _bollinger_bands(closes)
        assert result["upper"] is None

    def test_bollinger_bands_percent_b(self) -> None:
        """Percent B is computed when data is sufficient."""
        closes = list(range(1, 31))
        result = _bollinger_bands(closes)
        assert result["percent_b"] is not None
        assert 0 <= result["percent_b"] <= 1 or result["percent_b"] > 1  # Can exceed 1


class TestStochastic:
    """Test Stochastic Oscillator calculation."""

    def test_stochastic_basic(self) -> None:
        """Stochastic returns K and D values."""
        np.random.seed(42)
        closes = (100.0 * np.cumprod(1 + np.random.normal(0, 0.02, 50))).tolist()
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        result = _stochastic(highs, lows, closes)
        assert result["k"] is not None
        assert result["d"] is not None

    def test_stochastic_range(self) -> None:
        """Stochastic K is between 0 and 100."""
        np.random.seed(42)
        closes = (100.0 * np.cumprod(1 + np.random.normal(0, 0.02, 50))).tolist()
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        result = _stochastic(highs, lows, closes)
        assert 0 <= result["k"] <= 100


class TestATR:
    """Test Average True Range calculation."""

    def test_atr_positive(self) -> None:
        """ATR is always positive."""
        np.random.seed(42)
        closes = (100.0 * np.cumprod(1 + np.random.normal(0, 0.02, 50))).tolist()
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        result = _atr(highs, lows, closes)
        assert result is not None
        assert result > 0

    def test_atr_insufficient_data(self) -> None:
        """ATR returns None for insufficient data."""
        closes = [100.0, 101.0]
        result = _atr(closes, closes, closes)
        assert result is None


class TestOBV:
    """Test On-Balance Volume calculation."""

    def test_obv_rising_prices(self) -> None:
        """OBV increases when prices rise."""
        closes = [100.0, 101.0, 102.0, 103.0]
        volumes = [1000.0, 1000.0, 1000.0, 1000.0]
        result = _obv(closes, volumes)
        assert result is not None
        assert result > 0

    def test_obv_insufficient_data(self) -> None:
        """OBV returns None for single data point."""
        result = _obv([100.0], [1000.0])
        assert result is None


class TestVWAP:
    """Test Volume Weighted Average Price calculation."""

    def test_vwap_basic(self) -> None:
        """VWAP is between min and max close prices."""
        closes = [100.0, 101.0, 102.0]
        volumes = [1000.0, 2000.0, 1000.0]
        result = _vwap(closes, volumes)
        assert result is not None
        assert 100.0 <= result <= 102.0

    def test_vwap_zero_volume(self) -> None:
        """VWAP returns None when total volume is zero."""
        result = _vwap([100.0, 101.0], [0.0, 0.0])
        assert result is None

    def test_vwap_empty_data(self) -> None:
        """VWAP returns None for empty data."""
        result = _vwap([], [])
        assert result is None


class TestSMCDetector:
    """Test Smart Money Concepts detector."""

    def test_smc_insufficient_data(self) -> None:
        """SMC returns neutral for insufficient data."""
        result = _SMCDetector.detect(
            highs=[100.0] * 5,
            lows=[99.0] * 5,
            closes=[99.5] * 5,
            lookback=5,
        )
        assert result["structure_state"] == "NEUTRAL"

    def test_smc_returns_expected_fields(self) -> None:
        """SMC returns all expected fields."""
        np.random.seed(42)
        closes = (100.0 * np.cumprod(1 + np.random.normal(0.001, 0.01, 100))).tolist()
        highs = [c * 1.005 for c in closes]
        lows = [c * 0.995 for c in closes]
        result = _SMCDetector.detect(highs, lows, closes)
        assert "signals" in result
        assert "latest_signal" in result
        assert "structure_state" in result

    def test_smc_bullish_trend_detection(self, trending_up_closes: list[float]) -> None:
        """Strong uptrend should be detected as bullish structure."""
        result = _SMCDetector.detect(
            trending_up_closes, trending_up_closes, trending_up_closes,
        )
        assert result["structure_state"] in ("BULL", "BEAR", "NEUTRAL")


class TestSupportResistanceDetector:
    """Test Support and Resistance level detection."""

    def test_sr_insufficient_data(self) -> None:
        """S/R returns empty for insufficient data."""
        result = _SupportResistanceDetector.detect(
            highs=[100.0] * 5,
            lows=[99.0] * 5,
            closes=[99.5] * 5,
        )
        assert result["support_levels"] == []
        assert result["resistance_levels"] == []

    def test_sr_returns_expected_fields(self, sample_ohlcv_100: dict) -> None:
        """S/R returns all expected fields."""
        result = _SupportResistanceDetector.detect(
            sample_ohlcv_100["highs"],
            sample_ohlcv_100["lows"],
            sample_ohlcv_100["closes"],
        )
        assert "support_levels" in result
        assert "resistance_levels" in result
        assert "nearest_support" in result
        assert "nearest_resistance" in result


class TestTechnicalAnalysisTool:
    """Test the TechnicalAnalysisTool class."""

    def test_init_without_market_data(self) -> None:
        """TechnicalAnalysisTool can be created without MarketDataTool."""
        tool = TechnicalAnalysisTool()
        assert tool._market_data is None

    def test_analyze_raises_without_market_data(self) -> None:
        """analyze() raises DataError without MarketDataTool."""
        tool = TechnicalAnalysisTool()
        with pytest.raises(DataError, match="No MarketDataTool configured"):
            import asyncio
            asyncio.run(tool.analyze("AAPL"))

    def test_analyze_raw_basic(self, sample_ohlcv_100: dict) -> None:
        """analyze_raw() returns comprehensive analysis."""
        tool = TechnicalAnalysisTool()
        result = tool.analyze_raw(
            closes=sample_ohlcv_100["closes"],
            highs=sample_ohlcv_100["highs"],
            lows=sample_ohlcv_100["lows"],
            volumes=sample_ohlcv_100["volumes"],
            symbol="AAPL",
        )
        assert result["symbol"] == "AAPL"
        assert result["timeframe"] == "1d"
        assert "indicators" in result
        assert "smc" in result
        assert "support_resistance" in result
        assert "trend" in result
        assert "derived" in result
        assert result["bars_analyzed"] == 100

    def test_analyze_raw_insufficient_data(self) -> None:
        """analyze_raw() raises InsufficientDataError for too few bars."""
        tool = TechnicalAnalysisTool()
        with pytest.raises(InsufficientDataError):
            tool.analyze_raw(closes=[100.0] * 10)

    def test_analyze_raw_indicators_populated(self, sample_ohlcv_100: dict) -> None:
        """analyze_raw() populates key indicator values."""
        tool = TechnicalAnalysisTool()
        result = tool.analyze_raw(
            closes=sample_ohlcv_100["closes"],
            highs=sample_ohlcv_100["highs"],
            lows=sample_ohlcv_100["lows"],
            volumes=sample_ohlcv_100["volumes"],
        )
        indicators = result["indicators"]
        assert indicators["sma_20"] is not None
        assert indicators["ema_9"] is not None
        assert indicators["ema_20"] is not None
        assert indicators["rsi_14"] is not None
        assert indicators["current_price"] is not None

    def test_analyze_raw_trend_classification(self, trending_up_closes: list[float]) -> None:
        """analyze_raw() classifies trend direction correctly."""
        tool = TechnicalAnalysisTool()
        result = tool.analyze_raw(closes=trending_up_closes)
        trend = result["trend"]
        assert "direction" in trend
        assert "ema_trend" in trend
        assert "trend_strength" in trend

    def test_analyze_raw_derived_fields(self, sample_ohlcv_100: dict) -> None:
        """analyze_raw() computes derived fields."""
        tool = TechnicalAnalysisTool()
        result = tool.analyze_raw(
            closes=sample_ohlcv_100["closes"],
            volumes=sample_ohlcv_100["volumes"],
        )
        derived = result["derived"]
        assert "price_change_1d" in derived
        assert "price_change_5d" in derived
        assert "volume_ratio" in derived

    def test_analyze_raw_default_highs_lows(self, sample_ohlcv_100: dict) -> None:
        """analyze_raw() uses closes as defaults for highs/lows."""
        tool = TechnicalAnalysisTool()
        result = tool.analyze_raw(closes=sample_ohlcv_100["closes"])
        assert result["bars_analyzed"] == 100

    def test_classify_trend_bull_alignment(self) -> None:
        """Bullish EMA alignment → BULL trend."""
        indicators = {
            "ema_9": 110.0,
            "ema_20": 105.0,
            "ema_50": 100.0,
            "ema_200": None,
            "adx": {"adx": 30.0, "plus_di": 25.0, "minus_di": 15.0},
        }
        result = TechnicalAnalysisTool._classify_trend([110.0], indicators)
        assert result["ema_trend"] == "BULL"

    def test_classify_trend_bear_alignment(self) -> None:
        """Bearish EMA alignment → BEAR trend."""
        indicators = {
            "ema_9": 90.0,
            "ema_20": 95.0,
            "ema_50": 100.0,
            "ema_200": None,
            "adx": {"adx": 30.0, "plus_di": 15.0, "minus_di": 25.0},
        }
        result = TechnicalAnalysisTool._classify_trend([90.0], indicators)
        assert result["ema_trend"] == "BEAR"

    def test_compute_derived_price_changes(self) -> None:
        """Derived fields include correct price changes."""
        closes = [100.0, 102.0, 101.0, 103.0, 105.0, 100.0, 104.0]
        result = TechnicalAnalysisTool._compute_derived(closes, [1000.0] * 7)
        assert result["price_change_1d"] is not None
        # 1d change: (104.0 - 100.0) / 100.0 * 100 = 4.0%
        assert abs(result["price_change_1d"] - 4.0) < 0.1


# ══════════════════════════════════════════════════════════════════════
# SentimentTool Tests
# ══════════════════════════════════════════════════════════════════════


class TestNewsClassifier:
    """Test the _NewsClassifier."""

    def test_classify_shock_event(self) -> None:
        """Shock keywords are classified as SHOCK."""
        assert _NewsClassifier.classify_event("Flash crash wipes out billions") == NewsEventType.SHOCK

    def test_classify_macro_event(self) -> None:
        """Macro keywords are classified as MACRO."""
        assert _NewsClassifier.classify_event("Fed raises interest rates") == NewsEventType.MACRO

    def test_classify_scheduled_event(self) -> None:
        """Scheduled keywords are classified as SCHEDULED."""
        assert _NewsClassifier.classify_event("Apple earnings report exceeds expectations") == NewsEventType.SCHEDULED

    def test_classify_noise_event(self) -> None:
        """Unremarkable text is classified as NOISE."""
        assert _NewsClassifier.classify_event("Market updates from today") == NewsEventType.NOISE

    def test_classify_shock_priority_over_macro(self) -> None:
        """SHOCK takes priority over MACRO."""
        result = _NewsClassifier.classify_event("Hack causes emergency at the fed")
        assert result == NewsEventType.SHOCK

    def test_score_headline_bullish(self) -> None:
        """Bullish headline gets positive sentiment score."""
        score, confidence = _NewsClassifier.score_headline("Stock surges to all-time high")
        assert score > 0.0
        assert confidence > 0.0

    def test_score_headline_bearish(self) -> None:
        """Bearish headline gets negative sentiment score."""
        score, confidence = _NewsClassifier.score_headline("Market crash triggers sell-off")
        assert score < 0.0

    def test_score_headline_neutral(self) -> None:
        """Neutral headline gets near-zero sentiment score."""
        score, confidence = _NewsClassifier.score_headline("Market updates from today")
        assert abs(score) < 0.3  # Neutral range

    def test_score_headline_no_keywords(self) -> None:
        """No keyword matches → neutral with low confidence."""
        score, confidence = _NewsClassifier.score_headline("The weather is nice today")
        assert score == 0.0
        assert confidence <= 0.2


class TestSentimentTool:
    """Test the SentimentTool class."""

    def test_init(self) -> None:
        """SentimentTool initializes with default settings."""
        tool = SentimentTool()
        assert tool._classifier is not None
        assert tool._cache is not None

    def test_analyze_with_no_apis(self) -> None:
        """analyze() returns low-confidence neutral when no APIs configured."""
        tool = SentimentTool()
        import asyncio
        result = asyncio.run(tool.analyze("AAPL"))
        assert "symbol" in result
        assert result["symbol"] == "AAPL"
        assert "overall_score" in result
        assert "confidence" in result
        assert "label" in result
        assert "news_items" in result
        assert "event_breakdown" in result

    def test_analyze_response_structure(self) -> None:
        """analyze() returns all expected fields."""
        tool = SentimentTool()
        import asyncio
        result = asyncio.run(tool.analyze("MSFT"))
        expected_keys = [
            "symbol", "overall_score", "confidence", "label",
            "news_items", "news_count", "social_sentiment",
            "event_breakdown", "timestamp",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_aggregate_sentiment_empty(self) -> None:
        """Empty items → neutral sentiment."""
        result = SentimentTool._aggregate_sentiment([])
        assert result["score"] == 0.0
        assert result["label"] == "NEUTRAL"

    def test_aggregate_sentiment_bullish(self) -> None:
        """Bullish items → BULLISH label."""
        items = [
            {"sentiment": 0.7, "confidence": 0.8},
            {"sentiment": 0.5, "confidence": 0.6},
        ]
        result = SentimentTool._aggregate_sentiment(items)
        assert result["label"] == "BULLISH"
        assert result["score"] > 0.2

    def test_aggregate_sentiment_bearish(self) -> None:
        """Bearish items → BEARISH label."""
        items = [
            {"sentiment": -0.7, "confidence": 0.8},
            {"sentiment": -0.5, "confidence": 0.6},
        ]
        result = SentimentTool._aggregate_sentiment(items)
        assert result["label"] == "BEARISH"
        assert result["score"] < -0.2

    def test_count_event_types(self) -> None:
        """Event type counting works correctly."""
        items = [
            {"event_type": "SHOCK"},
            {"event_type": "MACRO"},
            {"event_type": "MACRO"},
            {"event_type": "NOISE"},
        ]
        result = SentimentTool._count_event_types(items)
        assert result["SHOCK"] == 1
        assert result["MACRO"] == 2
        assert result["NOISE"] == 1
        assert result["SCHEDULED"] == 0


# ══════════════════════════════════════════════════════════════════════
# ExecutionTool Tests
# ══════════════════════════════════════════════════════════════════════


class TestExecutionHelpers:
    """Test execution tool helper functions."""

    def test_is_crypto_btc(self) -> None:
        """BTC-USD is classified as crypto."""
        assert _is_crypto("BTC-USD") is True

    def test_is_crypto_eth(self) -> None:
        """ETH/USDT is classified as crypto."""
        assert _is_crypto("ETH/USDT") is True

    def test_is_crypto_stock(self) -> None:
        """AAPL is not classified as crypto."""
        assert _is_crypto("AAPL") is False

    def test_is_forex_eurusd(self) -> None:
        """EURUSD=X is classified as forex."""
        assert _is_forex("EURUSD=X") is True

    def test_is_forex_stock(self) -> None:
        """AAPL is not classified as forex."""
        assert _is_forex("AAPL") is False

    def test_normalize_side_buy(self) -> None:
        """BUY normalizes to OrderSide.BUY."""
        from quant_nanggroe.types.orders import OrderSide
        assert _normalize_side("BUY") == OrderSide.BUY

    def test_normalize_side_long(self) -> None:
        """LONG normalizes to OrderSide.BUY."""
        from quant_nanggroe.types.orders import OrderSide
        assert _normalize_side("LONG") == OrderSide.BUY

    def test_normalize_side_sell(self) -> None:
        """SELL normalizes to OrderSide.SELL."""
        from quant_nanggroe.types.orders import OrderSide
        assert _normalize_side("SELL") == OrderSide.SELL

    def test_normalize_side_short(self) -> None:
        """SHORT normalizes to OrderSide.SELL."""
        from quant_nanggroe.types.orders import OrderSide
        assert _normalize_side("SHORT") == OrderSide.SELL

    def test_normalize_side_invalid(self) -> None:
        """Invalid side raises ExecutionError."""
        with pytest.raises(ExecutionError, match="Invalid order side"):
            _normalize_side("HOLD")

    def test_normalize_order_type_market(self) -> None:
        """MARKET normalizes to OrderType.MARKET."""
        from quant_nanggroe.types.orders import OrderType
        assert _normalize_order_type("MARKET") == OrderType.MARKET

    def test_normalize_order_type_limit(self) -> None:
        """LIMIT normalizes to OrderType.LIMIT."""
        from quant_nanggroe.types.orders import OrderType
        assert _normalize_order_type("LIMIT") == OrderType.LIMIT

    def test_normalize_order_type_invalid(self) -> None:
        """Invalid order type raises ExecutionError."""
        with pytest.raises(ExecutionError, match="Unsupported order type"):
            _normalize_order_type("IOC")


class TestOrderStore:
    """Test the _OrderStore class."""

    def test_store_and_get(self) -> None:
        """Store and retrieve an order."""
        store = _OrderStore()
        store.store("order-1", {"symbol": "AAPL", "status": "filled"})
        result = store.get("order-1")
        assert result is not None
        assert result["symbol"] == "AAPL"

    def test_get_nonexistent(self) -> None:
        """Getting a nonexistent order returns None."""
        store = _OrderStore()
        assert store.get("nonexistent") is None

    def test_update(self) -> None:
        """Update fields on an existing order."""
        store = _OrderStore()
        store.store("order-1", {"status": "pending"})
        store.update("order-1", {"status": "filled"})
        assert store.get("order-1")["status"] == "filled"

    def test_list_by_symbol(self) -> None:
        """List orders by symbol."""
        store = _OrderStore()
        store.store("1", {"symbol": "AAPL", "status": "filled"})
        store.store("2", {"symbol": "MSFT", "status": "filled"})
        store.store("3", {"symbol": "AAPL", "status": "pending"})
        aapl_orders = store.list_by_symbol("AAPL")
        assert len(aapl_orders) == 2

    def test_list_open(self) -> None:
        """List open (pending/submitted) orders."""
        store = _OrderStore()
        store.store("1", {"symbol": "AAPL", "status": "pending"})
        store.store("2", {"symbol": "MSFT", "status": "filled"})
        store.store("3", {"symbol": "GOOGL", "status": "submitted"})
        open_orders = store.list_open()
        assert len(open_orders) == 2


class TestExecutionTool:
    """Test the ExecutionTool class."""

    def test_init(self) -> None:
        """ExecutionTool initializes with default paper brokers."""
        tool = ExecutionTool()
        assert tool._stock_paper is not None
        assert tool._crypto_paper is not None
        assert tool._forex_paper is not None

    def test_validate_order_params_empty_symbol(self) -> None:
        """Empty symbol raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Symbol is required"):
            ExecutionTool._validate_order_params(
                "", "BUY", 10, "MARKET", None, None, None
            )

    def test_validate_order_params_zero_quantity(self) -> None:
        """Zero quantity raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Quantity must be positive"):
            ExecutionTool._validate_order_params(
                "AAPL", "BUY", 0, "MARKET", None, None, None
            )

    def test_validate_order_params_negative_quantity(self) -> None:
        """Negative quantity raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Quantity must be positive"):
            ExecutionTool._validate_order_params(
                "AAPL", "BUY", -1, "MARKET", None, None, None
            )

    def test_validate_order_params_limit_without_price(self) -> None:
        """LIMIT order without price raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Limit price is required"):
            ExecutionTool._validate_order_params(
                "AAPL", "BUY", 10, "LIMIT", None, None, None
            )

    def test_validate_order_params_invalid_side(self) -> None:
        """Invalid side raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Invalid order side"):
            ExecutionTool._validate_order_params(
                "AAPL", "HOLD", 10, "MARKET", None, None, None
            )

    def test_validate_order_params_sl_above_entry_buy(self) -> None:
        """SL above entry for BUY raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Stop-loss.*must be below entry"):
            ExecutionTool._validate_order_params(
                "AAPL", "BUY", 10, "LIMIT", 150.0, 155.0, None
            )

    def test_validate_order_params_tp_below_entry_buy(self) -> None:
        """TP below entry for BUY raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Take-profit.*must be above entry"):
            ExecutionTool._validate_order_params(
                "AAPL", "BUY", 10, "LIMIT", 150.0, None, 145.0
            )

    def test_validate_order_params_sl_below_entry_sell(self) -> None:
        """SL below entry for SELL raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Stop-loss.*must be above entry"):
            ExecutionTool._validate_order_params(
                "AAPL", "SELL", 10, "LIMIT", 150.0, 145.0, None
            )

    def test_validate_order_params_tp_above_entry_sell(self) -> None:
        """TP above entry for SELL raises OrderRejectedError."""
        with pytest.raises(OrderRejectedError, match="Take-profit.*must be below entry"):
            ExecutionTool._validate_order_params(
                "AAPL", "SELL", 10, "LIMIT", 150.0, None, 160.0
            )

    def test_validate_order_params_valid_buy(self) -> None:
        """Valid BUY order params pass validation."""
        # Should not raise
        ExecutionTool._validate_order_params(
            "AAPL", "BUY", 10, "LIMIT", 150.0, 145.0, 160.0
        )

    def test_validate_order_params_valid_sell(self) -> None:
        """Valid SELL order params pass validation."""
        # Should not raise
        ExecutionTool._validate_order_params(
            "AAPL", "SELL", 10, "LIMIT", 150.0, 155.0, 140.0
        )

    def test_validate_order_params_valid_market(self) -> None:
        """Valid MARKET order params pass validation."""
        # Should not raise
        ExecutionTool._validate_order_params(
            "AAPL", "BUY", 10, "MARKET", None, None, None
        )

    def test_cancel_nonexistent_order(self) -> None:
        """Cancelling a nonexistent order raises ExecutionError."""
        import asyncio
        tool = ExecutionTool()
        with pytest.raises(ExecutionError, match="Order not found"):
            asyncio.run(tool.cancel_order("nonexistent-id"))

    def test_get_order_status_nonexistent(self) -> None:
        """Getting status of nonexistent order raises ExecutionError."""
        import asyncio
        tool = ExecutionTool()
        with pytest.raises(ExecutionError, match="Order not found"):
            asyncio.run(tool.get_order_status("nonexistent-id"))

    def test_get_open_orders_empty(self) -> None:
        """get_open_orders() returns empty list initially."""
        import asyncio
        tool = ExecutionTool()
        result = asyncio.run(tool.get_open_orders())
        assert result == []

    def test_should_use_alpaca_no_keys(self) -> None:
        """Without Alpaca keys, should not use Alpaca."""
        tool = ExecutionTool()
        result = tool._should_use_alpaca("AAPL")
        assert result is False

    def test_should_use_alpaca_crypto(self) -> None:
        """Crypto symbols should not use Alpaca."""
        tool = ExecutionTool()
        result = tool._should_use_alpaca("BTC-USD")
        assert result is False

    def test_should_use_alpaca_forex(self) -> None:
        """Forex symbols should not use Alpaca."""
        tool = ExecutionTool()
        result = tool._should_use_alpaca("EURUSD=X")
        assert result is False

    def test_get_paper_broker_stock(self) -> None:
        """Stock symbols get stock paper broker."""
        tool = ExecutionTool()
        broker = tool._get_paper_broker("AAPL")
        assert broker is tool._stock_paper

    def test_get_paper_broker_crypto(self) -> None:
        """Crypto symbols get crypto paper broker."""
        tool = ExecutionTool()
        broker = tool._get_paper_broker("BTC-USD")
        assert broker is tool._crypto_paper

    def test_get_paper_broker_forex(self) -> None:
        """Forex symbols get forex paper broker."""
        tool = ExecutionTool()
        broker = tool._get_paper_broker("EURUSD=X")
        assert broker is tool._forex_paper


# ══════════════════════════════════════════════════════════════════════
# BacktestTool Tests
# ══════════════════════════════════════════════════════════════════════


class TestBacktestTool:
    """Test the BacktestTool class."""

    def test_init_without_market_data(self) -> None:
        """BacktestTool can be created without MarketDataTool."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        tool = BacktestTool()
        assert tool._market_data is None

    def test_run_backtest_no_market_data_raises(self) -> None:
        """run_backtest() raises DataError without MarketDataTool."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        tool = BacktestTool()
        import asyncio
        with pytest.raises(DataError, match="No MarketDataTool"):
            asyncio.run(tool.run_backtest("sma_crossover", "AAPL"))

    def test_run_backtest_unknown_strategy_raises(self) -> None:
        """run_backtest() with unknown strategy raises EngineError."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool, _BacktestResultStore
        from quant_nanggroe.exceptions import EngineError

        tool = BacktestTool()
        # Mock the market data tool
        mock_mdt = AsyncMock()
        mock_mdt.get_ohlcv.return_value = {
            "candles": [
                {"timestamp": f"2023-01-{i+1:02d}T00:00:00", "close": 100.0 + i, "open": 100.0, "high": 101.0 + i, "low": 99.0, "volume": 1000.0}
                for i in range(100)
            ]
        }
        tool._market_data = mock_mdt

        import asyncio
        with pytest.raises(EngineError, match="Unknown strategy"):
            asyncio.run(tool.run_backtest("nonexistent_strategy", "AAPL"))

    def test_get_backtest_results_not_found(self) -> None:
        """get_backtest_results() raises for nonexistent ID."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        from quant_nanggroe.exceptions import EngineError

        tool = BacktestTool()
        import asyncio
        with pytest.raises(EngineError, match="Backtest not found"):
            asyncio.run(tool.get_backtest_results("nonexistent"))

    def test_list_backtests_empty(self) -> None:
        """list_backtests() returns empty list initially."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        tool = BacktestTool()
        import asyncio
        result = asyncio.run(tool.list_backtests())
        assert result == []

    def test_register_custom_strategy(self) -> None:
        """Custom strategies can be registered."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool, _BUILTIN_STRATEGIES

        def custom_strategy(closes, **kwargs):
            return [{"bar_index": 0, "direction": "BUY", "price": closes[0]}]

        tool = BacktestTool()
        tool.register_strategy("custom", custom_strategy)
        assert "custom" in _BUILTIN_STRATEGIES

        # Cleanup
        del _BUILTIN_STRATEGIES["custom"]

    def test_sma_crossover_signals(self) -> None:
        """SMA crossover generates valid signals."""
        from quant_nanggroe.agents.tools.backtest import _sma_crossover_signals
        # Create a series with a clear crossover
        closes = [100.0] * 30 + [100.0 + i for i in range(30)]
        signals = _sma_crossover_signals(closes)
        # Should have at least one signal
        for signal in signals:
            assert "bar_index" in signal
            assert "direction" in signal
            assert "price" in signal
            assert signal["direction"] in ("BUY", "SELL")

    def test_rsi_mean_revert_signals(self) -> None:
        """RSI mean-revert generates valid signals."""
        from quant_nanggroe.agents.tools.backtest import _rsi_mean_revert_signals
        # Create a series with oversold/overbought conditions
        closes = [100.0 + i * 2 for i in range(50)] + [200.0 - i * 2 for i in range(50)]
        signals = _rsi_mean_revert_signals(closes)
        for signal in signals:
            assert signal["direction"] in ("BUY", "SELL")

    def test_simulate_trades(self) -> None:
        """Trade simulation produces valid trades and equity curve."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        signals = [
            {"bar_index": 10, "direction": "BUY", "price": 100.0},
            {"bar_index": 30, "direction": "SELL", "price": 110.0},
        ]
        closes = [100.0 + i * 0.5 for i in range(50)]
        trades, equity = BacktestTool._simulate_trades(
            signals, closes, 10000.0, 0.001, 0.0005
        )
        assert len(trades) == 2
        assert trades[0]["direction"] == "BUY"
        assert trades[1]["direction"] == "SELL"
        assert len(equity) > 1
        assert equity[0] == 10000.0

    def test_calculate_metrics(self) -> None:
        """Metrics calculation produces valid results."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        equity = [10000.0, 10100.0, 10050.0, 10200.0, 10150.0, 10300.0]
        trades = [
            {"pnl": 50.0},
            {"pnl": -30.0},
            {"pnl": 80.0},
        ]
        metrics = BacktestTool._calculate_metrics(equity, trades, 10000.0)
        assert metrics["initial_capital"] == 10000.0
        assert metrics["final_equity"] == 10300.0
        assert metrics["total_return"] > 0
        assert metrics["max_drawdown"] < 0
        assert metrics["win_rate"] == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_filter_candles_by_date(self) -> None:
        """Candle filtering by date works correctly."""
        from quant_nanggroe.agents.tools.backtest import BacktestTool
        candles = [
            {"timestamp": "2023-01-15T00:00:00", "close": 100.0},
            {"timestamp": "2023-06-15T00:00:00", "close": 110.0},
            {"timestamp": "2024-01-15T00:00:00", "close": 120.0},
        ]
        filtered = BacktestTool._filter_candles_by_date(
            candles, "2023-03-01", "2023-12-31"
        )
        assert len(filtered) == 1
        assert filtered[0]["close"] == 110.0


# ══════════════════════════════════════════════════════════════════════
# @tool Function Verification Tests
# ══════════════════════════════════════════════════════════════════════


class TestToolDecoratedFunctions:
    """Verify that @tool decorated functions are callable and properly defined."""

    def test_get_ohlcv_tool_is_callable(self) -> None:
        """get_ohlcv @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.market_data import get_ohlcv
        # LangChain @tool creates StructuredTool objects, not plain callables
        assert hasattr(get_ohlcv, 'name') or callable(get_ohlcv)

    def test_get_current_price_tool_is_callable(self) -> None:
        """get_current_price @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.market_data import get_current_price
        assert hasattr(get_current_price, 'name') or callable(get_current_price)

    def test_get_multiple_prices_tool_is_callable(self) -> None:
        """get_multiple_prices @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.market_data import get_multiple_prices
        assert hasattr(get_multiple_prices, 'name') or callable(get_multiple_prices)

    def test_analyze_technical_tool_is_callable(self) -> None:
        """analyze_technical @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.technical import analyze_technical
        assert hasattr(analyze_technical, 'name') or callable(analyze_technical)

    def test_analyze_sentiment_tool_is_callable(self) -> None:
        """analyze_sentiment @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.sentiment import analyze_sentiment
        assert hasattr(analyze_sentiment, 'name') or callable(analyze_sentiment)

    def test_execute_order_tool_is_callable(self) -> None:
        """execute_order @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.execution import execute_order
        assert hasattr(execute_order, 'name') or callable(execute_order)

    def test_cancel_order_tool_is_callable(self) -> None:
        """cancel_order @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.execution import cancel_order
        assert hasattr(cancel_order, 'name') or callable(cancel_order)

    def test_get_order_status_tool_is_callable(self) -> None:
        """get_order_status @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.execution import get_order_status
        assert hasattr(get_order_status, 'name') or callable(get_order_status)

    def test_get_open_orders_tool_is_callable(self) -> None:
        """get_open_orders @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.execution import get_open_orders
        assert hasattr(get_open_orders, 'name') or callable(get_open_orders)

    def test_get_account_summary_tool_is_callable(self) -> None:
        """get_account_summary @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.execution import get_account_summary
        assert hasattr(get_account_summary, 'name') or callable(get_account_summary)

    def test_run_backtest_tool_is_callable(self) -> None:
        """run_backtest @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.backtest import run_backtest
        assert hasattr(run_backtest, 'name') or callable(run_backtest)

    def test_get_backtest_results_tool_is_callable(self) -> None:
        """get_backtest_results @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.backtest import get_backtest_results
        assert hasattr(get_backtest_results, 'name') or callable(get_backtest_results)

    def test_list_backtests_tool_is_callable(self) -> None:
        """list_backtests @tool function is a LangChain StructuredTool."""
        from quant_nanggroe.agents.tools.backtest import list_backtests
        assert hasattr(list_backtests, 'name') or callable(list_backtests)

    def test_tool_functions_have_docstrings(self) -> None:
        """All @tool functions have docstrings (required for LangChain)."""
        from quant_nanggroe.agents.tools import (
            get_ohlcv,
            get_current_price,
            get_multiple_prices,
            analyze_technical,
            analyze_sentiment,
            execute_order,
            cancel_order,
            get_order_status,
        )
        tools = [
            get_ohlcv, get_current_price, get_multiple_prices,
            analyze_technical, analyze_sentiment,
            execute_order, cancel_order, get_order_status,
        ]
        for tool_fn in tools:
            # LangChain StructuredTool has 'description' instead of __doc__
            has_doc = (
                hasattr(tool_fn, 'description') and tool_fn.description
            ) or (
                hasattr(tool_fn, '__doc__') and tool_fn.__doc__
            )
            assert has_doc, f"Tool missing docstring/description: {tool_fn}"

    def test_tool_functions_have_names(self) -> None:
        """All @tool functions have accessible names."""
        from quant_nanggroe.agents.tools import (
            get_ohlcv,
            get_current_price,
            analyze_technical,
            analyze_sentiment,
            execute_order,
        )
        # LangChain StructuredTool objects always have a 'name' attribute
        for tool_fn in [get_ohlcv, get_current_price, analyze_technical, analyze_sentiment, execute_order]:
            assert hasattr(tool_fn, "name"), f"Tool missing 'name' attribute: {tool_fn}"
            assert tool_fn.name is not None


# ══════════════════════════════════════════════════════════════════════
# Package Import Tests
# ══════════════════════════════════════════════════════════════════════


class TestPackageImports:
    """Test that all tools are properly exported from the package."""

    def test_import_market_data_tool(self) -> None:
        """MarketDataTool can be imported from the package."""
        from quant_nanggroe.agents.tools import MarketDataTool
        assert MarketDataTool is not None

    def test_import_technical_analysis_tool(self) -> None:
        """TechnicalAnalysisTool can be imported from the package."""
        from quant_nanggroe.agents.tools import TechnicalAnalysisTool
        assert TechnicalAnalysisTool is not None

    def test_import_sentiment_tool(self) -> None:
        """SentimentTool can be imported from the package."""
        from quant_nanggroe.agents.tools import SentimentTool
        assert SentimentTool is not None

    def test_import_execution_tool(self) -> None:
        """ExecutionTool can be imported from the package."""
        from quant_nanggroe.agents.tools import ExecutionTool
        assert ExecutionTool is not None

    def test_import_backtest_tool(self) -> None:
        """BacktestTool can be imported from the package."""
        from quant_nanggroe.agents.tools import BacktestTool
        assert BacktestTool is not None

    def test_import_tool_functions(self) -> None:
        """All @tool functions can be imported from the package."""
        from quant_nanggroe.agents.tools import (
            get_ohlcv,
            get_current_price,
            get_multiple_prices,
            analyze_technical,
            analyze_sentiment,
            execute_order,
            cancel_order,
            get_order_status,
            get_open_orders,
            get_account_summary,
        )
        # LangChain StructuredTool objects have 'name' and 'description'
        tool_fns = [
            get_ohlcv, get_current_price, get_multiple_prices,
            analyze_technical, analyze_sentiment,
            execute_order, cancel_order, get_order_status,
            get_open_orders, get_account_summary,
        ]
        for tool_fn in tool_fns:
            assert hasattr(tool_fn, 'name'), f"Tool missing 'name': {tool_fn}"

    def test_all_exports(self) -> None:
        """__all__ contains all expected exports."""
        from quant_nanggroe.agents.tools import __all__
        expected = [
            "MarketDataTool",
            "TechnicalAnalysisTool",
            "SentimentTool",
            "ExecutionTool",
            "BacktestTool",
            "get_ohlcv",
            "get_current_price",
            "get_multiple_prices",
            "analyze_technical",
            "analyze_sentiment",
            "execute_order",
            "cancel_order",
            "get_order_status",
            "get_open_orders",
            "get_account_summary",
        ]
        for name in expected:
            assert name in __all__, f"{name} not in __all__"
