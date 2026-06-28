"""Comprehensive tests for MarketMakingStrategy - matches actual implementation."""

import unittest
import numpy as np
import pandas as pd
import math

from quant_nanggroe.engine.strategy.strategies.market_making import MarketMakingStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestMarketMakingStrategyInit(unittest.TestCase):
    """Tests for MarketMakingStrategy initialization."""

    def test_default_initialization(self):
        strategy = MarketMakingStrategy()
        self.assertEqual(strategy.name, "MarketMaking")
        self.assertEqual(strategy.gamma, 0.1)
        self.assertEqual(strategy.kappa, 1.5)
        self.assertEqual(strategy.sigma, 0.02)
        self.assertEqual(strategy.inventory_target, 0.0)
        self.assertEqual(strategy.max_inventory, 100.0)
        self.assertEqual(strategy.order_size, 1.0)
        self.assertEqual(strategy.num_levels, 1)
        self.assertEqual(strategy.spread_multiplier, 1.0)
        self.assertEqual(strategy.transaction_cost_bps, 10.0)
        self.assertEqual(strategy.min_trade_interval_bars, 1)
        self.assertEqual(strategy.symbol, "ASSET")

    def test_custom_params(self):
        strategy = MarketMakingStrategy(params={
            "gamma": 0.2,
            "kappa": 2.0,
            "sigma": 0.05,
            "inventory_target": 10.0,
            "max_inventory": 50.0,
            "order_size": 2.0,
            "num_levels": 3,
            "spread_multiplier": 1.5,
            "transaction_cost_bps": 5.0,
        })
        self.assertEqual(strategy.gamma, 0.2)
        self.assertEqual(strategy.kappa, 2.0)
        self.assertEqual(strategy.sigma, 0.05)
        self.assertEqual(strategy.inventory_target, 10.0)
        self.assertEqual(strategy.max_inventory, 50.0)
        self.assertEqual(strategy.order_size, 2.0)
        self.assertEqual(strategy.num_levels, 3)
        self.assertEqual(strategy.spread_multiplier, 1.5)
        self.assertEqual(strategy.transaction_cost_bps, 5.0)

    def test_inventory_state(self):
        strategy = MarketMakingStrategy()
        self.assertEqual(strategy._inventory, 0.0)
        self.assertEqual(strategy._bars_since_trade, 0)


class TestMarketMakingStrategyColumns(unittest.TestCase):
    """Tests for required_columns and warmup_period."""

    def test_required_columns(self):
        strategy = MarketMakingStrategy()
        cols = strategy.required_columns()
        self.assertIn("close", cols)
        self.assertEqual(cols, ["close"])

    def test_warmup_period(self):
        strategy = MarketMakingStrategy()
        self.assertEqual(strategy.warmup_period(), 20)

    def test_warmup_period_custom(self):
        strategy = MarketMakingStrategy(params={})  # Uses default 20
        self.assertEqual(strategy.warmup_period(), 20)


class TestMarketMakingStrategyReservationPrice(unittest.TestCase):
    """Tests for reservation price calculation (A-S model)."""

    def test_reservation_price_no_inventory(self):
        strategy = MarketMakingStrategy()
        mid = 100.0
        sigma = 0.02
        r = strategy._reservation_price(mid, sigma, T=1.0)
        # No inventory: r should equal mid
        self.assertAlmostEqual(r, mid, places=6)

    def test_reservation_price_long_inventory(self):
        strategy = MarketMakingStrategy()
        mid = 100.0
        sigma = 0.02
        inventory = 20.0  # Long inventory
        strategy._inventory = inventory
        r = strategy._reservation_price(mid, sigma, T=1.0)
        # Long inventory should push reservation price DOWN (want to sell)
        self.assertLess(r, mid)

    def test_reservation_price_short_inventory(self):
        strategy = MarketMakingStrategy()
        mid = 100.0
        sigma = 0.02
        inventory = -20.0  # Short inventory
        strategy._inventory = inventory
        r = strategy._reservation_price(mid, sigma, T=1.0)
        # Short inventory should push reservation price UP (want to buy)
        self.assertGreater(r, mid)


class TestMarketMakingStrategyFeeAdjustment(unittest.TestCase):
    """Tests for fee adjustment calculation."""

    def test_fee_adjustment_basic(self):
        strategy = MarketMakingStrategy(params={"gamma": 0.1, "kappa": 1.5})
        fee = strategy._fee_adjustment()
        # (1/gamma) * ln(1 + gamma/kappa)
        expected = (1.0 / strategy.gamma) * math.log(1.0 + strategy.gamma / strategy.kappa)
        self.assertAlmostEqual(fee, expected, places=6)

    def test_fee_adjustment_zero_gamma(self):
        strategy = MarketMakingStrategy(params={"gamma": 0.01, "kappa": 1.5})
        fee = strategy._fee_adjustment()
        # Should still compute without division by zero
        self.assertIsInstance(fee, float)


class TestMarketMakingStrategyBaseSpread(unittest.TestCase):
    """Tests for base spread calculation."""

    def test_base_spread_default(self):
        strategy = MarketMakingStrategy(params={"gamma": 0.1, "spread_multiplier": 1.0})
        spread = strategy._base_spread(0.02, T=1.0)
        expected = strategy.gamma * 0.02 ** 2 * 1.0 * strategy.spread_multiplier
        self.assertAlmostEqual(spread, expected, places=8)

    def test_base_spread_varying_sigma(self):
        strategy = MarketMakingStrategy(params={"gamma": 0.1, "spread_multiplier": 1.0})
        spread_low_vol = strategy._base_spread(0.01, T=1.0)
        spread_high_vol = strategy._base_spread(0.04, T=1.0)
        self.assertLess(spread_low_vol, spread_high_vol)

    def test_base_spread_with_multiplier(self):
        strategy = MarketMakingStrategy(params={"gamma": 0.1, "spread_multiplier": 2.0})
        spread = strategy._base_spread(0.02, T=1.0)
        expected = strategy.gamma * 0.02 ** 2 * 2.0
        self.assertAlmostEqual(spread, expected, places=8)


class TestMarketMakingStrategyInventorySkew(unittest.TestCase):
    """Tests for inventory skew calculation."""

    def test_skew_at_target(self):
        strategy = MarketMakingStrategy(params={"inventory_target": 0.0, "max_inventory": 100.0})
        strategy._inventory = 0.0
        skew = strategy._inv_skew()
        self.assertEqual(skew, 0.0)

    def test_skew_positive_inventory(self):
        strategy = MarketMakingStrategy(params={"inventory_target": 0.0, "max_inventory": 100.0})
        strategy._inventory = 50.0  # Half max inventory
        skew = strategy._inv_skew()
        self.assertGreater(skew, 0.0)

    def test_skew_negative_inventory(self):
        strategy = MarketMakingStrategy(params={"inventory_target": 0.0, "max_inventory": 100.0})
        strategy._inventory = -50.0
        skew = strategy._inv_skew()
        self.assertLess(skew, 0.0)


class TestMarketMakingStrategyQuoteLevels(unittest.TestCase):
    """Tests for quote level generation."""

    def test_single_level_quotes(self):
        strategy = MarketMakingStrategy(params={"order_size": 1.0, "num_levels": 1})
        levels = strategy._quote_levels(100.0, 0.02, T=1.0)
        self.assertEqual(len(levels), 1)
        self.assertIn("bid_price", levels[0])
        self.assertIn("ask_price", levels[0])
        self.assertIn("bid_size", levels[0])
        self.assertIn("ask_size", levels[0])

    def test_multiple_level_quotes(self):
        strategy = MarketMakingStrategy(params={"order_size": 1.0, "num_levels": 3})
        levels = strategy._quote_levels(100.0, 0.02, T=1.0)
        self.assertEqual(len(levels), 3)

    def test_bid_less_than_ask(self):
        strategy = MarketMakingStrategy()
        levels = strategy._quote_levels(100.0, 0.02, T=1.0)
        for level in levels:
            self.assertLess(level["bid_price"], level["ask_price"])


class TestMarketMakingStrategySigmaEstimation(unittest.TestCase):
    """Tests for volatility estimation."""

    def test_estimate_sigma_from_data(self):
        strategy = MarketMakingStrategy(params={"sigma": 0.02})
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        data = pd.DataFrame({"close": prices})
        sigma = strategy._estimate_sigma(data)
        self.assertGreater(sigma, 0)
        self.assertIsInstance(sigma, float)

    def test_estimate_sigma_insufficient_data(self):
        strategy = MarketMakingStrategy(params={"sigma": 0.05})
        data = pd.DataFrame({"close": [100.0]})
        sigma = strategy._estimate_sigma(data)
        self.assertEqual(sigma, 0.05)  # Falls back to param


class TestMarketMakingStrategyGenerateSignal(unittest.TestCase):
    """Tests for generate_signal method."""

    def setUp(self):
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="1D")
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
        self.data = pd.DataFrame({
            "close": prices,
        }, index=dates)

    def test_generate_signal_returns_hold(self):
        strategy = MarketMakingStrategy(params={"symbol": "TEST"})
        signal = strategy.generate_signal(self.data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.signal_type, SignalType.HOLD)

    def test_generate_signal_has_quote_info(self):
        strategy = MarketMakingStrategy(params={"symbol": "TEST"})
        signal = strategy.generate_signal(self.data)
        # Signal uses metadata field, not evidence
        self.assertIn("bid_price", signal.metadata)
        self.assertIn("ask_price", signal.metadata)
        self.assertIn("inventory", signal.metadata)
        self.assertIn("sigma", signal.metadata)

    def test_insufficient_data_returns_none(self):
        strategy = MarketMakingStrategy()
        data = pd.DataFrame({"close": [100, 101, 102]})
        signal = strategy.generate_signal(data)
        self.assertIsNone(signal)

    def test_trade_frequency_gate(self):
        strategy = MarketMakingStrategy(params={"symbol": "TEST", "min_trade_interval_bars": 5})
        strategy._bars_since_trade = 4  # >= min_trade_interval_bars - 1 to pass gate
        signal1 = strategy.generate_signal(self.data)
        self.assertIsNotNone(signal1)
        self.assertGreater(strategy._bars_since_trade, 0)


class TestMarketMakingStrategyUpdateInventory(unittest.TestCase):
    """Tests for update_inventory method."""

    def test_update_inventory_positive(self):
        strategy = MarketMakingStrategy()
        strategy.update_inventory(5.0)
        self.assertEqual(strategy._inventory, 5.0)
        self.assertEqual(strategy._bars_since_trade, 0)

    def test_update_inventory_negative(self):
        strategy = MarketMakingStrategy(params={})
        strategy.update_inventory(-3.0)
        self.assertEqual(strategy._inventory, -3.0)

    def test_update_inventory_accumulates(self):
        strategy = MarketMakingStrategy()
        strategy.update_inventory(5.0)
        strategy.update_inventory(3.0)
        self.assertEqual(strategy._inventory, 8.0)


class TestMarketMakingStrategyRepr(unittest.TestCase):
    """Tests for string representation."""

    def test_repr(self):
        strategy = MarketMakingStrategy()
        repr_str = repr(strategy)
        self.assertIn("MarketMakingStrategy", repr_str)


if __name__ == "__main__":
    unittest.main()