#!/usr/bin/env python3
"""Tests: MonteCarloSimulator — trade shuffle, bootstrap, parametric,
regime-aware, price path, confidence intervals, multi-metric.

Run: python3 -m unittest tests/test_monte_carlo.py -v
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest import (
    MonteCarloSimulator,
    MonteCarloResult,
)
from quant_nanggroe.engine.simulation import MultiMetricMonteCarloResult


class TestMonteCarloSimulatorInit(unittest.TestCase):
    """Tests for MonteCarloSimulator construction."""

    def test_default_params(self):
        sim = MonteCarloSimulator()
        self.assertEqual(sim.num_simulations, 1000)
        self.assertIsNone(sim.random_seed)
        self.assertEqual(sim.confidence_levels, [0.90, 0.95, 0.99])

    def test_custom_params(self):
        sim = MonteCarloSimulator(num_simulations=500, random_seed=42, confidence_levels=[0.95])
        self.assertEqual(sim.num_simulations, 500)
        self.assertEqual(sim.random_seed, 42)
        self.assertEqual(sim.confidence_levels, [0.95])

    def test_seeded_reproducibility(self):
        sim1 = MonteCarloSimulator(num_simulations=10, random_seed=42)
        sim2 = MonteCarloSimulator(num_simulations=10, random_seed=42)
        r1 = sim1.simulate_price_path(0.001, 0.02, 100, metric="total_return")
        r2 = sim2.simulate_price_path(0.001, 0.02, 100, metric="total_return")
        self.assertAlmostEqual(r1.mean_value, r2.mean_value, places=10)


class TestMonteCarloSimulateTradeShuffle(unittest.TestCase):
    """Tests for simulate_trade_shuffle()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=50, random_seed=42)

    def test_returns_monte_carlo_result(self):
        pnls = [100.0, -50.0, 200.0, -30.0, 75.0]
        result = self.sim.simulate_trade_shuffle(pnls)
        self.assertIsInstance(result, MonteCarloResult)
        self.assertEqual(result.metric_name, "total_return")

    def test_original_value_is_calculated(self):
        pnls = [100.0, -50.0, 200.0]
        result = self.sim.simulate_trade_shuffle(pnls)
        expected = (100 - 50 + 200) / 1_000_000.0
        self.assertAlmostEqual(result.original_value, expected, places=6)

    def test_empty_pnl_returns_empty_result(self):
        result = self.sim.simulate_trade_shuffle([])
        self.assertEqual(result.num_simulations, 0)
        self.assertEqual(result.original_value, 0.0)

    def test_empty_pnl_probability_of_loss_is_one(self):
        result = self.sim.simulate_trade_shuffle([])
        self.assertEqual(result.probability_of_loss, 1.0)

    def test_single_trade(self):
        result = self.sim.simulate_trade_shuffle([250.0])
        self.assertGreater(result.mean_value, 0)

    def test_all_losses(self):
        result = self.sim.simulate_trade_shuffle([-100.0, -200.0, -50.0])
        self.assertLess(result.original_value, 0)

    def test_custom_initial_capital(self):
        pnls = [100.0] * 10
        result = self.sim.simulate_trade_shuffle(pnls, initial_capital=500_000.0)
        self.assertGreater(result.original_value, 0)

    def test_metric_max_drawdown(self):
        pnls = [100.0, -500.0, 200.0]
        result = self.sim.simulate_trade_shuffle(pnls, metric="max_drawdown")
        self.assertLessEqual(result.original_value, 0)

    def test_metric_win_rate(self):
        pnls = [100.0, -50.0, 200.0, 0.0]
        result = self.sim.simulate_trade_shuffle(pnls, metric="win_rate")
        self.assertGreaterEqual(result.original_value, 0)

    def test_result_fields_present(self):
        pnls = [100.0, -50.0, 200.0]
        result = self.sim.simulate_trade_shuffle(pnls)
        self.assertIsInstance(result.p5, float)
        self.assertIsInstance(result.p95, float)
        self.assertIsInstance(result.confidence_95, tuple)
        self.assertEqual(len(result.confidence_95), 2)


class TestMonteCarloSimulateBootstrap(unittest.TestCase):
    """Tests for simulate_bootstrap()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=50, random_seed=42)

    def test_returns_monte_carlo_result(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_bootstrap(returns)
        self.assertIsInstance(result, MonteCarloResult)

    def test_empty_returns_returns_empty(self):
        result = self.sim.simulate_bootstrap(pd.Series([], dtype=float))
        self.assertEqual(result.num_simulations, 0)

    def test_constant_returns(self):
        returns = pd.Series(np.ones(50) * 0.001)
        result = self.sim.simulate_bootstrap(returns)
        self.assertIsInstance(result.mean_value, float)

    def test_block_bootstrap(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_bootstrap(returns, block_size=5)
        self.assertEqual(result.metric_name, "total_return")

    def test_single_return(self):
        result = self.sim.simulate_bootstrap(pd.Series([0.01]))
        self.assertEqual(result.num_simulations, 0)

    def test_custom_metric(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_bootstrap(returns, metric="sharpe_ratio")
        self.assertEqual(result.metric_name, "sharpe_ratio")
        self.assertIsInstance(result.original_value, float)

    def test_all_negative_returns(self):
        returns = pd.Series(np.full(50, -0.01))
        result = self.sim.simulate_bootstrap(returns)
        self.assertLess(result.original_value, 0)

    def test_return_resample_alias(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_return_resample(returns)
        self.assertIsInstance(result, MonteCarloResult)


class TestMonteCarloSimulateParametric(unittest.TestCase):
    """Tests for simulate_parametric()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=50, random_seed=42)

    def test_normal_distribution(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_parametric(returns, distribution="normal")
        self.assertIsInstance(result, MonteCarloResult)

    def test_less_than_two_returns(self):
        result = self.sim.simulate_parametric(pd.Series([0.01]))
        self.assertEqual(result.num_simulations, 0)

    def test_unknown_distribution_raises(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        with self.assertRaises(ValueError):
            self.sim.simulate_parametric(returns, distribution="unknown")

    def test_custom_n_bars(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_parametric(returns, n_bars=50)
        self.assertIsInstance(result.mean_value, float)

    def test_skew_normal_falls_back_to_normal_without_scipy(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_parametric(returns, distribution="skew_normal")
        self.assertIsInstance(result, MonteCarloResult)


class TestMonteCarloSimulateRegimeAware(unittest.TestCase):
    """Tests for simulate_regime_aware()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=30, random_seed=42)

    def test_returns_monte_carlo_result(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_regime_aware(returns)
        self.assertIsInstance(result, MonteCarloResult)

    def test_less_than_30_returns_empty(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 10))
        result = self.sim.simulate_regime_aware(returns)
        self.assertEqual(result.num_simulations, 0)

    def test_two_regimes(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_regime_aware(returns, n_regimes=2)
        self.assertIsInstance(result.mean_value, float)


class TestMonteCarloSimulatePricePath(unittest.TestCase):
    """Tests for simulate_price_path()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=50, random_seed=42)

    def test_returns_monte_carlo_result(self):
        result = self.sim.simulate_price_path(0.001, 0.02, 100)
        self.assertIsInstance(result, MonteCarloResult)

    def test_original_value_from_mean_return(self):
        result = self.sim.simulate_price_path(0.001, 0.02, 100)
        self.assertAlmostEqual(result.original_value, 0.001 * 100, places=10)

    def test_various_metrics(self):
        for metric in ("total_return", "sharpe_ratio", "sortino_ratio", "calmar_ratio"):
            result = self.sim.simulate_price_path(0.001, 0.02, 100, metric=metric)
            self.assertIsInstance(result, MonteCarloResult)

    def test_zero_mean_return(self):
        result = self.sim.simulate_price_path(0.0, 0.02, 100)
        self.assertAlmostEqual(result.original_value, 0.0, places=10)

    def test_zero_volatility(self):
        result = self.sim.simulate_price_path(0.001, 0.0, 50)
        self.assertIsInstance(result.mean_value, float)

    def test_single_bar(self):
        result = self.sim.simulate_price_path(0.001, 0.02, 1)
        self.assertIsInstance(result, MonteCarloResult)


class TestMonteCarloMultiMetric(unittest.TestCase):
    """Tests for simulate_multi_metric()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(num_simulations=30, random_seed=42)

    def test_returns_multi_metric_result(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns)
        self.assertIsInstance(result, MultiMetricMonteCarloResult)
        self.assertIn("total_return", result.metrics)
        self.assertIn("max_drawdown", result.metrics)
        self.assertIn("sharpe_ratio", result.metrics)
        self.assertIn("sortino_ratio", result.metrics)

    def test_custom_metrics(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns, metrics=["total_return", "calmar_ratio"])
        self.assertIn("total_return", result.metrics)
        self.assertIn("calmar_ratio", result.metrics)

    def test_parametric_method(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns, method="parametric")
        self.assertIsInstance(result, MultiMetricMonteCarloResult)

    def test_unknown_method_raises(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        with self.assertRaises(ValueError):
            self.sim.simulate_multi_metric(returns, method="unknown")

    def test_num_simulations_matches(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = self.sim.simulate_multi_metric(returns)
        self.assertEqual(result.num_simulations, 30)


class TestMonteCarloConfidenceIntervals(unittest.TestCase):
    """Tests for compute_confidence_intervals()."""

    def setUp(self):
        self.sim = MonteCarloSimulator(confidence_levels=[0.90, 0.95, 0.99])

    def test_returns_dict_with_all_levels(self):
        values = np.random.default_rng(42).normal(0, 1, 1000)
        ci = self.sim.compute_confidence_intervals(values)
        self.assertIn(0.90, ci)
        self.assertIn(0.95, ci)
        self.assertIn(0.99, ci)

    def test_ci_lower_less_than_upper(self):
        values = np.random.default_rng(42).normal(0, 1, 1000)
        ci = self.sim.compute_confidence_intervals(values)
        for level, (lower, upper) in ci.items():
            self.assertLess(lower, upper, f"CI for {level} has lower >= upper")

    def test_narrower_ci_for_wider_interval(self):
        values = np.random.default_rng(42).normal(0, 1, 1000)
        ci = self.sim.compute_confidence_intervals(values)
        span_90 = ci[0.90][1] - ci[0.90][0]
        span_99 = ci[0.99][1] - ci[0.99][0]
        self.assertLess(span_90, span_99)

    def test_single_value(self):
        ci = self.sim.compute_confidence_intervals(np.array([5.0]))
        self.assertIsInstance(ci, dict)


class TestMonteCarloResultDataclass(unittest.TestCase):
    """Tests for MonteCarloResult fields."""

    def test_result_fields_accessible(self):
        result = MonteCarloResult(
            num_simulations=100,
            metric_name="total_return",
            original_value=0.15,
            mean_value=0.12,
            median_value=0.13,
            p5=-0.05,
            p25=0.05,
            p75=0.20,
            p95=0.30,
            confidence_95=(-0.05, 0.30),
            probability_of_loss=0.05,
        )
        self.assertEqual(result.num_simulations, 100)
        self.assertEqual(result.metric_name, "total_return")
        self.assertEqual(result.original_value, 0.15)
        self.assertEqual(result.probability_of_loss, 0.05)
        self.assertEqual(result.confidence_95, (-0.05, 0.30))

    def test_all_sim_values_optional(self):
        result = MonteCarloResult(
            num_simulations=10,
            metric_name="sharpe",
            original_value=1.0,
            mean_value=1.0,
            median_value=1.0,
            p5=0.5, p25=0.8, p75=1.2, p95=1.5,
            confidence_95=(0.5, 1.5),
            probability_of_loss=0.0,
        )
        self.assertIsNone(result.all_sim_values)

    def test_multi_metric_result(self):
        mm = MultiMetricMonteCarloResult(
            metrics={},
            num_simulations=50,
        )
        self.assertEqual(mm.num_simulations, 50)
        self.assertEqual(mm.metrics, {})


class TestMonteCarloRegimeDetection(unittest.TestCase):
    """Tests for internal _detect_regimes and _estimate_transition_matrix."""

    def test_detect_regimes_short_data(self):
        returns = np.array([1.0, 2.0, 3.0])
        regimes = MonteCarloSimulator._detect_regimes(returns)
        self.assertEqual(len(regimes), 3)
        self.assertTrue(np.all(regimes == 0))

    def test_detect_regimes_two_regimes(self):
        returns = np.random.default_rng(42).normal(0, 1, 100)
        regimes = MonteCarloSimulator._detect_regimes(returns, n_regimes=2)
        self.assertEqual(len(regimes), 100)
        self.assertTrue(set(regimes).issubset({0, 1}))

    def test_transition_matrix(self):
        regimes = np.array([0, 0, 1, 1, 0, 1, 0, 0, 1])
        tm = MonteCarloSimulator._estimate_transition_matrix(regimes, n_regimes=2)
        self.assertEqual(tm.shape, (2, 2))
        for row in tm:
            self.assertAlmostEqual(row.sum(), 1.0, places=6)

    def test_transition_matrix_single_regime(self):
        regimes = np.zeros(10, dtype=int)
        tm = MonteCarloSimulator._estimate_transition_matrix(regimes, n_regimes=1)
        self.assertEqual(tm.shape, (1, 1))

    def test_block_bootstrap(self):
        rng = np.random.default_rng(42)
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        resampled = MonteCarloSimulator._block_bootstrap(rng, data, block_size=2, total_length=6)
        self.assertEqual(len(resampled), 6)

    def test_empty_result_fields(self):
        result = MonteCarloSimulator(num_simulations=50, random_seed=42)._empty_result("total_return")
        self.assertEqual(result.num_simulations, 0)
        self.assertEqual(result.original_value, 0.0)
        self.assertEqual(result.p5, 0.0)
        self.assertEqual(result.p95, 0.0)
        self.assertEqual(result.probability_of_loss, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
