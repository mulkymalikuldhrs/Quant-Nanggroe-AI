#!/usr/bin/env python3
"""
Unit tests for MathEngine - RSI, MACD, Bollinger Bands, ATR calculations
Run with: python -m pytest tests/test_math_engine.py -v
"""

import sys
import math
from pathlib import Path

# Add src to path so we can import tools
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.math_engine import MathEngine


# ─── Helper ───────────────────────────────────────────────────────

def generate_trending_up(n: int = 100, base: float = 100.0, step: float = 0.5) -> dict:
    """Generate a simple trending-up price series."""
    closes = [base + i * step for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    volumes = [1000.0] * n
    return {"closes": closes, "highs": highs, "lows": lows, "volumes": volumes}


def generate_trending_down(n: int = 100, base: float = 200.0, step: float = 0.5) -> dict:
    """Generate a simple trending-down price series."""
    closes = [base - i * step for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    volumes = [1000.0] * n
    return {"closes": closes, "highs": highs, "lows": lows, "volumes": volumes}


def generate_ranging(n: int = 100, base: float = 150.0, amplitude: float = 5.0) -> dict:
    """Generate a ranging/sideways price series using a sine wave."""
    closes = [base + amplitude * math.sin(2 * math.pi * i / 20) for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    volumes = [1000.0] * n
    return {"closes": closes, "highs": highs, "lows": lows, "volumes": volumes}


# ─── RSI Tests ────────────────────────────────────────────────────

class TestRSI:
    """Tests for the RSI (Relative Strength Index) calculation."""

    def test_rsi_length_matches_input(self):
        """RSI output list should have the same length as the input."""
        data = generate_trending_up(50)
        result = MathEngine.rsi(data["closes"], 14)
        assert len(result) == len(data["closes"])

    def test_rsi_first_values_are_none(self):
        """First `period` values should be None (not enough data)."""
        data = generate_trending_up(50)
        result = MathEngine.rsi(data["closes"], 14)
        for i in range(14):
            assert result[i] is None, f"RSI at index {i} should be None"

    def test_rsi_range_0_to_100(self):
        """RSI values should be between 0 and 100."""
        data = generate_trending_up(100)
        result = MathEngine.rsi(data["closes"], 14)
        for val in result:
            if val is not None:
                assert 0 <= val <= 100, f"RSI {val} out of [0, 100] range"

    def test_rsi_high_for_uptrend(self):
        """RSI should be high (>60) for a strongly trending-up series."""
        data = generate_trending_up(100, step=1.0)
        result = MathEngine.rsi(data["closes"], 14)
        last_rsi = result[-1]
        assert last_rsi is not None
        assert last_rsi > 60, f"RSI for strong uptrend should be >60, got {last_rsi}"

    def test_rsi_low_for_downtrend(self):
        """RSI should be low (<40) for a strongly trending-down series."""
        data = generate_trending_down(100, step=1.0)
        result = MathEngine.rsi(data["closes"], 14)
        last_rsi = result[-1]
        assert last_rsi is not None
        assert last_rsi < 40, f"RSI for strong downtrend should be <40, got {last_rsi}"

    def test_rsi_insufficient_data(self):
        """RSI with too few data points should return all None."""
        closes = [100.0, 101.0, 102.0]
        result = MathEngine.rsi(closes, 14)
        assert all(v is None for v in result)


# ─── MACD Tests ──────────────────────────────────────────────────

class TestMACD:
    """Tests for the MACD calculation."""

    def test_macd_keys(self):
        """MACD should return dict with 'macd', 'signal', 'histogram' keys."""
        data = generate_trending_up(100)
        result = MathEngine.macd(data["closes"])
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_macd_output_length(self):
        """MACD output lists should match input length."""
        data = generate_trending_up(100)
        result = MathEngine.macd(data["closes"])
        assert len(result["macd"]) == len(data["closes"])
        assert len(result["signal"]) == len(data["closes"])
        assert len(result["histogram"]) == len(data["closes"])

    def test_macd_histogram_equals_diff(self):
        """Histogram should equal MACD line minus signal line where both exist."""
        data = generate_trending_up(100)
        result = MathEngine.macd(data["closes"])
        for i in range(len(data["closes"])):
            if result["macd"][i] is not None and result["signal"][i] is not None:
                expected = result["macd"][i] - result["signal"][i]
                actual = result["histogram"][i]
                assert actual is not None
                assert abs(actual - expected) < 1e-10, \
                    f"Histogram mismatch at index {i}: {actual} vs {expected}"

    def test_macd_positive_for_uptrend(self):
        """MACD line should be positive for a strong uptrend (EMA_fast > EMA_slow)."""
        data = generate_trending_up(100, step=1.0)
        result = MathEngine.macd(data["closes"])
        last_macd = result["macd"][-1]
        assert last_macd is not None
        assert last_macd > 0, f"MACD for uptrend should be positive, got {last_macd}"

    def test_macd_negative_for_downtrend(self):
        """MACD line should be negative for a strong downtrend (EMA_fast < EMA_slow)."""
        data = generate_trending_down(100, step=1.0)
        result = MathEngine.macd(data["closes"])
        last_macd = result["macd"][-1]
        assert last_macd is not None
        assert last_macd < 0, f"MACD for downtrend should be negative, got {last_macd}"


# ─── Bollinger Bands Tests ───────────────────────────────────────

class TestBollingerBands:
    """Tests for the Bollinger Bands calculation."""

    def test_bollinger_keys(self):
        """Bollinger Bands should return dict with required keys."""
        data = generate_trending_up(100)
        result = MathEngine.bollinger_bands(data["closes"])
        for key in ["middle", "upper", "lower", "bandwidth", "percent_b"]:
            assert key in result, f"Missing key: {key}"

    def test_bollinger_output_length(self):
        """Bollinger Bands output lists should match input length."""
        data = generate_trending_up(100)
        result = MathEngine.bollinger_bands(data["closes"])
        for key in ["middle", "upper", "lower", "bandwidth", "percent_b"]:
            assert len(result[key]) == len(data["closes"])

    def test_bollinger_upper_above_lower(self):
        """Upper band should always be >= lower band."""
        data = generate_trending_up(100)
        result = MathEngine.bollinger_bands(data["closes"])
        for i in range(len(data["closes"])):
            if result["upper"][i] is not None and result["lower"][i] is not None:
                assert result["upper"][i] >= result["lower"][i], \
                    f"Upper < Lower at index {i}: {result['upper'][i]} < {result['lower'][i]}"

    def test_bollinger_middle_between_bands(self):
        """Middle band should be between upper and lower bands."""
        data = generate_ranging(100)
        result = MathEngine.bollinger_bands(data["closes"])
        for i in range(len(data["closes"])):
            if result["middle"][i] is not None:
                assert result["lower"][i] <= result["middle"][i] <= result["upper"][i], \
                    f"Middle not between bands at index {i}"

    def test_bollinger_bandwidth_positive(self):
        """Bandwidth should be non-negative where defined."""
        data = generate_trending_up(100)
        result = MathEngine.bollinger_bands(data["closes"])
        for val in result["bandwidth"]:
            if val is not None:
                assert val >= 0, f"Bandwidth should be >= 0, got {val}"

    def test_bollinger_percent_b_range(self):
        """%B should typically be between 0 and 1 for ranging data, but can exceed for trends."""
        data = generate_ranging(100)
        result = MathEngine.bollinger_bands(data["closes"])
        # Just verify it's a valid float
        for val in result["percent_b"]:
            if val is not None:
                assert isinstance(val, float)

    def test_bollinger_first_values_none(self):
        """First `period-1` values should be None."""
        period = 20
        data = generate_trending_up(50)
        result = MathEngine.bollinger_bands(data["closes"], period=period)
        for i in range(period - 1):
            assert result["middle"][i] is None
            assert result["upper"][i] is None
            assert result["lower"][i] is None


# ─── ATR Tests ───────────────────────────────────────────────────

class TestATR:
    """Tests for the ATR (Average True Range) calculation."""

    def test_atr_length_matches_input(self):
        """ATR output list should have the same length as the input."""
        data = generate_trending_up(50)
        result = MathEngine.atr(data["highs"], data["lows"], data["closes"], 14)
        assert len(result) == len(data["closes"])

    def test_atr_positive_values(self):
        """ATR values should be non-negative (range can't be negative)."""
        data = generate_trending_up(100)
        result = MathEngine.atr(data["highs"], data["lows"], data["closes"], 14)
        for val in result:
            if val is not None:
                assert val >= 0, f"ATR should be >= 0, got {val}"

    def test_atr_constant_range_equals_high_low_spread(self):
        """ATR for constant-range bars should equal the high-low spread."""
        n = 50
        closes = [100.0] * n
        highs = [102.0] * n
        lows = [98.0] * n
        result = MathEngine.atr(highs, lows, closes, 14)
        last_atr = result[-1]
        assert last_atr is not None
        # For constant range of 4.0, ATR should converge to 4.0
        assert abs(last_atr - 4.0) < 0.5, \
            f"ATR for constant range should be ~4.0, got {last_atr}"

    def test_atr_increases_with_volatility(self):
        """ATR should be higher for more volatile data."""
        low_vol = generate_ranging(100, amplitude=2.0)
        high_vol = generate_ranging(100, amplitude=10.0)
        atr_low = MathEngine.atr(low_vol["highs"], low_vol["lows"],
                                 low_vol["closes"], 14)
        atr_high = MathEngine.atr(high_vol["highs"], high_vol["lows"],
                                  high_vol["closes"], 14)
        assert atr_low[-1] is not None and atr_high[-1] is not None
        assert atr_high[-1] > atr_low[-1], \
            f"High-vol ATR ({atr_high[-1]}) should exceed low-vol ATR ({atr_low[-1]})"

    def test_atr_insufficient_data(self):
        """ATR with too few data points should return all None."""
        closes = [100.0]
        highs = [101.0]
        lows = [99.0]
        result = MathEngine.atr(highs, lows, closes, 14)
        assert all(v is None for v in result)

    def test_atr_first_values_none(self):
        """First `period` ATR values should be None."""
        data = generate_trending_up(50)
        result = MathEngine.atr(data["highs"], data["lows"], data["closes"], 14)
        for i in range(14):
            assert result[i] is None, f"ATR at index {i} should be None"


# ─── Integration: analyze_sequence ───────────────────────────────

class TestAnalyzeSequence:
    """Tests for the master analyze_sequence function."""

    def test_analyze_sequence_returns_indicators(self):
        """analyze_sequence should return a dict with 'indicators' key."""
        data = generate_trending_up(60)
        result = MathEngine.analyze_sequence(
            data["closes"], data["highs"], data["lows"], data["volumes"]
        )
        assert "indicators" in result
        assert "latest_close" in result
        assert result["bars"] == 60

    def test_analyze_sequence_insufficient_data(self):
        """analyze_sequence with <30 bars should return error."""
        closes = [100.0] * 10
        result = MathEngine.analyze_sequence(closes)
        assert "error" in result

    def test_analyze_sequence_rsi_present(self):
        """analyze_sequence should include RSI in indicators."""
        data = generate_trending_up(60)
        result = MathEngine.analyze_sequence(
            data["closes"], data["highs"], data["lows"], data["volumes"]
        )
        assert "rsi_14" in result["indicators"]


if __name__ == "__main__":
    # Simple runner for quick verification without pytest
    import traceback
    test_classes = [TestRSI, TestMACD, TestBollingerBands, TestATR, TestAnalyzeSequence]
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for attr in dir(instance):
            if attr.startswith("test_"):
                try:
                    getattr(instance, attr)()
                    passed += 1
                    print(f"  PASS: {cls.__name__}.{attr}")
                except Exception as e:
                    failed += 1
                    print(f"  FAIL: {cls.__name__}.{attr}: {e}")
                    traceback.print_exc()
    print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed} tests")
    sys.exit(0 if failed == 0 else 1)
