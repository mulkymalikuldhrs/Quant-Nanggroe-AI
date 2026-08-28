#!/usr/bin/env python3
"""Tests: HMMRegimeDetector, RegimeState, Regime — regime detection core."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import numpy as np

from quant_nanggroe.engine.regime.hmm_detector import (
    _HMM_AVAILABLE,
    _REGIME_INDEX,
    _REGIME_ORDER,
    HMMRegimeDetector,
    Regime,
    RegimeState,
)


class TestRegimeEnum(unittest.TestCase):
    def test_values(self):
        self.assertEqual(Regime.BULL.value, "BULL")
        self.assertEqual(Regime.BEAR.value, "BEAR")
        self.assertEqual(Regime.SIDEWAYS.value, "SIDEWAYS")
        self.assertEqual(Regime.CRISIS.value, "CRISIS")
        self.assertEqual(Regime.HIGH_VOL.value, "HIGH_VOL")
        self.assertEqual(Regime.LOW_VOL.value, "LOW_VOL")

    def test_membership(self):
        all_regimes = {Regime.BULL, Regime.BEAR, Regime.SIDEWAYS, Regime.CRISIS, Regime.HIGH_VOL, Regime.LOW_VOL}
        self.assertEqual(len(all_regimes), 6)

    def test_regime_order(self):
        self.assertEqual(_REGIME_ORDER, [Regime.BULL, Regime.SIDEWAYS, Regime.BEAR, Regime.CRISIS])
        self.assertEqual(_REGIME_INDEX[Regime.BULL], 0)
        self.assertEqual(_REGIME_INDEX[Regime.SIDEWAYS], 1)
        self.assertEqual(_REGIME_INDEX[Regime.BEAR], 2)
        self.assertEqual(_REGIME_INDEX[Regime.CRISIS], 3)


class TestRegimeState(unittest.TestCase):
    def test_default_construction(self):
        rs = RegimeState()
        self.assertEqual(rs.regime, Regime.SIDEWAYS)
        self.assertEqual(rs.confidence, 0.0)
        self.assertEqual(rs.method, "simple")
        self.assertEqual(rs.regime_index, 1)  # SIDEWAYS is index 1 in _REGIME_ORDER
        self.assertIsNotNone(rs.timestamp)
        self.assertIsNotNone(rs.result_id)
        self.assertEqual(rs.features, {})

    def test_is_stressed_bear(self):
        rs = RegimeState(regime=Regime.BEAR)
        self.assertTrue(rs.is_stressed)

    def test_is_stressed_crisis(self):
        rs = RegimeState(regime=Regime.CRISIS)
        self.assertTrue(rs.is_stressed)

    def test_is_not_stressed_bull(self):
        rs = RegimeState(regime=Regime.BULL)
        self.assertFalse(rs.is_stressed)

    def test_is_not_stressed_sideways(self):
        rs = RegimeState(regime=Regime.SIDEWAYS)
        self.assertFalse(rs.is_stressed)

    def test_to_api_dict(self):
        rs = RegimeState(
            regime=Regime.BULL, confidence=0.85, method="hmm",
            features={"mean_return": 0.001, "volatility": 0.02},
        )
        d = rs.to_api_dict()
        self.assertEqual(d["regime"], "BULL")
        self.assertEqual(d["confidence"], 0.85)
        self.assertEqual(d["method"], "hmm")
        self.assertEqual(d["regime_index"], 0)
        self.assertIn("features", d)
        self.assertIn("timestamp", d)
        self.assertIn("result_id", d)

    def test_to_api_dict_rounds_values(self):
        rs = RegimeState(regime=Regime.BEAR, confidence=0.12345)
        d = rs.to_api_dict()
        self.assertEqual(d["confidence"], 0.1235)

    def test_transition_probabilities_in_api_dict(self):
        rs = RegimeState(regime=Regime.BULL, transition_probabilities={"BEAR": 0.3, "BULL": 0.7})
        d = rs.to_api_dict()
        self.assertEqual(d["transition_probabilities"]["BEAR"], 0.3)

    def test_confidence_clamped(self):
        rs = RegimeState(regime=Regime.BULL, confidence=1.5)
        self.assertLessEqual(rs.confidence, 1.0)


class TestHMMRegimeDetectorInit(unittest.TestCase):
    def test_default_params(self):
        d = HMMRegimeDetector()
        self.assertEqual(d.n_regimes, 4)
        self.assertEqual(d.lookback, 252)
        self.assertEqual(d.volatility_window, 20)
        self.assertEqual(d.random_state, 42)
        self.assertFalse(d.is_fitted)
        self.assertIsNone(d.hmm)
        self.assertEqual(d.use_hmm, _HMM_AVAILABLE)

    def test_custom_params(self):
        d = HMMRegimeDetector(n_regimes=3, lookback=100, volatility_window=10, random_state=99)
        self.assertEqual(d.n_regimes, 3)
        self.assertEqual(d.lookback, 100)
        self.assertEqual(d.volatility_window, 10)
        self.assertEqual(d.random_state, 99)

    def test_stats_before_fit(self):
        d = HMMRegimeDetector()
        s = d.stats
        self.assertFalse(s["is_fitted"])
        self.assertEqual(s["use_hmm"], _HMM_AVAILABLE)
        self.assertEqual(s["n_regimes"], 4)
        self.assertEqual(s["hmm_available"], _HMM_AVAILABLE)


class TestHMMRegimeDetectorFit(unittest.TestCase):
    def test_fit_insufficient_data_returns_unfitted(self):
        d = HMMRegimeDetector(lookback=100)
        d.fit([0.01, 0.02, 0.03])
        self.assertFalse(d.is_fitted)

    def test_fit_sufficient_data_simple(self):
        d = HMMRegimeDetector(lookback=50)
        np.random.seed(42)
        returns = list(np.random.normal(0.001, 0.02, 200))
        d.fit(returns)
        self.assertTrue(d.is_fitted)

    def test_fit_with_volumes(self):
        d = HMMRegimeDetector(lookback=50)
        np.random.seed(42)
        returns = list(np.random.normal(0.001, 0.02, 200))
        volumes = list(np.random.uniform(1000, 10000, 200))
        result = d.fit(returns, volumes)
        self.assertIs(result, d)
        self.assertTrue(d.is_fitted)


class TestHMMRegimeDetectorPredict(unittest.TestCase):
    def test_predict_unfitted_short_data_returns_sideways(self):
        d = HMMRegimeDetector()
        rs = d.predict([0.01, 0.02])
        self.assertEqual(rs.regime, Regime.SIDEWAYS)
        self.assertEqual(rs.confidence, 0.0)
        self.assertEqual(rs.method, "unfitted")

    def test_predict_unfitted_long_data_fits_automatically(self):
        d = HMMRegimeDetector(lookback=50)
        np.random.seed(42)
        returns = list(np.random.normal(0.0005, 0.015, 200))
        rs = d.predict(returns)
        self.assertIsInstance(rs, RegimeState)
        self.assertIn(rs.method, ("simple", "hmm"))

    def test_predict_with_volumes(self):
        d = HMMRegimeDetector(lookback=50)
        np.random.seed(42)
        returns = list(np.random.normal(0.0005, 0.015, 200))
        volumes = list(np.random.uniform(1000, 10000, 200))
        rs = d.predict(returns, volumes)
        self.assertIsInstance(rs, RegimeState)

    def test_compute_regime_simple_crisis(self):
        d = HMMRegimeDetector()
        returns = [-0.01, -0.02, -0.03, -0.04, -0.06, -0.02, -0.01, -0.03, -0.02, -0.04]
        rs = d._compute_regime_simple(returns)
        self.assertEqual(rs.regime, Regime.CRISIS)
        self.assertGreater(rs.confidence, 0.8)

    def test_compute_regime_simple_bear_high_vol(self):
        d = HMMRegimeDetector()
        np.random.seed(42)
        returns = list(np.random.normal(-0.006, 0.04, 30))
        rs = d._compute_regime_simple(returns)
        self.assertEqual(rs.regime, Regime.BEAR)

    def test_compute_regime_simple_bull(self):
        d = HMMRegimeDetector()
        np.random.seed(42)
        returns = [0.003, 0.004, 0.003, 0.005, 0.004, 0.003, 0.006, 0.005, 0.004, 0.003]
        for _ in range(20):
            returns.append(0.003)
        rs = d._compute_regime_simple(returns)
        self.assertIn(rs.regime, (Regime.BULL, Regime.SIDEWAYS))

    def test_compute_regime_simple_insufficient_data(self):
        d = HMMRegimeDetector()
        rs = d._compute_regime_simple([0.01, 0.02, 0.03])
        self.assertEqual(rs.regime, Regime.SIDEWAYS)
        self.assertEqual(rs.confidence, 0.0)
        self.assertEqual(rs.method, "simple")

    def test_compute_adx_approx_insufficient_data(self):
        result = HMMRegimeDetector._compute_adx_approx([0.01, 0.02])
        self.assertEqual(result, 0.0)

    def test_compute_adx_approx_all_up(self):
        result = HMMRegimeDetector._compute_adx_approx([0.01, 0.02, 0.03, 0.04, 0.05])
        self.assertEqual(result, 100.0)

    def test_compute_adx_approx_mixed(self):
        result = HMMRegimeDetector._compute_adx_approx([0.01, -0.01, 0.02, -0.02, 0.03])
        self.assertGreater(result, 0)
        self.assertLessEqual(result, 100)

    def test_compute_adx_approx_zero_total(self):
        result = HMMRegimeDetector._compute_adx_approx([0.0, 0.0, 0.0])
        self.assertEqual(result, 0.0)

    def test_compute_rolling_volatility_empty(self):
        result = HMMRegimeDetector._compute_rolling_volatility([], window=20)
        self.assertEqual(result, [])

    def test_compute_rolling_volatility_short(self):
        result = HMMRegimeDetector._compute_rolling_volatility([0.01, 0.02, 0.03], window=10)
        self.assertEqual(len(result), 3)

    def test_compute_rolling_volatility_normal(self):
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        result = HMMRegimeDetector._compute_rolling_volatility(returns, window=20)
        self.assertEqual(len(result), 100)

    def test_compute_volume_change_empty(self):
        result = HMMRegimeDetector._compute_volume_change([])
        self.assertEqual(result, [])

    def test_compute_volume_change_single(self):
        result = HMMRegimeDetector._compute_volume_change([100])
        self.assertEqual(result, [0.0])

    def test_compute_volume_change_normal(self):
        result = HMMRegimeDetector._compute_volume_change([100, 110, 90])
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result[1], 0.1)
        self.assertAlmostEqual(result[2], -0.1818, places=3)

    def test_compute_volume_change_zero_prev(self):
        result = HMMRegimeDetector._compute_volume_change([0, 100])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], 0.0)

    def test_compute_simple_transitions_high_vol(self):
        d = HMMRegimeDetector()
        probs = d._compute_simple_transitions(Regime.BULL, 0.001, 0.04, 30)
        self.assertIn("CRISIS", probs)
        self.assertIn("BEAR", probs)
        total = sum(probs.values())
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_compute_simple_transitions_bull_strong_return(self):
        d = HMMRegimeDetector()
        probs = d._compute_simple_transitions(Regime.BULL, 0.01, 0.02, 40)
        self.assertIn("BULL", probs)
        total = sum(probs.values())
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_build_features(self):
        d = HMMRegimeDetector(volatility_window=20)
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        features = d._build_features(returns)
        self.assertEqual(features.shape[0], 100)
        self.assertEqual(features.shape[1], 3)

    def test_build_features_with_volumes(self):
        d = HMMRegimeDetector(volatility_window=20)
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        volumes = list(np.random.uniform(1000, 10000, 100))
        features = d._build_features(returns, volumes)
        self.assertEqual(features.shape[1], 3)

    def test_build_features_mismatched_volumes(self):
        d = HMMRegimeDetector(volatility_window=20)
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.02, 100))
        features = d._build_features(returns, [1, 2, 3])
        self.assertEqual(features.shape[1], 3)

    def test_build_state_map_no_hmm(self):
        d = HMMRegimeDetector()
        d._build_state_map()
        self.assertEqual(d._state_map, {})

    def test_stats_after_fit(self):
        d = HMMRegimeDetector(lookback=50)
        np.random.seed(42)
        returns = list(np.random.normal(0.001, 0.02, 200))
        d.fit(returns)
        s = d.stats
        self.assertTrue(s["is_fitted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
