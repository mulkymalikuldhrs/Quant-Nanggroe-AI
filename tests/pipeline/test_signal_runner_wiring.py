"""Tests for pipeline signal engine ↔ ProductionStrategyRunner wiring.

Covers:
  - ProductionStrategyRunner loads the full registry (not a hardcoded 4-name list)
  - UnifiedSignalEngine._try_strategies calls the real generate_signals() API
    with dict args (no dead run_strategies path, no wrong-signature fallback)
"""

from __future__ import annotations

from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
from quant_nanggroe.engine_production_bridge import Signal as BridgeSignal
from quant_nanggroe.pipeline.signal import Signal as PipelineSignal
from quant_nanggroe.pipeline.signal import UnifiedSignalEngine


def _candles(n: int = 40, price: float = 100.0) -> list[dict]:
    return [
        {"open": price, "high": price * 1.01, "low": price * 0.99, "close": price, "volume": 10.0}
        for _ in range(n)
    ]


class FakeRunner:
    """Duck-typed runner exposing ONLY the real generate_signals() API."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.strategies = {"fake": object()}
        self._loaded = True

    def generate_signals(self, market_data, prices, active_strategies=None):
        self.calls.append((market_data, prices, active_strategies))
        sym = next(iter(prices))
        return [BridgeSignal(symbol=sym, side="buy", confidence=0.9, strategy="fake", price=prices[sym], reason="test")]


def test_runner_loads_more_than_four_strategies(monkeypatch):
    # Simulate lifecycle unavailable → all registry strategies must load
    monkeypatch.setattr(ProductionStrategyRunner, "_lazy_lifecycle", lambda self: None)
    runner = ProductionStrategyRunner()
    assert len(runner.available) > 4, "registry should expose the full strategy list"
    assert len(runner.strategies) > 4, "runner must load more than the old hardcoded 4"


def test_runner_has_no_run_strategies_method():
    # The old pipeline path called a method that never existed — keep it dead.
    assert not hasattr(ProductionStrategyRunner, "run_strategies")


def test_try_strategies_calls_generate_signals_with_dict_args():
    engine = UnifiedSignalEngine()
    fake = FakeRunner()
    engine._strategy_runner = fake

    out = engine._try_strategies("BTCUSDT", {"price": 100.0, "candles": _candles()})

    # generate_signals invoked exactly once, with dict-shaped args
    assert len(fake.calls) == 1
    market_data, prices, _ = fake.calls[0]
    assert isinstance(market_data, dict) and "BTCUSDT" in market_data
    assert isinstance(prices, dict) and prices["BTCUSDT"] == 100.0
    assert len(market_data["BTCUSDT"]) >= 30

    # bridge Signal converted to pipeline Signal dataclass
    assert len(out) == 1
    sig = out[0]
    assert isinstance(sig, PipelineSignal)
    assert sig.symbol == "BTCUSDT"
    assert sig.side == "buy"
    assert sig.strategy == "fake"
    assert sig.price == 100.0


def test_try_strategies_fails_closed_without_candles():
    engine = UnifiedSignalEngine()
    fake = FakeRunner()
    engine._strategy_runner = fake

    class NoDataProvider:
        def get_klines(self, *args, **kwargs):
            return []

    engine._data_provider = NoDataProvider()
    out = engine._try_strategies("BTCUSDT", {"price": 100.0})

    assert out == []
    assert fake.calls == [], "runner must never be invoked without real candles (fail-closed)"
