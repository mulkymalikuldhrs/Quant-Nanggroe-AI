#!/usr/bin/env python3
"""Tests: CorrelationRegimeDetector — correlation-based regime detection."""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np

from quant_nanggroe.engine.regime.correlation_regime import CorrelationRegimeDetector
from quant_nanggroe.engine.regime.hmm_detector import Regime, RegimeState


class TestCorrelationRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = CorrelationRegimeDetector(window=63)

    def test_default_params(self):
        self.assertEqual(self.detector.window, 63)

    def test_insufficient_data_returns_sideways(self):
        returns = np.random.randn(10, 3)
        result = self.detector.predict(returns)
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.method, "correlation")

    def test_single_asset_returns_sideways_with_confidence(self):
        returns = np.random.randn(100, 1)
        result = self.detector.predict(returns)
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertEqual(result.confidence, 0.5)

    def test_high_correlation_detects_crisis(self):
        np.random.seed(42)
        n = 100
        common = np.random.randn(n)
        returns = np.column_stack([common * 0.8 + np.random.randn(n) * 0.2 for _ in range(3)])
        result = self.detector.predict(returns)
        self.assertEqual(result.regime, Regime.CRISIS)
        self.assertAlmostEqual(result.confidence, 0.8)

    def test_moderate_correlation_detects_bear(self):
        np.random.seed(42)
        n = 100
        common = np.random.randn(n) * 0.5
        returns = np.column_stack([common + np.random.randn(n) * 0.5 for _ in range(3)])
        result = self.detector.predict(returns)
        self.assertIn(result.regime, (Regime.BEAR, Regime.CRISIS))

    def test_low_correlation_detects_bull(self):
        np.random.seed(42)
        n = 100
        returns = np.random.randn(n, 3)
        result = self.detector.predict(returns)
        self.assertEqual(result.regime, Regime.BULL)

    def test_avg_correlation_in_features(self):
        np.random.seed(42)
        returns = np.random.randn(100, 3)
        result = self.detector.predict(returns)
        self.assertIn("avg_correlation", result.features)
        self.assertIn("n_assets", result.features)
        self.assertEqual(result.features["n_assets"], 3)

    def test_custom_window(self):
        detector = CorrelationRegimeDetector(window=20)
        self.assertEqual(detector.window, 20)
        returns = np.random.randn(10, 2)
        result = detector.predict(returns)
        self.assertEqual(result.regime, Regime.SIDEWAYS)

    def test_many_assets(self):
        np.random.seed(42)
        returns = np.random.randn(100, 10)
        result = self.detector.predict(returns)
        self.assertIsInstance(result, RegimeState)
        self.assertEqual(result.features["n_assets"], 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
