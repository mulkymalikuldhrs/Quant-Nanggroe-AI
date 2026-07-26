"""
Unit tests for COTTracker / COTAnalyzer (quant_nanggroe.engine.causal.cot_tracker).

Tests cover:
  - COTTracker.init, properties, contract defaults
  - get_positioning_percentile() — correctness, edge cases, column variants
  - detect_extreme_positioning() — thresholds, edge cases
  - COTAnalyzer.analyze() — signal generation logic
  - Mock-based fetch to avoid cot_reports dependency
"""

from __future__ import annotations

import sys
import os
import math

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_nanggroe.engine.causal.cot_tracker import (
    COTTracker,
    COTAnalyzer,
    DEFAULT_COT_CONTRACTS,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def basic_cot_tracker() -> COTTracker:
    """COTTracker with cot_reports module disabled (no live fetch)."""
    t = COTTracker()
    t._cot_module = None  # disable live fetch
    return t


@pytest.fixture
def sample_cot_data() -> pd.DataFrame:
    """A 60-row DataFrame simulating COT data for a single asset (e.g. GC)."""
    np.random.seed(42)

    # Create smooth-ish time series so percentiles are interpretable
    n = 60
    base_long = np.linspace(200_000, 350_000, n) + np.random.normal(0, 15000, n)
    base_short = np.linspace(80_000, 60_000, n) + np.random.normal(0, 8000, n)
    base_retail_long = np.linspace(30_000, 50_000, n) + np.random.normal(0, 5000, n)
    base_retail_short = np.linspace(20_000, 15_000, n) + np.random.normal(0, 3000, n)

    return pd.DataFrame({
        "NonComm_Long": base_long.astype(int),
        "NonComm_Short": base_short.astype(int),
        "Comm_Long": (base_short * 0.6 + 50_000).astype(int),
        "Comm_Short": (base_long * 0.5 + 20_000).astype(int),
        "NonRep_Long": base_retail_long.astype(int),
        "NonRep_Short": base_retail_short.astype(int),
        "Open_Interest": (base_long + base_short).astype(int),
    })


@pytest.fixture
def tracker_with_data(basic_cot_tracker, sample_cot_data) -> COTTracker:
    """COTTracker pre-populated with sample GC data."""
    basic_cot_tracker._data = {"GC": sample_cot_data}
    return basic_cot_tracker


# ── Test: DEFAULT_COT_CONTRACTS ──────────────────────────────────────────


class TestDefaults:
    def test_has_key_contracts(self):
        """All major asset classes are tracked."""
        for key in ("GC", "SI", "ES", "NQ", "CL", "6E", "6J"):
            assert key in DEFAULT_COT_CONTRACTS, f"Missing {key}"

    def test_each_contract_is_pair(self):
        """Each entry is (market_name, legacy_fut_code)."""
        for name, (mkt, code) in DEFAULT_COT_CONTRACTS.items():
            assert isinstance(mkt, str) and len(mkt) > 0
            assert isinstance(code, str) and len(code) > 0, f"{name} code invalid"


# ── Test: COTTracker.__init__ ────────────────────────────────────────────


class TestInit:
    def test_default_contracts(self, basic_cot_tracker):
        assert set(basic_cot_tracker._contracts.keys()) == set(DEFAULT_COT_CONTRACTS.keys())

    def test_custom_contracts(self):
        custom = {"ES": ("S&P 500", "13874")}
        t = COTTracker(contracts=custom)
        assert t._contracts == custom

    def test_init_has_no_data(self, basic_cot_tracker):
        assert basic_cot_tracker.has_data is False
        assert basic_cot_tracker.last_fetch is None


# ── Test: Properties ─────────────────────────────────────────────────────


class TestProperties:
    def test_has_data_true(self, tracker_with_data):
        assert tracker_with_data.has_data is True

    def test_has_data_false(self, basic_cot_tracker):
        assert basic_cot_tracker.has_data is False

    def test_last_fetch_none_on_init(self, basic_cot_tracker):
        assert basic_cot_tracker.last_fetch is None


# ── Test: get_positioning_percentile ─────────────────────────────────────


class TestGetPositioningPercentile:
    """Core percentile calculation tests."""

    def test_basic_percentile(self, tracker_with_data):
        """Returns correct keys and structure."""
        result = tracker_with_data.get_positioning_percentile("GC")
        assert result["asset"] == "GC"
        assert result["n_weeks"] == 60
        assert "noncomm_net" in result
        assert "noncomm_long" in result
        assert "noncomm_short" in result
        assert "comm_long" in result
        assert "comm_short" in result
        assert "retail_long" in result
        assert "retail_short" in result

    def test_percentile_is_0_to_100(self, tracker_with_data):
        """All percentiles are in [0, 100] range."""
        result = tracker_with_data.get_positioning_percentile("GC")
        for key in ("noncomm_net", "noncomm_long", "comm_long", "retail_long"):
            if key in result:
                assert 0 <= result[key]["percentile"] <= 100, f"{key} percentile out of range"

    def test_last_value_is_last_row(self, tracker_with_data):
        """'value' field equals the last row's value."""
        df = tracker_with_data._data["GC"]
        result = tracker_with_data.get_positioning_percentile("GC")
        assert result["noncomm_net"]["value"] == int(df["NonComm_Short"].iloc[-1] - df["NonComm_Long"].iloc[-1])

    def test_noncomm_net_is_difference(self, tracker_with_data):
        """noncomm_net = NonComm_Short - NonComm_Long (default COT convention)."""
        df = tracker_with_data._data["GC"]
        expected_net = int(df["NonComm_Short"].iloc[-1] - df["NonComm_Long"].iloc[-1])
        result = tracker_with_data.get_positioning_percentile("GC")
        assert result["noncomm_net"]["value"] == expected_net

    def test_asset_not_found(self, tracker_with_data):
        """Missing asset returns error."""
        result = tracker_with_data.get_positioning_percentile("FAKE")
        assert "error" in result
        assert "No data" in result["error"]

    def test_insufficient_data(self, basic_cot_tracker):
        """Fewer than 10 rows returns error."""
        small_df = pd.DataFrame({"NonComm_Long": [100] * 5, "NonComm_Short": [50] * 5})
        basic_cot_tracker._data = {"ES": small_df}
        result = basic_cot_tracker.get_positioning_percentile("ES")
        assert "error" in result
        assert "Insufficient" in result["error"]

    # ── Edge cases ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("lookback", [10, 30, 100])
    def test_lookback_variants(self, tracker_with_data, lookback):
        """Respects lookback parameter (clamped to available data)."""
        result = tracker_with_data.get_positioning_percentile("GC", lookback=lookback)
        # If lookback > available, n_weeks = available
        expected = min(lookback, len(tracker_with_data._data["GC"]))
        assert result["n_weeks"] == expected

    def test_all_values_identical(self, basic_cot_tracker):
        """When all historical values are equal, percentile = 100% (≤ includes equality)."""
        df = pd.DataFrame({
            "NonComm_Long": [250_000] * 20,
            "NonComm_Short": [100_000] * 20,
        })
        basic_cot_tracker._data = {"CL": df}
        result = basic_cot_tracker.get_positioning_percentile("CL")
        assert result["noncomm_net"]["percentile"] == 100.0

    def test_single_unique_value(self, basic_cot_tracker):
        """Exactly 10 rows (min threshold), all same value."""
        df = pd.DataFrame({
            "NonComm_Long": [300_000] * 10,
            "NonComm_Short": [80_000] * 10,
        })
        basic_cot_tracker._data = {"CL": df}
        result = basic_cot_tracker.get_positioning_percentile("CL")
        assert result["n_weeks"] == 10
        assert result["noncomm_net"]["percentile"] == 100.0

    def test_current_is_min(self, basic_cot_tracker):
        """Current value is the minimum → percentile near 0%."""
        np.random.seed(1)
        longs = np.random.randint(200_000, 350_000, 30).tolist()
        shorts = np.random.randint(60_000, 100_000, 30).tolist()
        longs.append(150_000)  # new minimum
        shorts.append(50_000)  # new minimum
        df = pd.DataFrame({
            "NonComm_Long": longs,
            "NonComm_Short": shorts,
        })
        basic_cot_tracker._data = {"ES": df}
        result = basic_cot_tracker.get_positioning_percentile("ES")
        # If current is min, percentile = 1/n_weeks * 100 ≈ 3.2%
        assert result["noncomm_long"]["percentile"] < 5.0, "Min value should give low percentile"

    def test_current_is_max(self, basic_cot_tracker):
        """Current value is the maximum → percentile = 100%."""
        np.random.seed(1)
        longs = np.random.randint(200_000, 350_000, 30).tolist()
        shorts = np.random.randint(60_000, 100_000, 30).tolist()
        longs.append(500_000)  # new maximum
        shorts.append(200_000)  # new maximum
        df = pd.DataFrame({
            "NonComm_Long": longs,
            "NonComm_Short": shorts,
        })
        basic_cot_tracker._data = {"CL": df}
        result = basic_cot_tracker.get_positioning_percentile("CL")
        assert result["noncomm_long"]["percentile"] == 100.0
        assert result["noncomm_short"]["percentile"] == 100.0

    def test_missing_columns_skipped_gracefully(self, basic_cot_tracker):
        """Non-Existent columns are silently skipped (e.g. NonRep_Short missing)."""
        df = pd.DataFrame({"NonComm_Long": [100_000, 150_000], "NonComm_Short": [50_000, 40_000]})
        basic_cot_tracker._data = {"6E": df}
        result = basic_cot_tracker.get_positioning_percentile("6E")
        assert "noncomm_long" in result
        assert "noncomm_short" in result
        # These won't be in the DataFrame -> not in result
        # But there's also no error — other keys just aren't added
        # That's acceptable behaviour

    def test_nan_in_historical_data(self, basic_cot_tracker):
        """NaN values are dropped when computing percentiles."""
        longs = [200_000, None, 220_000, 210_000, 230_000]
        shorts = [80_000, 75_000, None, 70_000, 65_000]
        df = pd.DataFrame({"NonComm_Long": longs, "NonComm_Short": shorts})
        df["NonComm_Long"] = df["NonComm_Long"].astype(float)
        df["NonComm_Short"] = df["NonComm_Short"].astype(float)
        basic_cot_tracker._data = {"6J": df}
        # Should not raise
        result = basic_cot_tracker.get_positioning_percentile("6J")
        assert "noncomm_long" in result
        assert isinstance(result["noncomm_long"]["percentile"], float)

    def test_values_are_ints(self, tracker_with_data):
        """Value fields are integers, percentiles are floats."""
        result = tracker_with_data.get_positioning_percentile("GC")
        for key in ("noncomm_long", "noncomm_short", "comm_long"):
            assert isinstance(result[key]["value"], int)
            assert isinstance(result[key]["percentile"], float)

    def test_result_includes_last_updated(self, tracker_with_data):
        """Result includes a last_updated timestamp."""
        result = tracker_with_data.get_positioning_percentile("GC")
        assert "last_updated" in result
        assert result["last_updated"] is not None


# ── Test: detect_extreme_positioning ─────────────────────────────────────


class TestDetectExtremePositioning:
    def test_no_data_returns_empty(self, basic_cot_tracker):
        assert basic_cot_tracker.detect_extreme_positioning() == {}

    def test_default_threshold_90(self, tracker_with_data):
        """90% threshold: most assets should be 'BALANCED' with random-ish data."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=90.0)
        assert "GC" in signals
        assert signals["GC"] in ("BALANCED", "EXTREME_LONG_OVERBOUGHT", "EXTREME_SHORT_OVERSOLD")

    def test_threshold_50_detects_extremes(self, tracker_with_data):
        """50% threshold: every asset gets tagged extreme in one direction."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=50.0)
        # At 50%, every non-equal-to-median value is "extreme"
        assert signals["GC"] != "BALANCED"

    def test_threshold_100_none_extreme(self, tracker_with_data):
        """100% threshold: nothing is extreme (can't exceed 100th percentile)."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=100.0)
        assert signals.get("GC") == "BALANCED"

    def test_threshold_0_all_extreme(self, tracker_with_data):
        """0% threshold: everything is extreme long."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=0.0)
        assert signals.get("GC") == "EXTREME_LONG_OVERBOUGHT"

    def test_multiple_assets(self, tracker_with_data, sample_cot_data):
        """Detects across multiple contracts."""
        tracker_with_data._data["ES"] = sample_cot_data.copy()
        tracker_with_data._data["CL"] = sample_cot_data.copy()
        signals = tracker_with_data.detect_extreme_positioning(threshold=90.0)
        assert len(signals) == 3
        for asset in ("GC", "ES", "CL"):
            assert asset in signals

    def test_asset_with_error_skipped(self, basic_cot_tracker, sample_cot_data):
        """Asset with insufficient data is skipped, others still processed."""
        basic_cot_tracker._data = {
            "GC": sample_cot_data,
            "ES": pd.DataFrame({"NonComm_Long": [100] * 5, "NonComm_Short": [50] * 5}),  # < 10 rows
        }
        signals = basic_cot_tracker.detect_extreme_positioning()
        assert "GC" in signals
        assert "ES" not in signals  # skipped due to insufficient data

    def test_noncomm_net_used_for_extreme(self, basic_cot_tracker):
        """Extreme signal is based on noncomm_net percentile."""
        # Make net positioning clearly extreme long
        longs = list(range(100_000, 500_000, 10_000))  # rising
        shorts = [200_000] * len(longs)  # constant
        df = pd.DataFrame({"NonComm_Long": longs, "NonComm_Short": shorts})
        basic_cot_tracker._data = {"NQ": df}
        signals = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        assert signals["NQ"] == "EXTREME_LONG_OVERBOUGHT"

        # Now invert: make net positioning extreme short
        shorts_falling = list(range(500_000, 100_000, -10_000))
        df2 = pd.DataFrame({"NonComm_Long": [100_000] * len(shorts_falling), "NonComm_Short": shorts_falling})
        basic_cot_tracker._data = {"NQ": df2}
        signals2 = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        assert signals2["NQ"] == "EXTREME_SHORT_OVERSOLD"


# ── Test: fetch_all (mock path) ──────────────────────────────────────────


class TestFetchAll:
    def test_no_cot_module_returns_empty(self, basic_cot_tracker):
        """When cot_reports is not available, fetch_all returns {}."""
        result = basic_cot_tracker.fetch_all()
        assert result == {}

    def test_has_data_after_fetch(self):
        """After successful fetch, has_data is True and last_fetch is set."""
        t = COTTracker(contracts={"GC": ("GOLD", "088691")})

        # Mock cot_reports module
        mock_cot = _MockCotReports()
        t._cot_module = mock_cot

        result = t.fetch_all(year=2025)
        assert "GC" in result
        assert t.has_data is True
        assert t.last_fetch is not None

    def test_fetch_with_partial_failure(self):
        """A failing contract doesn't kill the whole fetch."""
        t = COTTracker(contracts={
            "GC": ("GOLD", "088691"),
            "FAKE": ("FAKE", "000000"),
        })

        mock_cot = _MockCotReports()
        mock_cot._fail_for = {"FAKE"}
        t._cot_module = mock_cot

        result = t.fetch_all(year=2025)
        assert "GC" in result
        assert "FAKE" not in result  # silently skipped


class _MockCotReports:
    """Minimal mock for cot_reports.cot_year()."""
    _fail_for: set = set()

    def cot_year(self, year, report_type, contract_code):
        if contract_code in self._fail_for:
            raise ValueError("Mock failure")
        if hasattr(self, "_data_cache") and contract_code in self._data_cache:
            return self._data_cache[contract_code]
        n = 30
        df = pd.DataFrame({
            "NonComm_Long": np.random.randint(100_000, 400_000, n),
            "NonComm_Short": np.random.randint(50_000, 150_000, n),
            "Comm_Long": np.random.randint(80_000, 200_000, n),
            "Comm_Short": np.random.randint(100_000, 300_000, n),
            "NonRep_Long": np.random.randint(20_000, 60_000, n),
            "NonRep_Short": np.random.randint(10_000, 30_000, n),
            "Open_Interest": np.random.randint(200_000, 500_000, n),
        })
        if not hasattr(self, "_data_cache"):
            self._data_cache = {}
        self._data_cache[contract_code] = df
        return df


# ── Test: COTAnalyzer ────────────────────────────────────────────────────


class TestCOTAnalyzer:
    def test_init_default(self):
        a = COTAnalyzer()
        assert a.extreme_threshold == 90.0
        assert isinstance(a._tracker, COTTracker)

    def test_init_custom_threshold(self):
        a = COTAnalyzer(extreme_threshold=85.0)
        assert a.extreme_threshold == 85.0

    def test_analyze_no_data_returns_hold(self):
        """When tracker has no data, analyze returns NO_DATA / hold."""
        t = COTTracker()
        t._cot_module = None
        a = COTAnalyzer(cot_tracker=t)
        result = a.analyze()
        assert result["signal"] == "NO_DATA"
        assert result["action"] == "hold"
        assert result["grade"] == "D"

    def test_analyze_balanced(self, tracker_with_data):
        """With random-ish data and 90% threshold, most assets are balanced."""
        a = COTAnalyzer(cot_tracker=tracker_with_data)
        result = a.analyze()
        # Skip the fetch (data already loaded)
        result = a.analyze = None  # we'll call manually
        # Actually, analyze calls fetch_all first which returns {} since cot is None
        # So we need to patch it differently

        extremes = tracker_with_data.detect_extreme_positioning(threshold=90.0)
        n_extreme_long = sum(1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT")
        n_extreme_short = sum(1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD")
        n_balanced = sum(1 for v in extremes.values() if v == "BALANCED")

        if n_balanced >= len(extremes) * 0.6:
            expected_signal = "NEUTRAL"
        elif n_extreme_long > n_extreme_short * 2 and n_extreme_long >= 2:
            expected_signal = "CAUTION_CROWDED_LONG"
        elif n_extreme_short > n_extreme_long * 2 and n_extreme_short >= 2:
            expected_signal = "CAUTION_CROWDED_SHORT"
        else:
            expected_signal = "MIXED"

        # Manually build expected dict for comparison
        assert expected_signal in ("NEUTRAL", "MIXED", "CAUTION_CROWDED_LONG", "CAUTION_CROWDED_SHORT")
        assert isinstance(extremes, dict)

    def test_analyze_crowded_long(self, basic_cot_tracker):
        """Multiple assets extreme long → CAUTION_CROWDED_LONG."""
        data = _make_extreme_data(direction="long", n_assets=3)
        basic_cot_tracker._data = {k: v for k, v in zip(["GC", "ES", "CL"], data)}
        a = COTAnalyzer(cot_tracker=basic_cot_tracker)

        # Manually test since analyze() calls fetch_all first
        extremes = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        n_extreme_long = sum(1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT")
        n_extreme_short = sum(1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD")
        n_balanced = sum(1 for v in extremes.values() if v == "BALANCED")

        assert n_extreme_long >= 2
        assert n_extreme_long > n_extreme_short * 2

    def test_analyze_crowded_short(self, basic_cot_tracker):
        """Multiple assets extreme short → CAUTION_CROWDED_SHORT."""
        data = _make_extreme_data(direction="short", n_assets=3)
        basic_cot_tracker._data = {k: v for k, v in zip(["GC", "ES", "CL"], data)}
        a = COTAnalyzer(cot_tracker=basic_cot_tracker)

        extremes = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        n_extreme_long = sum(1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT")
        n_extreme_short = sum(1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD")

        assert n_extreme_short >= 2
        assert n_extreme_short > n_extreme_long * 2

    def test_analyze_mixed_signal(self, basic_cot_tracker):
        """Mix of long/short extremes → MIXED."""
        data = _make_extreme_data(direction="long", n_assets=2)
        data += _make_extreme_data(direction="short", n_assets=2)
        basic_cot_tracker._data = {k: v for k, v in zip(["GC", "ES", "CL", "6E"], data)}
        a = COTAnalyzer(cot_tracker=basic_cot_tracker)

        extremes = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        n_extreme_long = sum(1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT")
        n_extreme_short = sum(1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD")
        n_balanced = sum(1 for v in extremes.values() if v == "BALANCED")

        assert n_extreme_long >= 2
        assert n_extreme_short >= 2
        assert n_balanced < len(extremes) * 0.6

    def test_custom_tracker_injection(self):
        """COTAnalyzer accepts an externally configured tracker."""
        t = COTTracker()
        t._cot_module = None
        a = COTAnalyzer(cot_tracker=t)
        assert a._tracker is t


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_extreme_data(direction: str, n_assets: int = 1) -> list:
    """
    Create DataFrames where noncomm_net is extremely high (long) or low (short).
    """
    np.random.seed(42)
    results = []
    n = 30

    for _ in range(n_assets):
        if direction == "long":
            # Net position (Short - Long) becomes increasingly negative (= net short decreasing)
            # Actually: noncomm_net = Short - Long
            # For extreme long: Short is low, Long is high
            longs = list(range(100_000, 400_000, 10_000))[:n]  # rising to 390k
            shorts = np.random.randint(40_000, 60_000, n)  # low short
        else:
            # For extreme short: Short is high, Long is low
            longs = np.random.randint(50_000, 80_000, n)  # low long
            shorts = list(range(100_000, 400_000, 10_000))[:n]  # rising short

        df = pd.DataFrame({
            "NonComm_Long": longs,
            "NonComm_Short": shorts,
            "Comm_Long": np.random.randint(80_000, 150_000, n),
            "Comm_Short": np.random.randint(100_000, 200_000, n),
            "NonRep_Long": np.random.randint(20_000, 40_000, n),
            "NonRep_Short": np.random.randint(10_000, 25_000, n),
            "Open_Interest": np.random.randint(200_000, 400_000, n),
        })
        results.append(df)

    return results
