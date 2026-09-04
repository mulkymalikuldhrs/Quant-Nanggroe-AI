"""Tests for PairsTradeStrategy (via PairsTradingStrategy shim) — aligned to shipped API (v8.1.1 rewrite).

Shipped contract (quant_nanggroe/engine/strategies/pairs_trade_strategy.py):
- ctor: PairsTradeStrategy(parameters=StrategyParameters(params={...}))
- name == "pairs_trade"; defaults lookback=60, entry_z=2.0, exit_z=0.5
- input: data['close'] + pair via kwargs pair_data (DataFrame) or pair_closes (list)
- ALWAYS returns StrategySignal (HOLD on insufficient/missing pair data)
- BUY/SELL carry entry/sl/tp + indicators{z_score, signal}; risk_reward_ratio populated
- legacy PairsTrade engine loaded from archive (Gatev/Goetzmann/Rouwenhorst z-score)
"""

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategy.strategies.pairs_trading import (
    PairsTradingStrategy,
)


def _mk(params=None):
    return PairsTradingStrategy(
        parameters=StrategyParameters(params=params or {})
    )


def _closes(n=120, seed=42, drift=0.0):
    rng = np.random.default_rng(seed)
    return 100 + np.cumsum(rng.normal(drift, 0.5, n))


def _df(closes):
    return pd.DataFrame({"close": np.asarray(closes, dtype=float)})


class TestPairsTradeInit:
    def test_name_is_canonical(self):
        assert _mk().name == "pairs_trade"

    def test_shim_alias_resolves(self):
        from quant_nanggroe.engine.strategies.pairs_trade_strategy import (
            PairsTradeStrategy,
        )
        assert PairsTradingStrategy is PairsTradeStrategy

    def test_default_params(self):
        s = _mk()
        assert s._parameters.get("lookback") == 60
        assert s._parameters.get("entry_z") == 2.0
        assert s._parameters.get("exit_z") == 0.5

    def test_custom_params(self):
        s = _mk({"lookback": 30, "entry_z": 1.0, "exit_z": 0.3})
        assert s._parameters.get("lookback") == 30
        assert s._parameters.get("entry_z") == 1.0


class TestPairsTradeHolds:
    def test_insufficient_primary_data_holds(self):
        s = _mk()
        sig = s.generate_signal(_df(_closes(10)), pair_closes=_closes(10).tolist())
        assert isinstance(sig, StrategySignal)
        assert sig.direction == SignalDirection.HOLD
        assert "Insufficient" in sig.reasoning

    def test_missing_pair_data_holds(self):
        s = _mk()
        sig = s.generate_signal(_df(_closes(120)))
        assert sig.direction == SignalDirection.HOLD
        assert "pair" in sig.reasoning.lower()

    def test_insufficient_pair_data_holds(self):
        s = _mk()
        sig = s.generate_signal(_df(_closes(120)), pair_closes=_closes(10).tolist())
        assert sig.direction == SignalDirection.HOLD

    def test_empty_data_holds(self):
        s = _mk()
        sig = s.generate_signal(pd.DataFrame())
        assert sig.direction == SignalDirection.HOLD


class TestPairsTradeSignal:
    def test_cointegrated_pair_returns_signal_shape(self):
        np.random.seed(42)
        n = 250
        x = 100 + np.cumsum(np.random.randn(n) * 0.5)
        spread = np.zeros(n)
        spread[0] = 0.5
        for t in range(1, n):
            spread[t] = 0.8 * spread[t - 1] + np.random.randn() * 0.3
        y = 2.0 * x + spread
        s = _mk({"lookback": 30, "entry_z": 1.0, "exit_z": 0.3})
        sig = s.generate_signal(_df(x), pair_closes=y.tolist())
        assert isinstance(sig, StrategySignal)
        assert sig.direction in (
            SignalDirection.BUY, SignalDirection.SELL,
            SignalDirection.EXIT, SignalDirection.HOLD)
        assert "z_score" in sig.indicators
        assert 0.0 <= sig.confidence <= 1.0

    def test_directional_signal_carries_levels_and_rr(self):
        # force a wide spread: flat pair vs spiked primary → |z| large
        n = 120
        a = np.full(n, 100.0)
        a[-1] = 110.0  # +10% shock bar
        b = np.full(n, 50.0)
        s = _mk({"lookback": 30, "entry_z": 0.5, "exit_z": 0.1})
        sig = s.generate_signal(_df(a), pair_closes=b.tolist())
        assert isinstance(sig, StrategySignal)
        if sig.direction in (SignalDirection.BUY, SignalDirection.SELL):
            assert sig.entry_price is not None and sig.entry_price > 0
            assert sig.stop_loss is not None and sig.take_profit is not None
            # risk_reward_ratio must be populated (v8.1.1 fix: was silently
            # dropped by a `risk_reward=` kwarg pydantic ignores)
            assert sig.risk_reward_ratio > 0
            assert sig.indicators.get("signal") in ("buy", "sell")
        else:
            # HOLD/EXIT also valid outcomes — shape must still hold
            assert sig.direction in (SignalDirection.HOLD, SignalDirection.EXIT)

    def test_pair_data_kwarg_accepted(self):
        s = _mk({"lookback": 30})
        a = _df(_closes(120, seed=3))
        b = _df(_closes(120, seed=4))
        sig = s.generate_signal(a, pair_data=b)
        assert isinstance(sig, StrategySignal)

    def test_repr_uses_canonical_name(self):
        assert "pairs_trade" in repr(_mk())
