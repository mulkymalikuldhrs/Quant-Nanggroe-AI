"""
Circuit Breaker + Retry Hardening
==================================

Provides circuit breaker pattern with configurable states (CLOSED, OPEN,
HALF_OPEN), exponential backoff retry policy, and decorator for wrapping
functions with automatic circuit breaker protection.

The circuit breaker prevents cascading failures by tracking consecutive
failures and temporarily blocking calls when the failure threshold is
exceeded. After a recovery timeout, it transitions to HALF_OPEN state
to probe whether the downstream service has recovered.

Usage::

    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    @breaker.protect
    def call_external_api():
        ...

    # Or use retry policy
    policy = RetryPolicy(max_retries=3, base_delay=1.0)
    result = policy.execute(call_external_api)
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from quant_nanggroe.exceptions import EngineError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerMetrics:
    """Metrics for a single circuit breaker instance."""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_count / self.total_calls


class CircuitBreakerError(EngineError):
    """Raised when a circuit breaker blocks a call."""

    def __init__(self, name: str, state: CircuitState) -> None:
        self.circuit_name = name
        self.circuit_state = state
        super().__init__(
            f"Circuit breaker '{name}' is {state.value} — call blocked"
        )


class CircuitBreaker:
    """Circuit breaker with CLOSED, OPEN, HALF_OPEN states.

    Attributes:
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait before transitioning OPEN → HALF_OPEN.
        half_open_max_calls: Max calls allowed in HALF_OPEN state before deciding.
        name: Identifier for this circuit breaker (for logging).
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.name = name

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> CircuitState:
        """Current state, auto-transitioning OPEN → HALF_OPEN if timeout expired."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        self._metrics.state_changes += 1

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._half_open_successes = 0

        logger.info(
            f"Circuit '{self.name}': {old_state.value} → {new_state.value}"
        )

    def record_success(self) -> None:
        """Record a successful call."""
        self._metrics.success_count += 1
        self._metrics.total_calls += 1
        self._metrics.last_success_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            self._half_open_calls += 1
            if self._half_open_successes >= self.half_open_max_calls:
                self._consecutive_failures = 0
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._metrics.failure_count += 1
        self._metrics.total_calls += 1
        self._metrics.consecutive_failures += 1
        self._metrics.last_failure_time = time.monotonic()
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit breaker."""
        current_state = self.state  # triggers auto-transition check

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        else:  # OPEN
            return False

    def reset(self) -> None:
        """Reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        self._half_open_successes = 0
        logger.info(f"Circuit '{self.name}': reset to CLOSED")

    def get_metrics(self) -> Dict[str, Any]:
        """Return current circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "total_calls": self._metrics.total_calls,
            "success_count": self._metrics.success_count,
            "failure_count": self._metrics.failure_count,
            "success_rate": round(self._metrics.success_rate, 4),
            "state_changes": self._metrics.state_changes,
            "last_failure": self._metrics.last_failure_time,
            "last_success": self._metrics.last_success_time,
        }

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator that wraps a function with circuit breaker protection.

        Usage::

            @circuit_breaker.protect
            def call_api():
                ...
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.allow_request():
                raise CircuitBreakerError(self.name, self.state)
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except CircuitBreakerError:
                raise
            except Exception:
                self.record_failure()
                raise
        return wrapper


# ── Retry Policy ──────────────────────────────────────────────────────

@dataclass
class RetryPolicy:
    """Retry policy with exponential backoff and jitter.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds between retries.
        max_delay: Maximum delay cap in seconds.
        backoff_factor: Multiplier for exponential backoff.
        jitter: Whether to add random jitter to delays.
        retryable_exceptions: Tuple of exception types that trigger retry.
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (ConnectionError, TimeoutError, OSError)

    def compute_delay(self, attempt: int) -> float:
        """Compute delay for a given retry attempt."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay *= random.uniform(0.5, 1.5)
        return delay

    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs: Any,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            on_retry: Optional callback called with (attempt_number, exception).
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            Last exception if all retries fail.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exception = exc

                if attempt < self.max_retries:
                    delay = self.compute_delay(attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} after "
                        f"{delay:.2f}s: {exc}"
                    )
                    if on_retry:
                        on_retry(attempt + 1, exc)
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} retries exhausted: {exc}"
                    )

        raise last_exception  # type: ignore[misc]

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs: Any,
    ) -> Any:
        """Async version of execute with retry logic."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exception = exc

                if attempt < self.max_retries:
                    delay = self.compute_delay(attempt)
                    logger.warning(
                        f"Async retry {attempt + 1}/{self.max_retries} after "
                        f"{delay:.2f}s: {exc}"
                    )
                    if on_retry:
                        on_retry(attempt + 1, exc)
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} async retries exhausted: {exc}"
                    )

        raise last_exception  # type: ignore[misc]


# ── Combined Circuit Breaker + Retry ──────────────────────────────────

class ResilientCaller:
    """Combines circuit breaker and retry policy for resilient calls.

    Usage::

        caller = ResilientCaller(
            circuit_breaker=CircuitBreaker(failure_threshold=3),
            retry_policy=RetryPolicy(max_retries=2),
        )
        result = caller.call(request_fn, arg1, arg2)
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None,
        name: str = "resilient_caller",
    ) -> None:
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name=name)
        self.retry_policy = retry_policy or RetryPolicy()
        self.name = name

    def call(
        self,
        func: Callable[..., T],
        *args: Any,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs: Any,
    ) -> T:
        """Execute a function with circuit breaker + retry.

        First checks circuit breaker state. If allowed, attempts the call
        with retry policy. Records success/failure on circuit breaker.

        Raises:
            CircuitBreakerError: If circuit is open.
            Last exception: If all retries fail.
        """
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerError(
                self.circuit_breaker.name, self.circuit_breaker.state
            )

        last_exception: Optional[Exception] = None

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except CircuitBreakerError:
                raise
            except self.retry_policy.retryable_exceptions as exc:
                last_exception = exc
                self.circuit_breaker.record_failure()

                if attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.compute_delay(attempt)
                    logger.warning(
                        f"[{self.name}] Retry {attempt + 1}/{self.retry_policy.max_retries} "
                        f"after {delay:.2f}s: {exc}"
                    )
                    if on_retry:
                        on_retry(attempt + 1, exc)
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[{self.name}] All retries exhausted: {exc}"
                    )
                    raise

            except Exception as exc:
                self.circuit_breaker.record_failure()
                raise

        raise last_exception  # type: ignore[misc]

    def get_status(self) -> Dict[str, Any]:
        """Return combined status of circuit breaker and retry policy."""
        return {
            "name": self.name,
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "retry_policy": {
                "max_retries": self.retry_policy.max_retries,
                "base_delay": self.retry_policy.base_delay,
                "backoff_factor": self.retry_policy.backoff_factor,
            },
        }


# ── Module-level circuit breakers ────────────────────────────────────

_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Get or create a named circuit breaker (singleton per name)."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            name=name,
        )
    return _circuit_breakers[name]


def protect_with_circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0,
) -> Callable:
    """Decorator that protects a function with a named circuit breaker.

    Usage::

        @protect_with_circuit_breaker("data_provider", failure_threshold=5)
        def fetch_data():
            ...
    """
    breaker = get_circuit_breaker(name, failure_threshold, recovery_timeout)
    return breaker.protect
