"""
Tests for Factor Models Engine
==============================
Tests Fama-French 3/5 factor models, Barra model,
z-score normalization, return decomposition, and risk attribution.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quant_nanggroe_ai.engine.models import (
    FactorModelsEngine,
    FactorExposure,
    FactorReturnDecomposition,
    RiskAttribution,
    FactorModelResult,
    ZScoreResult,
    BARRA_FACTORS,
    FF3_FACTORS,
    FF5_FACTORS,
)
from quant_nanggroe_ai.exceptions import InsufficientDataError, InvalidParameterError


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> FactorModelsEngine:
    """Fresh FactorModelsEngine instance."""
    return FactorModelsEngine()


@pytest.fixture
def synthetic_ff3_data() -> dict:
    """Generate synthetic data for FF3 model testing (100 observations)."""
    np.random.seed(42)
    n = 100
    market_returns = np.random.normal(0.0005, 0.01, n).tolist()
    smb_returns = np.random.normal(0.0002, 0.005, n).tolist()
    hml_returns = np.random.normal(-0.0001, 0.006, n).tolist()

    # Asset returns as a linear combination plus noise
    asset_returns = [
        0.001 + 1.2 * m + 0.5 * s + 0.3 * h + np.random.normal(0, 0.002)
        for m, s, h in zip(market_returns, smb_returns, hml_returns)
    ]
    return {
        "asset_returns": asset_returns,
        "market_returns": market_returns,
        "smb_returns": smb_returns,
        "hml_returns": hml_returns,
    }


@pytest.fixture
def synthetic_ff5_data(synthetic_ff3_data: dict) -> dict:
    """Generate synthetic data for FF5 model testing."""
    np.random.seed(42)
    n = 100
    data = dict(synthetic_ff3_data)
    data["rmw_returns"] = np.random.normal(0.0003, 0.004, n).tolist()
    data["cma_returns"] = np.random.normal(-0.0002, 0.003, n).tolist()

    # Asset returns extended
    data["asset_returns"] = [
        ar + 0.2 * r + 0.15 * c
        for ar, r, c in zip(
            data["asset_returns"],
            data["rmw_returns"],
            data["cma_returns"],
        )
    ]
    return data


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL TESTS
# ══════════════════════════════════════════════════════════════════════


class TestFactorExposureModel:
    def test_creation(self) -> None:
        fe = FactorExposure(asset="AAPL", factor="MKT", beta=1.2, t_stat=3.5)
        assert fe.beta == 1.2
        assert fe.t_stat == 3.5
        assert fe.p_value == 1.0  # default

    def test_defaults(self) -> None:
        fe = FactorExposure(asset="X", factor="Y", beta=0.5)
        assert fe.t_stat == 0.0
        assert fe.p_value == 1.0


class TestFactorReturnDecomposition:
    def test_creation(self) -> None:
        frd = FactorReturnDecomposition(
            asset="AAPL",
            total_return=0.05,
            factor_contributions={"MKT": 0.03, "SMB": 0.01, "HML": 0.005},
            idiosyncratic_return=0.005,
            r_squared=0.85,
        )
        assert frd.total_return == 0.05
        assert frd.r_squared == 0.85


class TestRiskAttributionModel:
    def test_defaults(self) -> None:
        ra = RiskAttribution()
        assert ra.total_risk == 0.0
        assert ra.factor_risk == {}
        assert ra.idiosyncratic_risk == 0.0


class TestZScoreResultModel:
    def test_creation(self) -> None:
        zsr = ZScoreResult(asset="AAPL", raw_value=1.5, z_score=1.2, rank=8, percentile=80.0)
        assert zsr.z_score == 1.2


# ══════════════════════════════════════════════════════════════════════
# FACTOR MODEL ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════


class TestFamaFrench3Factor:
    """Test FF3 model estimation."""

    def test_ff3_returns_result(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(
            asset_name="TEST", **synthetic_ff3_data
        )
        assert isinstance(result, FactorModelResult)
        assert result.model_type == "FAMA_FRENCH_3"
        assert set(result.factors) == set(FF3_FACTORS)

    def test_ff3_factor_returns(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(**synthetic_ff3_data)
        for factor in FF3_FACTORS:
            assert factor in result.factor_returns

    def test_ff3_exposures(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(**synthetic_ff3_data)
        assert len(result.exposures) == 3
        # MKT beta should be close to 1.2 (as designed in synthetic data)
        mkt_exposure = next(e for e in result.exposures if e.factor == "MKT")
        assert abs(mkt_exposure.beta - 1.2) < 0.5  # Reasonable tolerance

    def test_ff3_decomposition(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(**synthetic_ff3_data)
        assert len(result.decompositions) == 1
        decomp = result.decompositions[0]
        assert decomp.r_squared > 0  # Should have some explanatory power
        assert "MKT" in decomp.factor_contributions

    def test_ff3_risk_attribution(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(**synthetic_ff3_data)
        assert result.risk_attribution is not None
        assert result.risk_attribution.total_risk > 0

    def test_ff3_factor_covariance(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        result = engine.fama_french_3_factor(**synthetic_ff3_data)
        for f1 in FF3_FACTORS:
            assert f1 in result.factor_covariance
            for f2 in FF3_FACTORS:
                assert f2 in result.factor_covariance[f1]

    def test_ff3_insufficient_data(self, engine: FactorModelsEngine) -> None:
        with pytest.raises(InsufficientDataError):
            engine.fama_french_3_factor(
                asset_returns=[0.01] * 10,
                market_returns=[0.01] * 10,
                smb_returns=[0.01] * 10,
                hml_returns=[0.01] * 10,
            )

    def test_ff3_mismatched_lengths(self, engine: FactorModelsEngine) -> None:
        with pytest.raises(InvalidParameterError):
            engine.fama_french_3_factor(
                asset_returns=[0.01] * 100,
                market_returns=[0.01] * 50,
                smb_returns=[0.01] * 100,
                hml_returns=[0.01] * 100,
            )


class TestFamaFrench5Factor:
    """Test FF5 model estimation."""

    def test_ff5_returns_result(
        self, engine: FactorModelsEngine, synthetic_ff5_data: dict
    ) -> None:
        result = engine.fama_french_5_factor(
            asset_name="TEST",
            asset_returns=synthetic_ff5_data["asset_returns"],
            market_returns=synthetic_ff5_data["market_returns"],
            smb_returns=synthetic_ff5_data["smb_returns"],
            hml_returns=synthetic_ff5_data["hml_returns"],
            rmw_returns=synthetic_ff5_data["rmw_returns"],
            cma_returns=synthetic_ff5_data["cma_returns"],
        )
        assert result.model_type == "FAMA_FRENCH_5"
        assert set(result.factors) == set(FF5_FACTORS)

    def test_ff5_insufficient_data(self, engine: FactorModelsEngine) -> None:
        with pytest.raises(InsufficientDataError):
            engine.fama_french_5_factor(
                asset_returns=[0.01] * 10,
                market_returns=[0.01] * 10,
                smb_returns=[0.01] * 10,
                hml_returns=[0.01] * 10,
                rmw_returns=[0.01] * 10,
                cma_returns=[0.01] * 10,
            )

    def test_ff5_mismatched_lengths(self, engine: FactorModelsEngine) -> None:
        with pytest.raises(InvalidParameterError):
            engine.fama_french_5_factor(
                asset_returns=[0.01] * 100,
                market_returns=[0.01] * 100,
                smb_returns=[0.01] * 100,
                hml_returns=[0.01] * 100,
                rmw_returns=[0.01] * 50,  # Mismatch
                cma_returns=[0.01] * 100,
            )


class TestBarraModel:
    """Test Barra-style multi-factor model."""

    def test_barra_basic(self, engine: FactorModelsEngine) -> None:
        np.random.seed(42)
        n_assets = 10
        asset_returns = np.random.normal(0.001, 0.02, n_assets).tolist()
        factor_exposures = {
            "MARKET": [1.0] * n_assets,
            "SIZE": np.random.normal(0, 1, n_assets).tolist(),
            "VALUE": np.random.normal(0, 1, n_assets).tolist(),
        }

        result = engine.barra_model(
            asset_returns=asset_returns,
            factor_exposures_matrix=factor_exposures,
        )
        assert result.model_type == "BARRA"
        assert set(result.factors) == {"MARKET", "SIZE", "VALUE"}
        assert len(result.factor_returns) == 3

    def test_barra_with_risk_attribution(
        self, engine: FactorModelsEngine
    ) -> None:
        np.random.seed(42)
        n_assets = 10
        asset_returns = np.random.normal(0.001, 0.02, n_assets).tolist()
        factor_exposures = {
            "MARKET": [1.0] * n_assets,
            "SIZE": [0.5] * n_assets,
        }

        result = engine.barra_model(
            asset_returns=asset_returns,
            factor_exposures_matrix=factor_exposures,
        )
        assert result.risk_attribution is not None

    def test_barra_insufficient_data(self, engine: FactorModelsEngine) -> None:
        # Need at least len(factors) + 2 assets
        with pytest.raises(InsufficientDataError):
            engine.barra_model(
                asset_returns=[0.01, 0.02],  # Only 2 assets
                factor_exposures_matrix={
                    "MARKET": [1.0, 1.0],
                    "SIZE": [0.5, 0.5],
                },  # Need 4 assets min
            )

    def test_barra_exposure_dimension_mismatch(
        self, engine: FactorModelsEngine
    ) -> None:
        with pytest.raises(InvalidParameterError):
            engine.barra_model(
                asset_returns=[0.01] * 10,
                factor_exposures_matrix={
                    "MARKET": [1.0] * 10,
                    "SIZE": [0.5] * 5,  # Wrong length
                },
            )


class TestZScoreNormalization:
    """Test cross-sectional z-score normalization."""

    def test_basic_normalization(self) -> None:
        values = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0, "E": 5.0}
        results = FactorModelsEngine.z_score_normalize(values)

        assert len(results) == 5
        # Middle value should have z-score near 0
        mid_result = next(r for r in results if r.asset == "C")
        assert abs(mid_result.z_score) < 0.5  # Roughly centered

    def test_z_score_ranks(self) -> None:
        values = {"A": 1.0, "B": 5.0, "C": 3.0}
        results = FactorModelsEngine.z_score_normalize(values)
        sorted_results = sorted(results, key=lambda r: r.raw_value)
        # Ranks should be monotonically increasing
        ranks = [r.rank for r in sorted_results]
        assert ranks == sorted(ranks)

    def test_empty_input(self) -> None:
        results = FactorModelsEngine.z_score_normalize({})
        assert results == []

    def test_single_value(self) -> None:
        results = FactorModelsEngine.z_score_normalize({"A": 5.0})
        assert len(results) == 1
        assert results[0].z_score == 0.0  # No variance → z = 0
        assert results[0].rank == 1

    def test_two_values(self) -> None:
        results = FactorModelsEngine.z_score_normalize({"A": 1.0, "B": 3.0})
        assert len(results) == 2
        # Z-scores should be opposites for symmetric two-value set
        z_scores = sorted(r.z_score for r in results)
        assert abs(z_scores[0] + z_scores[1]) < 0.01  # Symmetric around 0

    def test_winsorization(self) -> None:
        # With extreme outlier
        values = {f"V{i}": float(i) for i in range(10)}
        values["OUTLIER"] = 1000.0

        results_with = FactorModelsEngine.z_score_normalize(
            values, winsorize=True, winsorize_std=2.0
        )
        results_without = FactorModelsEngine.z_score_normalize(
            values, winsorize=False
        )

        # With winsorization, the outlier's raw_value in the result should reflect
        # the original value, but its z_score should be less extreme than without
        outlier_with = next(r for r in results_with if r.asset == "OUTLIER")
        outlier_without = next(r for r in results_without if r.asset == "OUTLIER")
        # The raw_value stored is the original, but z_score is computed on winsorized data
        # With a 2-sigma clip, the outlier should be pulled in
        assert outlier_with.raw_value == 1000.0
        assert outlier_with.z_score <= outlier_without.z_score


class TestReturnDecomposition:
    """Test factor return decomposition."""

    def test_decompose_returns(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        factor_data = {
            "MKT": synthetic_ff3_data["market_returns"],
            "SMB": synthetic_ff3_data["smb_returns"],
            "HML": synthetic_ff3_data["hml_returns"],
        }
        decomp = engine.decompose_returns(
            asset_returns=synthetic_ff3_data["asset_returns"],
            factor_returns_data=factor_data,
        )
        assert isinstance(decomp, FactorReturnDecomposition)
        assert decomp.r_squared > 0
        assert "MKT" in decomp.factor_contributions

    def test_decompose_mismatched_lengths(
        self, engine: FactorModelsEngine
    ) -> None:
        with pytest.raises(InvalidParameterError):
            engine.decompose_returns(
                asset_returns=[0.01] * 100,
                factor_returns_data={"MKT": [0.01] * 50},
            )


class TestEngineProperties:
    """Test engine properties and status."""

    def test_last_result_none_initially(self, engine: FactorModelsEngine) -> None:
        assert engine.last_result is None

    def test_last_result_updated_after_ff3(
        self, engine: FactorModelsEngine, synthetic_ff3_data: dict
    ) -> None:
        engine.fama_french_3_factor(**synthetic_ff3_data)
        assert engine.last_result is not None
        assert engine.last_result.model_type == "FAMA_FRENCH_3"

    def test_status(self, engine: FactorModelsEngine) -> None:
        status = engine.status()
        assert "last_model_type" in status
        assert "history_size" in status
        assert "supported_models" in status
        assert "min_observations" in status
        assert status["last_model_type"] is None  # No model run yet


class TestFactorDefinitions:
    """Test factor name constants."""

    def test_barra_factors(self) -> None:
        assert set(BARRA_FACTORS) == {
            "MARKET", "SIZE", "VALUE", "MOMENTUM", "VOLATILITY",
        }

    def test_ff3_factors(self) -> None:
        assert set(FF3_FACTORS) == {"MKT", "SMB", "HML"}

    def test_ff5_factors(self) -> None:
        assert set(FF5_FACTORS) == {"MKT", "SMB", "HML", "RMW", "CMA"}
