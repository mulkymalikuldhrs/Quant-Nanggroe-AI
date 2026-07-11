"""Reusable CircuitBreaker for guarding external service calls.

Implements the Circuit Breaker pattern with three states:
- CLOSED: Normal operation — calls pass through, failures are counted.
- OPEN:  Too many failures — calls are rejected immediately with a fallback.
- HALF_OPEN: Timeout elapsed — a limited number of probe calls are allowed
  to test recovery.

Usage::

    from quant_nanggroe.core.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(name="nim_client", failure_threshold=5)

    if cb.can_execute():
        try:
            result = await external_call()
            cb.record_success()
            return result
        except Exception:
            cb.record_failure()
            return fallback()

This module also provides :class:`CircuitBreakerMiddleware` which wraps
an async callable with circuit-breaker protection automatically.
"""

from __future__ import annotations

import enum
import logging
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


T = TypeVar("T")


class CircuitBreaker:
    """Thread-safe circuit breaker with configurable threshold and timeout.

    Parameters
    ----------
    name : str
        Human-readable name used in log messages.
    failure_threshold : int
        Number of consecutive failures before the circuit opens.
    recovery_timeout : float
        Seconds to wait in OPEN state before transitioning to HALF_OPEN.
    half_open_max : int
        Number of successful calls in HALF_OPEN needed to close the circuit.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_successes = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change_time: float = time.monotonic()

    # ── Public properties ───────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        """Current state, automatically transitioning OPEN -> HALF_OPEN after timeout."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if (time.monotonic() - self._last_failure_time) > self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_open(self) -> bool:
        """True when the circuit is OPEN (calls should be rejected)."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None and (
                time.monotonic() - self._last_failure_time
            ) >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
                logger.info("circuit_half_open: name=%s", self.name)
                return False
            return True
        return False

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    # ── State checks ────────────────────────────────────────────────────

    def can_execute(self) -> bool:
        """Return True if a call is allowed to proceed."""
        return not self.is_open

    # ── Recording outcomes ──────────────────────────────────────────────

    def record_success(self) -> None:
        """Record a successful call."""
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_max:
                self._transition(CircuitState.CLOSED)
                logger.info(
                    "circuit_closed: name=%s, half_open_probes=%d",
                    self.name,
                    self._half_open_successes,
                )

        elif self._state == CircuitState.CLOSED:
            # Reset consecutive failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # A single failure in half-open immediately reopens
            self._transition(CircuitState.OPEN)
            logger.warning(
                "circuit_reopened: name=%s",
                self.name,
            )
        elif self._failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN)
            logger.warning(
                "circuit_opened: name=%s, failures=%d, threshold=%d",
                self.name,
                self._failure_count,
                self.failure_threshold,
            )

    # ── Manual control ──────────────────────────────────────────────────

    def reset(self) -> None:
        """Force the circuit back to CLOSED state."""
        self._transition(CircuitState.CLOSED)
        logger.info("circuit_reset: name=%s", self.name)

    # ── Introspection ───────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable snapshot of the circuit state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
        }

    # ── Internal helpers ────────────────────────────────────────────────

    def _transition(self, new_state: CircuitState) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self._last_state_change_time = time.monotonic()

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        logger.debug(
            "circuit_transition: name=%s, %s -> %s",
            self.name,
            old.value,
            new_state.value,
        )


class CircuitBreakerMiddleware:
    """Wrap an async callable with circuit-breaker protection.

    Parameters
    ----------
    breaker : CircuitBreaker
        The circuit breaker instance to use.
    fallback : callable
        A zero-argument async callable (or plain callable) returned when
        the circuit is OPEN.

    Usage::

        cb = CircuitBreaker(name="nim_client", failure_threshold=3)
        mw = CircuitBreakerMiddleware(cb, fallback=lambda: default_response())

        result = await mw.call(external_fetch_func, arg1, arg2)
    """

    def __init__(
        self,
        breaker: CircuitBreaker,
        fallback: Callable[[], Any],
    ) -> None:
        self.breaker = breaker
        self.fallback = fallback

    async def call(self, fn: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* with circuit-breaker protection.

        If the circuit is OPEN, the fallback is returned instead.
        Successes and failures are recorded automatically.
        """
        if not self.breaker.can_execute():
            logger.warning(
                "circuit_open_returning_fallback: name=%s",
                self.breaker.name,
            )
            result = self.fallback()
            if result is not None and hasattr(result, "__await__"):
                result = await result
            return result

        try:
            result = await fn(*args, **kwargs)
            self.breaker.record_success()
            return result
        except Exception:
            self.breaker.record_failure()
            raise
