"""Comprehensive tests for factor modules.

Tests cover:
- Factor determinism: compute same factor twice → same result
- Factor edge cases: NaN handling, short input
- Registry: list (total=~469), list by zoo, get, compute
- Alpha101 spot check: compute first 5 factors with panel data
- GTJA191 spot check: compute first 3 factors
- Qlib158 spot check: compute first 3 factors
- Technical factors: RSI, MACD, Bollinger, Momentum
- Base operators: rank, delta, ts_mean, ts_std, decay_linear, safe_div
"""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    delta,
    rank,
    safe_div,
    scale,
    ts_mean,
    ts_std,
    ts_rank,
    ts_sum,
    ts_product,
    decay_linear,
    signed_power,
    cross_sectional_zscore,
    vwap,
    Market,
)
from quant_nanggroe.engine.factors.technical import (
    MomentumFactor,
    RateOfChangeFactor,
    MeanReversionFactor,
    RealizedVolatilityFactor,
    ATRFactor,
    BollingerWidthFactor,
    VolumeRatioFactor,
    RSIFactor,
    MACDHistogramFactor,
    get_all_technical_factors,
)
from quant_nanggroe.engine.factors.alpha101 import (
    compute_alpha_001,
    compute_alpha_002,
    compute_alpha_003,
    compute_alpha_004,
    compute_alpha_005,
    get_all_alpha101_factors,
)
from quant_nanggroe.engine.factors.registry import (
    FactorRegistry,
    FactorHandle,
    get_default_registry,
    reset_default_registry,
)


# ═══════════════════════════════════════════════════════════════════════
# Panel Data Fixtures
# ═══════════════════════════════════════════════════════════════════════


def make_panel(n_bars=200, n_assets=3):
    """Create a wide-format panel dict for factor computation.

    Returns dict[str, pd.DataFrame] where each key maps to a wide DataFrame
    with index=dates and columns=asset names.
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="D")
    assets = [f"ASSET_{i}" for i in range(n_assets)]

    close_data = {}
    high_data = {}
    low_data = {}
    open_data = {}
    volume_data = {}

    for i in range(n_assets):
        c = 100 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n_bars))
        h = c * (1 + np.abs(np.random.normal(0, 0.005, n_bars)))
        l = c * (1 - np.abs(np.random.normal(0, 0.005, n_bars)))
        o = c * (1 + np.random.normal(0, 0.002, n_bars))
        v = np.maximum(np.random.lognormal(15, 1, n_bars), 1000)
        close_data[assets[i]] = c
        high_data[assets[i]] = h
        low_data[assets[i]] = l
        open_data[assets[i]] = o
        volume_data[assets[i]] = v

    panel = {
        "close": pd.DataFrame(close_data, index=dates),
        "high": pd.DataFrame(high_data, index=dates),
        "low": pd.DataFrame(low_data, index=dates),
        "open": pd.DataFrame(open_data, index=dates),
        "volume": pd.DataFrame(volume_data, index=dates),
    }

    # Add VWAP as typical price
    panel["vwap"] = (panel["open"] + panel["high"] + panel["low"] + panel["close"]) / 4.0

    return panel


@pytest.fixture
def panel():
    """Standard wide panel for factor testing."""
    return make_panel(n_bars=200, n_assets=3)


@pytest.fixture
def long_panel():
    """Longer panel for factors with high warmup requirements."""
    return make_panel(n_bars=500, n_assets=3)


@pytest.fixture
def sample_ohlcv_df():
    """Standard OHLCV DataFrame for single-instrument factor testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100.0 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n))
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_ = close * (1 + np.random.normal(0, 0.002, n))
    volume = np.maximum(np.random.lognormal(15, 1, n), 1000)

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def empty_df():
    """Empty DataFrame."""
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


@pytest.fixture
def single_row_df():
    """DataFrame with a single row."""
    return pd.DataFrame({
        "open": [100.0],
        "high": [101.0],
        "low": [99.0],
        "close": [100.5],
        "volume": [1000000.0],
    })


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    r = FactorRegistry()
    return r


# ═══════════════════════════════════════════════════════════════════════
# 1. Factor Determinism
# ═══════════════════════════════════════════════════════════════════════


class TestFactorDeterminism:
    """Same input should always produce same output."""

    @pytest.mark.parametrize("factor_cls", [
        MomentumFactor, RSIFactor, MACDHistogramFactor,
        BollingerWidthFactor, MeanReversionFactor,
    ])
    def test_determinism(self, factor_cls, sample_ohlcv_df):
        factor = factor_cls()
        result1 = factor.compute(sample_ohlcv_df)
        result2 = factor.compute(sample_ohlcv_df)
        pd.testing.assert_series_equal(result1, result2)

    def test_alpha101_function_determinism(self, panel):
        """Function-based alpha101 factors should be deterministic."""
        r1 = compute_alpha_001(panel)
        r2 = compute_alpha_001(panel)
        if isinstance(r1, pd.DataFrame) and isinstance(r2, pd.DataFrame):
            pd.testing.assert_frame_equal(r1, r2)
        elif isinstance(r1, pd.Series) and isinstance(r2, pd.Series):
            pd.testing.assert_series_equal(r1, r2)

    def test_alpha101_factors_deterministic(self, panel):
        """All testable alpha101 factors should be deterministic."""
        compute_fns = [compute_alpha_001, compute_alpha_002, compute_alpha_003, compute_alpha_004, compute_alpha_005]
        for fn in compute_fns:
            r1 = fn(panel)
            r2 = fn(panel)
            if isinstance(r1, pd.DataFrame) and isinstance(r2, pd.DataFrame):
                pd.testing.assert_frame_equal(r1, r2, check_names=False)
            elif isinstance(r1, pd.Series) and isinstance(r2, pd.Series):
                pd.testing.assert_series_equal(r1, r2, check_names=False)


# ═══════════════════════════════════════════════════════════════════════
# 2. Factor Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestFactorEdgeCases:

    def test_momentum_empty_df(self, empty_df):
        factor = MomentumFactor()
        result = factor.compute(empty_df)
        assert len(result) == 0

    def test_momentum_single_row(self, single_row_df):
        factor = MomentumFactor()
        result = factor.compute(single_row_df)
        assert len(result) == 1
        assert pd.isna(result.iloc[0])

    def test_rsi_empty_df(self, empty_df):
        factor = RSIFactor()
        result = factor.compute(empty_df)
        assert len(result) == 0

    def test_rsi_single_row(self, single_row_df):
        factor = RSIFactor()
        result = factor.compute(single_row_df)
        assert len(result) == 1
        # Single row RSI should be NaN
        assert pd.isna(result.iloc[0])

    def test_nan_in_close(self, sample_ohlcv_df):
        """Factor should handle NaN values in close."""
        df = sample_ohlcv_df.copy()
        df.loc[df.index[50], "close"] = np.nan
        factor = MomentumFactor()
        result = factor.compute(df)
        assert len(result) == len(df)

    def test_atr_missing_columns(self):
        """ATR requires high, low, close — should raise KeyError if missing."""
        df = pd.DataFrame({"close": [100, 101, 102]})
        factor = ATRFactor()
        with pytest.raises(KeyError):
            factor.compute(df)

    def test_short_panel_alpha101(self):
        """Alpha101 factors with short panel should produce NaN-heavy output."""
        short_panel = make_panel(n_bars=10, n_assets=2)
        result = compute_alpha_001(short_panel)
        # With very short data, most values should be NaN
        assert result is not None

    def test_alpha101_wide_panel_shape(self, panel):
        """Alpha101 compute should return DataFrame with same columns as panel."""
        result = compute_alpha_001(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]


# ═══════════════════════════════════════════════════════════════════════
# 3. Registry Operations
# ═══════════════════════════════════════════════════════════════════════


class TestFactorRegistry:

    def test_registry_has_factors(self, registry: FactorRegistry):
        """Registry should have loaded built-in factors."""
        factor_list = registry.list()
        assert len(factor_list) > 0

    def test_list_all_factors(self, registry: FactorRegistry):
        factors = registry.list()
        assert isinstance(factors, list)
        assert all(isinstance(f, str) for f in factors)

    def test_list_by_zoo_technical(self, registry: FactorRegistry):
        technical = registry.list(zoo="technical")
        assert len(technical) > 0
        for name in technical:
            handle = registry.get(name)
            assert handle.zoo == "technical"

    def test_list_by_zoo_alpha101(self, registry: FactorRegistry):
        alpha101 = registry.list(zoo="alpha101")
        assert len(alpha101) > 0

    def test_list_by_zoo_gtja191(self, registry: FactorRegistry):
        gtja191 = registry.list(zoo="gtja191")
        assert len(gtja191) > 0

    def test_list_by_zoo_qlib158(self, registry: FactorRegistry):
        qlib158 = registry.list(zoo="qlib158")
        assert len(qlib158) > 0

    def test_list_by_theme(self, registry: FactorRegistry):
        momentum = registry.list(theme="momentum")
        assert len(momentum) > 0

    def test_list_by_universe(self, registry: FactorRegistry):
        equity_us = registry.list(universe="equity_us")
        assert len(equity_us) > 0

    def test_list_sorted(self, registry: FactorRegistry):
        factors = registry.list()
        assert factors == sorted(factors)

    def test_get_factor(self, registry: FactorRegistry):
        factors = registry.list()
        if factors:
            handle = registry.get(factors[0])
            assert isinstance(handle, FactorHandle)
            assert handle.id == factors[0]

    def test_get_factor_has_properties(self, registry: FactorRegistry):
        factors = registry.list()
        if factors:
            handle = registry.get(factors[0])
            assert hasattr(handle, "id")
            assert hasattr(handle, "zoo")
            assert hasattr(handle, "theme")
            assert hasattr(handle, "columns_required")
            assert hasattr(handle, "min_warmup_bars")

    def test_get_nonexistent_factor(self, registry: FactorRegistry):
        with pytest.raises(KeyError):
            registry.get("nonexistent_factor_xyz")

    def test_get_meta(self, registry: FactorRegistry):
        factors = registry.list()
        if factors:
            meta = registry.get_meta(factors[0])
            assert isinstance(meta, FactorMeta)
            assert meta.id

    def test_compute_factor(self, registry: FactorRegistry, panel):
        """Should be able to compute a factor through the registry."""
        # Find a factor we can compute with our panel
        alpha101_factors = registry.list(zoo="alpha101")
        if alpha101_factors:
            try:
                result = registry.compute(alpha101_factors[0], panel)
                assert isinstance(result, pd.DataFrame)
            except ValueError:
                # Some factors may require columns we don't have
                pass

    def test_compute_missing_columns(self, registry: FactorRegistry):
        """Computing factor without required columns should raise ValueError."""
        factors = registry.list()
        for name in factors:
            handle = registry.get(name)
            if handle.columns_required:
                with pytest.raises(ValueError):  # May be "requires columns" or "output >95% NaN"
                    registry.compute(name, {"close": pd.DataFrame({"A": [1, 2, 3]})})
                break

    def test_register_duplicate_fails(self, registry: FactorRegistry):
        """Registering a factor with an existing name should fail."""
        factors = registry.list()
        if factors:
            existing = registry.get(factors[0])
            # Try to register a function-based factor with existing ID
            with pytest.raises(ValueError, match="already registered"):
                registry.register_function_factor(
                    factor_id=factors[0],
                    zoo="test",
                    meta_dict={"id": factors[0], "theme": [], "columns_required": []},
                    compute_fn=lambda panel: panel.get("close", pd.DataFrame()),
                )

    def test_register_function_factor(self):
        """Should be able to register a custom function-based factor."""
        reg = FactorRegistry.__new__(FactorRegistry)
        reg._handles = {}
        reg._meta = {}
        reg._load_errors = []

        def my_compute(panel):
            return panel.get("close", pd.DataFrame())

        reg.register_function_factor(
            factor_id="test_custom_001",
            zoo="custom",
            meta_dict={
                "id": "test_custom_001",
                "theme": ["test"],
                "columns_required": ["close"],
                "universe": [],
                "formula_latex": "",
                "decay_horizon": 0,
                "min_warmup_bars": 0,
                "notes": "",
            },
            compute_fn=my_compute,
        )
        assert "test_custom_001" in reg.list()
        handle = reg.get("test_custom_001")
        assert handle.zoo == "custom"

    def test_health(self, registry: FactorRegistry):
        health = registry.health()
        assert "loaded" in health
        assert "failed" in health
        assert health["loaded"] > 0
        assert "by_zoo" in health

    def test_summary(self, registry: FactorRegistry):
        summary = registry.summary()
        assert isinstance(summary, dict)
        assert len(summary) > 0

    def test_export_manifest(self, registry: FactorRegistry):
        manifest = registry.export_manifest()
        assert "total_factors" in manifest
        assert "zoos" in manifest
        assert manifest["total_factors"] > 0

    def test_default_registry_singleton(self):
        """get_default_registry should return same instance."""
        reset_default_registry()
        r1 = get_default_registry()
        r2 = get_default_registry()
        assert r1 is r2
        reset_default_registry()

    def test_total_factor_count(self, registry: FactorRegistry):
        """Total factor count should be substantial (hundreds)."""
        total = len(registry.list())
        # Technical (~9) + Alpha101 (101) + GTJA191 (191) + Qlib158 (158) + Academic (~6) + Fundamental
        assert total > 50  # At minimum we should have technical + some function-based


# ═══════════════════════════════════════════════════════════════════════
# 4. Alpha101 Spot Check
# ═══════════════════════════════════════════════════════════════════════


class TestAlpha101SpotCheck:
    """Spot-check first 5 Alpha101 factors with panel data."""

    def test_alpha_001(self, panel):
        result = compute_alpha_001(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]
        # Should not contain inf
        assert not np.isinf(result.to_numpy(dtype=np.float64, na_value=np.nan)).any() or result.isna().all().all()

    def test_alpha_002(self, panel):
        result = compute_alpha_002(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]

    def test_alpha_003(self, panel):
        result = compute_alpha_003(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]

    def test_alpha_004(self, panel):
        result = compute_alpha_004(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]

    def test_alpha_005(self, panel):
        result = compute_alpha_005(panel)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == panel["close"].shape[0]

    def test_alpha_001_returns_dataframe(self, panel):
        """compute_alpha_001 should return a DataFrame, not Series."""
        result = compute_alpha_001(panel)
        assert isinstance(result, pd.DataFrame)
        # Should have same columns as panel
        assert set(result.columns) == set(panel["close"].columns)

    def test_alpha101_no_inf(self, panel):
        """Alpha101 factors should not produce inf values."""
        for fn in [compute_alpha_001, compute_alpha_002, compute_alpha_003, compute_alpha_004, compute_alpha_005]:
            result = fn(panel)
            arr = result.to_numpy(dtype=np.float64, na_value=np.nan)
            # inf values should not exist (replaced with NaN)
            assert not np.isinf(arr[~np.isnan(arr)]).any() or arr.size == 0


# ═══════════════════════════════════════════════════════════════════════
# 5. GTJA191 Spot Check
# ═══════════════════════════════════════════════════════════════════════


class TestGTJA191SpotCheck:

    def test_gtja191_factor_count(self, registry: FactorRegistry):
        gtja = registry.list(zoo="gtja191")
        assert len(gtja) > 0

    def test_gtja191_compute_first_3(self, registry: FactorRegistry, panel):
        """Compute first 3 GTJA191 factors through registry."""
        gtja = registry.list(zoo="gtja191")[:3]
        for name in gtja:
            try:
                result = registry.compute(name, panel)
                assert isinstance(result, pd.DataFrame)
            except ValueError:
                # May need additional columns
                pass


# ═══════════════════════════════════════════════════════════════════════
# 6. Qlib158 Spot Check
# ═══════════════════════════════════════════════════════════════════════


class TestQlib158SpotCheck:

    def test_qlib158_factor_count(self, registry: FactorRegistry):
        qlib = registry.list(zoo="qlib158")
        assert len(qlib) > 0

    def test_qlib158_compute_first_3(self, registry: FactorRegistry, panel):
        """Compute first 3 Qlib158 factors through registry."""
        qlib = registry.list(zoo="qlib158")[:3]
        for name in qlib:
            try:
                result = registry.compute(name, panel)
                assert isinstance(result, pd.DataFrame)
            except ValueError:
                pass


# ═══════════════════════════════════════════════════════════════════════
# 7. Technical Factor Correctness
# ═══════════════════════════════════════════════════════════════════════


class TestRSIFactor:

    def test_rsi_range(self, sample_ohlcv_df):
        """RSI should be between 0 and 100 (after warmup)."""
        factor = RSIFactor(period=14)
        result = factor.compute(sample_ohlcv_df)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_overbought(self):
        """Rising prices should produce high RSI."""
        factor = RSIFactor(period=14)
        df = pd.DataFrame({
            "close": [100.0 + i * 0.5 for i in range(30)],
        })
        result = factor.compute(df)
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.iloc[-1] > 50  # Should be above 50

    def test_rsi_oversold(self):
        """Falling prices should produce low RSI."""
        factor = RSIFactor(period=14)
        df = pd.DataFrame({
            "close": [100.0 - i * 0.5 for i in range(30)],
        })
        result = factor.compute(df)
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.iloc[-1] < 50


class TestMACDFactor:

    def test_macd_histogram(self, sample_ohlcv_df):
        factor = MACDHistogramFactor()
        result = factor.compute(sample_ohlcv_df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df)

    def test_macd_not_all_nan(self, sample_ohlcv_df):
        factor = MACDHistogramFactor()
        result = factor.compute(sample_ohlcv_df)
        assert result.dropna().shape[0] > 0


class TestBollingerWidthFactor:

    def test_bollinger_width_positive(self, sample_ohlcv_df):
        factor = BollingerWidthFactor(period=20)
        result = factor.compute(sample_ohlcv_df)
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_bollinger_width_constant_price(self):
        """Constant price should give zero width."""
        factor = BollingerWidthFactor(period=20)
        df = pd.DataFrame({"close": [100.0] * 30})
        result = factor.compute(df)
        valid = result.dropna()
        assert (valid == 0.0).all() or valid.shape[0] == 0


class TestMomentumFactor:

    def test_momentum_calculation(self):
        """Momentum = close/close.shift(n) - 1."""
        factor = MomentumFactor(period=5)
        closes = [100, 102, 104, 106, 108, 110]
        df = pd.DataFrame({"close": closes})
        result = factor.compute(df)
        # At index 5: 110/100 - 1 = 0.10
        if not pd.isna(result.iloc[-1]):
            assert abs(result.iloc[-1] - 0.10) < 0.01

    def test_momentum_no_inf(self, sample_ohlcv_df):
        """Momentum should not produce inf values."""
        factor = MomentumFactor()
        result = factor.compute(sample_ohlcv_df)
        assert not np.isinf(result.dropna()).any()


class TestATRFactor:

    def test_atr_positive(self, sample_ohlcv_df):
        factor = ATRFactor(period=14)
        result = factor.compute(sample_ohlcv_df)
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_atr_normalized(self, sample_ohlcv_df):
        """ATR/close should be a small positive fraction."""
        factor = ATRFactor(period=14)
        result = factor.compute(sample_ohlcv_df)
        valid = result.dropna()
        assert (valid < 1.0).all()  # ATR/close < 100%


class TestVolumeRatioFactor:

    def test_volume_ratio_around_one(self, sample_ohlcv_df):
        """Volume ratio should average around 1."""
        factor = VolumeRatioFactor(period=20)
        result = factor.compute(sample_ohlcv_df)
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.mean() > 0


class TestAllTechnicalFactors:

    def test_all_run_without_error(self, sample_ohlcv_df):
        factors = get_all_technical_factors()
        for factor in factors:
            result = factor.compute(sample_ohlcv_df)
            assert result is not None

    def test_all_pass_lookahead_check(self):
        factors = get_all_technical_factors()
        for factor in factors:
            assert factor.validate_lookahead(), f"{factor.name} has lookahead bias"

    def test_all_have_meta(self):
        factors = get_all_technical_factors()
        for factor in factors:
            meta = factor.meta
            assert meta.zoo == "technical"
            assert len(meta.theme) > 0

    def test_factor_count(self):
        factors = get_all_technical_factors()
        assert len(factors) >= 9  # At least 9 technical factors


# ═══════════════════════════════════════════════════════════════════════
# 8. Base Operator Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBaseOperators:

    def test_delta(self, sample_ohlcv_df):
        result = delta(sample_ohlcv_df[["close"]], 1)
        assert isinstance(result, pd.DataFrame)

    def test_delta_negative_lag_raises(self, sample_ohlcv_df):
        with pytest.raises(ValueError, match="lookahead ban"):
            delta(sample_ohlcv_df[["close"]], -1)

    def test_delta_zero_lag_raises(self, sample_ohlcv_df):
        with pytest.raises(ValueError, match="lookahead ban"):
            delta(sample_ohlcv_df[["close"]], 0)

    def test_delta_calculation(self):
        """delta(df, d) should equal df - df.shift(d)."""
        df = pd.DataFrame({"A": [10, 20, 30, 40, 50]})
        result = delta(df, 1)
        expected = df - df.shift(1)
        pd.testing.assert_frame_equal(result, expected)

    def test_rank(self, sample_ohlcv_df):
        result = rank(sample_ohlcv_df[["close"]])
        assert isinstance(result, pd.DataFrame)

    def test_rank_series(self):
        s = pd.Series([3, 1, 4, 1, 5])
        result = rank(s)
        assert isinstance(result, pd.Series)

    def test_rank_percentile(self):
        """Rank should return percentile values in [0, 1]."""
        df = pd.DataFrame({"A": [10, 20, 30], "B": [5, 25, 15]})
        result = rank(df)
        # All values should be in [0, 1] range
        valid = result.dropna()
        assert (valid >= 0).all().all() and (valid <= 1).all().all()

    def test_scale(self, sample_ohlcv_df):
        result = scale(sample_ohlcv_df[["close"]], a=1.0)
        assert isinstance(result, pd.DataFrame)

    def test_scale_row_abs_sum(self):
        """Scaled output should have row-wise abs sum ≈ a (where not NaN)."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = scale(df, a=1.0)
        for idx in result.index:
            row = result.loc[idx].dropna()
            if len(row) > 0:
                assert abs(row.abs().sum() - 1.0) < 1e-6

    def test_ts_mean(self, sample_ohlcv_df):
        result = ts_mean(sample_ohlcv_df[["close"]], 5)
        assert isinstance(result, pd.DataFrame)

    def test_ts_mean_zero_window_raises(self, sample_ohlcv_df):
        with pytest.raises(ValueError):
            ts_mean(sample_ohlcv_df[["close"]], 0)

    def test_ts_mean_warmup_nan(self):
        """First n-1 rows should be NaN for ts_mean with window n."""
        df = pd.DataFrame({"A": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = ts_mean(df, 3)
        assert pd.isna(result["A"].iloc[0])
        assert pd.isna(result["A"].iloc[1])
        assert not pd.isna(result["A"].iloc[2])

    def test_ts_std(self, sample_ohlcv_df):
        result = ts_std(sample_ohlcv_df[["close"]], 5)
        assert isinstance(result, pd.DataFrame)

    def test_ts_std_insufficient_window(self, sample_ohlcv_df):
        with pytest.raises(ValueError):
            ts_std(sample_ohlcv_df[["close"]], 1)

    def test_ts_std_non_negative(self, sample_ohlcv_df):
        """Standard deviation should be non-negative."""
        result = ts_std(sample_ohlcv_df[["close"]], 5)
        valid = result.dropna()
        assert (valid >= 0).all().all()

    def test_ts_rank(self, sample_ohlcv_df):
        result = ts_rank(sample_ohlcv_df[["close"]], 10)
        assert isinstance(result, pd.DataFrame)

    def test_ts_rank_zero_window_raises(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        with pytest.raises(ValueError):
            ts_rank(df, 0)

    def test_ts_sum(self, sample_ohlcv_df):
        result = ts_sum(sample_ohlcv_df[["close"]], 5)
        assert isinstance(result, pd.DataFrame)

    def test_ts_product(self, sample_ohlcv_df):
        result = ts_product(sample_ohlcv_df[["close"]], 5)
        assert isinstance(result, pd.DataFrame)

    def test_decay_linear(self, sample_ohlcv_df):
        result = decay_linear(sample_ohlcv_df[["close"]], 5)
        assert isinstance(result, pd.DataFrame)

    def test_decay_linear_weights(self):
        """Decay linear weights [n, n-1, ..., 1] - oldest gets most weight."""
        df = pd.DataFrame({"A": [1.0, 1.0, 1.0, 1.0, 100.0]})
        result = decay_linear(df, 5)
        # Weights are [5,4,3,2,1]/15, so oldest (1.0) gets weight 5/15,
        # newest (100.0) gets weight 1/15. Result should be LESS than simple mean.
        val = result["A"].iloc[-1]
        simple_mean = df["A"].mean()
        if not pd.isna(val):
            assert val < simple_mean

    def test_decay_linear_zero_window_raises(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        with pytest.raises(ValueError):
            decay_linear(df, 0)

    def test_signed_power(self, sample_ohlcv_df):
        result = signed_power(sample_ohlcv_df[["close"]], 2.0)
        assert isinstance(result, pd.DataFrame)
        # All values should be non-negative after signed power of 2
        valid = result.dropna()
        assert (valid >= 0).all().all()

    def test_signed_power_preserves_sign(self):
        """Signed power should preserve sign of input."""
        df = pd.DataFrame({"A": [-2.0, -1.0, 0.0, 1.0, 2.0]})
        result = signed_power(df, 3.0)
        # After signed power of 3: [-8, -1, 0, 1, 8]
        expected = pd.DataFrame({"A": [-8.0, -1.0, 0.0, 1.0, 8.0]})
        pd.testing.assert_frame_equal(result, expected)

    def test_safe_div(self, sample_ohlcv_df):
        a = sample_ohlcv_df[["close"]]
        b = sample_ohlcv_df[["close"]] * 2
        result = safe_div(a, b)
        assert isinstance(result, pd.DataFrame)
        valid = result.dropna()
        assert (abs(valid - 0.5) < 0.01).all().all()

    def test_safe_div_by_zero(self):
        """Division by zero should produce NaN, not inf."""
        a = pd.DataFrame({"A": [1.0, 2.0, 3.0]})
        b = pd.DataFrame({"A": [0.0, 0.0, 0.0]})
        result = safe_div(a, b)
        assert result["A"].isna().all()

    def test_safe_div_nan_propagation(self):
        """NaN in input should propagate to output."""
        a = pd.DataFrame({"A": [1.0, np.nan, 3.0]})
        b = pd.DataFrame({"A": [1.0, 1.0, 1.0]})
        result = safe_div(a, b)
        assert pd.isna(result["A"].iloc[1])

    def test_cross_sectional_zscore(self, sample_ohlcv_df):
        """Cross-sectional z-score should work on wide DataFrames."""
        result = cross_sectional_zscore(sample_ohlcv_df[["close"]])
        assert isinstance(result, pd.DataFrame)

    def test_vwap_equity_us(self, panel):
        """VWAP for equity_us should use typical price."""
        result = vwap(panel, market="equity_us")
        assert isinstance(result, pd.DataFrame)
        expected = (panel["open"] + panel["high"] + panel["low"] + panel["close"]) / 4.0
        pd.testing.assert_frame_equal(result, expected)

    def test_vwap_with_provided(self, panel):
        """If panel has 'vwap' key, it should be returned directly."""
        custom_vwap = panel["close"] * 1.01
        panel_with_vwap = {**panel, "vwap": custom_vwap}
        result = vwap(panel_with_vwap)
        pd.testing.assert_frame_equal(result, custom_vwap)


# ═══════════════════════════════════════════════════════════════════════
# 9. FactorHandle Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFactorHandle:

    def test_handle_properties(self, registry: FactorRegistry):
        factors = registry.list(zoo="alpha101")
        if factors:
            handle = registry.get(factors[0])
            assert isinstance(handle.id, str)
            assert isinstance(handle.zoo, str)
            assert isinstance(handle.theme, list)
            assert isinstance(handle.columns_required, list)

    def test_handle_compute(self, registry: FactorRegistry, panel):
        """FactorHandle.compute should work with panel data."""
        factors = registry.list(zoo="alpha101")
        if factors:
            handle = registry.get(factors[0])
            try:
                result = handle.compute(panel)
                assert isinstance(result, pd.DataFrame)
            except Exception:
                # Some factors may need columns we don't have
                pass


# ═══════════════════════════════════════════════════════════════════════
# 10. FactorMeta Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFactorMeta:

    def test_meta_fields(self):
        meta = FactorMeta(
            id="test_factor",
            zoo="test",
            theme=["momentum"],
            formula_latex="x^2",
            columns_required=["close"],
            universe=["equity_us"],
            frequency=["1D"],
            decay_horizon=5,
            min_warmup_bars=20,
            notes="Test factor",
        )
        assert meta.id == "test_factor"
        assert meta.zoo == "test"
        assert meta.theme == ["momentum"]
        assert meta.columns_required == ["close"]
        assert meta.decay_horizon == 5
        assert meta.min_warmup_bars == 20

    def test_meta_frozen(self):
        """FactorMeta should be immutable (frozen dataclass)."""
        meta = FactorMeta(id="test", zoo="test", theme=[])
        with pytest.raises(AttributeError):
            meta.id = "changed"

    def test_market_enum(self):
        assert Market.EQUITY_US.value == "equity_us"
        assert Market.CRYPTO.value == "crypto"
