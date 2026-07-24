"""Smoke tests for engine/risk/correlation.py — CorrelationMonitor."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.risk.correlation import CorrelationMonitor


class TestCorrelationMonitorIsCorrelated:
    """CorrelationMonitor.is_correlated() — known-group matching."""

    def test_same_group_returns_true(self):
        cm = CorrelationMonitor()
        assert cm.is_correlated("EURUSD", "GBPUSD")
        assert cm.is_correlated("USDJPY", "USDCHF")
        assert cm.is_correlated("XAUUSD", "XAGUSD")
        assert cm.is_correlated("BTCUSDT", "ETHUSDT")
        assert cm.is_correlated("SPY", "QQQ")

    def test_different_groups_returns_false(self):
        cm = CorrelationMonitor()
        assert not cm.is_correlated("EURUSD", "BTCUSDT")
        assert not cm.is_correlated("XAUUSD", "SPY")
        assert not cm.is_correlated("USDJPY", "EURUSD")

    def test_case_insensitive(self):
        cm = CorrelationMonitor()
        assert cm.is_correlated("eurusd", "gbpusd")
        assert cm.is_correlated("xauusd", "xagusd")

    def test_unknown_symbol_returns_false(self):
        cm = CorrelationMonitor()
        assert not cm.is_correlated("UNKNOWN", "EURUSD")
        assert not cm.is_correlated("FOO", "BAR")

    def test_same_symbol_returns_true(self):
        cm = CorrelationMonitor()
        assert cm.is_correlated("EURUSD", "EURUSD")

    def test_all_group_pairs_covered(self):
        cm = CorrelationMonitor()
        pairs = [
            ("EURUSD", "GBPUSD"), ("EURUSD", "AUDUSD"), ("EURUSD", "NZDUSD"),
            ("GBPUSD", "AUDUSD"), ("GBPUSD", "NZDUSD"), ("AUDUSD", "NZDUSD"),
            ("USDJPY", "USDCHF"), ("USDJPY", "USDCAD"), ("USDCHF", "USDCAD"),
            ("XAUUSD", "XAGUSD"),
            ("BTCUSDT", "ETHUSDT"),
            ("SPY", "QQQ"), ("SPY", "IWM"), ("QQQ", "IWM"),
        ]
        for a, b in pairs:
            assert cm.is_correlated(a, b), f"{a} / {b} should be correlated"


class TestCorrelationMonitorCountCorrelated:
    """CorrelationMonitor.count_correlated_positions()."""

    def test_count_one_correlated(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("EURUSD", ["GBPUSD", "BTCUSDT"])
        assert count == 1

    def test_count_multiple_correlated(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("EURUSD", ["GBPUSD", "AUDUSD", "NZDUSD"])
        assert count == 3

    def test_count_none_correlated(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("EURUSD", ["BTCUSDT", "SPY"])
        assert count == 0

    def test_empty_positions(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("EURUSD", [])
        assert count == 0

    def test_self_is_correlated(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("EURUSD", ["EURUSD"])
        assert count == 1

    def test_gbp_vs_dollar_group(self):
        cm = CorrelationMonitor()
        count = cm.count_correlated_positions("GBPUSD", ["EURUSD", "AUDUSD"])
        assert count == 2


class TestCorrelationMonitorDetectStress:
    """CorrelationMonitor.detect_stress() with various data."""

    def test_normal_uncorrelated_data(self):
        cm = CorrelationMonitor(stress_threshold=0.8)
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "A": np.random.normal(0, 0.01, n),
            "B": np.random.normal(0, 0.01, n),
            "C": np.random.normal(0, 0.01, n),
        })
        result = cm.detect_stress(df)
        assert not result["stress_detected"]
        assert result["stress_level"] == "NORMAL"
        assert -0.5 <= result["avg_correlation"] <= 0.5

    def test_highly_correlated_data_detects_stress(self):
        cm = CorrelationMonitor(stress_threshold=0.3, high_correlation_threshold=0.2)
        np.random.seed(42)
        n = 100
        base = np.random.normal(0, 0.01, n)
        df = pd.DataFrame({
            "A": base,
            "B": base + np.random.normal(0, 0.001, n),
            "C": base + np.random.normal(0, 0.001, n),
        })
        result = cm.detect_stress(df)
        assert result["stress_detected"]
        assert result["stress_level"] == "STRESS"
        assert result["avg_correlation"] > result["min_pairwise"]

    def test_single_asset_returns_no_stress(self):
        cm = CorrelationMonitor()
        df = pd.DataFrame({"A": np.random.normal(0, 0.01, 50)})
        result = cm.detect_stress(df)
        assert not result["stress_detected"]
        assert result["stress_level"] == "NORMAL"
        assert result["avg_correlation"] == 0.0

    def test_dict_input_coerces_to_dataframe(self):
        cm = CorrelationMonitor(stress_threshold=0.8)
        np.random.seed(42)
        data = {
            "A": np.random.normal(0, 0.01, 100).tolist(),
            "B": np.random.normal(0, 0.01, 100).tolist(),
        }
        result = cm.detect_stress(data)
        assert not result["stress_detected"]
        assert "avg_correlation" in result

    def test_short_window(self):
        cm = CorrelationMonitor(stress_threshold=0.8, lookback=10)
        np.random.seed(42)
        df = pd.DataFrame({
            "A": np.random.normal(0, 0.01, 20),
            "B": np.random.normal(0, 0.01, 20),
        })
        result = cm.detect_stress(df, window=10)
        assert "avg_correlation" in result
        assert "max_pairwise" in result
        assert "min_pairwise" in result

    def test_elevated_not_stress(self):
        cm = CorrelationMonitor(stress_threshold=0.9, high_correlation_threshold=0.3)
        np.random.seed(42)
        n = 100
        base = np.random.normal(0, 0.01, n)
        df = pd.DataFrame({
            "A": base + np.random.normal(0, 0.005, n),
            "B": base + np.random.normal(0, 0.005, n),
        })
        result = cm.detect_stress(df)
        assert not result["stress_detected"]
        assert result["stress_level"] in ("ELEVATED", "NORMAL")