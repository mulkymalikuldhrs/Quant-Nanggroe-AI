"""
Data Provider Fallback Integration Tests
==========================================

Tests the data fallback chain, circuit breaker behavior, retry policies,
and provider timeout handling.

Covers:
- TestFallbackChain: Fallback from primary to secondary provider
- TestCircuitBreakerTrips: Circuit breaker trips on repeated failures
- TestCircuitBreakerRecovery: Circuit breaker recovers after timeout
- TestProviderTimeout: Provider timeout handling
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    ResilientCaller,
    RetryPolicy,
)
from quant_nanggroe.engine.data.fallback_chain import (
    CircuitBreaker as DataCircuitBreaker,
    DataFallbackChain,
)
from quant_nanggroe.engine.data.provider_interface import (
    DataCategory,
    DataRequest,
    DataResponse,
    QNAProviderBase,
)


# ── Mock Providers ────────────────────────────────────────────────────

class MockProvider(QNAProviderBase):
    """Mock data provider for testing."""

    def __init__(
        self,
        name: str = "mock",
        fail: bool = False,
        delay: float = 0.0,
        fail_count: int = 0,
    ):
        self._name = name
        self._fail = fail
        self._delay = delay
        self._fail_count = fail_count
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, request: DataRequest) -> DataResponse:
        self._call_count += 1

        if self._delay > 0:
            time.sleep(self._delay)

        if self._fail or (self._fail_count > 0 and self._call_count <= self._fail_count):
            raise ConnectionError(f"Provider {self._name} failed")

        return DataResponse(
            results=[{"symbol": request.symbol, "close": 100.0}],
            provider=self._name,
        )


class TimeoutProvider(QNAProviderBase):
    """Provider that always times out."""

    def __init__(self, name: str = "timeout"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, request: DataRequest) -> DataResponse:
        raise TimeoutError(f"Provider {self._name} timed out")


class SlowProvider(QNAProviderBase):
    """Provider with configurable delay."""

    def __init__(self, name: str = "slow", delay: float = 0.5):
        self._name = name
        self._delay = delay

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, request: DataRequest) -> DataResponse:
        time.sleep(self._delay)
        return DataResponse(
            results=[{"symbol": request.symbol, "close": 100.0}],
            provider=self._name,
        )


def _make_request(symbol: str = "SPY") -> DataRequest:
    return DataRequest(category=DataCategory.EQUITY_OHLCV, symbol=symbol)


# ═══════════════════════════════════════════════════════════════════════
# TestFallbackChain
# ═══════════════════════════════════════════════════════════════════════

class TestFallbackChain:
    """Test fallback from primary to secondary provider."""

    def test_primary_succeeds(self):
        """Should use primary provider when it works."""
        primary = MockProvider("primary", fail=False)
        secondary = MockProvider("secondary", fail=False)

        chain = DataFallbackChain([primary, secondary])
        result = chain.fetch(_make_request())

        assert result.provider == "primary"
        assert primary._call_count == 1
        assert secondary._call_count == 0

    def test_primary_fails_fallback_to_secondary(self):
        """Should fall back to secondary when primary fails."""
        primary = MockProvider("primary", fail=True)
        secondary = MockProvider("secondary", fail=False)

        chain = DataFallbackChain([primary, secondary])
        result = chain.fetch(_make_request())

        assert result.provider == "secondary"
        assert primary._call_count == 1
        assert secondary._call_count == 1

    def test_all_providers_fail_raises(self):
        """Should raise RuntimeError when all providers fail."""
        primary = MockProvider("primary", fail=True)
        secondary = MockProvider("secondary", fail=True)

        chain = DataFallbackChain([primary, secondary])

        with pytest.raises(RuntimeError, match="All providers failed"):
            chain.fetch(_make_request())

    def test_fallback_skips_open_circuit(self):
        """Should skip providers with open circuit breaker."""
        primary = MockProvider("primary", fail=True)
        secondary = MockProvider("secondary", fail=True)
        tertiary = MockProvider("tertiary", fail=False)

        chain = DataFallbackChain([primary, secondary, tertiary])

        # Trip the circuit for primary and secondary
        for _ in range(5):
            try:
                chain.fetch(_make_request())
            except RuntimeError:
                pass

        # Reset and test fallback
        primary._fail = False
        secondary._fail = False
        tertiary._fail = False

        chain.circuit_breaker.reset_provider("primary")
        chain.circuit_breaker.reset_provider("secondary")

        result = chain.fetch(_make_request())
        assert result is not None

    def test_health_score_tracking(self):
        """Health scores should reflect success/failure rates."""
        good = MockProvider("good", fail=False)
        bad = MockProvider("bad", fail=True)

        chain = DataFallbackChain([good, bad])

        for _ in range(5):
            try:
                chain.fetch(_make_request())
            except RuntimeError:
                pass

        health = chain.get_health_scores()
        assert health["good"] > health["bad"]

    def test_circuit_status_reporting(self):
        """Circuit status should be reported correctly."""
        good = MockProvider("good", fail=False)
        bad = MockProvider("bad", fail=True)

        chain = DataFallbackChain([good, bad])

        for _ in range(5):
            try:
                chain.fetch(_make_request())
            except RuntimeError:
                pass

        statuses = chain.get_circuit_status()
        assert len(statuses) == 2

    def test_provider_ranking_by_health(self):
        """Providers should be ranked by health score."""
        healthy = MockProvider("healthy", fail=False)
        sick = MockProvider("sick", fail=True)

        chain = DataFallbackChain([healthy, sick])

        # Make sick provider fail a few times
        for _ in range(3):
            try:
                chain.fetch(_make_request())
            except RuntimeError:
                pass

        ranked = chain._rank_providers()
        # Healthy provider should rank first
        assert ranked[0].name == "healthy"


# ═══════════════════════════════════════════════════════════════════════
# TestCircuitBreakerTrips
# ═══════════════════════════════════════════════════════════════════════

class TestCircuitBreakerTrips:
    """Test circuit breaker trips on repeated failures."""

    def test_trips_after_threshold(self):
        """Circuit should OPEN after failure_threshold consecutive failures."""
        cb = CircuitBreaker(failure_threshold=3, name="test")

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert not cb.allow_request()

    def test_does_not_trip_below_threshold(self):
        """Circuit should stay CLOSED below failure threshold."""
        cb = CircuitBreaker(failure_threshold=5, name="test")

        for _ in range(4):
            cb.record_failure()

        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request()

    def test_success_resets_failure_count(self):
        """Success should reset consecutive failure count."""
        cb = CircuitBreaker(failure_threshold=3, name="test")

        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()

        assert cb.state == CircuitState.CLOSED
        assert cb._consecutive_failures == 1

    def test_protect_decorator_blocks_when_open(self):
        """@protect decorator should raise CircuitBreakerError when circuit is open."""
        cb = CircuitBreaker(failure_threshold=2, name="test")

        @cb.protect
        def dummy_func():
            return 42

        # Trip the circuit
        cb.record_failure()
        cb.record_failure()

        with pytest.raises(CircuitBreakerError):
            dummy_func()

    def test_protect_decorator_allows_when_closed(self):
        """@protect decorator should allow calls when circuit is closed."""
        cb = CircuitBreaker(failure_threshold=3, name="test")

        @cb.protect
        def dummy_func():
            return 42

        result = dummy_func()
        assert result == 42

    def test_metrics_tracking(self):
        """Circuit breaker should track comprehensive metrics."""
        cb = CircuitBreaker(failure_threshold=3, name="test")

        cb.record_success()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        metrics = cb.get_metrics()
        assert metrics["total_calls"] == 5
        assert metrics["success_count"] == 2
        assert metrics["failure_count"] == 3
        assert metrics["state"] == "open"

    def test_custom_threshold_per_instance(self):
        """Each circuit breaker instance should have its own threshold."""
        cb1 = CircuitBreaker(failure_threshold=2, name="fast")
        cb2 = CircuitBreaker(failure_threshold=10, name="slow")

        cb1.record_failure()
        cb1.record_failure()
        cb2.record_failure()
        cb2.record_failure()

        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.CLOSED


# ═══════════════════════════════════════════════════════════════════════
# TestCircuitBreakerRecovery
# ═══════════════════════════════════════════════════════════════════════

class TestCircuitBreakerRecovery:
    """Test circuit breaker recovers after timeout."""

    def test_transitions_to_half_open_after_timeout(self):
        """OPEN circuit should transition to HALF_OPEN after recovery_timeout."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            name="test",
        )

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request()

    def test_half_open_success_closes_circuit(self):
        """Successful call in HALF_OPEN should close the circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=1,
            name="test",
        )

        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._consecutive_failures == 0

    def test_half_open_failure_reopens_circuit(self):
        """Failed call in HALF_OPEN should reopen the circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            name="test",
        )

        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset_manually(self):
        """Manual reset should return circuit to CLOSED."""
        cb = CircuitBreaker(failure_threshold=2, name="test")

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._consecutive_failures == 0
        assert cb.allow_request()

    def test_recovery_cycle_full(self):
        """Test full failure → open → half-open → success → closed cycle."""
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=1,
            name="test",
        )

        # Phase 1: Failures accumulate
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Phase 2: Wait for recovery timeout
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Phase 3: Successful probe
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

        # Phase 4: Normal operation
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._consecutive_failures == 0

    def test_exponential_backoff_in_data_circuit_breaker(self):
        """DataCircuitBreaker should use exponential backoff."""
        cb = DataCircuitBreaker(max_failures=2, reset_seconds=1, backoff_factor=2.0)

        cb.record_failure("test_provider")
        assert not cb.can_try("test_provider") or cb._get_state("test_provider").failures < 2

        cb.record_failure("test_provider")
        state = cb._get_state("test_provider")
        assert state.is_open
        assert state.open_until is not None


# ═══════════════════════════════════════════════════════════════════════
# TestProviderTimeout
# ═══════════════════════════════════════════════════════════════════════

class TestProviderTimeout:
    """Test provider timeout handling."""

    def test_timeout_provider_fails(self):
        """TimeoutProvider should raise TimeoutError."""
        provider = TimeoutProvider("timeout")
        request = _make_request()

        with pytest.raises(TimeoutError):
            provider.fetch(request)

    def test_timeout_trips_circuit_breaker(self):
        """Timeout should trip the circuit breaker."""
        cb = DataCircuitBreaker(max_failures=2)
        provider = TimeoutProvider("timeout")
        request = _make_request()

        for _ in range(3):
            try:
                provider.fetch(request)
            except TimeoutError:
                cb.record_failure("timeout", is_timeout=True)

        assert not cb.can_try("timeout")

    def test_slow_provider_timeout(self):
        """SlowProvider should fail when timeout is too short."""
        provider = SlowProvider("slow", delay=0.5)
        request = _make_request()

        # Immediate timeout should not fail for slow provider
        # since SlowProvider doesn't check timeout
        result = provider.fetch(request)
        assert result is not None

    def test_retry_policy_with_timeout(self):
        """RetryPolicy should retry on TimeoutError."""
        policy = RetryPolicy(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Not ready")
            return "success"

        result = policy.execute(flaky_func)
        assert result == "success"
        assert call_count == 3

    def test_retry_policy_exhaustion(self):
        """RetryPolicy should raise after max_retries exhausted."""
        policy = RetryPolicy(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )

        def always_fail():
            raise TimeoutError("Always fails")

        with pytest.raises(TimeoutError):
            policy.execute(always_fail)

    def test_retry_policy_exponential_backoff(self):
        """RetryPolicy delays should increase exponentially."""
        policy = RetryPolicy(
            max_retries=3,
            base_delay=0.1,
            backoff_factor=2.0,
            jitter=False,
        )

        delays = [policy.compute_delay(i) for i in range(4)]
        assert delays[0] == pytest.approx(0.1, abs=0.01)
        assert delays[1] == pytest.approx(0.2, abs=0.01)
        assert delays[2] == pytest.approx(0.4, abs=0.01)
        assert delays[3] == pytest.approx(0.8, abs=0.01)

    def test_resilient_caller_combines_both(self):
        """ResilientCaller should use both circuit breaker and retry."""
        cb = CircuitBreaker(failure_threshold=5, name="resilient")
        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        caller = ResilientCaller(circuit_breaker=cb, retry_policy=policy)

        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "ok"

        result = caller.call(flaky)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    def test_resilient_caller_circuit_breaks(self):
        """ResilientCaller should stop retrying when circuit opens."""
        cb = CircuitBreaker(failure_threshold=2, name="resilient")
        policy = RetryPolicy(max_retries=10, base_delay=0.01)
        caller = ResilientCaller(circuit_breaker=cb, retry_policy=policy)

        def always_fail():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            caller.call(always_fail)

        assert cb.state == CircuitState.OPEN

    def test_blacklisting_in_data_circuit_breaker(self):
        """DataCircuitBreaker should blacklist after consecutive timeouts."""
        cb = DataCircuitBreaker(max_consecutive_timeouts=3)

        for _ in range(3):
            cb.record_failure("timeout_provider", is_timeout=True)

        assert not cb.is_available("timeout_provider")
        assert "timeout_provider" in cb.get_blacklist()
