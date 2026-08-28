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

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_nanggroe.engine.causal.cot_tracker import (
    DEFAULT_COT_CONTRACTS,
    COTAnalyzer,
    COTTracker,
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
    """A 60-row DataFrame simulating COT data for a single asset (e.g. GC).
    
    Includes NonComm_Net column so the percentile lookup works end-to-end.
    """
    np.random.seed(101)
    n = 60
    longs = np.linspace(200_000, 350_000, n) + np.random.normal(0, 15000, n)
    shorts = np.linspace(80_000, 60_000, n) + np.random.normal(0, 8000, n)

    return pd.DataFrame({
        "NonComm_Long": longs.astype(int),
        "NonComm_Short": shorts.astype(int),
        "NonComm_Net": (shorts - longs).astype(int),
        "Comm_Long": (shorts * 0.6 + 50_000).astype(int),
        "Comm_Short": (longs * 0.5 + 20_000).astype(int),
        "NonRep_Long": np.random.randint(30_000, 50_000, n).astype(int),
        "NonRep_Short": np.random.randint(15_000, 25_000, n).astype(int),
        "Open_Interest": (longs + shorts).astype(int),
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
        assert result["n_weeks"] == 52  # default lookback=52 < 60 rows
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
        for key in ("noncomm_net", "noncomm_long", "noncomm_short", "comm_long", "retail_long"):
            if key in result:
                assert 0 <= result[key]["percentile"] <= 100, f"{key} percentile out of range"

    def test_noncomm_net_value(self, tracker_with_data):
        """noncomm_net uses the NonComm_Net column directly (not computed)."""
        df = tracker_with_data._data["GC"]
        expected = int(df["NonComm_Net"].iloc[-1])
        result = tracker_with_data.get_positioning_percentile("GC")
        assert result["noncomm_net"]["value"] == expected

    def test_last_value_is_last_row(self, tracker_with_data):
        """'value' field equals the last row's value."""
        df = tracker_with_data._data["GC"]
        result = tracker_with_data.get_positioning_percentile("GC")
        assert result["noncomm_long"]["value"] == int(df["NonComm_Long"].iloc[-1])

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
        # No NonComm_Net column, so only core fields are present
        assert result["n_weeks"] == 20

    def test_single_unique_value(self, basic_cot_tracker):
        """Exactly 10 rows (min threshold), all same value."""
        df = pd.DataFrame({
            "NonComm_Long": [300_000] * 10,
            "NonComm_Short": [80_000] * 10,
        })
        basic_cot_tracker._data = {"CL": df}
        result = basic_cot_tracker.get_positioning_percentile("CL")
        assert result["n_weeks"] == 10

    def test_current_is_min(self, basic_cot_tracker):
        """Current value is the minimum → percentile near 0%."""
        longs = np.random.default_rng(201).integers(200_000, 350_000, 30).tolist()
        shorts = np.random.default_rng(202).integers(60_000, 100_000, 30).tolist()
        longs.append(150_000)  # new minimum
        shorts.append(50_000)
        df = pd.DataFrame({"NonComm_Long": longs, "NonComm_Short": shorts})
        basic_cot_tracker._data = {"ES": df}
        result = basic_cot_tracker.get_positioning_percentile("ES")
        assert result["noncomm_long"]["percentile"] < 5.0, "Min value should give low percentile"

    def test_current_is_max(self, basic_cot_tracker):
        """Current value is the maximum → percentile = 100%."""
        longs = np.random.default_rng(301).integers(200_000, 350_000, 30).tolist()
        shorts = np.random.default_rng(302).integers(60_000, 100_000, 30).tolist()
        longs.append(500_000)  # new maximum
        shorts.append(200_000)
        df = pd.DataFrame({"NonComm_Long": longs, "NonComm_Short": shorts})
        basic_cot_tracker._data = {"CL": df}
        result = basic_cot_tracker.get_positioning_percentile("CL")
        assert result["noncomm_long"]["percentile"] == 100.0

    def test_missing_columns_skipped_gracefully(self, basic_cot_tracker):
        """Non-existent columns are silently skipped."""
        df = pd.DataFrame({"NonComm_Long": [100_000, 110_000, 120_000, 130_000, 140_000,
                                              150_000, 160_000, 170_000, 180_000, 190_000],
                             "NonComm_Short": [50_000, 48_000, 46_000, 44_000, 42_000,
                                               40_000, 38_000, 36_000, 34_000, 32_000]})
        basic_cot_tracker._data = {"6E": df}
        result = basic_cot_tracker.get_positioning_percentile("6E")
        assert "noncomm_long" in result
        assert "noncomm_short" in result

    def test_nan_in_historical_data(self, basic_cot_tracker):
        """NaN values are dropped when computing percentiles."""
        longs = [200_000, None, 220_000, 210_000, 230_000, 240_000, 250_000,
                 260_000, 270_000, 280_000, 290_000]
        shorts = [80_000, 75_000, None, 70_000, 65_000, 60_000, 55_000,
                  50_000, 45_000, 40_000, 35_000]
        df = pd.DataFrame({"NonComm_Long": longs, "NonComm_Short": shorts})
        df["NonComm_Long"] = df["NonComm_Long"].astype(float)
        df["NonComm_Short"] = df["NonComm_Short"].astype(float)
        basic_cot_tracker._data = {"6J": df}
        result = basic_cot_tracker.get_positioning_percentile("6J")
        assert "noncomm_long" in result
        assert isinstance(result["noncomm_long"]["percentile"], float)

    def test_values_are_ints(self, tracker_with_data):
        """Value fields are integers, percentiles are floats."""
        result = tracker_with_data.get_positioning_percentile("GC")
        for key in ("noncomm_long", "noncomm_short", "noncomm_net", "comm_long"):
            if key in result:
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
        """50% threshold: every non-median value gets tagged extreme."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=50.0)
        assert signals["GC"] in ("EXTREME_LONG_OVERBOUGHT", "EXTREME_SHORT_OVERSOLD")

    def test_threshold_100_none_extreme(self, tracker_with_data):
        """100% threshold: nothing is extreme (can't exceed 100th percentile)."""
        signals = tracker_with_data.detect_extreme_positioning(threshold=100.0)
        assert signals.get("GC") == "BALANCED"

    def test_threshold_0_all_extreme_long(self, tracker_with_data):
        """0% threshold: everything qualifies as extreme long."""
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
            "ES": pd.DataFrame({"NonComm_Long": [100] * 5, "NonComm_Short": [50] * 5}),
        }
        signals = basic_cot_tracker.detect_extreme_positioning()
        assert "GC" in signals
        assert "ES" not in signals

    def test_net_extreme_long(self, basic_cot_tracker):
        """NonComm_Net at max percentile → EXTREME_LONG_OVERBOUGHT."""
        rng = np.random.default_rng(401)
        net = rng.integers(50_000, 80_000, 30).tolist()
        net.append(200_000)  # new maximum
        df = pd.DataFrame({"NonComm_Long": [100_000] * 31, "NonComm_Short": [100_000] * 31, "NonComm_Net": net})
        basic_cot_tracker._data = {"NQ": df}
        signals = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        assert signals["NQ"] == "EXTREME_LONG_OVERBOUGHT"

    def test_net_extreme_short(self, basic_cot_tracker):
        """NonComm_Net at min percentile → EXTREME_SHORT_OVERSOLD."""
        rng = np.random.default_rng(501)
        net = rng.integers(-80_000, -50_000, 30).tolist()
        net.append(-200_000)  # new minimum
        df = pd.DataFrame({"NonComm_Long": [100_000] * 31, "NonComm_Short": [100_000] * 31, "NonComm_Net": net})
        basic_cot_tracker._data = {"NQ": df}
        signals = basic_cot_tracker.detect_extreme_positioning(threshold=90.0)
        assert signals["NQ"] == "EXTREME_SHORT_OVERSOLD"


# ── Test: fetch_all (mock path) ──────────────────────────────────────────


class TestFetchAll:
    def test_no_cot_module_returns_empty(self, basic_cot_tracker):
        """When cot_reports is not available, fetch_all returns {}."""
        result = basic_cot_tracker.fetch_all()
        assert result == {}

    def test_has_data_after_fetch(self):
        """After successful fetch, has_data is True and last_fetch is set."""
        t = COTTracker(contracts={"GC": ("GOLD", "088691")})
        mock_cot = _MockCotReports()
        t._cot_module = mock_cot
        result = t.fetch_all(year=2025)
        assert "GC" in result
        assert t.has_data is True
        assert t.last_fetch is not None

    def test_fetch_with_partial_failure(self):
        """A failing contract doesn't kill the whole fetch."""
        t = COTTracker(contracts={"GC": ("GOLD", "088691"), "FAKE": ("FAKE", "000000")})
        mock_cot = _MockCotReports()
        mock_cot._fail_for = {"000000"}  # contract code for FAKE
        t._cot_module = mock_cot
        result = t.fetch_all(year=2025)
        assert "GC" in result
        assert "FAKE" not in result


class _MockCotReports:
    """Minimal mock for cot_reports.cot_year()."""
    _fail_for: set = set()

    def cot_year(self, year, report_type, contract_code):
        if contract_code in self._fail_for:
            raise ValueError("Mock failure")
        rng = np.random.default_rng(abs(hash(contract_code)) % 10_000)
        n = 30
        longs = rng.integers(100_000, 400_000, n)
        shorts = rng.integers(50_000, 150_000, n)
        return pd.DataFrame({
            "NonComm_Long": longs,
            "NonComm_Short": shorts,
            "NonComm_Net": (shorts - longs),
            "Comm_Long": rng.integers(80_000, 200_000, n),
            "Comm_Short": rng.integers(100_000, 300_000, n),
            "NonRep_Long": rng.integers(20_000, 60_000, n),
            "NonRep_Short": rng.integers(10_000, 30_000, n),
            "Open_Interest": rng.integers(200_000, 500_000, n),
        })


# ── Test: COTAnalyzer ────────────────────────────────────────────────────


class TestCOTAnalyzer:
    """Tests for COTAnalyzer.analyze() signal generation.

    Because COTAnalyzer.analyze() calls fetch_all() internally (which clears
    _data when no cot_reports module is available), we patch fetch_all to
    preserve pre-loaded data in all tests that need the signal logic.
    """

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

    # ── Helper to patch fetch_all so pre-loaded data survives analyze()──

    @staticmethod
    def _patch_noop_fetch(tracker):
        """Replace fetch_all with a no-op that preserves _data."""
        tracker._real_fetch_all = tracker.fetch_all
        tracker.fetch_all = lambda year=None: tracker._data

    @staticmethod
    def _unpatch_fetch(tracker):
        tracker.fetch_all = tracker._real_fetch_all

    def test_analyze_balanced(self, tracker_with_data):
        """With random-ish data and 90% threshold, result is balanced or mixed."""
        self._patch_noop_fetch(tracker_with_data)
        try:
            a = COTAnalyzer(cot_tracker=tracker_with_data)
            result = a.analyze()
        finally:
            self._unpatch_fetch(tracker_with_data)

        assert result["signal"] in ("NEUTRAL", "MIXED")
        assert result["grade"] in ("B", "C")
        assert "action" in result
        assert result["total_tracked"] >= 1

    def test_analyze_crowded_long(self, basic_cot_tracker):
        """Multiple assets extreme long → CAUTION_CROWDED_LONG."""
        data = _make_extreme_data("long", n_assets=3)
        basic_cot_tracker._data = dict(zip(["GC", "ES", "CL"], data))
        self._patch_noop_fetch(basic_cot_tracker)
        try:
            a = COTAnalyzer(cot_tracker=basic_cot_tracker)
            result = a.analyze()
        finally:
            self._unpatch_fetch(basic_cot_tracker)

        assert result["signal"] == "CAUTION_CROWDED_LONG"
        assert result["n_extreme_long"] >= 2
        assert result["n_extreme_short"] == 0

    def test_analyze_crowded_short(self, basic_cot_tracker):
        """Multiple assets extreme short → CAUTION_CROWDED_SHORT."""
        data = _make_extreme_data("short", n_assets=3)
        basic_cot_tracker._data = dict(zip(["GC", "ES", "CL"], data))
        self._patch_noop_fetch(basic_cot_tracker)
        try:
            a = COTAnalyzer(cot_tracker=basic_cot_tracker)
            result = a.analyze()
        finally:
            self._unpatch_fetch(basic_cot_tracker)

        assert result["signal"] == "CAUTION_CROWDED_SHORT"
        assert result["n_extreme_short"] >= 2
        assert result["n_extreme_long"] == 0

    def test_analyze_mixed_signal(self, basic_cot_tracker):
        """Mix of long + short extremes → MIXED."""
        data_long = _make_extreme_data("long", n_assets=2)
        data_short = _make_extreme_data("short", n_assets=2)
        basic_cot_tracker._data = dict(zip(["GC", "ES", "CL", "6E"], data_long + data_short))
        self._patch_noop_fetch(basic_cot_tracker)
        try:
            a = COTAnalyzer(cot_tracker=basic_cot_tracker)
            result = a.analyze()
        finally:
            self._unpatch_fetch(basic_cot_tracker)

        assert result["signal"] == "MIXED"
        assert result["n_extreme_long"] >= 2
        assert result["n_extreme_short"] >= 2

    def test_custom_tracker_injection(self):
        """COTAnalyzer accepts an externally configured tracker."""
        t = COTTracker()
        t._cot_module = None
        a = COTAnalyzer(cot_tracker=t)
        assert a._tracker is t


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_extreme_data(direction: str, n_assets: int = 1) -> list[pd.DataFrame]:
    """
    Create DataFrames where noncomm_net is at an extreme percentile.

    Args:
        direction: 'long' → NonComm_Net at all-time high (last row = max).
                   'short' → NonComm_Net at all-time low (last row = min).

    Returns:
        List of DataFrames with COT columns.
    """
    rng = np.random.default_rng(601)
    results: list[pd.DataFrame] = []
    n = 30

    for _ in range(n_assets):
        if direction == "long":
            # NonComm_Net rises to all-time high at last row
            net_base = rng.integers(-50_000, -20_000, n).tolist()
            net_base.append(200_000)  # extreme max
            longs = rng.integers(100_000, 120_000, n + 1)
            shorts = (longs + [net_base[-1]]).tolist() if net_base[-1] > 0 else longs.tolist()
            # Recalc shorts so net matches
            shorts = (longs + net_base).tolist()
        else:
            # NonComm_Net falls to all-time low at last row
            net_base = rng.integers(20_000, 50_000, n).tolist()
            net_base.append(-200_000)  # extreme min
            longs = rng.integers(100_000, 120_000, n + 1)
            shorts = (longs + net_base).tolist()

        df = pd.DataFrame({
            "NonComm_Long": longs,
            "NonComm_Short": shorts,
            "NonComm_Net": net_base,
            "Comm_Long": rng.integers(80_000, 150_000, n + 1),
            "Comm_Short": rng.integers(100_000, 200_000, n + 1),
            "NonRep_Long": rng.integers(20_000, 40_000, n + 1),
            "NonRep_Short": rng.integers(10_000, 25_000, n + 1),
            "Open_Interest": rng.integers(200_000, 400_000, n + 1),
        })
        results.append(df)

    return results
