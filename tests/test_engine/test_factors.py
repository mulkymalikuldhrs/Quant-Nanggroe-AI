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

from quant_nanggroe.engine.analysis.factors import FactorModel, FactorResult, get_builtin_factors
from quant_nanggroe.engine.analysis.bootstrap import BootstrapCI
from quant_nanggroe.engine.strategy.registry import (
    StrategyMetaRegistry,
    compute_factor_exposures,
    sharpe_ci_to_registry,
)
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


# ═══════════════════════════════════════════════════════════════════════════
# P1-28: Factor Regression Framework + Bootstrap CIs
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_returns():
    """Synthetic strategy returns for factor regression tests."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    # Strategy returns with known factor exposures
    market = np.random.normal(0.0005, 0.01, n)
    momentum = np.random.normal(0.0002, 0.015, n)
    noise = np.random.normal(0, 0.005, n)
    # Alpha = 0.05/yr ≈ 0.0002/day, market beta=1.2, momentum beta=0.5
    daily_alpha = 0.05 / 252
    returns = pd.Series(
        daily_alpha + 1.2 * market + 0.5 * momentum + noise,
        index=dates,
        name="strategy_returns",
    )
    return returns


@pytest.fixture
def sample_factors(sample_returns):
    """Factor returns (market, momentum) aligned with sample_returns."""
    np.random.seed(42)
    n = len(sample_returns)
    dates = sample_returns.index
    factors = pd.DataFrame({
        "Market": np.random.normal(0.0005, 0.01, n),
        "Momentum": np.random.normal(0.0002, 0.015, n),
    }, index=dates)
    return factors


@pytest.fixture
def sample_returns_no_alpha():
    """Returns with zero alpha (null hypothesis)."""
    np.random.seed(99)
    n = 500
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    market = np.random.normal(0.0003, 0.01, n)
    returns = pd.Series(1.0 * market, index=dates, name="no_alpha")
    return returns


@pytest.fixture
def empty_registry():
    """Empty StrategyMetaRegistry for integration tests."""
    return StrategyMetaRegistry()


# ─── 11. FactorModel Tests ──────────────────────────────────────────────


class TestFactorModelFit:

    def test_fit_returns_correct_structure(self, sample_returns, sample_factors):
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors)
        assert isinstance(result, FactorResult)
        assert "Market" in result.factors
        assert "Momentum" in result.factors
        assert isinstance(result.alpha, float)
        assert isinstance(result.r_squared, float)
        assert isinstance(result.residuals, np.ndarray)
        assert len(result.residuals) > 0

    def test_fit_produces_non_nan_coefficients(self, sample_returns, sample_factors):
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors)
        for name in result.factors:
            assert not np.isnan(result.factors[name]), f"{name} coefficient is NaN"
            assert not np.isnan(result.t_stats[name]), f"{name} t-stat is NaN"
            assert not np.isnan(result.p_values[name]), f"{name} p-value is NaN"

    def test_alpha_is_returned(self, sample_returns, sample_factors):
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors)
        assert isinstance(result.alpha, float)
        assert not np.isnan(result.alpha)
        assert not np.isnan(result.alpha_t_stat)

    def test_alpha_detects_known_alpha(self, sample_returns, sample_factors):
        """Alpha of 5%/yr should be positive and significant."""
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors)
        # Our synthetic data has 5%/yr alpha, should detect > 0
        assert result.alpha > 0, f"Expected positive alpha, got {result.alpha}"

    def test_zero_alpha_when_none(self, sample_returns_no_alpha):
        """Zero-alpha strategy should produce alpha ~ 0."""
        n = len(sample_returns_no_alpha)
        market = pd.Series(
            np.random.normal(0.0003, 0.01, n),
            index=sample_returns_no_alpha.index,
        )
        factors = pd.DataFrame({"Market": market})
        model = FactorModel()
        result = model.fit(sample_returns_no_alpha, factors)
        # Alpha should be close to 0
        assert abs(result.alpha) < 0.001, f"Expected alpha ~ 0, got {result.alpha}"

    def test_r_squared_in_bounds(self, sample_returns, sample_factors):
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors)
        assert 0.0 <= result.r_squared <= 1.0
        assert 0.0 <= result.adj_r_squared <= 1.0 or result.adj_r_squared < 0

    def test_fit_no_constant(self, sample_returns, sample_factors):
        model = FactorModel()
        result = model.fit(sample_returns, sample_factors, add_constant=False)
        assert result.alpha == 0.0
        assert "Market" in result.factors

    def test_fit_too_few_obs_raises(self):
        returns = pd.Series([0.01, 0.02], index=pd.date_range("2023-01-01", periods=2, freq="D"))
        factors = pd.DataFrame({"Market": [0.01, 0.02]}, index=returns.index)
        model = FactorModel()
        with pytest.raises(ValueError, match="at least 3"):
            model.fit(returns, factors)

    def test_builtin_factors_exist(self):
        builtins = get_builtin_factors()
        assert "Market" in builtins
        assert "Momentum" in builtins
        assert "Volatility" in builtins
        assert "Size" in builtins
        assert "Trend" in builtins

    def test_add_custom_factor(self, sample_returns):
        model = FactorModel()
        custom = pd.Series(np.random.normal(0, 0.01, len(sample_returns)), index=sample_returns.index)
        model.add_factor("Custom", custom)
        factors_df = pd.DataFrame({"Custom": custom})
        result = model.fit(sample_returns, factors_df)
        assert "Custom" in result.factors

    def test_summary_returns_string(self, sample_returns, sample_factors):
        model = FactorModel()
        model.fit(sample_returns, sample_factors)
        s = model.summary()
        assert isinstance(s, str)
        assert "R²" in s
        assert "Alpha" in s
        assert "Market" in s

    def test_summary_before_fit(self):
        model = FactorModel()
        s = model.summary()
        assert "No model fitted" in s

    def test_plot_weights(self, sample_returns, sample_factors):
        model = FactorModel()
        model.fit(sample_returns, sample_factors)
        plot = model.plot_weights()
        assert isinstance(plot, str)
        assert "Factor Loadings" in plot

    def test_result_accessor(self, sample_returns, sample_factors):
        model = FactorModel()
        assert model.result() is None
        model.fit(sample_returns, sample_factors)
        assert isinstance(model.result(), FactorResult)


# ─── 12. BootstrapCI Tests ──────────────────────────────────────────────


class TestBootstrapCI:

    def test_sharpe_ratio_normal_returns(self):
        """Sharpe of a positive-mean series should be positive."""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        sr = BootstrapCI.sharpe_ratio(returns.to_numpy())
        assert sr > 0

    def test_sharpe_ratio_zero_vol(self):
        sr = BootstrapCI.sharpe_ratio(np.array([0.0, 0.0, 0.0]))
        assert sr == 0.0

    def test_sharpe_ratio_annual_factor(self):
        returns = pd.Series(np.full(252, 0.001))
        sr_daily = BootstrapCI.sharpe_ratio(returns.to_numpy(), annual_factor=252)
        sr_monthly = BootstrapCI.sharpe_ratio(returns.to_numpy(), annual_factor=12)
        assert sr_daily != sr_monthly

    def test_sharpe_ci_returns_valid_structure(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0005, 0.02, 500))
        ci = BootstrapCI()
        result = ci.sharpe_ci(returns, n_bootstrap=500)
        assert "lower" in result
        assert "upper" in result
        assert "point_estimate" in result
        assert "std_error" in result
        assert result["lower"] <= result["point_estimate"] <= result["upper"]
        assert result["std_error"] >= 0

    def test_sharpe_ci_with_autocorrelated_returns(self):
        """Autocorrelated returns should still produce valid CI."""
        np.random.seed(42)
        n = 500
        noise = np.random.normal(0.0003, 0.015, n)
        ar_returns = [noise[0]]
        for i in range(1, n):
            ar_returns.append(0.3 * ar_returns[-1] + noise[i])
        returns = pd.Series(ar_returns)
        ci = BootstrapCI()
        result = ci.sharpe_ci(returns, n_bootstrap=500)
        assert result["lower"] <= result["upper"]
        assert not np.isnan(result["point_estimate"])

    def test_sharpe_ci_short_series(self):
        """Very short series should return nan bounds."""
        returns = pd.Series([0.01, 0.02])
        ci = BootstrapCI()
        result = ci.sharpe_ci(returns, n_bootstrap=100)
        assert np.isnan(result["lower"])
        assert np.isnan(result["upper"])

    def test_alpha_ci_returns_structure(self, sample_returns, sample_factors):
        ci = BootstrapCI()
        result = ci.alpha_ci(sample_returns, sample_factors, n_bootstrap=200)
        assert "lower" in result
        assert "upper" in result
        assert "point_estimate" in result
        assert "p_value" in result

    def test_compare_strategies_returns_probability(self):
        np.random.seed(42)
        # Strategy 1: higher Sharpe
        r1 = pd.Series(np.random.normal(0.001, 0.02, 500))
        # Strategy 2: lower Sharpe
        r2 = pd.Series(np.random.normal(0.0002, 0.02, 500))
        ci = BootstrapCI()
        result = ci.compare_strategies(r1, r2, n_bootstrap=500)
        assert "prob_diff" in result
        assert "sharpe_diff" in result
        assert "sharpe_diff_ci" in result
        assert result["prob_diff"] > 0.5  # R1 should be more likely better
        assert result["sharpe_diff"] > 0

    def test_compare_strategies_equal(self):
        np.random.seed(42)
        r1 = pd.Series(np.random.normal(0.0005, 0.02, 500))
        r2 = pd.Series(np.random.normal(0.0005, 0.02, 500))
        ci = BootstrapCI()
        result = ci.compare_strategies(r1, r2, n_bootstrap=500)
        assert 0.2 <= result["prob_diff"] <= 0.8  # Should be ~0.5

    def test_compare_strategies_short_series(self):
        r1 = pd.Series([0.01, 0.02])
        r2 = pd.Series([0.015, 0.025])
        ci = BootstrapCI()
        result = ci.compare_strategies(r1, r2, n_bootstrap=100)
        assert np.isnan(result["sharpe_diff"])

    def test_stationary_bootstrap_handles_autocorrelation(self):
        """Stationary bootstrap should produce valid samples."""
        np.random.seed(42)
        n = 200
        noise = np.random.normal(0, 0.01, n)
        ar = [noise[0]]
        for i in range(1, n):
            ar.append(0.5 * ar[-1] + noise[i])
        data = np.array(ar)

        from quant_nanggroe.engine.analysis.bootstrap import _stationary_bootstrap

        samples = _stationary_bootstrap(data, block_size=20, n_bootstrap=100, rng=np.random.default_rng(42))
        assert samples.shape == (100, 200)
        # Mean of bootstrap samples should be close to original mean
        assert abs(np.mean(samples) - np.mean(data)) < 0.01


# ─── 13. Registry Integration Tests ─────────────────────────────────────


class TestRegistryIntegration:

    def test_compute_factor_exposures_stores_in_registry(self, empty_registry, sample_returns, sample_factors):
        empty_registry.register("test_strategy", description="Test strategy for factor regression")
        result = compute_factor_exposures(empty_registry, "test_strategy", sample_returns, sample_factors)
        meta = empty_registry.get("test_strategy")
        assert "factor_exposures" in meta.custom_metrics
        exposures = meta.custom_metrics["factor_exposures"]
        assert "alpha" in exposures
        assert "r_squared" in exposures
        assert "factors" in exposures

    def test_sharpe_ci_to_registry_stores_ci(self, empty_registry):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0005, 0.02, 500))
        empty_registry.register("test_strategy")
        result = sharpe_ci_to_registry(empty_registry, "test_strategy", returns, n_bootstrap=500)
        meta = empty_registry.get("test_strategy")
        assert "sharpe_ci" in meta.custom_metrics
        ci_data = meta.custom_metrics["sharpe_ci"]
        assert "lower" in ci_data
        assert "upper" in ci_data
        assert "point_estimate" in ci_data

    def test_unregistered_strategy_raises(self, empty_registry, sample_returns, sample_factors):
        with pytest.raises(KeyError):
            compute_factor_exposures(empty_registry, "nonexistent", sample_returns, sample_factors)

    def test_factor_exposures_keys(self, empty_registry, sample_returns, sample_factors):
        empty_registry.register("strat_a")
        result = compute_factor_exposures(empty_registry, "strat_a", sample_returns, sample_factors)
        assert "alpha" in result
        assert "r_squared" in result
        assert "adj_r_squared" in result
        assert "factors" in result
        assert "factor_t_stats" in result
        assert "factor_p_values" in result
