#!/usr/bin/env python3
"""Tests: Probabilistic Sharpe Ratio & Deflated Sharpe Ratio.

Run: python3 -m unittest tests/test_psr.py -v
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np

from quant_nanggroe.engine.backtest.psr import (
    estimate_sharpe,
    _moments,
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
    validate_backtest_metrics,
    psr_vs_sharpe,
)


class TestEstimateSharpe(unittest.TestCase):
    """Tests for estimate_sharpe()."""

    def test_positive_returns_positive_sharpe(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 252)
        sr = estimate_sharpe(returns)
        self.assertGreater(sr, 0)

    def test_negative_returns_negative_sharpe(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(-0.001, 0.02, 252)
        sr = estimate_sharpe(returns)
        self.assertLess(sr, 0)

    def test_constant_returns_zero_sharpe(self):
        returns = np.ones(50) * 0.01
        sr = estimate_sharpe(returns)
        self.assertEqual(sr, 0.0)

    def test_single_return_zero_sharpe(self):
        sr = estimate_sharpe(np.array([0.01]))
        self.assertEqual(sr, 0.0)

    def test_empty_returns_zero_sharpe(self):
        sr = estimate_sharpe(np.array([]))
        self.assertEqual(sr, 0.0)

    def test_two_returns_returns_value(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 2)
        sr = estimate_sharpe(returns)
        self.assertIsInstance(sr, float)


class TestMoments(unittest.TestCase):
    """Tests for _moments()."""

    def test_normal_returns_zero_skew(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 1, 1000)
        skew, kurt = _moments(returns)
        self.assertAlmostEqual(skew, 0, delta=0.2)
        self.assertAlmostEqual(kurt, 0, delta=0.5)

    def test_less_than_three_returns(self):
        skew, kurt = _moments(np.array([1.0, 2.0]))
        self.assertEqual(skew, 0.0)
        self.assertEqual(kurt, 0.0)

    def test_constant_returns(self):
        skew, kurt = _moments(np.ones(10) * 5.0)
        self.assertEqual(skew, 0.0)
        self.assertEqual(kurt, 0.0)


class TestProbabilisticSharpeRatio(unittest.TestCase):
    """Tests for probabilistic_sharpe_ratio()."""

    def test_good_returns_psr_above_threshold(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.015, 252)
        result = probabilistic_sharpe_ratio(returns, sharpe_benchmark=0.0)
        self.assertGreater(result.psr, 0.95)
        self.assertTrue(result.is_significant)

    def test_bad_returns_psr_below_threshold(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(-0.001, 0.015, 252)
        result = probabilistic_sharpe_ratio(returns, sharpe_benchmark=0.0)
        self.assertLess(result.psr, 0.5)
        self.assertFalse(result.is_significant)

    def test_zero_mean_returns_psr_around_half(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.015, 2520)
        mu = returns.mean()
        result = probabilistic_sharpe_ratio(returns - mu, 0.0)
        self.assertAlmostEqual(result.psr, 0.5, delta=0.1)

    def test_empty_returns(self):
        result = probabilistic_sharpe_ratio(np.array([]), 0.0)
        self.assertEqual(result.psr, 0.0)
        self.assertEqual(result.sharpe_observed, 0.0)
        self.assertEqual(result.n_observations, 0)
        self.assertFalse(result.is_significant)

    def test_single_return(self):
        result = probabilistic_sharpe_ratio(np.array([0.01]), 0.0)
        self.assertEqual(result.psr, 0.0)
        self.assertEqual(result.n_observations, 1)
        self.assertFalse(result.is_significant)

    def test_two_returns(self):
        result = probabilistic_sharpe_ratio(np.array([0.01, -0.005]), 0.0)
        self.assertEqual(result.psr, 0.0)
        self.assertEqual(result.n_observations, 2)
        self.assertFalse(result.is_significant)

    def test_constant_returns(self):
        returns = np.zeros(10) + 0.001
        result = probabilistic_sharpe_ratio(returns, 0.0)
        self.assertGreaterEqual(result.psr, 0.0)
        self.assertIsInstance(result.sharpe_observed, float)

    def test_high_skewness(self):
        rng = np.random.default_rng(42)
        returns = rng.gamma(2, 0.01, 252) - 0.01
        result = probabilistic_sharpe_ratio(returns, 0.0)
        skew = result.skewness
        self.assertGreater(abs(skew), 0)

    def test_high_kurtosis(self):
        rng = np.random.default_rng(42)
        t_samples = rng.standard_t(df=3, size=252) * 0.005
        result = probabilistic_sharpe_ratio(t_samples, 0.0)
        kurt = result.kurtosis
        self.assertGreater(kurt, 0)

    def test_benchmark_higher_than_observed(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 252)
        result = probabilistic_sharpe_ratio(returns, sharpe_benchmark=5.0)
        self.assertLess(result.psr, 0.5)
        self.assertFalse(result.is_significant)

    def test_result_fields(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        result = probabilistic_sharpe_ratio(returns, 0.5, 365)
        self.assertIsInstance(result.psr, float)
        self.assertIsInstance(result.sharpe_observed, float)
        self.assertIsInstance(result.is_significant, bool)
        self.assertEqual(result.n_observations, 100)
        self.assertEqual(result.sharpe_benchmark, 0.5)


class TestDeflatedSharpeRatio(unittest.TestCase):
    """Tests for deflated_sharpe_ratio()."""

    def test_single_trial_dsr_equals_psr(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.015, 252)
        dsr_result = deflated_sharpe_ratio(returns, num_trials=1)
        psr_result = probabilistic_sharpe_ratio(returns, 0.0)
        self.assertAlmostEqual(dsr_result.dsr, psr_result.psr, places=10)
        self.assertEqual(dsr_result.num_independent_trials, 1)

    def test_high_sharpe_survives_multiple_testing(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.002, 0.015, 500)
        result = deflated_sharpe_ratio(returns, num_trials=5)
        self.assertGreater(result.dsr, 0.5)

    def test_many_trials_reduces_dsr(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.02, 100)
        dsr_1 = deflated_sharpe_ratio(returns, num_trials=1).dsr
        dsr_1k = deflated_sharpe_ratio(returns, num_trials=1000).dsr
        self.assertGreaterEqual(dsr_1, dsr_1k)

    def test_num_trials_one(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        result = deflated_sharpe_ratio(returns, num_trials=1)
        self.assertEqual(result.num_trials, 1)
        self.assertEqual(result.num_independent_trials, 1)

    def test_correlation_reduces_independent_trials(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        low_corr = deflated_sharpe_ratio(returns, num_trials=10, correlation=0.1)
        high_corr = deflated_sharpe_ratio(returns, num_trials=10, correlation=0.9)
        self.assertLess(high_corr.num_independent_trials, low_corr.num_independent_trials)

    def test_result_fields(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        result = deflated_sharpe_ratio(returns, num_trials=10)
        self.assertIsInstance(result.dsr, float)
        self.assertIsInstance(result.sharpe_threshold, float)
        self.assertIsInstance(result.is_significant, bool)
        self.assertEqual(result.num_trials, 10)


class TestValidateBacktestMetrics(unittest.TestCase):
    """Tests for validate_backtest_metrics()."""

    def test_valid_strategy_returns_report(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.015, 252)
        report = validate_backtest_metrics("TestStrat", returns)
        self.assertEqual(report.strategy_name, "TestStrat")
        self.assertIsNotNone(report.psr)
        self.assertIsNone(report.dsr)
        self.assertGreater(report.sharpe_annualized, 0)

    def test_with_multiple_trials_includes_dsr(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.015, 252)
        report = validate_backtest_metrics("TestStrat", returns, num_trials=10)
        self.assertIsNotNone(report.dsr)

    def test_small_sample_adds_insufficient_note(self):
        returns = np.array([0.01, -0.02])
        report = validate_backtest_metrics("Small", returns)
        notes = " ".join(report.notes).lower()
        self.assertIn("insufficient", notes)

    def test_marginal_sample_adds_bootstrap_note(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 50)
        report = validate_backtest_metrics("Marginal", returns)
        notes = " ".join(report.notes).lower()
        self.assertIn("marginal", notes)

    def test_high_skewness_note(self):
        rng = np.random.default_rng(42)
        returns = rng.gamma(2, 0.01, 200) - 0.01
        report = validate_backtest_metrics("Skewed", returns)
        notes = " ".join(report.notes).lower()
        self.assertIn("skewness", notes)

    def test_notes_list_not_empty(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.015, 252)
        report = validate_backtest_metrics("Test", returns)
        self.assertGreater(len(report.notes), 0)


class TestPsrVsSharpe(unittest.TestCase):
    """Tests for psr_vs_sharpe()."""

    def test_returns_array_of_correct_length(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        sr_range = np.linspace(0, 2, 20)
        results = psr_vs_sharpe(returns, sr_range)
        self.assertEqual(len(results), 20)

    def test_monotonically_decreasing(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 100)
        sr_range = np.linspace(0, 2, 10)
        results = psr_vs_sharpe(returns, sr_range)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i + 1], results[i])

    def test_empty_returns_zeros(self):
        results = psr_vs_sharpe(np.array([]), np.linspace(0, 1, 5))
        self.assertTrue(np.all(results == 0.0))

    def test_short_returns_zeros(self):
        results = psr_vs_sharpe(np.array([1.0, 2.0]), np.linspace(0, 1, 5))
        self.assertTrue(np.all(results == 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
