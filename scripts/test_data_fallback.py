"""Test data fallback chain and circuit breaker."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly to avoid numpy dependency in normalizer
from quant_nanggroe.engine.data.fallback_chain import (
    CircuitBreaker,
    DataFallbackChain,
    create_default_chain,
)
from quant_nanggroe.engine.data.provider_interface import (
    DataCategory,
    DataRequest,
    DataResponse,
    QNAProviderBase,
)
from quant_nanggroe.engine.data.provider_registry import ProviderRegistry


# ─── Test CircuitBreaker ─────────────────────────────────────────────
def test_circuit_breaker():
    cb = CircuitBreaker(max_failures=2, reset_seconds=5)
    assert cb.can_try("test_provider") is True, "should start closed"
    cb.record_failure("test_provider")
    assert cb.can_try("test_provider") is True, "should still be closed (1/2)"
    cb.record_failure("test_provider")
    assert cb.can_try("test_provider") is False, "should OPEN at 2 failures"
    # verify status
    st = cb.status("test_provider")
    assert st["state"] == "open"
    assert st["failures"] == 2
    # reset after timeout
    import time; time.sleep(6)
    assert cb.can_try("test_provider") is True, "should reset after timeout"
    # record success should clear
    cb.record_failure("other")
    cb.record_success("other")
    assert cb.can_try("other") is True
    st2 = cb.status("other")
    assert st2["failures"] == 0
    print("[PASS] CircuitBreaker")


# ─── Test Fallback Chain ──────────────────────────────────────────────
class FakeProvider(QNAProviderBase):
    def __init__(self, name: str, succeeds: bool = True):
        self._name = name
        self._succeeds = succeeds

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, request: DataRequest) -> DataResponse:
        if not self._succeeds:
            raise RuntimeError(f"{self._name} failed")
        return DataResponse(
            results=[{"symbol": request.symbol, "price": 100}],
            provider=self._name,
        )


def test_fallback_chain_success_first():
    p1 = FakeProvider("primary", succeeds=True)
    p2 = FakeProvider("secondary", succeeds=True)
    chain = DataFallbackChain([p1, p2])
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    resp = chain.fetch(req)
    assert resp.provider == "primary"
    assert len(resp.results) == 1
    print("[PASS] FallbackChain success on first provider")


def test_fallback_chain_fallback():
    p1 = FakeProvider("primary", succeeds=False)
    p2 = FakeProvider("secondary", succeeds=True)
    chain = DataFallbackChain([p1, p2])
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    resp = chain.fetch(req)
    assert resp.provider == "secondary"
    print("[PASS] FallbackChain fallback to secondary")


def test_fallback_chain_all_fail():
    p1 = FakeProvider("primary", succeeds=False)
    p2 = FakeProvider("secondary", succeeds=False)
    chain = DataFallbackChain([p1, p2])
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    try:
        chain.fetch(req)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "All providers failed" in str(e)
    print("[PASS] FallbackChain all fail raises RuntimeError")


def test_fallback_chain_circuit_skip():
    p = FakeProvider("flakey", succeeds=False)
    chain = DataFallbackChain([p, FakeProvider("backup", succeeds=True)])
    cb = chain.circuit_breaker
    # Record enough failures to open (default max_failures=3)
    for _ in range(3):
        cb.record_failure("flakey")
    assert not cb.can_try("flakey"), "circuit should be open"
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    resp = chain.fetch(req)
    assert resp.provider == "backup"
    assert chain._stats["flakey"]["skip"] >= 1
    print("[PASS] FallbackChain skips open circuit provider")


def test_stats():
    p1 = FakeProvider("p1", succeeds=True)
    p2 = FakeProvider("p2", succeeds=True)
    chain = DataFallbackChain([p1, p2])
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    chain.fetch(req)
    stats = chain.get_stats()
    assert stats["p1"]["success"] == 1
    assert "p2" not in stats or stats["p2"].get("success", 0) == 0
    print("[PASS] FallbackChain stats tracking")


# ─── Test default chain creation ─────────────────────────────────────
def test_create_default_chain():
    registry = ProviderRegistry()
    # register a mock
    mock = FakeProvider("yfinance", succeeds=True)
    registry.register(mock)
    chain = create_default_chain(registry=registry, category=DataCategory.EQUITY_OHLCV)
    assert len(chain.providers) >= 1
    req = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="AAPL")
    resp = chain.fetch(req)
    assert resp.provider == "yfinance"
    print("[PASS] create_default_chain")


# ─── Run all tests ────────────────────────────────────────────────────
if __name__ == "__main__":
    test_circuit_breaker()
    test_fallback_chain_success_first()
    test_fallback_chain_fallback()
    test_fallback_chain_all_fail()
    test_fallback_chain_circuit_skip()
    test_stats()
    test_create_default_chain()
    print("\n=== ALL TESTS PASSED ===")
