#!/usr/bin/env python3
"""Tests: MacroRegimeDetector — GDP/inflation quadrant-based regime detection."""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.engine.regime.macro_regime import MacroRegimeDetector
from quant_nanggroe.engine.regime.hmm_detector import Regime, RegimeState


class TestMacroRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = MacroRegimeDetector()

    def test_default_quadrants(self):
        expected = ["GROWTH_INFLATION", "GROWTH_DEFLATION", "RECESSION_INFLATION", "RECESSION_DEFLATION"]
        self.assertEqual(self.detector.quadrants, expected)

    def test_growth_inflation_returns_bull_growth_inflation(self):
        result = self.detector.predict(gdp_growth=2.5, inflation=3.0)
        self.assertEqual(result.regime, Regime.BULL)
        self.assertAlmostEqual(result.confidence, 0.7)
        self.assertEqual(result.features["quadrant"], "GROWTH_INFLATION")

    def test_growth_deflation_returns_bull_growth_deflation(self):
        result = self.detector.predict(gdp_growth=2.0, inflation=1.5)
        self.assertEqual(result.regime, Regime.BULL)
        self.assertAlmostEqual(result.confidence, 0.8)
        self.assertEqual(result.features["quadrant"], "GROWTH_DEFLATION")

    def test_recession_inflation_returns_crisis(self):
        result = self.detector.predict(gdp_growth=-1.0, inflation=3.5)
        self.assertEqual(result.regime, Regime.CRISIS)
        self.assertAlmostEqual(result.confidence, 0.75)
        self.assertEqual(result.features["quadrant"], "RECESSION_INFLATION")

    def test_recession_deflation_returns_bear(self):
        result = self.detector.predict(gdp_growth=-0.5, inflation=1.0)
        self.assertEqual(result.regime, Regime.BEAR)
        self.assertAlmostEqual(result.confidence, 0.65)
        self.assertEqual(result.features["quadrant"], "RECESSION_DEFLATION")

    def test_zero_gdp_growth_positive(self):
        """GDP=0 is not >0, so it should fall to recession/deflation."""
        result = self.detector.predict(gdp_growth=0.0, inflation=1.0)
        self.assertEqual(result.regime, Regime.BEAR)

    def test_inflation_exactly_2(self):
        """Inflation=2.0: not >2.0, so it's NOT 'high'."""
        result = self.detector.predict(gdp_growth=2.0, inflation=2.0)
        self.assertEqual(result.regime, Regime.BULL)
        self.assertEqual(result.features["quadrant"], "GROWTH_DEFLATION")

    def test_features_contains_gdp_and_inflation(self):
        result = self.detector.predict(gdp_growth=1.5, inflation=2.5)
        self.assertAlmostEqual(result.features["gdp_growth"], 1.5)
        self.assertAlmostEqual(result.features["inflation"], 2.5)

    def test_is_regime_state(self):
        result = self.detector.predict(gdp_growth=3.0, inflation=0.5)
        self.assertIsInstance(result, RegimeState)
        self.assertEqual(result.method, "macro")

    def test_negative_gdp_high_inflation_is_crisis(self):
        result = self.detector.predict(gdp_growth=-2.0, inflation=5.0)
        self.assertEqual(result.regime, Regime.CRISIS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
