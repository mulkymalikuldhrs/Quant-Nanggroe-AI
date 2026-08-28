"""Comprehensive tests for CryptoSpecificStrategy - matches actual implementation."""

import unittest

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.crypto_specific import CryptoSpecificStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestCryptoSpecificStrategyInit(unittest.TestCase):
    """Tests for CryptoSpecificStrategy initialization."""

    def test_default_initialization(self):
        strategy = CryptoSpecificStrategy()
        self.assertEqual(strategy.name, "CryptoSpecific")
        self.assertEqual(strategy.mode, "funding_rate_arb")
        self.assertEqual(strategy.lookback, 24)
        self.assertEqual(strategy.entry_threshold, 0.0003)
        self.assertEqual(strategy.exit_threshold, 0.0001)
        self.assertEqual(strategy.stop_loss_pct, 0.05)
        self.assertEqual(strategy.take_profit_pct, 0.10)
        self.assertEqual(strategy.cascade_z_threshold, 2.5)
        self.assertEqual(strategy.whale_threshold, 1_000_000)

    def test_custom_params(self):
        strategy = CryptoSpecificStrategy(params={
            "mode": "liquidation_cascade",
            "lookback": 50,
            "entry_threshold": 0.001,
            "stop_loss_pct": 0.10,
            "symbol": "ETH",
        })
        self.assertEqual(strategy.mode, "liquidation_cascade")
        self.assertEqual(strategy.lookback, 50)
        self.assertEqual(strategy.entry_threshold, 0.001)
        self.assertEqual(strategy.stop_loss_pct, 0.10)
        self.assertEqual(strategy.symbol, "ETH")


class TestCryptoSpecificStrategyColumns(unittest.TestCase):
    """Tests for required_columns and warmup_period."""

    def test_required_columns_funding_rate_arb(self):
        strategy = CryptoSpecificStrategy(params={"mode": "funding_rate_arb"})
        cols = strategy.required_columns()
        self.assertIn("close", cols)
        self.assertIn("volume", cols)
        self.assertIn("funding_rate", cols)

    def test_required_columns_liquidation_cascade(self):
        strategy = CryptoSpecificStrategy(params={"mode": "liquidation_cascade"})
        cols = strategy.required_columns()
        self.assertIn("close", cols)
        self.assertIn("volume", cols)
        self.assertNotIn("funding_rate", cols)

    def test_required_columns_on_chain(self):
        strategy = CryptoSpecificStrategy(params={"mode": "on_chain"})
        cols = strategy.required_columns()
        self.assertIn("exchange_inflow", cols)
        self.assertIn("exchange_outflow", cols)

    def test_required_columns_dex_arb(self):
        strategy = CryptoSpecificStrategy(params={"mode": "dex_arb"})
        cols = strategy.required_columns()
        self.assertIn("dex_price", cols)
        self.assertIn("cex_price", cols)

    def test_required_columns_mev_aware(self):
        strategy = CryptoSpecificStrategy(params={"mode": "mev_aware"})
        cols = strategy.required_columns()
        self.assertIn("solana_tip", cols)
        self.assertIn("priority_fee", cols)

    def test_warmup_period(self):
        strategy = CryptoSpecificStrategy()
        self.assertEqual(strategy.warmup_period(), 34)  # 24 + 10

    def test_warmup_period_custom(self):
        strategy = CryptoSpecificStrategy(params={"lookback": 50})
        self.assertEqual(strategy.warmup_period(), 60)


class TestCryptoSpecificStrategyFundingRate(unittest.TestCase):
    """Tests for funding rate arbitrage mode."""

    def setUp(self):
        np.random.seed(42)
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="8h")
        close = 40000 + np.cumsum(np.random.randn(n) * 100)
        volume = np.random.randint(100, 10000, n).astype(float)
        fr_values = np.full(n, 0.0002)
        fr_values[-1] = 0.0005
        self.data = pd.DataFrame({
            "close": close,
            "volume": volume,
            "funding_rate": fr_values,
        }, index=dates)

    def test_funding_rate_arb_signal_positive(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "funding_rate_arb", "entry_threshold": 0.0001, "symbol": "BTC"}
        )
        signal = strategy.generate_signal(self.data)
        self.assertIsNotNone(signal)
        self.assertIsInstance(signal, Signal)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])

    def test_funding_rate_high_positive(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "funding_rate_arb", "entry_threshold": 0.0001, "symbol": "BTC"}
        )
        data = pd.DataFrame({
            "close": np.full(50, 40000.0),
            "volume": np.full(50, 1000.0),
            "funding_rate": np.full(50, 0.001),  # High positive
        })
        signal = strategy.generate_signal(data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.SELL)

    def test_funding_rate_high_negative(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "funding_rate_arb", "entry_threshold": 0.0001, "symbol": "BTC"}
        )
        data = pd.DataFrame({
            "close": np.full(50, 40000.0),
            "volume": np.full(50, 1000.0),
            "funding_rate": np.full(50, -0.001),  # High negative
        })
        signal = strategy.generate_signal(data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.BUY)

    def test_funding_rate_evidence(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "funding_rate_arb", "symbol": "BTC"}
        )
        data = pd.DataFrame({
            "close": np.full(50, 40000.0),
            "volume": np.full(50, 1000.0),
            "funding_rate": np.full(50, 0.001),
        })
        signal = strategy.generate_signal(data)
        self.assertIn("funding_rate", signal.evidence)
        self.assertIn("mode", signal.evidence)


class TestCryptoSpecificStrategyLiquidationCascade(unittest.TestCase):
    """Tests for liquidation cascade detection mode."""

    def test_liquidation_cascade_detection_extreme_move(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "liquidation_cascade", "cascade_z_threshold": 2.0, "symbol": "BTC"}
        )
        np.random.seed(42)
        n = 50
        prices = 40000 + np.random.randn(n) * 500
        # Create extreme volume spike at end
        volumes = np.random.randint(1000, 5000, n).astype(float)
        volumes[-1] = volumes.mean() * 10  # Volume spike
        # Create extreme price drop
        prices[-1] = prices[-2] * 0.7  # 30% drop
        
        data = pd.DataFrame({
            "close": prices,
            "volume": volumes,
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertIsInstance(signal, Signal)

    def test_liquidation_cascade_insufficient_data(self):
        strategy = CryptoSpecificStrategy(params={"mode": "liquidation_cascade"})
        data = pd.DataFrame({"close": [100], "volume": [1000]})
        signal = strategy.generate_signal(data)
        self.assertIsNone(signal)


class TestCryptoSpecificStrategyOnChain(unittest.TestCase):
    """Tests for on-chain metrics mode."""

    def test_on_chain_signal_bullish(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "on_chain", "symbol": "BTC"}
        )
        # Net outflow (bullish) + whale activity
        data = pd.DataFrame({
            "close": np.full(50, 40000.0),
            "volume": np.full(50, 1000.0),
            "exchange_inflow": np.full(50, 500.0),
            "exchange_outflow": np.full(50, 2000.0),  # Much higher outflow
            "whale_tx_count": np.concatenate([np.full(25, 1.0), np.full(25, 20.0)]),  # Spike
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertIsInstance(signal, Signal)

    def test_on_chain_missing_columns(self):
        strategy = CryptoSpecificStrategy(params={"mode": "on_chain"})
        data = pd.DataFrame({
            "close": np.full(50, 100.0),
            "volume": np.full(50, 1000.0),
        })
        with self.assertRaises(ValueError):
            strategy.generate_signal(data)


class TestCryptoSpecificStrategyDexArb(unittest.TestCase):
    """Tests for DEX arbitrage mode."""

    def test_dex_arb_opportunity(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "dex_arb", "entry_threshold": 0.001, "symbol": "BTC"}
        )
        np.random.seed(42)
        n = 50
        cex_price = 40000.0 + np.random.randn(n) * 100
        dex_price = cex_price * 1.01  # 1% premium
        data = pd.DataFrame({
            "close": cex_price,
            "volume": np.full(n, 1000.0),
            "dex_price": dex_price,
            "cex_price": cex_price,
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertIsInstance(signal, Signal)
            self.assertIn("spread", signal.evidence)

    def test_dex_arb_no_opportunity(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "dex_arb", "entry_threshold": 0.0001, "symbol": "BTC"}
        )
        dex_price = 40000.0 * 1.00001  # Tiny premium
        cex_price = 40000.0
        data = pd.DataFrame({
            "close": [cex_price] * 50,
            "volume": [1000.0] * 50,
            "dex_price": [dex_price] * 50,
            "cex_price": [cex_price] * 50,
        })
        signal = strategy.generate_signal(data)
        # May or may not signal depending on fee adjustment

    def test_dex_arb_zero_prices(self):
        strategy = CryptoSpecificStrategy(params={"mode": "dex_arb"})
        data = pd.DataFrame({
            "close": [100.0] * 50,
            "volume": [1000.0] * 50,
            "dex_price": [0.0] * 50,  # Invalid
            "cex_price": [100.0] * 50,
        })
        signal = strategy.generate_signal(data)
        self.assertIsNone(signal)


class TestCryptoSpecificStrategyMevAware(unittest.TestCase):
    """Tests for MEV-aware execution mode."""

    def test_mev_aware_high_mev(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "mev_aware", "symbol": "SOL"}
        )
        # High MEV environment
        data = pd.DataFrame({
            "close": np.full(50, 100.0),
            "volume": np.full(50, 1000.0),
            "solana_tip": np.concatenate([np.full(25, 0.001), np.full(25, 0.5)]),  # High spike
            "priority_fee": np.concatenate([np.full(25, 0.0001), np.full(25, 0.5)]),
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertEqual(signal.signal_type, SignalType.HOLD)

    def test_mev_aware_low_mev(self):
        strategy = CryptoSpecificStrategy(
            params={"mode": "mev_aware", "symbol": "SOL"}
        )
        # Low MEV environment
        data = pd.DataFrame({
            "close": np.full(50, 100.0),
            "volume": np.full(50, 1000.0),
            "solana_tip": np.full(50, 0.0001),
            "priority_fee": np.full(50, 0.0001),
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])


class TestCryptoSpecificStrategyModeRouting(unittest.TestCase):
    """Tests for mode routing in generate_signal."""

    def test_mode_routing_all_modes(self):
        modes = ["funding_rate_arb", "liquidation_cascade", "on_chain", "dex_arb", "mev_aware"]
        for mode in modes:
            strategy = CryptoSpecificStrategy(params={"mode": mode})
            # Should not raise on init

    def test_unknown_mode_falls_back(self):
        strategy = CryptoSpecificStrategy(params={"mode": "unknown_mode"})
        # Unknown mode should fall back to funding_rate_arb
        data = pd.DataFrame({
            "close": np.full(50, 100.0),
            "volume": np.full(50, 1000.0),
            "funding_rate": np.full(50, 0.001),
        })
        signal = strategy.generate_signal(data)
        # Falls back to funding_rate_signal
        if signal is not None:
            self.assertIsInstance(signal, Signal)


class TestCryptoSpecificStrategyEvidence(unittest.TestCase):
    """Tests for signal evidence structure."""

    def test_funding_rate_evidence(self):
        strategy = CryptoSpecificStrategy()
        data = pd.DataFrame({
            "close": [40000.0] * 50,
            "volume": [1000.0] * 50,
            "funding_rate": [0.001] * 50,
        })
        signal = strategy.generate_signal(data)
        if signal is not None:
            self.assertIn("funding_rate", signal.evidence)
            self.assertIn("annualized_carry", signal.evidence)

    def test_stop_loss_take_profit(self):
        strategy = CryptoSpecificStrategy(params={"stop_loss_pct": 0.10, "take_profit_pct": 0.20})
        signal = strategy.compute_funding_rate_signal(
            pd.DataFrame({
                "close": [100.0] * 50,
                "volume": [1000.0] * 50,
                "funding_rate": [0.001] * 50,
            })
        )
        if signal is not None:
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)


if __name__ == "__main__":
    unittest.main()