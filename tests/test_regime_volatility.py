#!/usr/bin/env python3
"""Tests: VolatilityRegimeDetector — clustering-based volatility regime detection."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np

from quant_nanggroe.engine.regime.hmm_detector import Regime, RegimeState
from quant_nanggroe.engine.regime.volatility_clustering import VolatilityRegimeDetector


class TestVolatilityRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = VolatilityRegimeDetector(lookback=21)

    def test_default_params(self):
        self.assertEqual(self.detector.lookback, 21)
        self.assertFalse(self.detector.is_fitted)
        self.assertEqual(self.detector.historical_vols, [])

    def test_insufficient_data_returns_low_vol(self):
        result = self.detector.predict([0.01, 0.02])
        self.assertEqual(result.regime, Regime.LOW_VOL)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.method, "volatility")

    def test_fit_insufficient_data(self):
        result = self.detector.fit([0.01, 0.02])
        self.assertFalse(self.detector.is_fitted)
        self.assertIs(result, self.detector)

    def test_fit_with_sufficient_data(self):
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        self.detector.fit(returns)
        self.assertTrue(self.detector.is_fitted)
        self.assertGreater(len(self.detector.historical_vols), 0)

    def test_predict_high_vol(self):
        np.random.seed(42)
        low_vol = list(np.random.normal(0, 0.01, 100))
        self.detector.fit(low_vol)
        high_vol_returns = list(np.random.normal(0, 0.05, 30))
        result = self.detector.predict(high_vol_returns)
        self.assertEqual(result.regime, Regime.HIGH_VOL)
        self.assertGreater(result.confidence, 0.5)

    def test_predict_low_vol(self):
        np.random.seed(42)
        normal_vol = list(np.random.normal(0, 0.02, 100))
        self.detector.fit(normal_vol)
        low_vol_returns = list(np.random.normal(0, 0.005, 30))
        result = self.detector.predict(low_vol_returns)
        self.assertEqual(result.regime, Regime.LOW_VOL)

    def test_predict_sideways(self):
        np.random.seed(42)
        normal_vol = list(np.random.normal(0, 0.02, 100))
        self.detector.fit(normal_vol)
        similar_vol_returns = list(np.random.normal(0, 0.02, 30))
        result = self.detector.predict(similar_vol_returns)
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertAlmostEqual(result.confidence, 0.5)

    def test_predict_without_fit_fits_automatically(self):
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        result = self.detector.predict(returns)
        self.assertTrue(self.detector.is_fitted)
        self.assertIn(result.regime, (Regime.SIDEWAYS, Regime.HIGH_VOL, Regime.LOW_VOL))

    def test_current_vol_in_features(self):
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        result = self.detector.predict(returns)
        self.assertIn("current_vol", result.features)
        self.assertIn("z_score", result.features)

    def test_custom_lookback(self):
        detector = VolatilityRegimeDetector(lookback=10)
        self.assertEqual(detector.lookback, 10)
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 50))
        result = detector.predict(returns)
        self.assertIsInstance(result, RegimeState)

    def test_fit_chaining(self):
        detector = VolatilityRegimeDetector(lookback=10)
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 50))
        result = detector.fit(returns)
        self.assertIs(result, detector)


if __name__ == "__main__":
    unittest.main(verbosity=2)
