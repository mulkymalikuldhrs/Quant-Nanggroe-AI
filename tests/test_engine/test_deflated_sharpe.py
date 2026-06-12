"""Tests for the Deflated Sharpe Ratio module."""

import math

import numpy as np
import pytest

from quant_nanggroe.engine.risk.deflated_sharpe import (
    DeflatedSharpeResult,
    OverfittingReport,
    deflated_sharpe_ratio,
    generate_overfitting_report,
    minimum_track_record_length,
    probability_of_backtest_overfitting,
)


class TestDeflatedSharpeRatio:
    """Tests for the deflated_sharpe_ratio function."""

    def test_zero_sharpe_returns_low_dsr(self):
        """Zero Sharpe Ratio should produce a very low DSR."""
        result = deflated_sharpe_ratio(
            observed_sharpe=0.0,
            num_trials=10,
            sample_length=252,
        )
        assert isinstance(result, DeflatedSharpeResult)
        assert result.observed_sharpe == 0.0
        assert result.dsr < 0.1
        assert not result.is_significant

    def test_high_sharpe_with_few_trials_is_significant(self):
        """A very high Sharpe with few trials should be significant."""
        result = deflated_sharpe_ratio(
            observed_sharpe=3.0,
            num_trials=5,
            sample_length=500,
        )
        assert result.observed_sharpe == 3.0
        assert result.dsr > 0.9
        assert result.is_significant
        assert result.expected_max_sharpe > 0

    def test_multiple_trials_inflate_expected_max(self):
        """More trials should inflate the expected maximum Sharpe Ratio."""
        result_few = deflated_sharpe_ratio(
            observed_sharpe=1.5, num_trials=5, sample_length=252
        )
        result_many = deflated_sharpe_ratio(
            observed_sharpe=1.5, num_trials=500, sample_length=252
        )
        # More trials -> higher expected max -> lower DSR
        assert result_many.expected_max_sharpe > result_few.expected_max_sharpe
        assert result_many.dsr < result_few.dsr

    def test_single_trial_dsr(self):
        """With a single trial, E[max(SR)] = 0 and DSR should be standard SR significance."""
        result = deflated_sharpe_ratio(
            observed_sharpe=1.5,
            num_trials=1,
            sample_length=252,
        )
        assert result.expected_max_sharpe == 0.0
        # With 1 trial, DSR = P(SR > 0) which for SR=1.5/√252 should be high
        assert result.dsr > 0.5

    def test_dsr_result_has_all_fields(self):
        """Result model should have all required fields populated."""
        result = deflated_sharpe_ratio(
            observed_sharpe=1.0,
            num_trials=10,
            sample_length=252,
        )
        assert result.observed_sharpe is not None
        assert result.expected_max_sharpe is not None
        assert result.sharpe_variance > 0
        assert 0 <= result.dsr <= 1
        assert isinstance(result.is_significant, bool)
        assert isinstance(result.min_track_record, int)
        assert result.num_trials == 10
        assert result.interpretation != ""

    def test_skewness_and_kurtosis_affect_dsr(self):
        """Skewness and kurtosis should affect the variance and thus DSR."""
        result_neutral = deflated_sharpe_ratio(
            observed_sharpe=1.0, num_trials=10, sample_length=252,
            skewness=0, kurtosis=0,
        )
        result_negative_skew = deflated_sharpe_ratio(
            observed_sharpe=1.0, num_trials=10, sample_length=252,
            skewness=-1.0, kurtosis=0,
        )
        # Negative skewness with positive SR increases variance -> lower DSR
        assert result_negative_skew.sharpe_variance > result_neutral.sharpe_variance
        assert result_negative_skew.dsr <= result_neutral.dsr


class TestMinimumTrackRecordLength:
    """Tests for the minimum_track_record_length function."""

    def test_mtl_positive_for_significant_sr(self):
        """MTL should be positive when observed SR exceeds expected max."""
        mtl = minimum_track_record_length(
            observed_sharpe=2.0, num_trials=10,
        )
        assert mtl > 0

    def test_mtl_negative_for_zero_sr(self):
        """MTL should be -1 when SR doesn't exceed expected max."""
        mtl = minimum_track_record_length(
            observed_sharpe=0.0, num_trials=100,
        )
        assert mtl == -1

    def test_mtl_increases_with_more_trials(self):
        """More trials should require a longer track record."""
        mtl_few = minimum_track_record_length(
            observed_sharpe=1.5, num_trials=10,
        )
        mtl_many = minimum_track_record_length(
            observed_sharpe=1.5, num_trials=200,
        )
        assert mtl_many > mtl_few


class TestProbabilityOfBacktestOverfitting:
    """Tests for the probability_of_backtest_overfitting function."""

    def test_pbo_with_tight_srs(self):
        """When all SRs are similar, PBO should be relatively low."""
        srs = [1.0, 1.05, 0.98, 1.02, 0.99, 1.01]
        pbo = probability_of_backtest_overfitting(srs)
        assert 0 <= pbo <= 1
        assert pbo < 0.7  # Should be low for tight distribution

    def test_pbo_with_outlier_best(self):
        """When one SR is an extreme outlier, PBO should be higher."""
        srs = [0.1, 0.05, -0.1, 0.0, 0.02, 3.5]
        pbo = probability_of_backtest_overfitting(srs)
        assert pbo > 0.3

    def test_pbo_single_strategy(self):
        """Single strategy should have PBO of 0 (no overfitting possible)."""
        pbo = probability_of_backtest_overfitting([1.5])
        assert pbo == 0.0


class TestOverfittingReport:
    """Tests for generate_overfitting_report."""

    def test_overfitting_report_structure(self):
        """Report should contain all required fields."""
        srs = [0.5, 0.6, 0.7, 0.8, 2.5]
        report = generate_overfitting_report(
            strategy_sharpe_ratios=srs,
            sample_length=252,
        )
        assert isinstance(report, OverfittingReport)
        assert report.strategies_tested == 5
        assert report.best_sharpe == 2.5
        assert 0 <= report.dsr <= 1
        assert 0 <= report.pbo <= 1
        assert report.verdict in ("OVERFITTING", "LIKELY_OVERFITTING", "ACCEPTABLE")
        assert len(report.recommendations) > 0

    def test_interpretation_string(self):
        """DSR result should include a meaningful interpretation string."""
        result = deflated_sharpe_ratio(
            observed_sharpe=0.5, num_trials=100, sample_length=252,
        )
        assert "DSR=" in result.interpretation
        assert "0.5" in result.interpretation
