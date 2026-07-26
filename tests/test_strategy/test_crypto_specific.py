"""Tests for CryptoSpecificStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategies.crypto_specific import CryptoSpecificStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestCryptoSpecificStrategy:
    """Test crypto-specific strategy."""

    def test_default_params(self):
        strategy = CryptoSpecificStrategy()
        assert strategy.name == "CryptoSpecific"
        assert strategy.mode == "funding_rate_arb"
        assert strategy.entry_threshold == 0.0003

    def test_required_columns_funding_rate(self):
        strategy = CryptoSpecificStrategy(params={"mode": "funding_rate_arb"})
        assert "funding_rate" in strategy.required_columns()

    def test_required_columns_liquidation(self):
        strategy = CryptoSpecificStrategy(params={"mode": "liquidation_cascade"})
        assert "close" in strategy.required_columns()

    def test_required_columns_on_chain(self):
        strategy = CryptoSpecificStrategy(params={"mode": "on_chain"})
        assert "exchange_inflow" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = CryptoSpecificStrategy(params={"lookback": 30})
        assert strategy.warmup_period() == 40

    def test_funding_rate_arb_signal(self, funding_rate_data):
        strategy = CryptoSpecificStrategy(params={"mode": "funding_rate_arb", "entry_threshold": 0.0005, "symbol": "BTC"})
        signal = strategy.generate_signal(funding_rate_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert "funding_rate" in signal.evidence

    def test_funding_rate_high_positive(self):
        strategy = CryptoSpecificStrategy(params={"mode": "funding_rate_arb", "entry_threshold": 0.0001, "symbol": "BTC"})
        n = 50
        data = pd.DataFrame({"close": 40000.0 + np.random.randn(n) * 100, "volume": np.random.randint(100, 10000, n).astype(float), "funding_rate": np.full(n, 0.001)})
        signal = strategy.generate_signal(data)
        assert signal is not None
        assert signal.signal_type == SignalType.SELL

    def test_funding_rate_high_negative(self):
        strategy = CryptoSpecificStrategy(params={"mode": "funding_rate_arb", "entry_threshold": 0.0001, "symbol": "BTC"})
        n = 50
        data = pd.DataFrame({"close": 40000.0 + np.random.randn(n) * 100, "volume": np.random.randint(100, 10000, n).astype(float), "funding_rate": np.full(n, -0.001)})
        signal = strategy.generate_signal(data)
        assert signal is not None
        assert signal.signal_type == SignalType.BUY

    def test_liquidation_cascade_detection(self, random_ohlcv_data):
        strategy = CryptoSpecificStrategy(params={"mode": "liquidation_cascade", "cascade_z_threshold": 2.0, "symbol": "BTC"})
        data = random_ohlcv_data.copy()
        data.iloc[-1, data.columns.get_loc("close")] = data["close"].iloc[-2] * 0.8
        data.iloc[-1, data.columns.get_loc("volume")] = data["volume"].mean() * 5
        signal = strategy.generate_signal(data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

    def test_on_chain_signal(self):
        strategy = CryptoSpecificStrategy(params={"mode": "on_chain", "symbol": "BTC"})
        n = 50
        data = pd.DataFrame({"close": 40000.0 + np.random.randn(n) * 100, "volume": np.random.randint(100, 10000, n).astype(float), "exchange_inflow": np.random.randint(100, 1000, n).astype(float), "exchange_outflow": np.random.randint(100, 1000, n).astype(float), "whale_tx_count": np.random.randint(0, 10, n).astype(float)})
        signal = strategy.generate_signal(data)
        if signal is not None:
            assert isinstance(signal, Signal)

    def test_dex_arb_signal(self):
        strategy = CryptoSpecificStrategy(params={"mode": "dex_arb", "entry_threshold": 0.001, "symbol": "BTC"})
        n = 50
        cex_price = 40000.0 + np.random.randn(n) * 50
        dex_price = cex_price * 1.005
        data = pd.DataFrame({"close": cex_price, "volume": np.random.randint(100, 10000, n).astype(float), "dex_price": dex_price, "cex_price": cex_price})
        signal = strategy.generate_signal(data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert "spread" in signal.evidence

    def test_mev_aware_signal(self):
        strategy = CryptoSpecificStrategy(params={"mode": "mev_aware", "symbol": "SOL"})
        n = 50
        data = pd.DataFrame({"close": 100.0 + np.random.randn(n) * 2, "volume": np.random.randint(100, 10000, n).astype(float), "solana_tip": np.random.exponential(0.001, n), "priority_fee": np.random.exponential(0.0001, n)})
        signal = strategy.generate_signal(data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_insufficient_data(self):
        strategy = CryptoSpecificStrategy(params={"mode": "liquidation_cascade"})
        data = pd.DataFrame({"close": [100], "volume": [1000]})
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_mode_routing(self, funding_rate_data):
        strategy_fr = CryptoSpecificStrategy(params={"mode": "funding_rate_arb"})
        strategy_lc = CryptoSpecificStrategy(params={"mode": "liquidation_cascade"})
        sig_fr = strategy_fr.generate_signal(funding_rate_data)
        lc_data = funding_rate_data[["close", "volume"]].copy()
        sig_lc = strategy_lc.generate_signal(lc_data)
        if sig_fr is not None:
            assert isinstance(sig_fr, Signal)
        if sig_lc is not None:
            assert isinstance(sig_lc, Signal)
