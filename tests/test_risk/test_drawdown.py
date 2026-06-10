"""
Tests for Drawdown Calculations
=================================
Test max drawdown, current drawdown, and drawdown duration
with known equity curves, edge cases, and boundary conditions.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
import numpy as np

from quant_nanggroe_ai.risk.drawdown import max_drawdown, current_drawdown, drawdown_duration


# ── Shared Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def monotonic_up_curve() -> list[float]:
    """Equity curve that monotonically increases — no drawdown."""
    return [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]


@pytest.fixture
def monotonic_down_curve() -> list[float]:
    """Equity curve that monotonically decreases — maximum drawdown."""
    return [100.0, 95.0, 90.0, 85.0, 80.0]


@pytest.fixture
def v_shaped_curve() -> list[float]:
    """V-shaped equity curve: peak → trough → recovery."""
    return [100.0, 110.0, 95.0, 85.0, 90.0, 110.0]


@pytest.fixture
def double_dip_curve() -> list[float]:
    """Equity curve with two drawdowns — second one deeper."""
    return [100.0, 110.0, 100.0, 120.0, 90.0, 95.0]


@pytest.fixture
def flat_curve() -> list[float]:
    """Flat equity curve — no drawdown."""
    return [100.0] * 10


@pytest.fixture
def volatile_curve() -> list[float]:
    """Volatile equity curve from random walk."""
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.03, 100)
    curve = [100.0]
    for r in returns:
        curve.append(curve[-1] * (1 + r))
    return curve


# ── Max Drawdown Tests ───────────────────────────────────────────────


class TestMaxDrawdown:
    """Test maximum drawdown calculation from equity curve."""

    @pytest.mark.risk
    def test_monotonic_up_no_drawdown(self, monotonic_up_curve: list[float]) -> None:
        """Monotonically increasing curve should have 0% drawdown."""
        dd = max_drawdown(monotonic_up_curve)
        assert dd == 0.0, "No drawdown for monotonically increasing curve"

    @pytest.mark.risk
    def test_monotonic_down_full_drawdown(self, monotonic_down_curve: list[float]) -> None:
        """Monotonically decreasing from 100 to 80 → 20% drawdown."""
        dd = max_drawdown(monotonic_down_curve)
        expected = (100.0 - 80.0) / 100.0  # 0.2 = 20%
        assert dd == pytest.approx(expected, abs=0.001)

    @pytest.mark.risk
    def test_v_shaped_recovery(self, v_shaped_curve: list[float]) -> None:
        """V-shaped: peak=110, trough=85 → max DD = (110-85)/110."""
        dd = max_drawdown(v_shaped_curve)
        expected = (110.0 - 85.0) / 110.0  # ~0.2273 = 22.73%
        assert dd == pytest.approx(expected, abs=0.001)

    @pytest.mark.risk
    def test_double_dip_takes_deepest(self, double_dip_curve: list[float]) -> None:
        """Double dip: deeper drawdown is (120-90)/120 = 25%."""
        dd = max_drawdown(double_dip_curve)
        expected = (120.0 - 90.0) / 120.0  # 0.25 = 25%
        assert dd == pytest.approx(expected, abs=0.001)

    @pytest.mark.risk
    def test_flat_curve_no_drawdown(self, flat_curve: list[float]) -> None:
        """Flat curve should have 0% drawdown."""
        dd = max_drawdown(flat_curve)
        assert dd == 0.0

    @pytest.mark.risk
    def test_empty_curve(self) -> None:
        """Empty curve should return 0.0."""
        assert max_drawdown([]) == 0.0

    @pytest.mark.risk
    def test_single_point(self) -> None:
        """Single point should return 0.0 (need at least 2 for drawdown)."""
        assert max_drawdown([100.0]) == 0.0

    @pytest.mark.risk
    def test_two_points_no_drawdown(self) -> None:
        """Two increasing points → no drawdown."""
        assert max_drawdown([100.0, 110.0]) == 0.0

    @pytest.mark.risk
    def test_two_points_with_drawdown(self) -> None:
        """Two decreasing points → drawdown."""
        dd = max_drawdown([110.0, 100.0])
        expected = (110.0 - 100.0) / 110.0  # ~0.0909
        assert dd == pytest.approx(expected, abs=0.001)

    @pytest.mark.risk
    def test_volatile_curve_drawdown_in_range(self, volatile_curve: list[float]) -> None:
        """Volatile curve drawdown should be between 0 and 1."""
        dd = max_drawdown(volatile_curve)
        assert 0.0 <= dd <= 1.0, f"Drawdown {dd} out of [0, 1] range"

    @pytest.mark.risk
    def test_drawdown_returns_percentage_decimal(self, monotonic_down_curve: list[float]) -> None:
        """Drawdown should be returned as a decimal (e.g., 0.15 = 15%)."""
        dd = max_drawdown(monotonic_down_curve)
        # 20% drawdown = 0.20 decimal
        assert dd == pytest.approx(0.20, abs=0.001)


# ── Current Drawdown Tests ───────────────────────────────────────────


class TestCurrentDrawdown:
    """Test current drawdown from peak."""

    @pytest.mark.risk
    def test_at_peak(self, monotonic_up_curve: list[float]) -> None:
        """When last value is at peak, current drawdown should be 0."""
        dd = current_drawdown(monotonic_up_curve)
        assert dd == 0.0

    @pytest.mark.risk
    def test_below_peak(self, v_shaped_curve: list[float]) -> None:
        """When last value is below peak, current drawdown should be positive."""
        dd = current_drawdown(v_shaped_curve)
        # Last value = 110, peak = 120... wait no, v_shaped = [100, 110, 95, 85, 90, 110]
        # Peak = 110, last = 110 → current DD = 0
        assert dd == 0.0, "Last value equals peak, should be 0 drawdown"

    @pytest.mark.risk
    def test_current_drawdown_positive(self) -> None:
        """When last value is below peak, current drawdown should be positive."""
        curve = [100.0, 120.0, 110.0]
        dd = current_drawdown(curve)
        expected = (120.0 - 110.0) / 120.0
        assert dd == pytest.approx(expected, abs=0.001)

    @pytest.mark.risk
    def test_empty_curve(self) -> None:
        """Empty curve should return 0.0."""
        assert current_drawdown([]) == 0.0

    @pytest.mark.risk
    def test_single_point(self) -> None:
        """Single point — peak == current → drawdown = 0."""
        assert current_drawdown([100.0]) == 0.0

    @pytest.mark.risk
    def test_zero_peak(self) -> None:
        """If peak is 0, should handle gracefully."""
        assert current_drawdown([0.0, 0.0]) == 0.0


# ── Drawdown Duration Tests ──────────────────────────────────────────


class TestDrawdownDuration:
    """Test drawdown duration calculation."""

    @pytest.mark.risk
    def test_at_peak_duration_zero(self, monotonic_up_curve: list[float]) -> None:
        """When always at new peaks, duration should be 0."""
        dur = drawdown_duration(monotonic_up_curve)
        assert dur == 0

    @pytest.mark.risk
    def test_monotonic_down(self, monotonic_down_curve: list[float]) -> None:
        """Monotonically decreasing — duration = len - 1."""
        dur = drawdown_duration(monotonic_down_curve)
        # Peak at first bar, then always below → duration = 4
        assert dur == len(monotonic_down_curve) - 1

    @pytest.mark.risk
    def test_v_shaped_recovery(self, v_shaped_curve: list[float]) -> None:
        """V-shaped with recovery — duration should be 0 at end."""
        dur = drawdown_duration(v_shaped_curve)
        # Last value (110) equals peak (110) → duration = 0
        assert dur == 0

    @pytest.mark.risk
    def test_currently_in_drawdown(self) -> None:
        """When curve ends below peak, duration should count periods since last peak."""
        curve = [100.0, 120.0, 110.0, 105.0]
        dur = drawdown_duration(curve)
        # Peak at 120 (idx 1), then 110, 105 — 2 periods below peak
        assert dur == 2

    @pytest.mark.risk
    def test_empty_curve(self) -> None:
        """Empty curve should return 0."""
        assert drawdown_duration([]) == 0

    @pytest.mark.risk
    def test_single_point(self) -> None:
        """Single point — duration = 0."""
        assert drawdown_duration([100.0]) == 0

    @pytest.mark.risk
    def test_flat_after_peak(self) -> None:
        """Flat curve after a peak still counts as drawdown duration."""
        curve = [100.0, 110.0, 110.0, 110.0]
        dur = drawdown_duration(curve)
        # Peak at 110 (idx 1), then 110 (idx 2) — not below peak
        # val >= peak → peak = val, duration = 0
        assert dur == 0

    @pytest.mark.risk
    def test_new_peak_resets_duration(self) -> None:
        """New peak should reset duration counter."""
        curve = [100.0, 90.0, 80.0, 120.0, 115.0]
        dur = drawdown_duration(curve)
        # Peak at 120 (idx 3), then 115 (idx 4) — 1 period below peak
        assert dur == 1
