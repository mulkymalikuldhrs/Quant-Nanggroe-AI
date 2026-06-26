"""Tests: AgentMarketplace — AI-Trader inspired agent registry."""
from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.agents.marketplace import AgentMarketplace, AgentListing


class TestAgentListing(unittest.TestCase):
    def test_default_signal_history_is_empty_list(self):
        listing = AgentListing(agent_id="a1", name="alice", strategy="momentum", asset_class="equity")
        self.assertEqual(listing.signal_history, [])

    def test_default_rating_is_zero(self):
        listing = AgentListing(agent_id="a1", name="alice", strategy="momentum", asset_class="equity")
        self.assertEqual(listing.rating, 0.0)

    def test_custom_signal_history(self):
        listing = AgentListing(
            agent_id="a1", name="alice", strategy="momentum", asset_class="equity",
            signal_history=[{"ts": "2024-01-01", "action": "buy"}],
            rating=4.5,
        )
        self.assertEqual(len(listing.signal_history), 1)
        self.assertEqual(listing.rating, 4.5)


class TestAgentMarketplace(unittest.TestCase):
    def setUp(self):
        self.m = AgentMarketplace()
        self.a1 = AgentListing("a1", "AlphaBot", "momentum", "equity", rating=4.8)
        self.a2 = AgentListing("a2", "BetaBot", "mean_reversion", "equity", rating=4.2)
        self.a3 = AgentListing("a3", "GammaBot", "trend", "crypto", rating=4.9)
        self.a4 = AgentListing("a4", "DeltaBot", "arbitrage", "crypto", rating=3.5)

    def test_init_empty_agents(self):
        self.assertEqual(self.m.agents, {})

    def test_register_adds_agent(self):
        self.m.register(self.a1)
        self.assertIn("a1", self.m.agents)
        self.assertEqual(self.m.agents["a1"].name, "AlphaBot")

    def test_register_multiple(self):
        self.m.register(self.a1)
        self.m.register(self.a2)
        self.assertEqual(len(self.m.agents), 2)

    def test_register_overwrites_existing(self):
        self.m.register(self.a1)
        dup = AgentListing("a1", "AlphaBotV2", "momentum", "equity", rating=5.0)
        self.m.register(dup)
        self.assertEqual(self.m.agents["a1"].rating, 5.0)
        self.assertEqual(self.m.agents["a1"].name, "AlphaBotV2")

    def test_find_by_asset_equity(self):
        self.m.register(self.a1)
        self.m.register(self.a2)
        self.m.register(self.a3)
        results = self.m.find_by_asset("equity")
        self.assertEqual(len(results), 2)
        self.assertIn(self.a1, results)
        self.assertIn(self.a2, results)

    def test_find_by_asset_crypto(self):
        self.m.register(self.a3)
        self.m.register(self.a4)
        results = self.m.find_by_asset("crypto")
        self.assertEqual(len(results), 2)
        self.assertIn(self.a3, results)
        self.assertIn(self.a4, results)

    def test_find_by_asset_returns_empty_list_for_unknown(self):
        self.m.register(self.a1)
        results = self.m.find_by_asset("forex")
        self.assertEqual(results, [])

    def test_find_top_rated_returns_sorted(self):
        self.m.register(self.a1)
        self.m.register(self.a2)
        self.m.register(self.a3)
        self.m.register(self.a4)
        top = self.m.find_top_rated(3)
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0].agent_id, "a3")  # 4.9
        self.assertEqual(top[1].agent_id, "a1")  # 4.8
        self.assertEqual(top[2].agent_id, "a2")  # 4.2

    def test_find_top_rated_default_n(self):
        self.m.register(self.a1)
        self.m.register(self.a2)
        self.m.register(self.a3)
        self.m.register(self.a4)
        top = self.m.find_top_rated()
        self.assertEqual(len(top), 4)

    def test_find_top_rated_less_than_n(self):
        self.m.register(self.a1)
        top = self.m.find_top_rated(10)
        self.assertEqual(len(top), 1)

    def test_find_top_rated_empty_marketplace(self):
        top = self.m.find_top_rated()
        self.assertEqual(top, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
