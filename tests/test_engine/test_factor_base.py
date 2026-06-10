"""Comprehensive tests for Alpha Factor base operators.

Tests all operator functions from the base module:
- rank, scale, ts_rank, ts_corr, ts_cov
- ts_mean, ts_std, ts_max, ts_min
- ts_argmax, ts_argmin, delta, delay
- decay_linear, signed_power
- ts_sum, ts_product, ts_median
- ts_skewness, ts_kurtosis
- safe_div, vwap
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.factors.base import (
    AlphaFactor, FactorMeta, Market,
    rank, scale, ts_rank, ts_corr, ts_cov,
    ts_mean, ts_std, ts_max, ts_min,
    ts_argmax, ts_argmin, delta, delay,
    decay_linear, signed_power,
    ts_sum, ts_product, ts_median,
    ts_skewness, ts_kurtosis,
    safe_div, vwap,
)


@pytest.fixture
def wide_df():
    """Wide DataFrame (index=dates, columns=instruments)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    data = {
        "AAPL": np.random.normal(100, 5, 50),
        "MSFT": np.random.normal(200, 10, 50),
        "GOOGL": np.random.normal(150, 7, 50),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def series():
    """Simple Series for operator testing."""
    np.random.seed(42)
    return pd.Series(np.random.normal(0, 1, 50), name="test")


class TestRank:
    def test_rank_dataframe(self, wide_df):
        result = rank(wide_df)
        assert result.shape == wide_df.shape
        # Each row should have ranks in [0, 1]
        for idx in result.index:
            row = result.loc[idx].dropna()
            if len(row) > 0:
                assert row.min() >= 0
                assert row.max() <= 1

    def test_rank_series(self, series):
        result = rank(series)
        assert len(result) == len(series)

    def test_rank_preserves_nan(self):
        s = pd.Series([1.0, np.nan, 3.0, 2.0])
        result = rank(s)
        assert result.iloc[1] is np.nan or pd.isna(result.iloc[1])


class TestScale:
    def test_scale_normalization(self, wide_df):
        result = scale(wide_df, a=1.0)
        # Each row's abs sum should be ~1.0 (where non-zero)
        for idx in result.index:
            row = result.loc[idx].dropna()
            if row.abs().sum() > 0:
                np.testing.assert_allclose(row.abs().sum(), 1.0, atol=1e-10)


class TestTsRank:
    def test_ts_rank_output_range(self, wide_df):
        result = ts_rank(wide_df, 10)
        valid = result.dropna()
        assert (valid >= 0).all().all()
        assert (valid <= 1).all().all()

    def test_ts_rank_invalid_window(self):
        with pytest.raises(ValueError):
            ts_rank(pd.DataFrame({"A": [1, 2, 3]}), 0)


class TestTsCorr:
    def test_ts_corr_diagonal(self, wide_df):
        result = ts_corr(wide_df, wide_df, 10)
        # Diagonal elements should be ~1.0 where valid
        valid = result.dropna()
        for col in valid.columns:
            if len(valid[col]) > 0:
                assert abs(valid[col].iloc[-1] - 1.0) < 0.01

    def test_ts_corr_invalid_window(self):
        with pytest.raises(ValueError):
            ts_corr(pd.DataFrame({"A": [1]}), pd.DataFrame({"A": [1]}), 1)


class TestTsCov:
    def test_ts_cov_output(self, wide_df):
        result = ts_cov(wide_df, wide_df, 10)
        assert result.shape == wide_df.shape

    def test_ts_cov_invalid_window(self):
        with pytest.raises(ValueError):
            ts_cov(pd.DataFrame({"A": [1]}), pd.DataFrame({"A": [1]}), 1)


class TestTsMean:
    def test_known_value(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ts_mean(s, 3)
        assert result.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
        assert result.iloc[3] == pytest.approx(3.0)  # (2+3+4)/3

    def test_warmup_nan(self, series):
        result = ts_mean(series, 5)
        assert result.iloc[:4].isna().all()

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            ts_mean(pd.Series([1.0]), 0)


class TestTsStd:
    def test_output_positive(self, wide_df):
        result = ts_std(wide_df, 10)
        valid = result.dropna()
        assert (valid >= 0).all().all()

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            ts_std(pd.Series([1.0]), 1)


class TestTsMinMax:
    def test_ts_max(self):
        s = pd.Series([1.0, 5.0, 3.0, 2.0, 4.0])
        result = ts_max(s, 3)
        assert result.iloc[2] == 5.0
        assert result.iloc[3] == 5.0  # max(5,3,2)
        assert result.iloc[4] == 4.0  # max(3,2,4)

    def test_ts_min(self):
        s = pd.Series([5.0, 1.0, 3.0, 2.0, 4.0])
        result = ts_min(s, 3)
        assert result.iloc[2] == 1.0
        assert result.iloc[3] == 1.0  # min(1,3,2)
        assert result.iloc[4] == 2.0  # min(3,2,4)


class TestTsArgMinMax:
    def test_ts_argmax(self):
        s = pd.Series([1.0, 5.0, 3.0])
        result = ts_argmax(s, 3)
        assert result.iloc[2] == 1.0  # Index of max value

    def test_ts_argmin(self):
        s = pd.Series([3.0, 1.0, 2.0])
        result = ts_argmin(s, 3)
        assert result.iloc[2] == 1.0  # Index of min value


class TestDelta:
    def test_known_value(self):
        s = pd.Series([10.0, 12.0, 15.0, 11.0])
        result = delta(s, 1)
        assert result.iloc[1] == pytest.approx(2.0)
        assert result.iloc[2] == pytest.approx(3.0)

    def test_invalid_lag(self):
        with pytest.raises(ValueError, match="lookahead"):
            delta(pd.Series([1.0]), 0)

    def test_negative_lag_forbidden(self):
        with pytest.raises(ValueError, match="lookahead"):
            delta(pd.Series([1.0]), -1)


class TestDelay:
    def test_delay_shifts(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0])
        result = delay(s, 2)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 1.0
        assert result.iloc[3] == 2.0

    def test_invalid_lag(self):
        with pytest.raises(ValueError, match="lookahead"):
            delay(pd.Series([1.0]), 0)


class TestDecayLinear:
    def test_output_type(self, wide_df):
        result = decay_linear(wide_df, 5)
        assert result.shape == wide_df.shape

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            decay_linear(pd.Series([1.0]), 0)


class TestSignedPower:
    def test_preserves_sign(self):
        s = pd.Series([-2.0, -1.0, 0.0, 1.0, 2.0])
        result = signed_power(s, 2.0)
        assert np.sign(result.iloc[0]) == -1.0
        assert np.sign(result.iloc[3]) == 1.0

    def test_squares_magnitude(self):
        s = pd.Series([2.0, -2.0])
        result = signed_power(s, 2.0)
        np.testing.assert_allclose(result.iloc[0], 4.0)
        np.testing.assert_allclose(result.iloc[1], -4.0)


class TestTsSum:
    def test_known_value(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ts_sum(s, 3)
        assert result.iloc[2] == pytest.approx(6.0)
        assert result.iloc[3] == pytest.approx(9.0)


class TestTsProduct:
    def test_known_value(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result = ts_product(s, 3)
        assert result.iloc[2] == pytest.approx(6.0)


class TestTsMedian:
    def test_known_value(self):
        s = pd.Series([1.0, 5.0, 2.0, 3.0, 4.0])
        result = ts_median(s, 3)
        assert result.iloc[2] == pytest.approx(2.0)  # median(1,5,2)
        assert result.iloc[3] == pytest.approx(3.0)  # median(5,2,3)


class TestTsSkewness:
    def test_output(self, wide_df):
        result = ts_skewness(wide_df, 20)
        assert result.shape == wide_df.shape

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            ts_skewness(pd.Series([1.0]), 2)


class TestTsKurtosis:
    def test_output(self, wide_df):
        result = ts_kurtosis(wide_df, 20)
        assert result.shape == wide_df.shape

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            ts_kurtosis(pd.Series([1.0]), 3)


class TestSafeDiv:
    def test_normal_division(self):
        s = pd.Series([10.0, 20.0, 30.0])
        result = safe_div(s, 2.0)
        np.testing.assert_allclose(result.values, [5.0, 10.0, 15.0])

    def test_zero_scalar_denom(self):
        s = pd.Series([10.0, 20.0])
        result = safe_div(s, 0)
        assert result.isna().all()

    def test_zero_series_denom(self):
        a = pd.Series([10.0, 20.0])
        b = pd.Series([0.0, 2.0])
        result = safe_div(a, b)
        assert pd.isna(result.iloc[0])
        assert result.iloc[1] == 10.0


class TestVwap:
    def test_us_market(self):
        panel = {
            "open": pd.DataFrame({"A": [100, 101]}),
            "high": pd.DataFrame({"A": [102, 103]}),
            "low": pd.DataFrame({"A": [98, 99]}),
            "close": pd.DataFrame({"A": [101, 102]}),
        }
        result = vwap(panel, Market.EQUITY_US)
        expected = (100 + 102 + 98 + 101) / 4
        assert abs(result["A"].iloc[0] - expected) < 0.01

    def test_missing_keys_raises(self):
        panel = {"open": pd.DataFrame({"A": [100]})}
        with pytest.raises(KeyError):
            vwap(panel, Market.EQUITY_US)

    def test_cn_market(self):
        panel = {
            "amount": pd.DataFrame({"A": [1000000]}),
            "volume": pd.DataFrame({"A": [10000]}),
        }
        result = vwap(panel, Market.EQUITY_CN)
        assert result is not None


class TestFactorMeta:
    def test_creation(self):
        meta = FactorMeta(
            id="test",
            zoo="test_zoo",
            theme=["momentum"],
            formula_latex=r"\alpha",
        )
        assert meta.id == "test"
        assert meta.decay_horizon == 0
        assert meta.min_warmup_bars == 0

    def test_frozen(self):
        meta = FactorMeta(id="test", zoo="test", theme=["test"])
        with pytest.raises(Exception):  # FrozenInstanceError
            meta.id = "changed"
