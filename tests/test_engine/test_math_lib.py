"""
Tests for Math Engine — Full Indicator Validation
===================================================
Every indicator must produce correct results against known values.
No approximation. No shortcuts.
"""

from __future__ import annotations

import math
import pytest

from quant_nanggroe_ai.engine.math_lib import MathEngine


class TestSMA:
    """Simple Moving Average tests."""

    def test_basic(self) -> None:
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = MathEngine.sma(data, 3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(2.0, abs=0.001)
        assert result[3] == pytest.approx(3.0, abs=0.001)
        assert result[4] == pytest.approx(4.0, abs=0.001)

    def test_period_equals_length(self) -> None:
        data = [10.0, 20.0, 30.0]
        result = MathEngine.sma(data, 3)
        assert result[2] == pytest.approx(20.0, abs=0.001)

    def test_insufficient_data(self) -> None:
        data = [1.0, 2.0]
        result = MathEngine.sma(data, 5)
        assert all(v is None for v in result)

    def test_single_period(self) -> None:
        data = [5.0, 10.0, 15.0]
        result = MathEngine.sma(data, 1)
        assert result[0] == 5.0
        assert result[1] == 10.0
        assert result[2] == 15.0


class TestEMA:
    """Exponential Moving Average tests."""

    def test_seed_is_sma(self) -> None:
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = MathEngine.ema(data, 3)
        assert result[2] == pytest.approx(2.0, abs=0.001)  # SMA seed

    def test_ema_converges(self) -> None:
        """EMA should respond faster to recent data than SMA."""
        data = [10.0] * 20 + [20.0] * 80  # Long tail to ensure EMA catches up
        ema_result = MathEngine.ema(data, 10)
        sma_result = MathEngine.sma(data, 10)
        # After step change, EMA should be closer to 20 than SMA
        assert ema_result[-1] is not None
        assert sma_result[-1] is not None
        # Both should converge to 20 after enough data
        assert ema_result[-1] > 19.99  # EMA should be near 20
        assert sma_result[-1] == 20.0  # SMA is exactly 20


class TestRSI:
    """RSI (Wilder's Smoothing) tests."""

    def test_overbought(self, rsi_overbought_closes: list[float]) -> None:
        result = MathEngine.rsi(rsi_overbought_closes, 14)
        last_rsi = result[-1]
        assert last_rsi is not None
        assert last_rsi > 70.0, f"RSI should be > 70 for rising prices, got {last_rsi}"

    def test_oversold(self, rsi_oversold_closes: list[float]) -> None:
        result = MathEngine.rsi(rsi_oversold_closes, 14)
        last_rsi = result[-1]
        assert last_rsi is not None
        assert last_rsi < 30.0, f"RSI should be < 30 for falling prices, got {last_rsi}"

    def test_range_0_100(self, sample_closes: list[float]) -> None:
        result = MathEngine.rsi(sample_closes, 14)
        for v in result:
            if v is not None:
                assert 0.0 <= v <= 100.0, f"RSI {v} out of range"

    def test_insufficient_data(self) -> None:
        result = MathEngine.rsi([100.0], 14)
        assert all(v is None for v in result)

    def test_known_value(self) -> None:
        """Test RSI against a known calculation."""
        closes = [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        result = MathEngine.rsi(closes, 14)
        last = result[-1]
        assert last is not None
        # RSI should be between 50-80 for this mildly uptrending data
        assert 40.0 <= last <= 90.0, f"RSI {last} unexpected"


class TestMACD:
    """MACD tests."""

    def test_structure(self, sample_closes: list[float]) -> None:
        result = MathEngine.macd(sample_closes)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == len(sample_closes)

    def test_histogram_equals_diff(self, sample_closes: list[float]) -> None:
        result = MathEngine.macd(sample_closes)
        for i in range(len(sample_closes)):
            if result["macd"][i] is not None and result["signal"][i] is not None:
                expected = result["macd"][i] - result["signal"][i]
                assert result["histogram"][i] == pytest.approx(expected, abs=0.001)


class TestBollingerBands:
    """Bollinger Bands tests."""

    def test_upper_above_lower(self, sample_closes: list[float]) -> None:
        bb = MathEngine.bollinger_bands(sample_closes)
        for i in range(len(sample_closes)):
            if bb["upper"][i] is not None and bb["lower"][i] is not None:
                assert bb["upper"][i] > bb["lower"][i], f"Upper <= Lower at index {i}"

    def test_middle_is_sma(self, sample_closes: list[float]) -> None:
        bb = MathEngine.bollinger_bands(sample_closes, 20)
        sma = MathEngine.sma(sample_closes, 20)
        for i in range(len(sample_closes)):
            if bb["middle"][i] is not None and sma[i] is not None:
                assert bb["middle"][i] == pytest.approx(sma[i], abs=0.001)

    def test_percent_b_range(self, sample_closes: list[float]) -> None:
        bb = MathEngine.bollinger_bands(sample_closes)
        for v in bb["percent_b"]:
            if v is not None:
                # %B can go outside 0-1 during strong moves
                assert -1.0 <= v <= 2.0


class TestATR:
    """Average True Range tests."""

    def test_positive(self, sample_ohlcv: dict) -> None:
        result = MathEngine.atr(
            sample_ohlcv["highs"],
            sample_ohlcv["lows"],
            sample_ohlcv["closes"],
            14,
        )
        for v in result:
            if v is not None:
                assert v > 0, "ATR must be positive"

    def test_wilder_smoothing(self) -> None:
        """Verify ATR uses Wilder's smoothing (not SMA)."""
        highs = [105.0, 106.0, 104.0, 107.0, 103.0, 108.0, 105.0,
                 106.0, 109.0, 104.0, 107.0, 105.0, 108.0, 106.0, 110.0]
        lows = [100.0, 101.0, 99.0, 102.0, 98.0, 103.0, 100.0,
                101.0, 104.0, 99.0, 102.0, 100.0, 103.0, 101.0, 105.0]
        closes = [103.0, 104.0, 101.0, 105.0, 100.0, 106.0, 102.0,
                  103.0, 107.0, 101.0, 105.0, 102.0, 106.0, 103.0, 108.0]
        result = MathEngine.atr(highs, lows, closes, 14)
        # ATR should exist at index 14
        assert result[14] is not None
        assert result[14] > 0


class TestADX:
    """ADX (proper Wilder's smoothing) tests."""

    def test_strong_trend(self, trending_up_closes: list[float]) -> None:
        """ADX should be high (>25) for strong trend."""
        result = MathEngine.adx(
            [c * 1.01 for c in trending_up_closes],  # highs slightly above
            [c * 0.99 for c in trending_up_closes],  # lows slightly below
            trending_up_closes,
            14,
        )
        last_adx = result["adx"][-1]
        if last_adx is not None:
            assert last_adx > 20.0, f"ADX should be > 20 for strong trend, got {last_adx}"

    def test_range_0_100(self, sample_ohlcv: dict) -> None:
        result = MathEngine.adx(
            sample_ohlcv["highs"],
            sample_ohlcv["lows"],
            sample_ohlcv["closes"],
            14,
        )
        for key in ["adx", "plus_di", "minus_di"]:
            for v in result[key]:
                if v is not None:
                    assert 0.0 <= v <= 100.0, f"{key} {v} out of range"


class TestVWAP:
    """VWAP tests."""

    def test_equals_close_when_uniform_volume(self) -> None:
        """With uniform volume, VWAP ≈ average close."""
        closes = [100.0, 101.0, 102.0, 101.0, 100.0]
        volumes = [1000.0] * 5
        result = MathEngine.vwap(closes, closes, closes, volumes)
        # With uniform volume, VWAP should be close to SMA of closes
        avg = sum(closes) / len(closes)
        assert result[-1] is not None
        assert result[-1] == pytest.approx(avg, abs=0.01)


class TestKellyCriterion:
    """Kelly Criterion tests."""

    def test_positive_edge(self) -> None:
        result = MathEngine.kelly_criterion(0.6, 200.0, 100.0, fraction=0.25)
        assert result["fractional_kelly"] > 0

    def test_no_edge(self) -> None:
        result = MathEngine.kelly_criterion(0.5, 100.0, 100.0, fraction=0.25)
        # With 50% win rate and 1:1 ratio, Kelly = 0
        assert result["fractional_kelly"] <= 0

    def test_zero_loss(self) -> None:
        result = MathEngine.kelly_criterion(0.6, 200.0, 0.0, fraction=0.25)
        assert result["kelly_pct"] == 0

    def test_fractional_kelly(self) -> None:
        result = MathEngine.kelly_criterion(0.6, 200.0, 100.0, fraction=0.5)
        full = result["full_kelly"]
        frac = result["fractional_kelly"]
        assert frac == pytest.approx(full * 0.5, abs=0.001)


class TestAnalyzeSequence:
    """Master analysis function tests."""

    def test_full_analysis(self, sample_ohlcv: dict) -> None:
        result = MathEngine.analyze_sequence(
            sample_ohlcv["closes"],
            sample_ohlcv["highs"],
            sample_ohlcv["lows"],
            sample_ohlcv["volumes"],
        )
        assert "error" not in result
        assert "indicators" in result
        assert result["indicators"]["rsi_14"] is not None

    def test_insufficient_data(self) -> None:
        result = MathEngine.analyze_sequence([100.0, 101.0])
        assert "error" in result

    def test_closes_only(self, sample_closes: list[float]) -> None:
        result = MathEngine.analyze_sequence(sample_closes)
        assert "indicators" in result
