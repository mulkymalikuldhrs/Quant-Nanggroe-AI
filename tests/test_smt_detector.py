"""
Tests for SMT divergence detector (Rencana 1.5).

Validates:
  - Structural Higher-High / Lower-High alignment logic
  - Divergence classification (aligned / fake breakout / both downside)
  - Output contract: {divergence_detected, pairs_affected, confidence, recommendation}
  - Missing data / short series guards
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.causal.smt_detector import (
    MONITORED_PAIRS,
    SMTDivergenceDetector,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_price_frame(
    rows: int = 120,
    seed: int = 0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {asset: 100.0 + rng.standard_normal(rows).cumsum() for asset in {"GC1!", "SI1!", "NQ1!", "ES1!", "BTC1!", "ETH1!", "DXY", "6E1!"}}
    )


# Both assets rally together in the last `lookback` bars → aligned.
def _aligned_rally(n: int = 40, lookback: int = 3):
    idx = np.arange(n)
    base = 100.0 + idx * 0.5
    noise = np.sin(idx * 0.3) * 1.5
    a = base + noise
    # Make the last bar clearly higher than the recent range.
    a[-1] = a[-2] + 1.5
    b = a + np.random.default_rng(7).normal(0.2, 0.2, n)  # correlated rally
    return pd.DataFrame({"GC1!": a, "SI1!": b}), lookback


# A continues higher, B turns lower → divergence.
def _divergent_rally(n: int = 40, lookback: int = 3):
    idx = np.arange(n)
    base = 100.0 + idx * 0.5
    a = base + np.sin(idx * 0.3) * 1.5
    a[-1] = a[-2] + 1.2  # new higher high
    b = a.copy()
    b[-1] = b[-2] - 1.5  # new lower high
    return pd.DataFrame({"GC1!": a, "SI1!": b}), lookback


# Both making lower highs → aligned downside.
def _aligned_drop(n: int = 40, lookback: int = 3):
    idx = np.arange(n)
    base = 120.0 - idx * 0.5
    a = base + np.cos(idx * 0.3) * 1.5
    a[-1] = a[-2] - 1.5
    b = a - np.random.default_rng(11).normal(0.1, 0.2, n)
    return pd.DataFrame({"GC1!": a, "SI1!": b}), lookback


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def detector() -> SMTDivergenceDetector:
    return SMTDivergenceDetector(lookback=3)


# ── Structural HH/LH edge cases ──────────────────────────────────


class TestStructuralSMT:
    def test_returns_hold_when_no_structural_move(self, detector):
        flat = pd.DataFrame({
            "A": [100.0] * 10,
            "B": [100.0] * 10,
        })
        report = detector.detect(flat)
        assert report["divergence_detected"] is False
        assert report["recommendation"] == "HOLD"

    def test_aligned_rally_detected(self, detector):
        df, lb = _aligned_rally(lookback=detector.lookback)
        details = detector.detect(df)["details"]
        key = "Gold/Silver"
        assert details[key]["aligned"] is True
        assert details[key]["divergence"] is False
        assert details[key]["a_higher_high"] is True
        assert details[key]["b_higher_high"] is True
        assert details[key]["recommendation"] == "HOLD"

    def test_divergent_rally_detected(self, detector):
        df, lb = _divergent_rally(lookback=detector.lookback)
        details = detector.detect(df)["details"]
        key = "Gold/Silver"
        assert details[key]["divergence"] is True
        assert details[key]["a_higher_high"] is True
        assert details[key]["b_lower_high"] is True
        assert details[key]["recommendation"] == "NO TRADE"

    def test_aligned_drop_detected(self, detector):
        df, lb = _aligned_drop(lookback=detector.lookback)
        details = detector.detect(df)["details"]
        key = "Gold/Silver"
        assert details[key]["aligned"] is True
        assert details[key]["a_lower_high"] is True
        assert details[key]["b_lower_high"] is True
        assert details[key]["divergence"] is False

    def test_confidence_above_threshold_sets_no_trade(self):
        detector = SMTDivergenceDetector(lookback=3, confidence_threshold=0.4)
        df, _ = _divergent_rally(lookback=3)
        report = detector.detect(df)
        assert report["recommendation"] == "NO TRADE"

    def test_confidence_below_threshold_sets_reduce(self):
        detector = SMTDivergenceDetector(lookback=3, confidence_threshold=0.99)
        df, _ = _divergent_rally(lookback=3)
        report = detector.detect(df)
        # Confidence capped at 0.8 in _analyze_pair, below 0.99 threshold.
        assert report["recommendation"] == "REDUCE"


# ── Output contract tests ────────────────────────────────────────


class TestOutputContract:
    def test_top_level_keys_present(self, detector):
        df = _make_price_frame()
        result = detector.detect(df)
        assert {"divergence_detected", "pairs_affected", "confidence", "recommendation", "details"} <= result.keys()

    def test_no_trade_has_divergence_true(self, detector):
        df = pd.DataFrame({
            "GC1!": [100.0 + (1.1 if i == 39 else 0.0) for i in range(40)],
            "SI1!": [100.0 - (1.1 if i == 39 else 0.0) for i in range(40)],
        })
        result = detector.detect(df)
        assert result["divergence_detected"] is True
        assert "Gold/Silver" in result["pairs_affected"]

    def test_pairs_affected_only_lists_divergent(self, detector):
        df, _ = _aligned_rally(lookback=detector.lookback)
        result = detector.detect(df)
        assert result["pairs_affected"] == []

    def test_confidence_within_bounds(self, detector):
        df = _make_price_frame(seed=42)
        result = detector.detect(df)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_recommendation_is_one_of_valid(self, detector):
        df = _make_price_frame(seed=1)
        result = detector.detect(df)
        assert result["recommendation"] in {"HOLD", "REDUCE", "NO TRADE"}


# ── Real-world pair integration tests ────────────────────────────


class TestMonitoredPairs:
    def test_monitored_pairs_declared(self):
        labels = {p[2] for p in MONITORED_PAIRS}
        assert "Gold/Silver" in labels
        assert "Nasdaq/S&P500" in labels
        assert "BTC/ETH" in labels
        assert "DXY/EUR" in labels

    def test_all_monitored_pairs_checked_when_data_complete(self, detector):
        rows = _make_price_frame(rows=200)
        result = detector.detect(rows)
        checked = set(result["details"].keys())
        expected = {label for _, _, label in detector._pairs}
        assert checked == expected

    def test_missing_columns_skipped_gracefully(self, detector):
        df = pd.DataFrame({"GC1!": np.linspace(100, 120, 120)})
        result = detector.detect(df)
        assert result["details"] == {}
        assert result["divergence_detected"] is False
        assert result["recommendation"] == "HOLD"

    def test_empty_dataframe_returns_hold(self, detector):
        result = detector.detect(pd.DataFrame())
        assert result["divergence_detected"] is False
        assert result["recommendation"] == "HOLD"

    def test_gold_silver_divergence_scenario(self, detector):
        n = 40
        idx = np.arange(n)
        base = 1800 + idx * 1.0
        gold = base + np.sin(idx * 0.3) * 1.5
        gold[-1] = gold[-2] + 2.0  # HH
        silver = base + np.sin(idx * 0.3) * 1.5 + np.random.default_rng(3).normal(0, 5, n)
        silver[-1] = silver[-2] - 2.0  # LH
        df = pd.DataFrame({"GC1!": gold, "SI1!": silver})
        report = detector.detect(df)
        assert report["details"]["Gold/Silver"]["divergence"] is True

    def test_nasdaq_sp500_divergence_scenario(self, detector):
        n = 40
        idx = np.arange(n)
        base = 15000 + idx * 5.0
        nq = base + np.sin(idx * 0.3) * 10
        nq[-1] = nq[-2] + 15.0  # HH
        es = base + np.sin(idx * 0.3) * 10 + np.random.default_rng(4).normal(0, 3, n)
        es[-1] = es[-2] - 15.0  # LH
        df = pd.DataFrame({"NQ1!": nq, "ES1!": es})
        report = detector.detect(df)
        assert report["details"]["Nasdaq/S&P500"]["divergence"] is True

    def test_btc_eth_divergence_scenario(self, detector):
        n = 40
        idx = np.arange(n)
        base = 30000 + idx * 50
        btc = base + np.sin(idx * 0.3) * 20
        btc[-1] = btc[-2] + 40  # HH
        eth = base + np.sin(idx * 0.3) * 20 + np.random.default_rng(5).normal(0, 5, n)
        eth[-1] = eth[-2] - 40  # LH
        df = pd.DataFrame({"BTC1!": btc, "ETH1!": eth})
        report = detector.detect(df)
        assert report["details"]["BTC/ETH"]["divergence"] is True

    def test_dxy_vs_6e_inverse_divergence(self, detector):
        n = 40
        idx = np.arange(n)
        dxy = 104 + idx * 0.05 + np.sin(idx * 0.3) * 0.2
        dxy[-1] = dxy[-2] + 0.5  # DXY makes HH
        eur = 1.07 + np.sin(idx * 0.3) * 0.02 + np.random.default_rng(6).normal(0, 0.01, n)
        eur[-1] = eur[-2] - 0.5  # EUR makes LH → DXY up / EUR down → divergence
        df = pd.DataFrame({"DXY": dxy, "6E1!": eur})
        report = detector.detect(df)
        assert report["details"]["DXY/EUR"]["divergence"] is True
        assert report["divergence_detected"] is True
        assert "DXY/EUR" in report["pairs_affected"]

    def test_dxy_6e_both_rally_aligned(self, detector):
        n = 40
        idx = np.arange(n)
        dxy = 104 + idx * 0.05
        dxy[-1] = dxy[-2] + 0.5
        eur = 1.07 + idx * 0.005
        eur[-1] = eur[-2] + 0.005
        df = pd.DataFrame({"DXY": dxy, "6E1!": eur})
        report = detector.detect(df)
        assert report["details"]["DXY/EUR"]["aligned"] is True
        assert report["details"]["DXY/EUR"]["divergence"] is False


# ── Hybrid extension hook tests ─────────────────────────────────


class TestHybridHook:
    def test_hybrid_returns_structural_report(self, detector):
        df = _make_price_frame(seed=42)
        report = detector.detect_hybrid(df)
        # Even without statsmodels, must not crash.
        assert "divergence_detected" in report
        assert "cointegration_active" in report
