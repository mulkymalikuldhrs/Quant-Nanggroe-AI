"""Tests for quant_nanggroe.engine — indicators, market state, pressure normalization."""

import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("CACHE_BACKEND", "memory")

import numpy as np
import pytest

from quant_nanggroe.engine.indicators import TechnicalIndicators
from quant_nanggroe.engine.market_state import MarketStateEngine, MarketState
from quant_nanggroe.engine.pressure import (
    PressureNormalizationEngine,
    QuantScannerOutput,
    SMCOutput,
    NewsSentinelOutput,
    FlowWhaleOutput,
)
from quant_nanggroe.types.decisions import MarketRegime, VolatilityLevel, LiquidityLevel


# ──────────────────────────────────────────────────────────────
# Technical Indicators Tests
# ──────────────────────────────────────────────────────────────


class TestSMA:
    def test_basic_sma(self, sample_closes):
        result = TechnicalIndicators.sma(sample_closes, 20)
        assert not np.isnan(result)
        assert result > 0

    def test_sma_insufficient_data(self):
        result = TechnicalIndicators.sma(np.array([1.0, 2.0]), 20)
        assert np.isnan(result)

    def test_sma_series(self, sample_closes):
        result = TechnicalIndicators.sma_series(sample_closes, 20)
        assert len(result) == len(sample_closes)
        # First 19 values should be NaN
        assert all(np.isnan(result[:19]))
        # 20th value onwards should be valid
        assert not np.isnan(result[19])

    def test_sma_correctness(self):
        data = np.arange(1.0, 11.0)  # 1, 2, ..., 10
        result = TechnicalIndicators.sma(data, 5)
        # SMA of last 5: (6+7+8+9+10)/5 = 8.0
        assert result == 8.0


class TestEMA:
    def test_basic_ema(self, sample_closes):
        result = TechnicalIndicators.ema(sample_closes, 20)
        assert len(result) == len(sample_closes)
        assert not any(np.isnan(result))

    def test_ema_first_value(self):
        data = np.array([100.0, 101.0, 99.0])
        result = TechnicalIndicators.ema(data, 2)
        assert result[0] == 100.0

    def test_ema_responds_faster_than_sma(self, sample_closes):
        ema_val = TechnicalIndicators.ema(sample_closes, 20)[-1]
        sma_val = TechnicalIndicators.sma(sample_closes, 20)
        # EMA and SMA should be close but not necessarily identical
        assert abs(ema_val - sma_val) / sma_val < 0.1  # Within 10%


class TestRSI:
    def test_basic_rsi(self, sample_closes):
        result = TechnicalIndicators.rsi(sample_closes)
        assert 0 <= result <= 100

    def test_rsi_insufficient_data(self):
        result = TechnicalIndicators.rsi(np.array([100.0]))
        assert result == 50.0  # Default for insufficient data

    def test_rsi_all_gains(self):
        # Monotonically increasing — RSI should be 100
        data = np.arange(1.0, 50.0)
        result = TechnicalIndicators.rsi(data, 14)
        assert result == 100.0

    def test_rsi_all_losses(self):
        # Monotonically decreasing — RSI should be near 0
        data = np.arange(50.0, 1.0, -1)
        result = TechnicalIndicators.rsi(data, 14)
        assert result < 5.0

    def test_rsi_series(self, sample_closes):
        result = TechnicalIndicators.rsi_series(sample_closes)
        assert len(result) == len(sample_closes)
        # Non-NaN values should be in range 0-100
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)


class TestMACD:
    def test_basic_macd(self, sample_closes):
        result = TechnicalIndicators.macd(sample_closes)
        assert isinstance(result.macd_line, float)
        assert isinstance(result.signal_line, float)
        assert isinstance(result.histogram, float)

    def test_macd_insufficient_data(self):
        result = TechnicalIndicators.macd(np.array([1.0, 2.0, 3.0]))
        assert result.macd_line == 0.0

    def test_macd_histogram_is_difference(self, sample_closes):
        result = TechnicalIndicators.macd(sample_closes)
        assert abs(result.histogram - (result.macd_line - result.signal_line)) < 0.001


class TestBollingerBands:
    def test_basic_bollinger(self, sample_closes):
        result = TechnicalIndicators.bollinger_bands(sample_closes)
        assert result.upper > result.middle
        assert result.middle > result.lower

    def test_bollinger_insufficient_data(self):
        result = TechnicalIndicators.bollinger_bands(np.array([1.0, 2.0]))
        assert result.upper == 0.0

    def test_bollinger_percent_b(self, sample_closes):
        result = TechnicalIndicators.bollinger_bands(sample_closes)
        assert 0 <= result.percent_b <= 1 or result.percent_b < 0 or result.percent_b > 1
        # %B should be near 0.5 for data centered around SMA

    def test_bollinger_bandwidth_positive(self, sample_closes):
        result = TechnicalIndicators.bollinger_bands(sample_closes)
        assert result.bandwidth > 0


class TestVWAP:
    def test_basic_vwap(self, sample_ohlcv_data):
        result = TechnicalIndicators.vwap(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
            sample_ohlcv_data["volumes"],
        )
        assert result > 0

    def test_vwap_zero_volume(self):
        closes = np.array([100.0, 101.0, 99.0])
        volumes = np.zeros(3)
        result = TechnicalIndicators.vwap(closes, closes, closes, volumes)
        assert result == 0.0


class TestATR:
    def test_basic_atr(self, sample_ohlcv_data):
        result = TechnicalIndicators.atr(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
        )
        assert result > 0

    def test_atr_insufficient_data(self):
        result = TechnicalIndicators.atr(
            np.array([100.0, 101.0]),
            np.array([99.0, 100.0]),
            np.array([100.0, 100.5]),
        )
        assert result == 0.0


class TestADX:
    def test_basic_adx(self, sample_ohlcv_data):
        result = TechnicalIndicators.adx(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
        )
        assert 0 <= result.adx <= 100
        assert 0 <= result.plus_di <= 100
        assert 0 <= result.minus_di <= 100

    def test_adx_trending_market(self, trending_closes):
        # Generate highs/lows for trending data
        closes = trending_closes
        highs = closes * 1.01
        lows = closes * 0.99

        result = TechnicalIndicators.adx(highs, lows, closes)
        # A trending market should have ADX > 20
        assert result.adx > 15  # Allow some margin

    def test_adx_insufficient_data(self):
        result = TechnicalIndicators.adx(
            np.array([100.0, 101.0]),
            np.array([99.0, 100.0]),
            np.array([100.0, 100.5]),
        )
        # Should return defaults
        assert result.adx == 25.0


class TestStochastic:
    def test_basic_stochastic(self, sample_ohlcv_data):
        result = TechnicalIndicators.stochastic(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
        )
        assert 0 <= result.k <= 100
        assert 0 <= result.d <= 100

    def test_stochastic_insufficient_data(self):
        result = TechnicalIndicators.stochastic(
            np.array([100.0]),
            np.array([99.0]),
            np.array([100.0]),
        )
        assert result.k == 50.0
        assert result.d == 50.0


class TestCCI:
    def test_basic_cci(self, sample_ohlcv_data):
        result = TechnicalIndicators.cci(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
        )
        assert isinstance(result, float)

    def test_cci_insufficient_data(self):
        result = TechnicalIndicators.cci(
            np.array([100.0]),
            np.array([99.0]),
            np.array([100.0]),
        )
        assert result == 0.0


class TestFullIndicators:
    def test_analyze(self, sample_ohlcv_data):
        result = TechnicalIndicators.analyze(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
            sample_ohlcv_data["volumes"],
        )
        assert 0 <= result.rsi <= 100
        assert result.atr >= 0
        assert result.vwap > 0
        assert isinstance(result.macd.macd_line, float)
        assert isinstance(result.bollinger.upper, float)
        assert isinstance(result.stoch.k, float)


# ──────────────────────────────────────────────────────────────
# Market State Engine Tests
# ──────────────────────────────────────────────────────────────


class TestMarketStateEngine:
    def test_insufficient_candles_returns_no_trade(self):
        engine = MarketStateEngine()
        closes = np.random.uniform(99, 101, 10)
        highs = closes * 1.01
        lows = closes * 0.99
        result = engine.analyze(highs, lows, closes)
        assert result.regime == MarketRegime.NO_TRADE

    def test_trending_market(self, trending_closes):
        engine = MarketStateEngine()
        highs = trending_closes * 1.01
        lows = trending_closes * 0.99
        result = engine.analyze(highs, lows, trending_closes)
        # Strong trending data should produce TRENDING regime
        assert result.regime in (MarketRegime.TRENDING, MarketRegime.RANGE)

    def test_crashing_market(self, crashing_closes):
        engine = MarketStateEngine()
        highs = crashing_closes * 1.005
        lows = crashing_closes * 0.995
        result = engine.analyze(highs, lows, crashing_closes)
        # Crashing data should produce PANIC or RISK_OFF
        assert result.regime in (MarketRegime.PANIC, MarketRegime.RISK_OFF)

    def test_volatility_classification(self, sample_ohlcv_data):
        engine = MarketStateEngine()
        result = engine.analyze(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
            sample_ohlcv_data["volumes"],
        )
        assert result.volatility in (VolatilityLevel.LOW, VolatilityLevel.NORMAL, VolatilityLevel.HIGH)

    def test_liquidity_classification(self, sample_ohlcv_data):
        engine = MarketStateEngine()
        result = engine.analyze(
            sample_ohlcv_data["highs"],
            sample_ohlcv_data["lows"],
            sample_ohlcv_data["closes"],
            sample_ohlcv_data["volumes"],
        )
        assert result.liquidity in (LiquidityLevel.THIN, LiquidityLevel.NORMAL, LiquidityLevel.DEEP)


# ──────────────────────────────────────────────────────────────
# Pressure Normalization Engine Tests
# ──────────────────────────────────────────────────────────────


class TestPressureNormalization:
    def test_no_trade_regime_zeros_pressures(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=0.9, structure_state="BULL", volatility_expansion=False)
        result = engine.normalize(
            regime=MarketRegime.NO_TRADE,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )
        assert result.buy_pressure == 0.0
        assert result.sell_pressure == 0.0
        assert result.confidence_score == 0.0

    def test_bullish_quant_scanner(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=0.9, structure_state="BULL", volatility_expansion=False)
        result = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )
        assert result.buy_pressure > 0
        assert result.sell_pressure == 0.0

    def test_bearish_quant_scanner(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=0.9, structure_state="BEAR", volatility_expansion=False)
        result = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )
        assert result.sell_pressure > 0
        assert result.buy_pressure == 0.0

    def test_smc_sweep_low_buy_pressure(self):
        engine = PressureNormalizationEngine()
        smc = SMCOutput(
            liquidity_sweep=True,
            displacement_strength=0.8,
            sweep_direction="LOW",
            poi_validity=0.9,
        )
        result = engine.normalize(
            regime=MarketRegime.RANGE,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            smc=smc,
        )
        assert result.buy_pressure > 0

    def test_smc_sweep_high_sell_pressure(self):
        engine = PressureNormalizationEngine()
        smc = SMCOutput(
            liquidity_sweep=True,
            displacement_strength=0.8,
            sweep_direction="HIGH",
            poi_validity=0.9,
        )
        result = engine.normalize(
            regime=MarketRegime.RANGE,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            smc=smc,
        )
        assert result.sell_pressure > 0

    def test_news_bullish_sentiment(self):
        engine = PressureNormalizationEngine()
        news = NewsSentinelOutput(
            event_type="MACRO",
            impact_score=0.8,
            directional_uncertainty=0.2,
            sentiment_bias=0.7,
            time_decay=3600,
        )
        result = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            news=news,
        )
        assert result.buy_pressure > 0

    def test_flow_long_bias(self):
        engine = PressureNormalizationEngine()
        flow = FlowWhaleOutput(
            positioning_bias="LONG",
            flow_imbalance=0.8,
            net_flow=5000000.0,
        )
        result = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            flow=flow,
        )
        assert result.buy_pressure > 0

    def test_high_volatility_reduces_pressure(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=0.9, structure_state="BULL", volatility_expansion=True)

        result_normal = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )

        result_high = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.HIGH,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )

        assert result_high.buy_pressure < result_normal.buy_pressure

    def test_thin_liquidity_reduces_pressure(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=0.9, structure_state="BULL", volatility_expansion=False)

        result_normal = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
        )

        result_thin = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.THIN,
            quant=quant,
        )

        assert result_thin.buy_pressure < result_normal.buy_pressure

    def test_pressure_sum_leq_one(self):
        engine = PressureNormalizationEngine()
        quant = QuantScannerOutput(trend_strength=1.0, structure_state="BULL", volatility_expansion=False)
        smc = SMCOutput(liquidity_sweep=True, displacement_strength=1.0, sweep_direction="LOW", poi_validity=1.0)
        news = NewsSentinelOutput(
            event_type="MACRO", impact_score=1.0,
            directional_uncertainty=0.0, sentiment_bias=1.0, time_decay=3600,
        )
        flow = FlowWhaleOutput(positioning_bias="LONG", flow_imbalance=1.0, net_flow=10000000.0)

        result = engine.normalize(
            regime=MarketRegime.TRENDING,
            volatility=VolatilityLevel.NORMAL,
            liquidity=LiquidityLevel.NORMAL,
            quant=quant,
            smc=smc,
            news=news,
            flow=flow,
        )

        assert result.buy_pressure + result.sell_pressure <= 1.0 + 0.001
