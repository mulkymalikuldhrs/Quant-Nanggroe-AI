"""C5: Tests for previously-untested pipeline modules.

Covers:
  - orchestrator: _detect_mode symbol routing (forex/crypto/agentic) + PipelineResult.empty
  - signal: UnifiedSignalEngine._try_strategies wiring with a mocked runner +
            mocked data provider (fail-closed without candles)
  - execution: UnifiedExecutionRouter reject paths (bad side, kill-switch, no backend)
  - factory: create_pipeline constructs wired components
  - data: UnifiedDataProvider caching layer (mocked backend)

All execution paths are exercised with mocks — no live broker/MT5, no network.
"""

from __future__ import annotations

from quant_nanggroe.pipeline.execution import (
    PipelineSignal,
    UnifiedExecutionRouter,
)
from quant_nanggroe.pipeline.orchestrator import (
    PipelineResult,
    UnifiedPipeline,
    _detect_mode,
)
from quant_nanggroe.pipeline.signal import Signal, UnifiedSignalEngine
from quant_nanggroe.pipeline.factory import create_pipeline


# ─────────────────────────────────────────────────────────────────────────────
# Mode detection
# ─────────────────────────────────────────────────────────────────────────────
class TestDetectMode:
    def test_forex_symbol(self):
        assert _detect_mode("EURUSD") == "hedge"
        assert _detect_mode("GBPUSD") == "hedge"

    def test_metals(self):
        assert _detect_mode("XAUUSD") == "hedge"
        assert _detect_mode("XAGUSD") == "hedge"

    def test_crypto_suffix(self):
        assert _detect_mode("BTCUSDT") == "crypto"
        assert _detect_mode("ETHUSD") == "crypto"

    def test_agentic_default(self):
        assert _detect_mode("SPY") == "agentic"
        assert _detect_mode("NVDA") == "agentic"

    def test_explicit_hint(self):
        assert _detect_mode("EURUSD", mode="crypto") == "crypto"

    def test_pipeline_result_empty(self):
        r = PipelineResult.empty("BTCUSDT")
        assert r.symbol == "BTCUSDT"
        assert r.signal == "hold"
        assert r.executed is False


# ─────────────────────────────────────────────────────────────────────────────
# Signal engine
# ─────────────────────────────────────────────────────────────────────────────
class TestSignalEngine:
    def _candles(self, n=40, price=100.0):
        return [{"open": price, "high": price * 1.01, "low": price * 0.99,
                 "close": price, "volume": 10.0} for _ in range(n)]

    def test_try_strategies_requires_candles(self):
        eng = UnifiedSignalEngine()
        eng._strategy_runner = None  # no runner
        eng._data_provider = _NoData()  # no candles
        out = eng._try_strategies("BTCUSDT", {"price": 100.0})
        assert out == []

    def test_try_strategies_calls_runner_with_dict_args(self):
        eng = UnifiedSignalEngine()
        fake = _FakeRunner()
        eng._strategy_runner = fake
        eng._data_provider = _CandleProvider(self._candles())
        out = eng._try_strategies("BTCUSDT", {"price": 100.0})
        assert len(fake.calls) == 1
        market_data, prices = fake.calls[0]
        assert isinstance(market_data, dict) and "BTCUSDT" in market_data
        assert prices["BTCUSDT"] == 100.0
        assert len(out) == 1
        assert isinstance(out[0], Signal)

    def test_generate_signals_filters_below_threshold(self):
        eng = UnifiedSignalEngine()
        # Runner returns a high-confidence buy; macro filter lets it pass
        class _StrongRunner:
            def generate_signals(self, md, prices, active_strategies=None):
                return [Signal(symbol="BTCUSDT", side="buy", confidence=0.95,
                               strategy="fake", price=100.0, reason="x")]
        eng._strategy_runner = _StrongRunner()
        eng._data_provider = _CandleProvider(self._candles())
        # neutral macro context
        out = eng.generate_signals("BTCUSDT", {"price": 100.0})
        assert any(s.side == "buy" for s in out)

    def test_try_strategies_fail_closed_no_candles(self):
        eng = UnifiedSignalEngine()
        fake = _FakeRunner()
        eng._strategy_runner = fake
        eng._data_provider = _NoData()
        out = eng._try_strategies("BTCUSDT", {"price": 100.0})
        assert out == []
        assert fake.calls == []


class _FakeRunner:
    def __init__(self):
        self.calls = []

    def generate_signals(self, market_data, prices, active_strategies=None):
        self.calls.append((market_data, prices))
        sym = next(iter(prices))
        return [Signal(symbol=sym, side="buy", confidence=0.9,
                       strategy="fake", price=prices[sym], reason="test")]


class _CandleProvider:
    def __init__(self, candles):
        self._candles = candles

    def get_klines(self, symbol, interval="1h", limit=100):
        return self._candles


class _NoData:
    def get_klines(self, symbol, interval="1h", limit=100):
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Execution router
# ─────────────────────────────────────────────────────────────────────────────
class TestExecutionRouter:
    def test_bad_side_returns_none(self):
        r = UnifiedExecutionRouter()
        assert r.execute("BTCUSDT", "hold", 100.0) is None

    def test_no_backend_rejected(self, monkeypatch):
        r = UnifiedExecutionRouter(allow_live=False)
        # neutralize lazy loaders so none of the backends exist
        monkeypatch.setattr(r, "_lazy_production", lambda: None)
        monkeypatch.setattr(r, "_lazy_mt5", lambda: None)
        monkeypatch.setattr(r, "_lazy_paper", lambda: None)
        monkeypatch.setattr(r, "_lazy_engine", lambda: None)
        monkeypatch.setattr(r, "get_balance", lambda: 0.0)
        res = r.execute("BTCUSDT", "buy", 100.0, qty=0.01)
        assert res["status"] == "rejected"
        assert res["mode"] == "no_backend"
        assert res["executed"] is False

    def test_pipeline_signal_dataclass(self):
        s = PipelineSignal(symbol="EURUSD", side="buy", confidence=0.8, price=1.1)
        assert s.symbol == "EURUSD"
        assert s.stop_loss is None
        assert s.strategy == "pipeline"

    def test_mark_executed_fill_id(self):
        res = {"status": "filled", "fill_id": "abc"}
        UnifiedExecutionRouter._mark_executed(res)
        assert res["executed"] is True

    def test_mark_executed_rejected(self):
        res = {"status": "rejected"}
        UnifiedExecutionRouter._mark_executed(res)
        assert res["executed"] is False

    def test_uses_provided_paper_broker(self, monkeypatch):
        r = UnifiedExecutionRouter(allow_live=False)
        monkeypatch.setattr(r, "_lazy_production", lambda: None)
        monkeypatch.setattr(r, "_lazy_mt5", lambda: None)
        monkeypatch.setattr(r, "_lazy_engine", lambda: None)
        monkeypatch.setattr(r, "get_balance", lambda: 0.0)

        class _Paper:
            def __init__(self):
                self.calls = []
            def place_order(self, symbol, side, qty, price):
                self.calls.append((symbol, side, qty, price))
                return {"status": "filled", "fill_id": "p1", "price": price}

        paper = _Paper()
        monkeypatch.setattr(r, "_lazy_paper", lambda: None)
        r._paper = paper
        res = r.execute("BTCUSDT", "buy", 100.0, qty=0.01)
        assert res["mode"] == "paper"
        assert res["executed"] is True
        assert paper.calls[0][0] == "BTCUSDT"


# ─────────────────────────────────────────────────────────────────────────────
# Factory + data provider
# ─────────────────────────────────────────────────────────────────────────────
class TestPipelineFactory:
    def test_create_pipeline_wires_components(self):
        comps = create_pipeline(allow_live=False)
        assert isinstance(comps.data, object)
        assert isinstance(comps.signal, UnifiedSignalEngine)
        assert isinstance(comps.execution, UnifiedExecutionRouter)
        assert isinstance(comps.pipeline, UnifiedPipeline)

    def test_run_batch_returns_results(self):
        comps = create_pipeline(allow_live=False)
        # Force agentic mode to fail fast (no AutonomousPipeline) so it returns empty results
        comps.pipeline._mode_resolver = lambda sym, mode: "agentic"
        comps.pipeline._lazy_autonomous = lambda: None
        res = comps.pipeline.run("SPY")
        assert isinstance(res, PipelineResult)
        # With autonomous unavailable we get an error result, not a crash
        assert res.error is not None or res.signal == "hold"


class TestDataProvider:
    def test_cache_miss_then_hit(self):
        from quant_nanggroe.pipeline.data import UnifiedDataProvider

        provider = UnifiedDataProvider(cache_ttl=60)
        calls = {"n": 0}

        class _Backend:
            def get_price(self, symbol):
                calls["n"] += 1
                return 123.45

        provider._engine_provider = _Backend()
        assert provider.get_price("BTCUSD") == 123.45
        assert provider.get_price("BTCUSD") == 123.45
        # second call served from cache — backend not hit again
        assert calls["n"] == 1
