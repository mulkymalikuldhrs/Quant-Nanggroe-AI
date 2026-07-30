"""Tests: LiquidityWallProvider — Order book wall detection.

Pure logic — no external mocking required.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.providers.tradebobby.liquidity_wall_provider import (
    LiquidityWallProvider,
)


def _depth_level(price: float, qty: float) -> dict:
    return {"price": price, "qty": qty}


class TestLiquidityWallProviderInit(unittest.TestCase):
    """Provider construction & defaults."""

    def test_default_params(self):
        prov = LiquidityWallProvider()
        self.assertEqual(prov._n, 30)
        self.assertEqual(prov._threshold, 2.2)
        self.assertEqual(prov._min_freq, 0.6)

    def test_custom_params(self):
        prov = LiquidityWallProvider(n_snapshots=10, wall_threshold=3.0, min_frequency=0.5)
        self.assertEqual(prov._n, 10)
        self.assertEqual(prov._threshold, 3.0)
        self.assertEqual(prov._min_freq, 0.5)


class TestUpdateDepth(unittest.TestCase):
    """update_depth() stores snapshots."""

    def setUp(self):
        self.prov = LiquidityWallProvider(n_snapshots=10)

    def test_update_depth_stores_bids_and_asks(self):
        bids = [_depth_level(100.0, 1.0), _depth_level(99.5, 2.0)]
        asks = [_depth_level(101.0, 1.5), _depth_level(101.5, 0.5)]
        self.prov.update_depth("BTCUSD", bids, asks)
        buf = self.prov._buffers.get("BTCUSD")
        self.assertIsNotNone(buf)
        self.assertEqual(len(buf), 1)
        self.assertEqual(len(buf[0].bids), 2)
        self.assertEqual(len(buf[0].asks), 2)

    def test_update_depth_multiple_symbols_independent(self):
        self.prov.update_depth("BTCUSD", [_depth_level(100, 1)], [_depth_level(101, 1)])
        self.prov.update_depth("ETHUSD", [_depth_level(3000, 10)], [_depth_level(3010, 10)])
        self.assertEqual(len(self.prov._buffers), 2)

    def test_update_depth_limits_buffer_size(self):
        for i in range(15):
            self.prov.update_depth("TEST", [_depth_level(float(i), 1.0)], [_depth_level(float(i) + 1, 1.0)])
        self.assertEqual(len(self.prov._buffers["TEST"]), 10)

    def test_update_depth_empty_lists(self):
        self.prov.update_depth("EMPTY", [], [])
        snap = self.prov._buffers["EMPTY"][0]
        self.assertEqual(len(snap.bids), 0)
        self.assertEqual(len(snap.asks), 0)


class TestGetWalls(unittest.TestCase):
    """get_walls() wall detection logic."""

    def setUp(self):
        self.prov = LiquidityWallProvider(n_snapshots=5, wall_threshold=2.2, min_frequency=0.6)

    def test_get_walls_returns_correct_structure(self):
        for _ in range(5):
            self.prov.update_depth(
                "TEST",
                [_depth_level(100.0, 1.0), _depth_level(99.5, 2.0)],
                [_depth_level(101.0, 1.5), _depth_level(101.5, 0.5)],
            )
        result = self.prov.get_walls("TEST")
        self.assertIn("bid_walls", result)
        self.assertIn("ask_walls", result)
        self.assertIsInstance(result["bid_walls"], list)
        self.assertIsInstance(result["ask_walls"], list)

    def test_get_walls_empty_when_no_walls_exist(self):
        for _ in range(5):
            self.prov.update_depth(
                "TEST2",
                [_depth_level(100.0, 1.0), _depth_level(99.5, 1.0), _depth_level(99.0, 1.0)],
                [_depth_level(101.0, 1.0), _depth_level(101.5, 1.0), _depth_level(102.0, 1.0)],
            )
        result = self.prov.get_walls("TEST2")
        self.assertEqual(len(result["bid_walls"]), 0)
        self.assertEqual(len(result["ask_walls"]), 0)

    def test_get_walls_detects_strong_bid_wall(self):
        """Wall detection: avg_qty > 2.2x global AND freq >= 0.6."""
        for _ in range(5):
            self.prov.update_depth(
                "STRONG",
                [
                    _depth_level(100.0, 1.0),
                    _depth_level(99.5, 1.0),
                    _depth_level(99.0, 10.0),  # wall candidate: qty much higher
                ],
                [_depth_level(101.0, 1.0), _depth_level(101.5, 1.0)],
            )
        result = self.prov.get_walls("STRONG")
        self.assertEqual(len(result["bid_walls"]), 1)
        self.assertEqual(result["bid_walls"][0]["price"], 99.0)

    def test_get_walls_detects_strong_ask_wall(self):
        for _ in range(5):
            self.prov.update_depth(
                "STRONG_ASK",
                [_depth_level(100.0, 1.0), _depth_level(99.5, 1.0)],
                [
                    _depth_level(101.0, 1.0),
                    _depth_level(101.5, 1.0),
                    _depth_level(102.0, 10.0),  # wall candidate
                ],
            )
        result = self.prov.get_walls("STRONG_ASK")
        self.assertEqual(len(result["ask_walls"]), 1)
        self.assertEqual(result["ask_walls"][0]["price"], 102.0)

    def test_get_walls_strength_field_format(self):
        for _ in range(5):
            self.prov.update_depth(
                "FMT",
                [_depth_level(100.0, 1.0), _depth_level(99.0, 10.0)],
                [_depth_level(101.0, 1.0)],
            )
        result = self.prov.get_walls("FMT")
        if result["bid_walls"]:
            wall = result["bid_walls"][0]
            self.assertIn("price", wall)
            self.assertIn("qty", wall)
            self.assertIn("frequency", wall)
            self.assertIn("strength", wall)
            self.assertIsInstance(wall["price"], float)
            self.assertIsInstance(wall["qty"], float)
            self.assertIsInstance(wall["frequency"], float)
            self.assertIsInstance(wall["strength"], float)

    def test_get_walls_requires_min_frequency(self):
        """A level that appears only 1/5 times should not be a wall."""
        self.prov.update_depth("FREQ", [_depth_level(100.0, 50.0)], [_depth_level(101.0, 1.0)])
        for _ in range(4):
            self.prov.update_depth("FREQ", [_depth_level(100.0, 1.0)], [_depth_level(101.0, 1.0)])
        result = self.prov.get_walls("FREQ")
        bid_walls = result["bid_walls"]
        # The 50.0 qty at 100.0 only appears once — freq=0.2 < 0.6
        for w in bid_walls:
            self.assertNotEqual(w["price"], 100.0)


class TestGetWallsEdgeCases(unittest.TestCase):
    """Boundary conditions."""

    def setUp(self):
        self.prov = LiquidityWallProvider(n_snapshots=5)

    def test_get_walls_requires_min_two_snapshots(self):
        self.prov.update_depth("NEW", [_depth_level(100, 1)], [_depth_level(101, 1)])
        result = self.prov.get_walls("NEW")
        self.assertEqual(result["bid_walls"], [])
        self.assertEqual(result["ask_walls"], [])

    def test_get_walls_unknown_symbol_returns_empty(self):
        result = self.prov.get_walls("UNKNOWN")
        self.assertEqual(result["bid_walls"], [])
        self.assertEqual(result["ask_walls"], [])


class TestClearHistory(unittest.TestCase):
    """clear_history() resets buffer."""

    def setUp(self):
        self.prov = LiquidityWallProvider()

    def test_clear_history_removes_symbol(self):
        self.prov.update_depth("BTCUSD", [_depth_level(100, 1)], [_depth_level(101, 1)])
        self.assertIn("BTCUSD", self.prov._buffers)
        self.prov.clear_history("BTCUSD")
        self.assertNotIn("BTCUSD", self.prov._buffers)

    def test_clear_history_nonexistent_symbol_no_error(self):
        self.prov.clear_history("NONEXISTENT")

    def test_clear_history_allows_reinsertion(self):
        self.prov.update_depth("X", [_depth_level(100, 1)], [_depth_level(101, 1)])
        self.prov.clear_history("X")
        self.prov.update_depth("X", [_depth_level(200, 1)], [_depth_level(201, 1)])
        self.assertEqual(len(self.prov._buffers["X"]), 1)
        self.assertEqual(self.prov._buffers["X"][0].bids[0].price, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
