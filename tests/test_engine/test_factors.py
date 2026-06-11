"""Tests for Alpha Factor Library.

Tests cover:
- Base class and operators (rank, delta, ts_corr, etc.)
- Alpha101 factors
- GTJA191 factors
- Technical factors
- Fundamental factors
- Factor registry
- Factor pipeline
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    open_ = close + np.random.randn(n) * 0.5
    high = np.maximum(close, open_) + np.abs(np.random.randn(n) * 1)
    low = np.minimum(close, open_) - np.abs(np.random.randn(n) * 1)
    volume = np.abs(np.random.randn(n) * 1000000 + 5000000)
    
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def wide_panel():
    """Generate wide-format panel (index=dates, columns=instruments)."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    symbols = ["AAPL", "GOOGL", "MSFT"]
    
    data = {}
    for sym in symbols:
        data[sym] = 100 + np.cumsum(np.random.randn(n) * 2)
    
    return pd.DataFrame(data, index=dates)


# ─── Base Operators Tests ─────────────────────────────────────────────────────

class TestBaseOperators:
    """Test base factor operators."""

    def test_rank(self, wide_panel):
        from quant_nanggroe.engine.factors.base import rank
        result = rank(wide_panel)
        assert result.shape == wide_panel.shape
        # Ranks should be between 0 and 1
        valid = result.dropna()
        assert (valid >= 0).all().all()
        assert (valid <= 1).all().all()

    def test_delta_lookahead_ban(self, wide_panel):
        from quant_nanggroe.engine.factors.base import delta
        # Positive lag should work
        result = delta(wide_panel, 1)
        assert result.shape == wide_panel.shape
        # Negative lag should raise error
        with pytest.raises(ValueError, match="lookahead ban"):
            delta(wide_panel, -1)
        with pytest.raises(ValueError, match="lookahead ban"):
            delta(wide_panel, 0)

    def test_ts_mean(self, wide_panel):
        from quant_nanggroe.engine.factors.base import ts_mean
        result = ts_mean(wide_panel, 20)
        assert result.shape == wide_panel.shape
        # First 19 rows should be NaN (warmup)
        assert result.iloc[:19].isna().all().all()
        # Remaining rows should have values
        assert result.iloc[20:].notna().any().any()

    def test_ts_std(self, wide_panel):
        from quant_nanggroe.engine.factors.base import ts_std
        result = ts_std(wide_panel, 20)
        assert result.shape == wide_panel.shape
        # Std should be non-negative
        valid = result.dropna()
        assert (valid >= 0).all().all()

    def test_ts_corr(self, wide_panel):
        from quant_nanggroe.engine.factors.base import ts_corr
        result = ts_corr(wide_panel, wide_panel.shift(1), 20)
        assert result.shape[0] == wide_panel.shape[0]
        # Correlation should be between -1 and 1
        valid = result.dropna()
        if len(valid) > 0:
            assert (valid >= -1).all().all()
            assert (valid <= 1).all().all()

    def test_safe_div(self, wide_panel):
        from quant_nanggroe.engine.factors.base import safe_div
        a = wide_panel
        b = wide_panel.replace(0, np.nan)
        result = safe_div(a, b)
        # No inf values
        assert not np.isinf(result.values[~np.isnan(result.values)]).any()

    def test_signed_power(self, wide_panel):
        from quant_nanggroe.engine.factors.base import signed_power
        result = signed_power(wide_panel, 2.0)
        # Result should be non-negative (power of 2)
        valid = result.dropna()
        assert (valid >= 0).all().all()

    def test_decay_linear(self, wide_panel):
        from quant_nanggroe.engine.factors.base import decay_linear
        result = decay_linear(wide_panel, 10)
        assert result.shape == wide_panel.shape
        # First 9 rows should be NaN
        assert result.iloc[:9].isna().all().all()


# ─── AlphaFactor Base Tests ──────────────────────────────────────────────────

class TestAlphaFactorBase:
    """Test AlphaFactor base class and validation."""

    def test_factor_lookahead_validation(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MomentumFactor
        factor = MomentumFactor(20)
        assert factor.validate_lookahead() is True

    def test_factor_output_validation(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MomentumFactor
        factor = MomentumFactor(20)
        result = factor.compute(sample_ohlcv)
        validated = factor.validate_output(result)
        # No inf values
        assert not np.isinf(validated.dropna()).any()

    def test_factor_metadata(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MomentumFactor
        factor = MomentumFactor(20)
        meta = factor.meta
        assert meta.zoo == "technical"
        assert "momentum" in meta.theme
        assert "close" in meta.columns_required


# ─── Alpha101 Tests ─────────────────────────────────────────────────────────

class TestAlpha101:
    """Test Alpha101 factors."""

    def test_alpha101_001(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.alpha101 import Alpha101_001
        factor = Alpha101_001()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)
        # No inf
        assert not np.isinf(result.dropna()).any()

    def test_alpha101_041(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.alpha101 import Alpha101_041
        factor = Alpha101_041()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)

    def test_alpha101_012(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.alpha101 import Alpha101_012
        factor = Alpha101_012()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)

    def test_get_all_alpha101(self):
        from quant_nanggroe.engine.factors.alpha101 import get_all_alpha101_factors
        factors = get_all_alpha101_factors()
        assert len(factors) > 0
        for f in factors:
            assert f.name.startswith("alpha101")


# ─── GTJA191 Tests ─────────────────────────────────────────────────────────

class TestGTJA191:
    """Test GTJA191 factors."""

    def test_gtja191_001(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.gtja191 import GTJA191_001
        factor = GTJA191_001()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)

    def test_gtja191_191(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.gtja191 import GTJA191_191
        factor = GTJA191_191()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)

    def test_get_all_gtja191(self):
        from quant_nanggroe.engine.factors.gtja191 import get_all_gtja191_factors
        factors = get_all_gtja191_factors()
        assert len(factors) > 0


# ─── Technical Factors Tests ────────────────────────────────────────────────

class TestTechnicalFactors:
    """Test technical factors."""

    def test_momentum(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MomentumFactor
        factor = MomentumFactor(20)
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        # Early values should be NaN (warmup)
        assert result.iloc[:20].isna().all()

    def test_rsi(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import RSIFactor
        factor = RSIFactor(14)
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        # RSI should be between 0 and 100
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_atr(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import ATRFactor
        factor = ATRFactor(14)
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        # ATR ratio should be positive
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_macd(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MACDHistogramFactor
        factor = MACDHistogramFactor()
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)

    def test_mean_reversion(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.technical import MeanReversionFactor
        factor = MeanReversionFactor(20)
        result = factor.compute(sample_ohlcv)
        assert isinstance(result, pd.Series)
        # Z-score can be positive or negative
        valid = result.dropna()
        # Most values should be within 3 std devs
        assert (valid.abs() < 5).sum() / len(valid) > 0.9

    def test_get_all_technical(self):
        from quant_nanggroe.engine.factors.technical import get_all_technical_factors
        factors = get_all_technical_factors()
        assert len(factors) >= 9


# ─── Fundamental Factors Tests ──────────────────────────────────────────────

class TestFundamentalFactors:
    """Test fundamental factors."""

    def test_pe_ratio_with_data(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.fundamental import PEFactor
        df = sample_ohlcv.copy()
        df["eps"] = np.random.uniform(2, 10, len(df))
        factor = PEFactor()
        result = factor.compute(df)
        assert isinstance(result, pd.Series)
        # P/E should be positive for positive EPS
        valid = result.dropna()
        assert (valid > 0).sum() > 0

    def test_pe_ratio_missing_eps(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.fundamental import PEFactor
        factor = PEFactor()
        result = factor.compute(sample_ohlcv)
        # Should return NaN when EPS not available
        assert result.isna().all()

    def test_roe(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.fundamental import ROEFactor
        df = sample_ohlcv.copy()
        df["net_income"] = np.random.uniform(100000, 500000, len(df))
        df["shareholders_equity"] = np.random.uniform(1000000, 5000000, len(df))
        factor = ROEFactor()
        result = factor.compute(df)
        assert isinstance(result, pd.Series)
        valid = result.dropna()
        assert len(valid) > 0


# ─── Registry Tests ─────────────────────────────────────────────────────────

class TestFactorRegistry:
    """Test factor registry."""

    def test_registry_creation(self):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        assert len(registry.list()) > 0

    def test_registry_list_by_zoo(self):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        alpha101 = registry.list(zoo="alpha101")
        assert len(alpha101) > 0
        for fid in alpha101:
            meta = registry.get_meta(fid)
            assert meta.zoo == "alpha101"

    def test_registry_list_by_theme(self):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        momentum = registry.list(theme="momentum")
        assert len(momentum) > 0

    def test_registry_compute(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        # Compute a technical factor
        result = registry.compute("momentum", sample_ohlcv)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)

    def test_registry_health(self):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        health = registry.health()
        assert "loaded" in health
        assert health["loaded"] > 0

    def test_registry_get_nonexistent(self):
        from quant_nanggroe.engine.factors.registry import FactorRegistry
        registry = FactorRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent_factor")


# ─── Pipeline Tests ─────────────────────────────────────────────────────────

class TestFactorPipeline:
    """Test factor pipeline."""

    def test_pipeline_creation(self):
        from quant_nanggroe.engine.factors.pipeline import FactorPipeline
        pipeline = FactorPipeline(factor_ids=["momentum", "rsi_14"])
        assert len(pipeline.factor_ids) == 2

    def test_pipeline_compute(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.pipeline import FactorPipeline
        pipeline = FactorPipeline(factor_ids=["momentum", "rsi_14"])
        results = pipeline.compute(sample_ohlcv)
        assert isinstance(results, dict)
        assert len(results) > 0

    def test_pipeline_as_dataframe(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.pipeline import FactorPipeline
        pipeline = FactorPipeline(factor_ids=["momentum", "rsi_14"])
        result_df = pipeline.compute_as_dataframe(sample_ohlcv)
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv)

    def test_pipeline_combine_signals(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.pipeline import FactorPipeline, CombineMethod
        pipeline = FactorPipeline(factor_ids=["momentum", "rsi_14"])
        results = pipeline.compute(sample_ohlcv)
        combined = pipeline.combine_signals(results, method=CombineMethod.RANK_AVERAGE)
        assert isinstance(combined, pd.Series)
        assert len(combined) == len(sample_ohlcv)

    def test_pipeline_validate_data(self, sample_ohlcv):
        from quant_nanggroe.engine.factors.pipeline import FactorPipeline
        pipeline = FactorPipeline(factor_ids=["momentum"])
        validation = pipeline.validate_data(sample_ohlcv)
        assert "ready" in validation
        assert len(validation["ready"]) > 0
