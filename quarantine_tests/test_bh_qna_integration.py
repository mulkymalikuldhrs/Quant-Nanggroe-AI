"""
BH+QNA Integration Tests
=========================

Tests cross-module data flow, analysis exchange, risk checks, and
execution pipeline between BH (Backtesting/Historical) and QNA
(Quant Nanggroe AI) modules.

Covers:
- TestMarketDataFlow: Market data flows from BH to QNA
- TestAnalysisFlow: QNA analysis results flow back to BH
- TestRiskChecks: Risk checks work across modules
- TestExecutionPipeline: Execution pipeline end-to-end
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.integration.bh_qna_bridge import (
    BHQnaBridge,
    BridgeConfig,
    BridgeResult,
    BridgeStatus,
    ModuleSide,
)
from quant_nanggroe.engine.core.edge_case_handler import (
    safe_divide,
    validate_returns,
    safe_kelly_fraction,
)
from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
from quant_nanggroe.engine.kelly.base import KellyParameters
from quant_nanggroe.engine.kelly.fractional import FractionalKelly
from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def bridge() -> BHQnaBridge:
    """Default BHQnaBridge instance."""
    return BHQnaBridge(config=BridgeConfig(
        request_timeout=10.0,
        max_retries=1,
        retry_delay=0.1,
        enable_fallback=True,
    ))


@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """Sample OHLCV market data."""
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.015, 200)
    close = 100.0 * np.cumprod(1 + returns)
    return pd.DataFrame({
        "open": close * (1 + rng.normal(0, 0.002, 200)),
        "high": close * (1 + np.abs(rng.normal(0, 0.005, 200))),
        "low": close * (1 - np.abs(rng.normal(0, 0.005, 200))),
        "close": close,
        "volume": rng.lognormal(15, 0.5, 200),
    }, index=dates)


@pytest.fixture
def backtest_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=100_000.0,
        commission_rate=0.001,
        slippage_bps=5.0,
        leverage=1.0,
        risk_per_trade=0.02,
    )


# ═══════════════════════════════════════════════════════════════════════
# TestMarketDataFlow
# ═══════════════════════════════════════════════════════════════════════

class TestMarketDataFlow:
    """Test market data flows from BH to QNA."""

    def test_market_data_fetch_success(self, bridge: BHQnaBridge):
        """Market data should be fetched successfully from BH."""
        result = bridge.get_market_data_from_bh(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-06-30",
        )

        assert result.status == BridgeStatus.SUCCESS
        assert isinstance(result.data, pd.DataFrame)
        assert not result.data.empty
        assert result.source == ModuleSide.BH
        assert result.target == ModuleSide.QNA
        assert result.latency_ms >= 0

    def test_market_data_has_ohlcv_columns(self, bridge: BHQnaBridge):
        """Fetched data should have OHLCV columns."""
        result = bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-06-30")

        assert result.status == BridgeStatus.SUCCESS
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in result.data.columns, f"Missing column: {col}"

    def test_market_data_datetime_index(self, bridge: BHQnaBridge):
        """Fetched data should have DatetimeIndex."""
        result = bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-06-30")

        assert result.status == BridgeStatus.SUCCESS
        assert isinstance(result.data.index, pd.DatetimeIndex)

    def test_market_data_no_inf_values(self, bridge: BHQnaBridge):
        """Fetched data should not contain inf values."""
        result = bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-06-30")

        assert result.status == BridgeStatus.SUCCESS
        for col in result.data.select_dtypes(include=[np.number]).columns:
            assert not np.any(np.isinf(result.data[col])), f"inf found in {col}"

    def test_market_data_synthetic_fallback(self):
        """When BH loader unavailable, should fall back to synthetic data."""
        config = BridgeConfig(enable_fallback=True)
        b = BHQnaBridge(config=config)

        result = b.get_market_data_from_bh("UNKNOWN", "2024-01-01", "2024-01-31")

        assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)
        if result.data is not None:
            assert not result.data.empty

    def test_market_data_custom_fields(self, bridge: BHQnaBridge):
        """Should respect custom field list."""
        result = bridge.get_market_data_from_bh(
            "SPY", "2024-01-01", "2024-06-30",
            fields=["close", "volume"],
        )

        assert result.status == BridgeStatus.SUCCESS
        assert "close" in result.data.columns
        assert "volume" in result.data.columns

    def test_market_data_metrics_tracked(self, bridge: BHQnaBridge):
        """Bridge should track operation metrics."""
        bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-06-30")
        bridge.get_market_data_from_bh("QQQ", "2024-01-01", "2024-06-30")

        metrics = bridge.get_metrics()
        assert metrics["total_calls"] >= 2
        assert metrics["success_count"] >= 1

    def test_market_data_result_to_dict(self, bridge: BHQnaBridge):
        """BridgeResult.to_dict should return serializable dict."""
        result = bridge.get_market_data_from_bh("SPY", "2024-01-01", "2024-06-30")
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "status" in d
        assert "latency_ms" in d
        assert "timestamp" in d


# ═══════════════════════════════════════════════════════════════════════
# TestAnalysisFlow
# ═══════════════════════════════════════════════════════════════════════

class TestAnalysisFlow:
    """Test QNA analysis results flow back to BH."""

    def test_analysis_full_type(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Full analysis should produce risk, kelly, and signal results."""
        result = bridge.run_qna_analysis(
            sample_market_data,
            analysis_type="full",
            params={"symbol": "SPY"},
        )

        assert result.status == BridgeStatus.SUCCESS
        assert isinstance(result.data, dict)
        assert "risk" in result.data
        assert "kelly" in result.data
        assert "signal" in result.data
        assert "returns_summary" in result.data

    def test_analysis_risk_type(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Risk analysis should produce risk metrics only."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="risk"
        )

        assert result.status == BridgeStatus.SUCCESS
        assert "risk" in result.data
        assert "var_95" in result.data["risk"]
        assert "cvar_95" in result.data["risk"]
        assert "volatility" in result.data["risk"]

    def test_analysis_kelly_type(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Kelly analysis should produce kelly parameters."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="kelly"
        )

        assert result.status == BridgeStatus.SUCCESS
        assert "kelly" in result.data
        kelly = result.data["kelly"]
        assert 0.0 <= kelly["win_rate"] <= 1.0
        assert kelly["kelly_f"] >= 0.0

    def test_analysis_signal_type(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Signal analysis should produce a trading signal."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="signal"
        )

        assert result.status == BridgeStatus.SUCCESS
        assert "signal" in result.data
        signal = result.data["signal"]
        assert signal["direction"] in ("BUY", "SELL", "HOLD")

    def test_analysis_send_to_bh(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Analysis results should be packaged correctly for BH."""
        analysis = bridge.run_qna_analysis(
            sample_market_data, analysis_type="full", params={"symbol": "SPY"}
        )

        bh_result = bridge.send_results_to_bh(analysis)

        assert bh_result.status == BridgeStatus.SUCCESS
        assert bh_result.source == ModuleSide.QNA
        assert bh_result.target == ModuleSide.BH
        assert isinstance(bh_result.data, dict)
        assert "bh_format" in bh_result.data
        assert bh_result.data["bh_format"] is True

    def test_analysis_bh_payload_has_signal_strength(
        self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame
    ):
        """BH payload should contain signal_strength and target_weight."""
        analysis = bridge.run_qna_analysis(
            sample_market_data, analysis_type="full", params={"symbol": "SPY"}
        )
        bh_result = bridge.send_results_to_bh(analysis)

        assert "signal_strength" in bh_result.data
        assert "target_weight" in bh_result.data
        assert -1.0 <= bh_result.data["target_weight"] <= 1.0

    def test_analysis_fallback_on_failure(self):
        """Should use fallback analysis when primary fails."""
        config = BridgeConfig(enable_fallback=True)
        b = BHQnaBridge(config=config)

        bad_data = pd.DataFrame({"close": [np.nan, np.nan]})

        result = b.run_qna_analysis(bad_data, analysis_type="full")

        assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)
        if result.fallback_used:
            assert result.data is not None

    def test_analysis_empty_data(self, bridge: BHQnaBridge):
        """Should handle empty data gracefully."""
        empty_df = pd.DataFrame()
        result = bridge.run_qna_analysis(empty_df)

        assert result.status in (BridgeStatus.FAILED, BridgeStatus.FALLBACK)


# ═══════════════════════════════════════════════════════════════════════
# TestRiskChecks
# ═══════════════════════════════════════════════════════════════════════

class TestRiskChecks:
    """Test risk checks work across BH and QNA modules."""

    def test_risk_metrics_in_analysis(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """QNA analysis should include valid risk metrics."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="risk"
        )

        risk = result.data["risk"]
        assert isinstance(risk["var_95"], float)
        assert isinstance(risk["cvar_95"], float)
        assert isinstance(risk["volatility"], float)
        assert risk["volatility"] >= 0.0

    def test_kelly_f_capped(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """Kelly fraction should be capped between 0 and 1."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="kelly"
        )

        kelly_f = result.data["kelly"]["kelly_f"]
        assert 0.0 <= kelly_f <= 1.0

    def test_var_95_negative(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """VaR 95% should be negative (loss at 95% confidence)."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="risk"
        )

        var_95 = result.data["risk"]["var_95"]
        assert var_95 <= 0.0

    def test_cvar_worse_than_var(self, bridge: BHQnaBridge, sample_market_data: pd.DataFrame):
        """CVaR should be worse than VaR (more negative)."""
        result = bridge.run_qna_analysis(
            sample_market_data, analysis_type="risk"
        )

        var_95 = result.data["risk"]["var_95"]
        cvar_95 = result.data["risk"]["cvar_95"]
        assert cvar_95 <= var_95

    def test_edge_case_nan_in_data(self, bridge: BHQnaBridge):
        """Risk checks should handle NaN in price data."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, 100))
        close[10] = np.nan
        close[50] = np.nan

        data = pd.DataFrame({
            "close": close,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "volume": 1000000,
        }, index=dates)

        result = bridge.run_qna_analysis(data, analysis_type="risk")
        assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)

    def test_edge_case_zero_prices(self, bridge: BHQnaBridge):
        """Risk checks should handle zero prices gracefully."""
        dates = pd.date_range("2024-01-01", periods=50, freq="B")
        close = np.ones(50) * 100.0
        close[25] = 0.0

        data = pd.DataFrame({
            "close": close,
            "open": close,
            "high": close,
            "low": close,
            "volume": 1000000,
        }, index=dates)

        result = bridge.run_qna_analysis(data, analysis_type="full")
        assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)

    def test_edge_case_extreme_returns(self, bridge: BHQnaBridge):
        """Risk checks should handle extreme return values."""
        dates = pd.date_range("2024-01-01", periods=50, freq="B")
        close = np.ones(50) * 100.0
        close[25] = 10000.0  # 9900% single-day return

        data = pd.DataFrame({
            "close": close,
            "open": close,
            "high": close,
            "low": close,
            "volume": 1000000,
        }, index=dates)

        result = bridge.run_qna_analysis(data, analysis_type="risk")
        assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)


# ═══════════════════════════════════════════════════════════════════════
# TestExecutionPipeline
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionPipeline:
    """Test full execution pipeline end-to-end."""

    def test_full_pipeline_success(self, bridge: BHQnaBridge):
        """Full BH→QNA→BH pipeline should complete successfully."""
        result = bridge.run_full_pipeline(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-06-30",
            analysis_type="full",
        )

        assert result.status == BridgeStatus.SUCCESS
        assert result.data is not None
        assert "pipeline" in result.data
        assert result.data["pipeline"]["total_ms"] > 0

    def test_full_pipeline_latency_breakdown(self, bridge: BHQnaBridge):
        """Pipeline should report latency breakdown."""
        result = bridge.run_full_pipeline(
            symbol="QQQ",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        assert result.status == BridgeStatus.SUCCESS
        pipeline = result.data["pipeline"]
        assert "data_fetch_ms" in pipeline
        assert "analysis_ms" in pipeline
        assert "total_ms" in pipeline

    def test_full_pipeline_with_backtest(self, bridge: BHQnaBridge):
        """Pipeline results should be usable in backtest engine."""
        pipeline_result = bridge.run_full_pipeline(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-06-30",
            analysis_type="full",
        )

        assert pipeline_result.status == BridgeStatus.SUCCESS
        bh_data = pipeline_result.data

        assert "target_weight" in bh_data
        assert "kelly_fraction" in bh_data

        target_weight = bh_data["target_weight"]
        assert -1.0 <= target_weight <= 1.0

    def test_full_pipeline_reproducibility(self, bridge: BHQnaBridge):
        """Running the same pipeline twice should produce consistent results."""
        result1 = bridge.run_full_pipeline(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-03-31",
            analysis_type="signal",
        )
        result2 = bridge.run_full_pipeline(
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-03-31",
            analysis_type="signal",
        )

        if result1.status == BridgeStatus.SUCCESS and result2.status == BridgeStatus.SUCCESS:
            assert result1.data["target_weight"] == pytest.approx(
                result2.data["target_weight"], abs=0.01
            )

    def test_pipeline_metrics_accumulation(self, bridge: BHQnaBridge):
        """Multiple pipeline runs should accumulate metrics."""
        for _ in range(3):
            bridge.run_full_pipeline(
                symbol="SPY",
                start_date="2024-01-01",
                end_date="2024-03-31",
            )

        metrics = bridge.get_metrics()
        assert metrics["total_calls"] >= 3

    def test_pipeline_different_symbols(self, bridge: BHQnaBridge):
        """Pipeline should work for different symbols."""
        for symbol in ["SPY", "QQQ", "AAPL", "MSFT"]:
            result = bridge.run_full_pipeline(
                symbol=symbol,
                start_date="2024-01-01",
                end_date="2024-03-31",
            )
            assert result.status in (BridgeStatus.SUCCESS, BridgeStatus.FALLBACK)
