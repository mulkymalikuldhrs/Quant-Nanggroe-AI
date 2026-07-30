"""Tests for core/scoring/cot_advanced.py."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from quant_nanggroe.core.scoring.cot_advanced import (
    COTAdvancedScorer,
    _compute_rolling_z,
    _delta_acceleration,
    _staleness_penalty,
    _z_to_score,
)


def _d(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _build_series(base_net: float, drift: float = 0.0, n: int = 160, oi: float = 200_000.0) -> list[dict]:
    history = []
    net = base_net - drift * n
    for i in range(n):
        net += drift
        history.append(
            {
                "report_date": _d(n - i),
                "commercial_long": int(oi + net),
                "commercial_short": int(oi - net),
                "non_commercial_long": int(oi + net * 1.2),
                "non_commercial_short": int(oi - net * 1.2),
                "open_interest": int(oi * 2),
            }
        )
    return history


class TestComputeRollingZ:
    def test_steady_state_zero(self):
        vals = [10.0] * 30
        z, mean, std = _compute_rolling_z(vals, 10.0)
        assert mean == pytest.approx(10.0)
        assert std == pytest.approx(0.0)
        assert z == 0.0

    def test_positive_z(self):
        vals = [1.0, 2.0, 3.0]
        z, mean, std = _compute_rolling_z(vals, 10.0)
        assert z > 0.0
        assert mean == pytest.approx(2.0)
        assert std == pytest.approx(0.816496580927726)

    def test_window_truncation(self):
        vals = [float(i) for i in range(200)]
        z, _, _ = _compute_rolling_z(vals, 100.0, window=52)
        recent = vals[-52:]
        mean = sum(recent) / len(recent)
        var = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = var**0.5
        assert z == pytest.approx((100.0 - mean) / std)


class TestZToScore:
    def test_neutral(self):
        assert _z_to_score(0.0) == pytest.approx(50.0)

    def test_positive(self):
        assert _z_to_score(2.0, max_z=4.0) == pytest.approx(75.0)

    def test_clip_extreme(self):
        s = _z_to_score(9.0, max_z=3.0)
        assert s == pytest.approx(100.0)
        assert _z_to_score(-9.0, max_z=3.0) == pytest.approx(0.0)


class TestStalenessPenalty:
    def test_fresh(self):
        assert _staleness_penalty(_d(0)) == pytest.approx(1.0)

    def test_one_week(self):
        assert _staleness_penalty(_d(7)) == pytest.approx(1.0)

    def test_mid(self):
        val = _staleness_penalty(_d(17))
        assert pytest.approx(0.75, abs=0.02) == val

    def test_old(self):
        assert _staleness_penalty(_d(30)) == pytest.approx(0.5)

    def test_bad_date(self):
        assert _staleness_penalty("not-a-date") == pytest.approx(0.5)


class TestDeltaAcceleration:
    def test_no_delta(self):
        history = [
            {"non_commercial_net": 0, "open_interest": 100},
            {"non_commercial_net": 0, "open_interest": 100},
            {"non_commercial_net": 0, "open_interest": 100},
        ]
        assert _delta_acceleration(history, "non_commercial_net", weeks=2) == pytest.approx(0.0)

    def test_positive_acceleration(self):
        history = [
            {"non_commercial_net": 0, "open_interest": 100},
            {"non_commercial_net": 0, "open_interest": 100},
            {"non_commercial_net": 20, "open_interest": 100},
        ]
        val = _delta_acceleration(history, "non_commercial_net", weeks=2)
        assert pytest.approx(2.0) == val

    def test_clipped(self):
        history = [
            {"non_commercial_net": -1000, "open_interest": 1},
            {"non_commercial_net": 1000, "open_interest": 1},
        ]
        assert _delta_acceleration(history, "non_commercial_net", weeks=2) == pytest.approx(1.0)


class TestCOTAdvancedScorer:
    def test_no_data_returns_neutral(self):
        s = COTAdvancedScorer()
        out = s.score(history=[])
        assert out.score == pytest.approx(50.0)
        assert out.confidence == pytest.approx(0.0)
        assert out.metadata["status"] == "NO_DATA"

    def test_single_point(self):
        s = COTAdvancedScorer()
        out = s.score(history=[], latest={
            "report_date": _d(0),
            "commercial_long": 10, "commercial_short": 0,
            "non_commercial_long": 20, "non_commercial_short": 0,
            "open_interest": 50,
        })
        assert out.score == pytest.approx(50.0)
        assert out.confidence == pytest.approx(0.2)
        assert out.metadata["status"] == "SINGLE_POINT"

    def test_extreme_bullish(self):
        hist = _build_series(base_net=50_000.0, drift=200.0, n=160)
        s = COTAdvancedScorer()
        out = s.score(history=hist)
        assert out.score > 75.0
        assert out.confidence > 0.3
        assert out.metadata["commercial_net_z"] > 2.0
        assert out.metadata["non_commercial_net_z"] > 2.0

    def test_extreme_bearish(self):
        hist = _build_series(base_net=-50_000.0, drift=-200.0, n=160)
        s = COTAdvancedScorer()
        out = s.score(history=hist)
        assert out.score < 25.0
        assert out.confidence > 0.3
        assert out.metadata["commercial_net_z"] < -2.0
        assert out.metadata["non_commercial_net_z"] < -2.0

    def test_staleness_lowers_confidence(self):
        hist = _build_series(base_net=20_000.0, drift=50.0, n=160)
        s = COTAdvancedScorer()
        fresh = s.score(history=hist)
        stale_hist = list(hist)
        stale_hist[-1] = dict(stale_hist[-1])
        stale_hist[-1]["report_date"] = _d(30)
        stale = s.score(history=stale_hist)
        assert stale.confidence < fresh.confidence
        assert pytest.approx(0.5) == stale.metadata["staleness_multiplier"]

    def test_acceleration_boosts_confidence(self):
        base = _build_series(base_net=10_000.0, drift=0.0, n=160)
        s = COTAdvancedScorer(acceleration_weeks=2)
        base_out = s.score(history=base)
        acc = list(base)
        acc[-1] = dict(acc[-1])
        acc[-2] = dict(acc[-2])
        acc[-2]["non_commercial_long"] += 20_000
        acc[-2]["non_commercial_short"] -= 20_000
        acc_out = s.score(history=acc)
        assert acc_out.confidence >= base_out.confidence

    def test_integration_with_positioning_scorer(self):
        from quant_nanggroe.core.scoring.positioning_scorer import PositioningScorer
        scorer = PositioningScorer(use_hidden_regime=False)
        ctx = {"symbol": "EURUSD", "cot_data": {"history": _build_series(20_000.0, 50.0, 120)}}
        res = scorer.score(ctx)
        assert -100.0 <= res.score <= 100.0
        assert 0.0 <= res.confidence <= 1.0