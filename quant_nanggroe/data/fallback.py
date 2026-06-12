"""Data Provider Fallback Chain with Circuit Breaker.

Implements a resilient data access layer that:
- Maintains ordered fallback chains per data type
- Tracks provider health with circuit breaker pattern
- Prevents cascading failures via half-open state testing
- Provides automatic recovery when providers come back online

Design follows the Constitutional Risk principle: data unavailability
should never cause a crash — only graceful degradation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"       # Normal operation — requests flow through
    OPEN = "open"           # Circuit tripped — requests are rejected
    HALF_OPEN = "half_open" # Testing recovery — one request allowed through


@dataclass
class FallbackEvent:
    """Record of a fallback chain event."""

    provider_name: str
    event_type: str  # "success", "failure", "circuit_open", "circuit_half_open", "fallback"
    timestamp: float = field(default_factory=time.time)
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ProviderHealth:
    """Health tracker for a single data provider.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation. Failures increment counter.
    - OPEN: Too many failures. All requests rejected for cooldown period.
    - HALF_OPEN: Cooldown elapsed. One test request allowed.
      - If success → back to CLOSED
      - If failure → back to OPEN with doubled cooldown
    """

    name: str
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0
    _current_recovery_timeout: float = 30.0
    total_requests: int = 0
    total_failures: int = 0

    def record_success(self, latency_ms: Optional[float] = None) -> None:
        """Record a successful request."""
        self.success_count += 1
        self.total_requests += 1
        self.last_success_time = time.time()
        self.failure_count = 0  # Reset failure count on success

        if self.circuit_state == CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker_recovered",
                extra={"provider": self.name, "state": "closed"},
            )
            self.circuit_state = CircuitState.CLOSED
            self._current_recovery_timeout = self.recovery_timeout_seconds

    def record_failure(self, error_message: str = "") -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.total_failures += 1
        self.total_requests += 1
        self.last_failure_time = time.time()

        if self.circuit_state == CircuitState.HALF_OPEN:
            # Failed during recovery test — back to open with exponential backoff
            self.circuit_state = CircuitState.OPEN
            self._current_recovery_timeout = min(
                self._current_recovery_timeout * 2, 300.0  # Max 5 min cooldown
            )
            logger.warning(
                "circuit_breaker_reopened",
                extra={
                    "provider": self.name,
                    "next_timeout": self._current_recovery_timeout,
                },
            )
        elif self.failure_count >= self.failure_threshold:
            self.circuit_state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "provider": self.name,
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                },
            )

    def can_attempt(self) -> bool:
        """Check if a request can be attempted.

        Returns True if the circuit is CLOSED or if enough time has
        elapsed in OPEN state to transition to HALF_OPEN.
        """
        if self.circuit_state == CircuitState.CLOSED:
            return True

        if self.circuit_state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self._current_recovery_timeout:
                self.circuit_state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"provider": self.name, "elapsed": elapsed},
                )
                return True
            return False

        # HALF_OPEN — allow one test request
        if self.circuit_state == CircuitState.HALF_OPEN:
            return True

        return False

    @property
    def health_score(self) -> float:
        """Health score from 0.0 (dead) to 1.0 (perfect)."""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests


class FallbackChain:
    """Ordered fallback chain for data providers.

    Maintains a list of data fetchers, ordered by priority. When a
    fetcher fails, the chain automatically falls through to the next
    one. Circuit breakers prevent hammering dead providers.

    Usage::

        chain = FallbackChain("ohlcv")
        chain.register_fetcher("yfinance", yf_fetcher)
        chain.register_fetcher("ccxt", ccxt_fetcher)
        chain.register_fetcher("alphavantage", av_fetcher)

        data = await chain.fetch("BTC/USD", timeframe="1d")
    """

    def __init__(
        self,
        data_type: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.data_type = data_type
        self._fetchers: Dict[str, Callable] = {}
        self._priority_order: List[str] = []
        self._provider_health: Dict[str, ProviderHealth] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_seconds
        self._event_log: List[FallbackEvent] = []

    def register_fetcher(
        self,
        name: str,
        fetcher: Callable,
        priority: Optional[int] = None,
    ) -> None:
        """Register a data fetcher with optional priority.

        Args:
            name: Unique provider name (e.g., "yfinance", "ccxt").
            fetcher: Async callable that fetches data.
            priority: Lower number = higher priority. Default = append.
        """
        self._fetchers[name] = fetcher
        self._provider_health[name] = ProviderHealth(
            name=name,
            failure_threshold=self._failure_threshold,
            recovery_timeout_seconds=self._recovery_timeout,
        )

        if priority is not None:
            self._priority_order.insert(priority, name)
        else:
            self._priority_order.append(name)

        logger.debug(
            "fetcher_registered",
            extra={"provider": name, "data_type": self.data_type},
        )

    async def fetch(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch data using the fallback chain.

        Tries each provider in priority order, skipping those with
        open circuits. Raises RuntimeError if all providers fail.

        Returns:
            Data from the first successful provider.

        Raises:
            RuntimeError: All providers failed or unavailable.
        """
        last_error: Optional[Exception] = None

        for provider_name in self._priority_order:
            health = self._provider_health[provider_name]

            if not health.can_attempt():
                self._log_event(provider_name, "circuit_open")
                logger.debug(
                    "skipping_provider",
                    extra={"provider": provider_name, "state": health.circuit_state.value},
                )
                continue

            fetcher = self._fetchers[provider_name]
            start_time = time.time()

            try:
                result = await fetcher(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                health.record_success(latency_ms)
                self._log_event(provider_name, "success", latency_ms=latency_ms)
                return result

            except Exception as exc:
                latency_ms = (time.time() - start_time) * 1000
                health.record_failure(str(exc))
                self._log_event(
                    provider_name,
                    "failure",
                    latency_ms=latency_ms,
                    error_message=str(exc),
                )
                last_error = exc
                logger.warning(
                    "provider_failed_falling_back",
                    extra={
                        "provider": provider_name,
                        "error": str(exc),
                        "next_providers": [
                            p for p in self._priority_order
                            if self._priority_order.index(p) > self._priority_order.index(provider_name)
                        ],
                    },
                )
                continue

        raise RuntimeError(
            f"All providers failed for {self.data_type}. Last error: {last_error}"
        )

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers in the chain."""
        return {
            name: {
                "state": health.circuit_state.value,
                "health_score": health.health_score,
                "total_requests": health.total_requests,
                "total_failures": health.total_failures,
                "failure_count": health.failure_count,
                "last_failure_time": health.last_failure_time,
                "last_success_time": health.last_success_time,
            }
            for name, health in self._provider_health.items()
        }

    def _log_event(
        self,
        provider_name: str,
        event_type: str,
        latency_ms: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record an event in the fallback chain log."""
        event = FallbackEvent(
            provider_name=provider_name,
            event_type=event_type,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self._event_log.append(event)
        # Keep log bounded
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]

    @property
    def event_log(self) -> List[FallbackEvent]:
        """Return recent fallback chain events."""
        return self._event_log[-100:]
