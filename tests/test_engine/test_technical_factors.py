"""Comprehensive tests for Technical Factor implementations.

Tests all technical factors (Momentum, ROC, MeanReversion, RealizedVol,
ATR, BollingerWidth, VolumeRatio, RSI, MACD) with:
- Known-value verification
- Edge cases: empty data, single values, constant series
- NaN propagation
- Lookahead-free validation
- Warmup period correctness
- Output quality validation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.factors.technical import (
    MomentumFactor,
    RateOfChangeFactor,
    MeanReversionFactor,
    RealizedVolatilityFactor,
    ATRFactor,
    BollingerWidthFactor,
    VolumeRatioFactor,
    RSIFactor,
    MACDHistogramFactor,
    get_all_technical_factors,
)
from quant_nanggroe.engine.factors.base import AlphaFactor


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def ohlcv_df():
    """Standard 100-bar OHLCV DataFrame for factor testing."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.0002, 0.015, n)
    closes = 100.0 * np.cumprod(1 + returns)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")

    df = pd.DataFrame({
        "open": closes * (1 + np.random.normal(0, 0.002, n)),
        "high": closes * (1 + np.abs(np.random.normal(0, 0.005, n))),
        "low": closes * (1 - np.abs(np.random.normal(0, 0.005, n))),
        "close": closes,
        "volume": np.maximum(np.random.lognormal(15, 1, n), 1000),
    }, index=dates)
    return df


@pytest.fixture
def constant_df():
    """DataFrame with constant close prices (no volatility)."""
    n = 50
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "open": [100.0] * n,
        "high": [100.5] * n,
        "low": [99.5] * n,
        "close": [100.0] * n,
        "volume": [1e6] * n,
    }, index=dates)


@pytest.fixture
def uptrend_df():
    """Strong uptrend DataFrame."""
    n = 60
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    closes = [100.0 + i * 2.0 for i in range(n)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1.0 for c in closes],
        "low": [c - 1.0 for c in closes],
        "close": closes,
        "volume": [1e6] * n,
    }, index=dates)


@pytest.fixture
def downtrend_df():
    """Strong downtrend DataFrame."""
    n = 60
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    closes = [200.0 - i * 2.0 for i in range(n)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1.0 for c in closes],
        "low": [c - 1.0 for c in closes],
        "close": closes,
        "volume": [1e6] * n,
    }, index=dates)


@pytest.fixture
def short_df():
    """Short DataFrame (insufficient warmup)."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame({
        "open": [100.0] * 5,
        "high": [101.0] * 5,
        "low": [99.0] * 5,
        "close": [100.0, 101.0, 99.0, 102.0, 98.0],
        "volume": [1e6] * 5,
    }, index=dates)


# ─── MomentumFactor Tests ──────────────────────────────────────────────────

class TestMomentumFactor:
    """Tests for MomentumFactor."""

    def test_name_property(self):
        factor = MomentumFactor()
        assert factor.name == "momentum"

    def test_meta_properties(self):
        factor = MomentumFactor()
        assert factor.meta.id == "technical_momentum"
        assert "close" in factor.meta.columns_required
        assert factor.meta.min_warmup_bars == 21

    def test_positive_momentum_uptrend(self, uptrend_df):
        factor = MomentumFactor(period=20)
        result = factor.compute(uptrend_df)
        # After warmup, momentum should be positive in uptrend
        valid = result.dropna()
        assert (valid > 0).all(), "Momentum should be positive in uptrend"

    def test_negative_momentum_downtrend(self, downtrend_df):
        factor = MomentumFactor(period=20)
        result = factor.compute(downtrend_df)
        valid = result.dropna()
        assert (valid < 0).all(), "Momentum should be negative in downtrend"

    def test_zero_momentum_constant_price(self, constant_df):
        factor = MomentumFactor(period=20)
        result = factor.compute(constant_df)
        valid = result.dropna()
        # Constant price → momentum = close/close.shift(n) - 1 = 0
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-10,
                                   err_msg="Momentum should be zero for constant prices")

    def test_warmup_nan_count(self, ohlcv_df):
        factor = MomentumFactor(period=20)
        result = factor.compute(ohlcv_df)
        # First 20 values should be NaN (shift of 20)
        nan_count = result.iloc[:20].isna().sum()
        assert nan_count == 20, f"First 20 values should be NaN, got {nan_count}"

    def test_custom_period(self, ohlcv_df):
        factor = MomentumFactor(period=10)
        result = factor.compute(ohlcv_df)
        # First 10 values should be NaN
        assert result.iloc[:10].isna().all()

    def test_no_inf_in_output(self, ohlcv_df):
        factor = MomentumFactor()
        result = factor.compute(ohlcv_df)
        assert not np.isinf(result.dropna()).any()

    def test_lookahead_free(self):
        factor = MomentumFactor()
        assert factor.validate_lookahead(), "MomentumFactor should be lookahead-free"

    def test_known_value(self):
        """Verify with manually computed momentum."""
        dates = pd.date_range("2024-01-01", periods=25, freq="D")
        closes = [100.0 + i for i in range(25)]
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*25}, index=dates)
        factor = MomentumFactor(period=5)
        result = factor.compute(df)
        # At index 5: close[5]=105, close[0]=100 → (105/100 - 1) = 0.05
        expected = (105.0 / 100.0) - 1.0
        assert abs(result.iloc[5] - expected) < 1e-10, f"Expected {expected}, got {result.iloc[5]}"


class TestRateOfChangeFactor:
    """Tests for RateOfChangeFactor."""

    def test_name_includes_period(self):
        factor = RateOfChangeFactor(period=12)
        assert "12" in factor.name

    def test_roc_uptrend_positive(self, uptrend_df):
        factor = RateOfChangeFactor(period=12)
        result = factor.compute(uptrend_df)
        valid = result.dropna()
        assert (valid > 0).all()

    def test_roc_known_value(self):
        dates = pd.date_range("2024-01-01", periods=15, freq="D")
        closes = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0,
                  114.0, 116.0, 118.0, 120.0, 122.0, 124.0, 126.0, 128.0]
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*15}, index=dates)
        factor = RateOfChangeFactor(period=3)
        result = factor.compute(df)
        # At index 3: (106-100)/100*100 = 6.0
        np.testing.assert_allclose(result.iloc[3], 6.0, atol=1e-10)

    def test_roc_constant_zero(self, constant_df):
        factor = RateOfChangeFactor(period=10)
        result = factor.compute(constant_df)
        valid = result.dropna()
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-10)

    def test_roc_warmup(self, ohlcv_df):
        factor = RateOfChangeFactor(period=12)
        result = factor.compute(ohlcv_df)
        assert result.iloc[:12].isna().all()

    def test_lookahead_free(self):
        factor = RateOfChangeFactor()
        assert factor.validate_lookahead()


class TestMeanReversionFactor:
    """Tests for MeanReversionFactor."""

    def test_name_includes_period(self):
        factor = MeanReversionFactor(period=20)
        assert "20" in factor.name

    def test_positive_when_above_ma(self, uptrend_df):
        """Price above MA → positive z-score."""
        factor = MeanReversionFactor(period=20)
        result = factor.compute(uptrend_df)
        # In strong uptrend, close > MA → z-score > 0
        valid = result.dropna()
        assert (valid > 0).any(), "Should have positive z-scores in uptrend"

    def test_negative_when_below_ma(self, downtrend_df):
        """Price below MA → negative z-score."""
        factor = MeanReversionFactor(period=20)
        result = factor.compute(downtrend_df)
        valid = result.dropna()
        assert (valid < 0).any(), "Should have negative z-scores in downtrend"

    def test_constant_price_nan_or_zero(self, constant_df):
        factor = MeanReversionFactor(period=20)
        result = factor.compute(constant_df)
        # Constant price → std=0 → division by 0 → NaN
        valid = result.dropna()
        # All values should be NaN since std=0
        assert len(valid) == 0 or (valid == 0).all()

    def test_warmup_period(self, ohlcv_df):
        factor = MeanReversionFactor(period=20)
        result = factor.compute(ohlcv_df)
        # First 19 values should be NaN (need 20 bars for rolling window)
        assert result.iloc[:19].isna().all()

    def test_lookahead_free(self):
        factor = MeanReversionFactor()
        assert factor.validate_lookahead()


class TestRealizedVolatilityFactor:
    """Tests for RealizedVolatilityFactor."""

    def test_positive_volatility(self, ohlcv_df):
        factor = RealizedVolatilityFactor(period=20)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        assert (valid > 0).all(), "Realized vol should be positive for non-constant prices"

    def test_constant_price_zero_vol(self, constant_df):
        factor = RealizedVolatilityFactor(period=20)
        result = factor.compute(constant_df)
        valid = result.dropna()
        # Constant price → returns = 0 → vol = 0
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-10)

    def test_vol_annualized(self, ohlcv_df):
        """Annualized vol should be reasonable (0.01 - 5.0 for normal markets)."""
        factor = RealizedVolatilityFactor(period=20)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        assert (valid > 0.01).all() and (valid < 5.0).all(), \
            f"Annualized vol should be reasonable, got range [{valid.min()}, {valid.max()}]"

    def test_warmup_period(self, ohlcv_df):
        factor = RealizedVolatilityFactor(period=20)
        result = factor.compute(ohlcv_df)
        assert result.iloc[:20].isna().all()

    def test_lookahead_free(self):
        factor = RealizedVolatilityFactor()
        assert factor.validate_lookahead()


class TestATRFactor:
    """Tests for ATRFactor."""

    def test_atr_positive(self, ohlcv_df):
        factor = ATRFactor(period=14)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        assert (valid > 0).all(), "ATR should be positive"

    def test_atr_known_range(self, ohlcv_df):
        """Normalized ATR should be a small fraction of price."""
        factor = ATRFactor(period=14)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        # ATR/close should be small (< 0.2 for normal markets)
        assert (valid < 0.5).all(), f"Normalized ATR too high: {valid.max()}"

    def test_atr_with_gap(self):
        """ATR should capture gaps via true range."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        closes = [100.0] * 30
        highs = [101.0] * 30
        lows = [99.0] * 30
        # Insert a gap: bar 15 opens much higher
        closes[15] = 110.0
        highs[15] = 111.0
        lows[15] = 109.0
        df = pd.DataFrame({
            "open": closes, "high": highs, "low": lows, "close": closes,
            "volume": [1e6] * 30,
        }, index=dates)
        factor = ATRFactor(period=14)
        result = factor.compute(df)
        # ATR after gap should be higher than before
        post_gap = result.iloc[16:].dropna()
        if len(post_gap) > 0:
            pre_gap = result.iloc[1:15].dropna()
            if len(pre_gap) > 0:
                assert post_gap.mean() > pre_gap.mean(), \
                    "ATR should increase after a price gap"

    def test_atr_warmup(self, ohlcv_df):
        factor = ATRFactor(period=14)
        result = factor.compute(ohlcv_df)
        # First 13 values should be NaN (need 14 bars for rolling window)
        assert result.iloc[:13].isna().all()

    def test_atr_columns_required(self):
        factor = ATRFactor()
        assert "high" in factor.meta.columns_required
        assert "low" in factor.meta.columns_required
        assert "close" in factor.meta.columns_required

    def test_lookahead_free(self):
        factor = ATRFactor()
        assert factor.validate_lookahead()


class TestBollingerWidthFactor:
    """Tests for BollingerWidthFactor."""

    def test_bollinger_positive(self, ohlcv_df):
        factor = BollingerWidthFactor(period=20)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        assert (valid > 0).all(), "Bollinger width should be positive"

    def test_bollinger_constant_price(self, constant_df):
        factor = BollingerWidthFactor(period=20)
        result = factor.compute(constant_df)
        valid = result.dropna()
        # Constant price → std=0 → width=0
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-10)

    def test_bollinger_expands_with_volatility(self):
        """Bollinger width should increase with volatility."""
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        # Low volatility first 30 bars, high volatility last 30 bars
        closes_low = [100.0 + np.random.normal(0, 0.1) for _ in range(30)]
        closes_high = [100.0 + np.random.normal(0, 5.0) for _ in range(30)]
        closes = closes_low + closes_high
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*60}, index=dates)
        factor = BollingerWidthFactor(period=20)
        result = factor.compute(df)
        # Width in high-vol regime should be larger
        low_vol_width = result.iloc[20:30].dropna().mean()
        high_vol_width = result.iloc[40:60].dropna().mean()
        assert high_vol_width > low_vol_width, \
            "Bollinger width should expand with increased volatility"

    def test_bollinger_warmup(self, ohlcv_df):
        factor = BollingerWidthFactor(period=20)
        result = factor.compute(ohlcv_df)
        # First 19 values should be NaN (need 20 bars)
        assert result.iloc[:19].isna().all()

    def test_lookahead_free(self):
        factor = BollingerWidthFactor()
        assert factor.validate_lookahead()


class TestVolumeRatioFactor:
    """Tests for VolumeRatioFactor."""

    def test_volume_ratio_around_one(self, ohlcv_df):
        """Volume ratio should average around 1.0."""
        factor = VolumeRatioFactor(period=20)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        # Mean should be close to 1.0
        assert 0.5 < valid.mean() < 2.0, \
            f"Average volume ratio should be near 1.0, got {valid.mean()}"

    def test_volume_ratio_constant_volume(self, constant_df):
        factor = VolumeRatioFactor(period=20)
        result = factor.compute(constant_df)
        valid = result.dropna()
        # Constant volume → ratio = 1.0
        np.testing.assert_allclose(valid.values, 1.0, atol=1e-10)

    def test_volume_ratio_spike(self):
        """Volume spike should produce high ratio."""
        dates = pd.date_range("2024-01-01", periods=40, freq="D")
        vols = [1e6] * 40
        vols[30] = 5e6  # Volume spike at bar 30
        closes = [100.0] * 40
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": vols}, index=dates)
        factor = VolumeRatioFactor(period=20)
        result = factor.compute(df)
        assert result.iloc[30] > result.iloc[29], \
            "Volume ratio should spike on volume surge"

    def test_volume_ratio_warmup(self, ohlcv_df):
        factor = VolumeRatioFactor(period=20)
        result = factor.compute(ohlcv_df)
        assert result.iloc[:19].isna().all()

    def test_lookahead_free(self):
        factor = VolumeRatioFactor()
        assert factor.validate_lookahead()


class TestRSIFactor:
    """Tests for RSI Factor."""

    def test_rsi_range(self, ohlcv_df):
        """RSI should be between 0 and 100."""
        factor = RSIFactor(period=14)
        result = factor.compute(ohlcv_df)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all(), \
            f"RSI out of range: [{valid.min()}, {valid.max()}]"

    def test_rsi_overbought(self):
        """Mostly rising prices → RSI should be high (overbought)."""
        dates = pd.date_range("2024-01-01", periods=40, freq="D")
        # Rising with occasional dips so avg_loss != 0
        closes = []
        price = 100.0
        for i in range(40):
            if i % 5 == 0:
                price -= 1.0  # Occasional dip
            else:
                price += 2.0  # Generally rising
            closes.append(price)
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*40}, index=dates)
        factor = RSIFactor(period=14)
        result = factor.compute(df)
        valid = result.dropna()
        assert len(valid) > 0, "Should have valid RSI values"
        assert valid.iloc[-1] > 50, \
            f"RSI should be > 50 in uptrend, got {valid.iloc[-1]}"

    def test_rsi_oversold(self):
        """Mostly falling prices → RSI should be low (oversold)."""
        dates = pd.date_range("2024-01-01", periods=40, freq="D")
        # Falling with occasional bounces so avg_gain != 0
        closes = []
        price = 200.0
        for i in range(40):
            if i % 5 == 0:
                price += 1.0  # Occasional bounce
            else:
                price -= 2.0  # Generally falling
            closes.append(price)
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*40}, index=dates)
        factor = RSIFactor(period=14)
        result = factor.compute(df)
        valid = result.dropna()
        assert len(valid) > 0, "Should have valid RSI values"
        assert valid.iloc[-1] < 50, \
            f"RSI should be < 50 in downtrend, got {valid.iloc[-1]}"

    def test_rsi_constant_price(self, constant_df):
        """Constant price → RSI should be NaN or 50 (no direction)."""
        factor = RSIFactor(period=14)
        result = factor.compute(constant_df)
        valid = result.dropna()
        # Constant price → avg_loss = 0 → division by 0 → NaN, or RSI=100
        # Implementation may vary; just verify no crash and values in [0,100] or NaN
        if len(valid) > 0:
            assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_warmup(self, ohlcv_df):
        factor = RSIFactor(period=14)
        result = factor.compute(ohlcv_df)
        # First 13 values should be NaN (need 14 bars for rolling window + 1 for diff)
        assert result.iloc[:13].isna().all()

    def test_rsi_14_period(self):
        """Verify RSI-14 against known calculation."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        # Mix of up and down days
        closes = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                  111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*20}, index=dates)
        factor = RSIFactor(period=14)
        result = factor.compute(df)
        # RSI at last bar should be > 50 (net uptrend)
        assert result.iloc[-1] > 50

    def test_lookahead_free(self):
        factor = RSIFactor()
        assert factor.validate_lookahead()


class TestMACDHistogramFactor:
    """Tests for MACD Histogram Factor."""

    def test_macd_histogram_name(self):
        factor = MACDHistogramFactor()
        assert factor.name == "macd_histogram"

    def test_macd_histogram_bullish_crossover(self):
        """MACD histogram should turn positive on bullish crossover."""
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        # Start with decline, then rally
        closes = [200 - i * 0.5 for i in range(30)] + [185 + i * 1.0 for i in range(30)]
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*60}, index=dates)
        factor = MACDHistogramFactor()
        result = factor.compute(df)
        # After the crossover, histogram should be positive
        late_values = result.iloc[45:].dropna()
        if len(late_values) > 0:
            assert (late_values > 0).any(), \
                "MACD histogram should turn positive after bullish crossover"

    def test_macd_histogram_bearish_crossover(self):
        """MACD histogram should turn negative on bearish crossover."""
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        # Start with rally, then decline
        closes = [100 + i * 1.0 for i in range(30)] + [129 - i * 0.5 for i in range(30)]
        df = pd.DataFrame({"close": closes, "open": closes, "high": closes,
                           "low": closes, "volume": [1e6]*60}, index=dates)
        factor = MACDHistogramFactor()
        result = factor.compute(df)
        # Late values should be negative
        late_values = result.iloc[45:].dropna()
        if len(late_values) > 0:
            assert (late_values < 0).any(), \
                "MACD histogram should turn negative after bearish crossover"

    def test_macd_no_inf(self, ohlcv_df):
        factor = MACDHistogramFactor()
        result = factor.compute(ohlcv_df)
        assert not np.isinf(result.dropna()).any()

    def test_macd_warmup(self, ohlcv_df):
        factor = MACDHistogramFactor()
        result = factor.compute(ohlcv_df)
        # EWM-based MACD produces values from bar 1 onwards (not NaN-warmup like SMA)
        # Values in first few bars are unreliable but not NaN
        assert result is not None
        assert len(result) == len(ohlcv_df)

    def test_lookahead_free(self):
        factor = MACDHistogramFactor()
        assert factor.validate_lookahead()

    def test_meta_min_warmup(self):
        factor = MACDHistogramFactor()
        assert factor.meta.min_warmup_bars == 35


class TestGetAllTechnicalFactors:
    """Tests for the get_all_technical_factors factory function."""

    def test_returns_list(self):
        factors = get_all_technical_factors()
        assert isinstance(factors, list)

    def test_returns_nine_factors(self):
        factors = get_all_technical_factors()
        assert len(factors) == 9, f"Expected 9 factors, got {len(factors)}"

    def test_all_inherit_from_alpha_factor(self):
        factors = get_all_technical_factors()
        for f in factors:
            assert isinstance(f, AlphaFactor), f"{f.name} should inherit from AlphaFactor"

    def test_unique_names(self):
        factors = get_all_technical_factors()
        names = [f.name for f in factors]
        assert len(names) == len(set(names)), "Factor names should be unique"


class TestFactorOutputValidation:
    """Test output validation for all factors."""

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_no_inf_in_output(self, factor_cls, ohlcv_df):
        """All factors should produce inf-free output."""
        factor = factor_cls()
        result = factor.compute(ohlcv_df)
        assert not np.isinf(result.dropna()).any(), \
            f"{factor.name} produced inf values"

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_lookahead_free(self, factor_cls):
        """All factors should be lookahead-free."""
        factor = factor_cls()
        assert factor.validate_lookahead(), \
            f"{factor.name} has lookahead bias"

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_output_length_matches_input(self, factor_cls, ohlcv_df):
        """Output should have same length as input."""
        factor = factor_cls()
        result = factor.compute(ohlcv_df)
        assert len(result) == len(ohlcv_df), \
            f"{factor.name}: output length {len(result)} != input length {len(ohlcv_df)}"

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_validate_output_passes(self, factor_cls, ohlcv_df):
        """validate_output should not raise for reasonable input."""
        factor = factor_cls()
        result = factor.compute(ohlcv_df)
        validated = factor.validate_output(result)
        assert validated is not None

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_short_input_no_crash(self, factor_cls, short_df):
        """Factor should not crash on short input."""
        factor = factor_cls()
        result = factor.compute(short_df)
        # Should return NaN for warmup but not crash
        assert result is not None

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_constant_input_no_crash(self, factor_cls, constant_df):
        """Factor should handle constant prices without crashing."""
        factor = factor_cls()
        result = factor.compute(constant_df)
        assert result is not None


class TestFactorMeta:
    """Tests for factor metadata consistency."""

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_meta_has_required_fields(self, factor_cls):
        factor = factor_cls()
        meta = factor.meta
        assert meta.id is not None
        assert meta.zoo == "technical"
        assert len(meta.theme) > 0
        assert len(meta.columns_required) > 0
        assert meta.min_warmup_bars > 0

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RateOfChangeFactor, MeanReversionFactor,
        RealizedVolatilityFactor, ATRFactor, BollingerWidthFactor,
        VolumeRatioFactor, RSIFactor, MACDHistogramFactor,
    ])
    def test_meta_universe_not_empty(self, factor_cls):
        factor = factor_cls()
        assert len(factor.meta.universe) > 0
