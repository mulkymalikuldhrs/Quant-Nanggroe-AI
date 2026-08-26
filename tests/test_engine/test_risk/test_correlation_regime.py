"""Tests: CorrelationRegimeDetector and CrossAssetMarginMonitor.

Run: python3 -m unittest tests/test_risk/test_correlation_regime.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np

from quant_nanggroe.engine.risk.correlation_regime import (
    CorrelationRegimeDetector,
    CrossAssetMarginMonitor,
)


class TestCorrelationRegimeDetector(unittest.TestCase):
    def test_default_params(self):
        detector = CorrelationRegimeDetector(window=30)
        self.assertEqual(detector.window, 30)

    def test_update_adds_returns(self):
        detector = CorrelationRegimeDetector(window=30)
        detector.update({"AAPL": 0.01, "MSFT": -0.005})
        self.assertIn("AAPL", detector._returns_history)
        self.assertIn("MSFT", detector._returns_history)
        self.assertEqual(len(detector._returns_history["AAPL"]), 1)

    def test_get_correlation_matrix_insufficient_data(self):
        detector = CorrelationRegimeDetector(window=30)
        detector.update({"AAPL": 0.01})
        matrix = detector.get_correlation_matrix()
        self.assertTrue(matrix.empty)

    def test_detect_low_correlation_regime(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        for _ in range(100):
            detector.update({
                "AAPL": float(rng.normal(0, 0.01)),
                "MSFT": float(rng.normal(0, 0.01)),
            })
        regime, confidence = detector.detect_regime()
        self.assertEqual(regime, "low_corr")
        self.assertGreater(confidence, 0.0)

    def test_detect_high_correlation_regime(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        common = rng.normal(0, 0.01, 100)
        for i in range(100):
            detector.update({
                "AAPL": float(common[i] * 0.8 + rng.normal(0, 0.01) * 0.2),
                "MSFT": float(common[i] * 0.8 + rng.normal(0, 0.01) * 0.2),
                "GOOG": float(common[i] * 0.8 + rng.normal(0, 0.01) * 0.2),
            })
        regime, confidence = detector.detect_regime()
        self.assertIn(regime, ("high_corr", "crisis_corr"))
        self.assertGreater(confidence, 0.6)

    def test_detect_crisis_correlation_regime(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        common = rng.normal(0, 0.01, 100)
        for i in range(100):
            common_move = common[i] * 0.95
            detector.update({
                "AAPL": float(common_move + rng.normal(0, 0.001) * 0.05),
                "MSFT": float(common_move + rng.normal(0, 0.001) * 0.05),
                "GOOG": float(common_move + rng.normal(0, 0.001) * 0.05),
                "TSLA": float(common_move + rng.normal(0, 0.001) * 0.05),
            })
        regime, confidence = detector.detect_regime()
        self.assertEqual(regime, "crisis_corr")
        self.assertGreaterEqual(confidence, 0.8)

    def test_low_correlation_margin_multiplier(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        for _ in range(100):
            detector.update({
                "AAPL": float(rng.normal(0, 0.01)),
                "MSFT": float(rng.normal(0, 0.01)),
            })
        mult = detector.get_margin_multiplier()
        self.assertEqual(mult, 1.2)

    def test_normal_correlation_margin_multiplier(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        common = rng.normal(0, 0.01, 100)
        for i in range(100):
            detector.update({
                "AAPL": float(common[i] * 0.5 + rng.normal(0, 0.01) * 0.5),
                "MSFT": float(common[i] * 0.5 + rng.normal(0, 0.01) * 0.5),
            })
        regime, _ = detector.detect_regime()
        mult = detector.get_margin_multiplier()
        self.assertEqual(regime, "normal_corr")
        self.assertEqual(mult, 1.0)

    def test_high_correlation_margin_multiplier(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        common = rng.normal(0, 0.01, 100)
        for i in range(100):
            detector.update({
                "AAPL": float(common[i] * 0.7 + rng.normal(0, 0.01) * 0.3),
                "MSFT": float(common[i] * 0.7 + rng.normal(0, 0.01) * 0.3),
                "GOOG": float(common[i] * 0.7 + rng.normal(0, 0.01) * 0.3),
            })
        mult = detector.get_margin_multiplier()
        self.assertEqual(mult, 0.6)

    def test_crisis_correlation_margin_multiplier(self):
        detector = CorrelationRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        common = rng.normal(0, 0.01, 100)
        for i in range(100):
            common_move = common[i] * 0.95
            detector.update({
                "AAPL": float(common_move),
                "MSFT": float(common_move),
                "GOOG": float(common_move),
            })
        mult = detector.get_margin_multiplier()
        self.assertEqual(mult, 0.3)

    def test_insufficient_data_returns_default_multiplier(self):
        detector = CorrelationRegimeDetector(window=30)
        mult = detector.get_margin_multiplier()
        self.assertEqual(mult, 1.0)

    def test_update_trims_to_window(self):
        detector = CorrelationRegimeDetector(window=5)
        for i in range(10):
            detector.update({"AAPL": float(i)})
        self.assertEqual(len(detector._returns_history["AAPL"]), 5)
        self.assertAlmostEqual(detector._returns_history["AAPL"][-1], 9.0)

    def test_correlation_matrix_with_two_symbols(self):
        detector = CorrelationRegimeDetector(window=30)
        for _ in range(30):
            detector.update({"AAPL": 0.01, "MSFT": 0.02})
        matrix = detector.get_correlation_matrix()
        self.assertEqual(matrix.shape, (2, 2))
        self.assertIn("AAPL", matrix.columns)
        self.assertIn("MSFT", matrix.columns)

    def test_detect_regime_no_data(self):
        detector = CorrelationRegimeDetector(window=30)
        regime, confidence = detector.detect_regime()
        self.assertEqual(regime, "normal_corr")
        self.assertEqual(confidence, 0.0)

    def test_detect_regime_single_symbol(self):
        detector = CorrelationRegimeDetector(window=30)
        for _ in range(30):
            detector.update({"AAPL": 0.01})
        regime, confidence = detector.detect_regime()
        self.assertEqual(regime, "normal_corr")
        self.assertEqual(confidence, 0.0)


class TestCrossAssetMarginMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = CrossAssetMarginMonitor()

    def test_margin_used_empty(self):
        self.assertEqual(self.monitor.margin_used(), 0.0)

    def test_margin_used_with_positions(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "entry_price": 50000, "current_price": 51000, "leverage": 2},
            "ETHUSDT": {"qty": 10.0, "entry_price": 3000, "current_price": 3100, "leverage": 1},
        })
        expected = (1.0 * 51000 / 2) + (10.0 * 3100 / 1)
        self.assertAlmostEqual(self.monitor.margin_used(), expected)

    def test_margin_available(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "leverage": 2, "entry_price": 49000},
        })
        avail = self.monitor.margin_available(100000)
        expected = 100000 - (1.0 * 50000 / 2)
        self.assertAlmostEqual(avail, expected)

    def test_margin_utilization(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "leverage": 2, "entry_price": 49000},
        })
        util = self.monitor.margin_utilization(100000)
        expected = (1.0 * 50000 / 2) / 100000
        self.assertAlmostEqual(util, expected)

    def test_margin_utilization_zero_equity(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "leverage": 1, "entry_price": 49000},
        })
        util = self.monitor.margin_utilization(0)
        self.assertEqual(util, 1.0)

    def test_margin_utilization_zero_equity_no_positions(self):
        util = self.monitor.margin_utilization(0)
        self.assertEqual(util, 0.0)

    def test_check_margin_call_no_call(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 0.1, "current_price": 50000, "leverage": 1, "entry_price": 49000},
        })
        result = self.monitor.check_margin_call(equity=100000, maintenance_margin=0.25)
        self.assertFalse(result["margin_call"])
        self.assertEqual(len(result["close_recommendations"]), 0)

    def test_check_margin_call_triggers(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 10.0, "current_price": 50000, "leverage": 1, "entry_price": 49000},
        })
        result = self.monitor.check_margin_call(equity=100000, maintenance_margin=0.25)
        self.assertTrue(result["margin_call"])
        self.assertGreater(len(result["close_recommendations"]), 0)

    def test_check_margin_call_close_recommendations(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 5.0, "current_price": 100000, "leverage": 1, "entry_price": 95000},
            "ETHUSDT": {"qty": 50.0, "current_price": 5000, "leverage": 1, "entry_price": 4800},
        })
        result = self.monitor.check_margin_call(equity=100000, maintenance_margin=0.25)
        self.assertTrue(result["margin_call"])
        # BTCUSDT (500k) should be first recommendation (larger position)
        self.assertEqual(result["close_recommendations"][0]["symbol"], "BTCUSDT")

    def test_status_output(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "leverage": 2, "entry_price": 49000},
        })
        status = self.monitor.status()
        self.assertEqual(status["num_positions"], 1)
        self.assertIn("positions", status)
        self.assertEqual(status["positions"][0]["symbol"], "BTCUSDT")

    def test_status_empty(self):
        status = self.monitor.status()
        self.assertEqual(status["num_positions"], 0)
        self.assertEqual(status["margin_used"], 0.0)

    def test_update_overwrites_positions(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "leverage": 1, "entry_price": 49000},
        })
        self.monitor.update({
            "ETHUSDT": {"qty": 10.0, "current_price": 3000, "leverage": 1, "entry_price": 2900},
        })
        self.assertEqual(self.monitor.status()["num_positions"], 1)
        self.assertNotIn("BTCUSDT", [p["symbol"] for p in self.monitor.status()["positions"]])

    def test_margin_used_zero_leverage_default(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 1.0, "current_price": 50000, "entry_price": 49000},
        })
        # leverage defaults to 1
        self.assertAlmostEqual(self.monitor.margin_used(), 50000.0)

    def test_check_margin_call_excess_calculation(self):
        self.monitor.update({
            "BTCUSDT": {"qty": 0.1, "current_price": 50000, "leverage": 1, "entry_price": 49000},
        })
        result = self.monitor.check_margin_call(equity=100000, maintenance_margin=0.25)
        used = 0.1 * 50000 / 1
        expected_excess = 100000 - used * (1 / 0.25 - 1)
        self.assertAlmostEqual(result["excess"], expected_excess)


if __name__ == "__main__":
    unittest.main(verbosity=2)
