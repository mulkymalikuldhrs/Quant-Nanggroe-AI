#!/usr/bin/env python3
"""Tests: RegimeEnsemble — weighted voting across regime detectors."""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock

from quant_nanggroe.engine.regime.ensemble import RegimeEnsemble
from quant_nanggroe.engine.regime.hmm_detector import RegimeState, Regime


class _MockDetector:
    """Minimal mock detector that returns a configurable RegimeState."""
    def __init__(self, state: RegimeState):
        self._state = state

    def predict(self, **kwargs) -> RegimeState:
        return self._state


class _FailingDetector:
    """Detector that raises on predict."""
    def predict(self, **kwargs) -> RegimeState:
        raise RuntimeError("predict failed")


class TestRegimeEnsembleInit(unittest.TestCase):
    def test_empty_detectors(self):
        ensemble = RegimeEnsemble([])
        self.assertEqual(ensemble.detectors, [])
        self.assertIn("hmm", ensemble.weights)

    def test_single_detector(self):
        d = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.8, method="hmm"))
        ensemble = RegimeEnsemble([d])
        self.assertEqual(len(ensemble.detectors), 1)


class TestRegimeEnsemblePredict(unittest.TestCase):
    def test_empty_detectors_returns_sideways(self):
        ensemble = RegimeEnsemble([])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.method, "ensemble_empty")

    def test_single_bull_detector(self):
        d = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.8, method="hmm"))
        ensemble = RegimeEnsemble([d])
        result = ensemble.predict(some_data=[1, 2, 3])
        self.assertEqual(result.regime, Regime.BULL)
        self.assertAlmostEqual(result.confidence, 0.8)
        self.assertEqual(result.method, "ensemble")

    def test_multiple_detectors_same_regime(self):
        d1 = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.9, method="hmm"))
        d2 = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.8, method="volatility"))
        ensemble = RegimeEnsemble([d1, d2])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.BULL)
        self.assertGreater(result.confidence, 0.8)

    def test_multiple_detectors_conflicting(self):
        d1 = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.9, method="hmm"))
        d2 = _MockDetector(RegimeState(regime=Regime.BEAR, confidence=0.9, method="volatility"))
        ensemble = RegimeEnsemble([d1, d2])
        result = ensemble.predict()
        # hmm has weight 0.35, volatility has 0.25, so hmm wins
        self.assertEqual(result.regime, Regime.BULL)

    def test_all_detectors_fail(self):
        d = _FailingDetector()
        ensemble = RegimeEnsemble([d])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.method, "ensemble_empty")

    def test_mixed_fail_and_success(self):
        d1 = _FailingDetector()
        d2 = _MockDetector(RegimeState(regime=Regime.CRISIS, confidence=0.85, method="macro"))
        ensemble = RegimeEnsemble([d1, d2])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.CRISIS)
        self.assertGreater(result.confidence, 0)

    def test_features_accumulated(self):
        d1 = _MockDetector(RegimeState(
            regime=Regime.BULL, confidence=0.8, method="hmm",
            features={"mean_return": 0.002, "volatility": 0.015},
        ))
        ensemble = RegimeEnsemble([d1])
        result = ensemble.predict()
        self.assertIn("mean_return", result.features)
        self.assertIn("volatility", result.features)

    def test_methods_used_in_features(self):
        d1 = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.8, method="hmm"))
        ensemble = RegimeEnsemble([d1])
        result = ensemble.predict()
        self.assertIn("methods_used", result.features)
        self.assertIn("hmm", result.features["methods_used"])

    def test_weights_influence_result(self):
        d_bull = _MockDetector(RegimeState(regime=Regime.BULL, confidence=0.9, method="hmm"))
        d_bear = _MockDetector(RegimeState(regime=Regime.BEAR, confidence=0.9, method="macro"))
        ensemble = RegimeEnsemble([d_bull, d_bear])
        # hmm weight=0.35, macro weight=0.20
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.BULL)


class TestRegimeEnsembleExtractKwargs(unittest.TestCase):
    def test_extract_matching_kwargs(self):
        def predict_func(self, returns=None, volumes=None):
            pass
        detector = type("TestDetector", (), {"predict": predict_func})()
        all_kwargs = {"returns": [1, 2, 3], "volumes": [4, 5, 6], "unused": "x"}
        result = RegimeEnsemble._extract_kwargs(detector, all_kwargs)
        self.assertEqual(set(result.keys()), {"returns", "volumes"})

    def test_extract_no_matching_kwargs(self):
        def predict_func(self, returns=None):
            pass
        detector = type("TestDetector", (), {"predict": predict_func})()
        result = RegimeEnsemble._extract_kwargs(detector, {"price": 100})
        self.assertEqual(result, {})


class TestRegimeEnsembleEdgeCases(unittest.TestCase):
    def test_detector_with_none_result(self):
        d = MagicMock()
        d.predict.return_value = None
        d.__class__.__name__ = "HMMRegimeDetector"
        ensemble = RegimeEnsemble([d])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.SIDEWAYS)
        self.assertEqual(result.confidence, 0.0)

    def test_detector_with_non_regime_result(self):
        d = MagicMock()
        d.predict.return_value = {"not": "a regime state"}
        d.__class__.__name__ = "HMMRegimeDetector"
        ensemble = RegimeEnsemble([d])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.SIDEWAYS)

    def test_detector_class_name_extraction(self):
        d = MagicMock()
        d.predict.return_value = RegimeState(regime=Regime.BEAR, confidence=0.8, method="hmm")
        d.__class__.__name__ = "HMMRegimeDetector"
        ensemble = RegimeEnsemble([d])
        result = ensemble.predict()
        self.assertEqual(result.regime, Regime.BEAR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
