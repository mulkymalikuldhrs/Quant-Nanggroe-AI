#!/usr/bin/env python3
"""Tests: RegimeStrategySelector — regime-to-strategy mapping and Kelly adjustment."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.engine.regime.strategy_selector import (
    _REGIME_LABEL_MAP,
    _RISK_MULTIPLIERS,
    REAL_QNA_STRATEGIES,
    REGIME_STRATEGY_MAP,
    RegimeStrategyMap,
    RegimeStrategySelector,
    StrategyConfig,
)


class TestConstants(unittest.TestCase):
    def test_real_qna_strategies_count(self):
        self.assertEqual(len(REAL_QNA_STRATEGIES), 3)
        self.assertIn("RegimeBased", REAL_QNA_STRATEGIES)
        self.assertIn("MeanReversion", REAL_QNA_STRATEGIES)
        self.assertIn("TrendFollow", REAL_QNA_STRATEGIES)

    def test_regime_strategy_map_keys(self):
        expected = {"bull_trend", "bear_trend", "high_volatility", "low_volatility", "sideways", "crisis", "recovery"}
        self.assertEqual(set(REGIME_STRATEGY_MAP.keys()), expected)

    def test_risk_multipliers_keys(self):
        expected = {"bull_trend", "bear_trend", "high_volatility", "low_volatility", "sideways", "crisis", "recovery"}
        self.assertEqual(set(_RISK_MULTIPLIERS.keys()), expected)

    def test_regime_label_map(self):
        self.assertEqual(_REGIME_LABEL_MAP["BULL"], "bull_trend")
        self.assertEqual(_REGIME_LABEL_MAP["BEAR"], "bear_trend")
        self.assertEqual(_REGIME_LABEL_MAP["HIGH_VOL"], "high_volatility")
        self.assertEqual(_REGIME_LABEL_MAP["LOW_VOL"], "low_volatility")
        self.assertEqual(_REGIME_LABEL_MAP["SIDEWAYS"], "sideways")
        self.assertEqual(_REGIME_LABEL_MAP["CRISIS"], "crisis")

    def test_crisis_multiplier_lowest(self):
        self.assertLess(_RISK_MULTIPLIERS["crisis"], _RISK_MULTIPLIERS["bull_trend"])


class TestStrategyConfig(unittest.TestCase):
    def test_default_construction(self):
        sc = StrategyConfig(name="Momentum")
        self.assertEqual(sc.name, "Momentum")
        self.assertEqual(sc.params, {})
        self.assertEqual(sc.weight, 1.0)
        self.assertEqual(sc.Kelly, {"fraction": 0.25})

    def test_custom_construction(self):
        sc = StrategyConfig(name="Test", params={"lookback": 10}, weight=0.5, Kelly={"fraction": 0.1})
        self.assertEqual(sc.name, "Test")
        self.assertEqual(sc.params, {"lookback": 10})
        self.assertEqual(sc.weight, 0.5)
        self.assertEqual(sc.Kelly, {"fraction": 0.1})


class TestRegimeStrategyMap(unittest.TestCase):
    def test_default_construction(self):
        rsm = RegimeStrategyMap(regime="bull_trend")
        self.assertEqual(rsm.regime, "bull_trend")
        self.assertEqual(rsm.active_strategies, [])
        self.assertEqual(rsm.risk_multiplier, 1.0)
        self.assertEqual(rsm.regime_confidence, 0.0)


class TestRegimeStrategySelectorNormalize(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeStrategySelector()

    def test_normalize_bull_label(self):
        self.assertEqual(self.selector.normalize_regime("BULL"), "bull_trend")

    def test_normalize_bear_label(self):
        self.assertEqual(self.selector.normalize_regime("BEAR"), "bear_trend")

    def test_normalize_high_vol_label(self):
        self.assertEqual(self.selector.normalize_regime("HIGH_VOL"), "high_volatility")

    def test_normalize_low_vol_label(self):
        self.assertEqual(self.selector.normalize_regime("LOW_VOL"), "low_volatility")

    def test_normalize_crisis_label(self):
        self.assertEqual(self.selector.normalize_regime("CRISIS"), "crisis")

    def test_normalize_sideways_label(self):
        self.assertEqual(self.selector.normalize_regime("SIDEWAYS"), "sideways")

    def test_normalize_lowercase_bull(self):
        self.assertEqual(self.selector.normalize_regime("bull"), "bull_trend")

    def test_normalize_whitespace(self):
        self.assertEqual(self.selector.normalize_regime("  BULL  "), "bull_trend")

    def test_normalize_unknown_returns_sideways(self):
        self.assertEqual(self.selector.normalize_regime("UNKNOWN_REGIME"), "sideways")

    def test_normalize_empty_string(self):
        self.assertEqual(self.selector.normalize_regime(""), "sideways")


class TestRegimeStrategySelectorSelect(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeStrategySelector()

    def test_select_bull_trend(self):
        result = self.selector.select_strategies("BULL", 0.8)
        self.assertEqual(result.regime, "bull_trend")
        self.assertGreater(len(result.active_strategies), 0)
        self.assertEqual(result.regime_confidence, 0.8)

    def test_select_bear_trend(self):
        result = self.selector.select_strategies("BEAR", 0.7)
        self.assertEqual(result.regime, "bear_trend")
        self.assertGreater(len(result.active_strategies), 0)

    def test_select_crisis(self):
        result = self.selector.select_strategies("CRISIS", 0.9)
        self.assertEqual(result.regime, "crisis")
        self.assertLess(result.risk_multiplier, _RISK_MULTIPLIERS["crisis"])

    def test_select_high_vol_with_high_confidence(self):
        result = self.selector.select_strategies("HIGH_VOL", 0.9)
        self.assertEqual(result.regime, "high_volatility")
        self.assertLess(result.risk_multiplier, _RISK_MULTIPLIERS["high_volatility"])

    def test_select_bear_with_high_confidence(self):
        result = self.selector.select_strategies("BEAR", 0.9)
        self.assertLess(result.risk_multiplier, _RISK_MULTIPLIERS["bear_trend"])

    def test_select_unknown_returns_sideways(self):
        result = self.selector.select_strategies("UNKNOWN", 0.5)
        self.assertEqual(result.regime, "sideways")

    def test_select_sideways(self):
        result = self.selector.select_strategies("SIDEWAYS", 0.6)
        self.assertEqual(result.regime, "sideways")
        self.assertAlmostEqual(result.risk_multiplier, _RISK_MULTIPLIERS["sideways"])

    def test_select_low_vol(self):
        result = self.selector.select_strategies("LOW_VOL", 0.7)
        self.assertEqual(result.regime, "low_volatility")

    def test_select_recovery(self):
        result = self.selector.select_strategies("recovery", 0.8)
        self.assertEqual(result.regime, "recovery")

    def test_crisis_risk_half_of_base(self):
        result = self.selector.select_strategies("CRISIS", 0.5)
        expected_base = _RISK_MULTIPLIERS["crisis"]
        expected = round(expected_base * 0.5, 4)
        self.assertEqual(result.risk_multiplier, expected)


class TestRegimeStrategySelectorGetters(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeStrategySelector()

    def test_get_regime_multiplier_bull(self):
        self.assertEqual(self.selector.get_regime_multiplier("BULL"), _RISK_MULTIPLIERS["bull_trend"])

    def test_get_regime_multiplier_crisis(self):
        self.assertEqual(self.selector.get_regime_multiplier("CRISIS"), _RISK_MULTIPLIERS["crisis"])

    def test_get_regime_multiplier_unknown(self):
        self.assertEqual(self.selector.get_regime_multiplier("UNKNOWN"), 0.6)

    def test_adjust_kelly_bull_high_confidence(self):
        result = self.selector.adjust_kelly(0.25, "BULL", 0.95)
        self.assertGreater(result, 0.25)
        self.assertLessEqual(result, 1.0)

    def test_adjust_kelly_bull_low_confidence(self):
        result = self.selector.adjust_kelly(0.25, "BULL", 0.3)
        self.assertLess(result, 0.25)

    def test_adjust_kelly_crisis(self):
        result = self.selector.adjust_kelly(0.25, "CRISIS", 0.5)
        self.assertLess(result, 0.25)

    def test_adjust_kelly_clamped_min(self):
        result = self.selector.adjust_kelly(0.001, "CRISIS", 0.3)
        self.assertGreaterEqual(result, 0.01)

    def test_adjust_kelly_clamped_max(self):
        result = self.selector.adjust_kelly(2.0, "LOW_VOL", 0.95)
        self.assertLessEqual(result, 1.0)

    def test_adjust_kelly_unknown_regime(self):
        result = self.selector.adjust_kelly(0.25, "UNKNOWN", 0.6)
        self.assertGreater(result, 0)

    def test_get_strategy_names_bull(self):
        names = self.selector.get_strategy_names("BULL")
        self.assertIn("RegimeBased", names)
        self.assertIn("TrendFollow", names)

    def test_get_strategy_names_unknown(self):
        names = self.selector.get_strategy_names("UNKNOWN")
        self.assertEqual(names, [s.name for s in REGIME_STRATEGY_MAP["sideways"]])


class TestRegimeStrategySelectorConfidenceBoundaries(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeStrategySelector()

    def test_confidence_exactly_0_5(self):
        """Boundary: confidence == 0.5 should use base multiplier (no halving)."""
        result = self.selector.select_strategies("BULL", 0.5)
        self.assertEqual(result.risk_multiplier, _RISK_MULTIPLIERS["bull_trend"])

    def test_confidence_just_below_0_5(self):
        result = self.selector.adjust_kelly(0.25, "BULL", 0.499)
        self.assertLess(result, 0.25)

    def test_confidence_just_above_0_9(self):
        result = self.selector.adjust_kelly(0.25, "BULL", 0.91)
        self.assertGreater(result, 0.25)


class TestRegimeStrategyMapInstantiation(unittest.TestCase):
    def test_with_strategies(self):
        sc = StrategyConfig("Momentum", {"lookback": 20}, weight=0.5)
        rsm = RegimeStrategyMap(
            regime="bull_trend",
            active_strategies=[sc],
            risk_multiplier=0.8,
            regime_confidence=0.75,
        )
        self.assertEqual(len(rsm.active_strategies), 1)
        self.assertEqual(rsm.active_strategies[0].name, "Momentum")
        self.assertEqual(rsm.risk_multiplier, 0.8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
