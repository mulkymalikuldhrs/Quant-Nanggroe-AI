"""Tests for CryptoSpecificStrategy — aligned to shipped API (v8.1.0 rewrite).

Shipped contract (quant_nanggroe/engine/strategies/crypto_specific.py):
- ctor: CryptoSpecificStrategy(parameters=StrategyParameters(params={...}))
- name == "crypto_specific" (snake_case, registry convention)
- generate_signal() ALWAYS returns StrategySignal (HOLD on no-data/insufficient)
- signal fields: direction (SignalDirection), confidence, reasoning, indicators{mode,...}
- modes: funding_rate_arb, liquidation_cascade, on_chain, dex_arb, mev_aware
"""

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.crypto_specific import CryptoSpecificStrategy


def _mk(params=None):
    return CryptoSpecificStrategy(
        parameters=StrategyParameters(params=params or {})
    )


class TestCryptoSpecificStrategy:
    def test_name_is_snake_case(self):
        assert _mk().name == "crypto_specific"

    def test_default_params(self):
        s = _mk()
        assert s.mode == "funding_rate_arb"
        assert s.entry_threshold == 0.0003
        assert s.lookback == 24

    def test_funding_rate_high_positive_sells(self):
        np.random.seed(7)
        n = 50
        s = _mk({"mode": "funding_rate_arb", "entry_threshold": 0.0001})
        data = pd.DataFrame({
            "close": 40000.0 + np.random.randn(n) * 100,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "funding_rate": np.full(n, 0.001),
        })
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction == SignalDirection.SELL
        assert sig.indicators.get("mode") == "funding_rate_arb"

    def test_funding_rate_high_negative_buys(self):
        np.random.seed(7)
        n = 50
        s = _mk({"mode": "funding_rate_arb", "entry_threshold": 0.0001})
        data = pd.DataFrame({
            "close": 40000.0 + np.random.randn(n) * 100,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "funding_rate": np.full(n, -0.001),
        })
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction == SignalDirection.BUY

    def test_funding_rate_missing_column_holds(self):
        np.random.seed(7)
        n = 50
        s = _mk({"mode": "funding_rate_arb"})
        data = pd.DataFrame({
            "close": 40000.0 + np.random.randn(n) * 100,
            "volume": np.random.randint(100, 10000, n).astype(float),
        })
        sig = s.generate_signal(data)
        assert sig.direction == SignalDirection.HOLD

    def test_dex_arb_signal(self):
        np.random.seed(11)
        n = 50
        s = _mk({"mode": "dex_arb", "entry_threshold": 0.001})
        cex = 40000.0 + np.random.randn(n) * 50
        dex = cex * 1.005
        data = pd.DataFrame({
            "close": cex,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "dex_price": dex,
            "cex_price": cex,
        })
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction in (SignalDirection.BUY, SignalDirection.SELL)
        assert sig.indicators.get("mode") == "dex_arb"

    def test_mev_aware_high_tip_holds_with_confidence(self):
        np.random.seed(13)
        n = 50
        s = _mk({"mode": "mev_aware", "lookback": 10})
        tips = np.full(n, 0.001)
        tips[-1] = 0.05  # spike → z > 2
        data = pd.DataFrame({
            "close": 100.0 + np.random.randn(n) * 2,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "solana_tip": tips,
            "priority_fee": np.full(n, 0.0001),
        })
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction == SignalDirection.HOLD
        assert sig.confidence == 0.8

    def test_on_chain_signal_shape(self):
        np.random.seed(17)
        n = 50
        s = _mk({"mode": "on_chain"})
        data = pd.DataFrame({
            "close": 40000.0 + np.random.randn(n) * 100,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "exchange_inflow": np.random.randint(100, 1000, n).astype(float),
            "exchange_outflow": np.random.randint(100, 1000, n).astype(float),
            "whale_tx_count": np.random.randint(0, 10, n).astype(float),
        })
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction in (
            SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD)

    def test_insufficient_data_holds(self):
        s = _mk({"mode": "liquidation_cascade"})
        data = pd.DataFrame({"close": [100.0], "volume": [1000.0]})
        sig = s.generate_signal(data)
        assert isinstance(sig, StrategySignal)
        assert sig.direction == SignalDirection.HOLD
        assert "Insufficient" in sig.reasoning

    def test_empty_data_holds(self):
        s = _mk()
        sig = s.generate_signal(pd.DataFrame())
        assert sig.direction == SignalDirection.HOLD

    def test_mode_routing(self):
        np.random.seed(19)
        n = 50
        base = {
            "close": 40000.0 + np.random.randn(n) * 100,
            "volume": np.random.randint(100, 10000, n).astype(float),
            "funding_rate": np.full(n, 0.001),
        }
        data = pd.DataFrame(base)
        sig_fr = _mk({"mode": "funding_rate_arb", "entry_threshold": 0.0001}).generate_signal(data)
        assert sig_fr.direction == SignalDirection.SELL
        sig_lc = _mk({"mode": "liquidation_cascade"}).generate_signal(
            data[["close", "volume"]])
        assert isinstance(sig_lc, StrategySignal)

    def test_liquidation_cascade_crash(self):
        np.random.seed(23)
        n = 60
        close = 40000.0 + np.random.randn(n) * 50
        close[-1] = close[-2] * 0.8  # -20% crash bar
        vol = np.random.randint(100, 10000, n).astype(float)
        vol[-1] = vol.mean() * 5
        s = _mk({"mode": "liquidation_cascade", "cascade_z_threshold": 2.0})
        sig = s.generate_signal(pd.DataFrame({"close": close, "volume": vol}))
        assert isinstance(sig, StrategySignal)
        assert sig.direction in (
            SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD)
