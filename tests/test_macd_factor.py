"""Tests for MACD histogram factor (QS013 research).

Research reference (QuantScience newsletter QS013, distilled in
quant-research-kb skill):
- 12-26-9 MACD histogram has mean rolling-30d correlation ≈ -0.237
  vs forward 5-day returns (mean-reverting signal).
- PPO (normalized) ≈ -0.40, stronger.
- 50-200-63 MACD magnitude stronger ≈ -0.37.

We assert structural correctness here (columns, math, finiteness),
not the empirical correlation — that requires real market data.
"""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.factors.macd_factor import (
    compute_macd_histogram,
    compute_ppo,
    rolling_corr_forward_returns,
)


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """Deterministic synthetic OHLCV: 200 bars, seeded."""
    rng = np.random.default_rng(42)
    n = 200
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = rng.integers(100, 10_000, n)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )


class TestComputeMacdHistogram:
    def test_returns_expected_columns(self, synthetic_ohlcv):
        df = compute_macd_histogram(synthetic_ohlcv)
        for col in ("macd_line", "signal_line", "macd_histogram"):
            assert col in df.columns, f"missing column {col}"

    def test_histogram_equals_line_minus_signal(self, synthetic_ohlcv):
        df = compute_macd_histogram(synthetic_ohlcv)
        np.testing.assert_allclose(
            df["macd_histogram"].dropna(),
            df["macd_line"].dropna() - df["signal_line"].dropna(),
            rtol=1e-10,
        )

    def test_finite_values_after_warmup(self, synthetic_ohlcv):
        df = compute_macd_histogram(synthetic_ohlcv)
        tail = df["macd_histogram"].dropna()
        assert len(tail) >= 150, f"too few valid values: {len(tail)}"
        assert np.isfinite(tail).all()

    def test_histogram_is_zero_for_constant_price(self):
        n = 120
        flat = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [101.0] * n,
                "low": [99.0] * n,
                "close": [100.0] * n,
                "volume": [1000] * n,
            },
            index=pd.date_range("2024-01-01", periods=n, freq="D"),
        )
        df = compute_macd_histogram(flat)
        tail = df["macd_histogram"].dropna()
        np.testing.assert_allclose(tail, 0.0, atol=1e-12)


class TestComputePpo:
    def test_ppo_exists_and_finite(self, synthetic_ohlcv):
        df = compute_ppo(synthetic_ohlcv)
        assert "ppo" in df.columns
        tail = df["ppo"].dropna()
        assert len(tail) >= 150
        assert np.isfinite(tail).all()


class TestRollingCorrForwardReturns:
    def test_returns_correlation_series(self, synthetic_ohlcv):
        df = compute_macd_histogram(synthetic_ohlcv)
        corr = rolling_corr_forward_returns(
            df["macd_histogram"], df["close"], window=30, forward=5
        )
        assert isinstance(corr, pd.Series)
        assert len(corr) > 0
        assert corr.dropna().between(-1.0, 1.0).all()

    def test_correlation_sign_on_mean_reverting_signal(self, synthetic_ohlcv):
        """Sanity: on synthetic data the correlation must be a valid
        [-1, 1] number; the sign on real data is expected negative
        (-0.237 mean per QS013) but is data-dependent here."""
        df = compute_macd_histogram(synthetic_ohlcv)
        corr = rolling_corr_forward_returns(
            df["macd_histogram"], df["close"], window=30, forward=5
        )
        mean_corr = corr.dropna().mean()
        assert -1.0 <= mean_corr <= 1.0
