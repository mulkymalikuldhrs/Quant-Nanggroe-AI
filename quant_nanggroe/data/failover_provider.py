"""Failover Data Provider — automatic provider failover with circuit breaker.

Wraps multiple data providers. On failure, falls through to the next
provider in the list. Tracks per-provider health and supports circuit
breaker integration for production resilience.

Usage:
    provider = FailoverDataProvider(providers=[twelvedata, coingecko, finnhub])
    data = provider.fetch_ohlcv("BTC/USDT", days=90)
    # If twelvedata fails → auto-try coingecko → auto-try finnhub
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Attempt CircuitBreaker import ──────────────────────────────────────

try:
    from quant_nanggroe.engine.core.circuit_breaker import (
        CircuitBreaker as _CircuitBreaker,
    )
    _HAS_CIRCUIT_BREAKER = True
except ImportError:
    _HAS_CIRCUIT_BREAKER = False

# ── Constants ──────────────────────────────────────────────────────────

_COOLDOWN_SECONDS = 60
_CONSECUTIVE_FAILURE_LIMIT = 3


# ── Exceptions ─────────────────────────────────────────────────────────


class AllProvidersFailedError(Exception):
    """All registered providers failed to return data."""

    def __init__(self, symbol: str, failures: List[Tuple[str, str]]) -> None:
        self.symbol = symbol
        self.failures = failures
        detail = "; ".join(f"{name}: {err}" for name, err in failures)
        super().__init__(f"All providers failed for '{symbol}': {detail}")


# ── Internal state per provider ────────────────────────────────────────


class _ProviderState:
    __slots__ = (
        "name", "failure_count", "consecutive_failures",
        "last_failure_time", "cooling_until", "total_calls", "success_count",
    )

    def __init__(self, name: str) -> None:
        self.name = name
        self.failure_count = 0
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None
        self.cooling_until = 0.0
        self.total_calls = 0
        self.success_count = 0

    @property
    def is_cooling(self) -> bool:
        return time.monotonic() < self.cooling_until


# ── 10-line fallback breaker ──────────────────────────────────────────


class _SimpleBreaker:
    __slots__ = ("_failures", "_cooldown_until")

    def __init__(self) -> None:
        self._failures = 0
        self._cooldown_until = 0.0

    def record_failure(self, cooldown: float) -> None:
        self._failures += 1
        if self._failures >= 3:
            self._cooldown_until = time.monotonic() + cooldown

    def record_success(self) -> None:
        self._failures = 0
        self._cooldown_until = 0.0

    @property
    def is_open(self) -> bool:
        return time.monotonic() < self._cooldown_until


# ── FailoverDataProvider ───────────────────────────────────────────────


class FailoverDataProvider:
    """Wraps multiple data providers. On failure, falls through to next.

    Each provider must expose a ``fetch_ohlcv(symbol, days, interval)``
    method. Providers are tried in order. If one raises an exception,
    the next is tried. After 3 consecutive failures, a provider enters
    a 60-second cooldown before being retried.

    If CircuitBreaker is available (``quant_nanggroe.engine.core.circuit_breaker``),
    each provider is wrapped in its own circuit breaker. Otherwise a
    lightweight 10-line fallback breaker is used.

    Args:
        providers: List of provider instances with ``fetch_ohlcv``.
        state_path: Optional path to JSON file for state persistence.
    """

    def __init__(
        self,
        providers: Optional[List[Any]] = None,
        state_path: Optional[str] = None,
    ) -> None:
        self._providers = providers or []
        self._state_path = state_path
        self._active_index = 0

        self._states: Dict[int, _ProviderState] = {}
        self._breakers: Dict[int, Any] = {}

        for i, p in enumerate(self._providers):
            name = getattr(p, "name", f"provider_{i}")
            self._states[i] = _ProviderState(name)
            if _HAS_CIRCUIT_BREAKER:
                self._breakers[i] = _CircuitBreaker(
                    failure_threshold=_CONSECUTIVE_FAILURE_LIMIT,
                    recovery_timeout=float(_COOLDOWN_SECONDS),
                    name=f"failover:{name}",
                )

        self._load_state()
        logger.info(
            "FailoverDataProvider ready — %d provider(s), circuit_breaker=%s",
            len(self._providers), _HAS_CIRCUIT_BREAKER,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        days: int = 90,
        interval: str = "1h",
    ) -> Any:
        """Fetch OHLCV data with automatic failover.

        Args:
            symbol: Trading pair or ticker symbol.
            days: Number of days of historical data.
            interval: Candle interval (e.g. ``"1h"``, ``"1d"``).

        Returns:
            Data from the first successful provider.

        Raises:
            AllProvidersFailedError: If every provider failed.
        """
        failures: List[Tuple[str, str]] = []

        for i, provider in enumerate(self._providers):
            state = self._states[i]

            # Cooling check (also covers simple breaker fallback)
            if state.is_cooling:
                logger.debug("Skipping '%s' — cooling down", state.name)
                continue

            # Circuit breaker allow check
            breaker = self._breakers.get(i)
            if breaker is not None and not self._cb_allow(breaker):
                logger.debug("Skipping '%s' — circuit breaker open", state.name)
                continue

            try:
                result = provider.fetch_ohlcv(symbol, days, interval)

                state.total_calls += 1
                state.success_count += 1
                state.consecutive_failures = 0
                self._active_index = i
                if breaker is not None:
                    breaker.record_success()
                self._save_state()
                return result

            except Exception as exc:
                err_msg = f"{type(exc).__name__}: {exc}"
                failures.append((state.name, err_msg))
                state.failure_count += 1
                state.consecutive_failures += 1
                state.last_failure_time = time.monotonic()
                state.total_calls += 1

                if breaker is not None:
                    breaker.record_failure()

                if state.consecutive_failures >= _CONSECUTIVE_FAILURE_LIMIT:
                    state.cooling_until = time.monotonic() + _COOLDOWN_SECONDS
                    logger.warning(
                        "'%s' — %d consecutive failures, cooling %ds",
                        state.name, state.consecutive_failures, _COOLDOWN_SECONDS,
                    )

                logger.warning("Provider '%s' failed for %s: %s", state.name, symbol, exc)
                self._save_state()

        raise AllProvidersFailedError(symbol, failures)

    def get_status(self) -> Dict[str, Any]:
        """Return current failover provider status."""
        provider_statuses: List[Dict[str, Any]] = []
        for i, p in enumerate(self._providers):
            s = self._states[i]
            status: Dict[str, Any] = {
                "name": s.name,
                "index": i,
                "active": i == self._active_index,
                "total_calls": s.total_calls,
                "success_count": s.success_count,
                "failure_count": s.failure_count,
                "consecutive_failures": s.consecutive_failures,
                "cooling": s.is_cooling,
            }
            if s.is_cooling:
                status["cooling_remaining_s"] = round(s.cooling_until - time.monotonic(), 1)
            if s.last_failure_time is not None:
                import datetime
                status["last_failure_time"] = datetime.datetime.fromtimestamp(
                    s.last_failure_time, tz=datetime.timezone.utc
                ).isoformat()
            if i in self._breakers:
                if _HAS_CIRCUIT_BREAKER:
                    status["circuit_breaker"] = self._breakers[i].get_metrics()
            provider_statuses.append(status)

        return {
            "active_provider": self._states[self._active_index].name if self._providers else None,
            "providers": provider_statuses,
            "total_failures": sum(s.failure_count for s in self._states.values()),
            "circuit_breaker_enabled": _HAS_CIRCUIT_BREAKER,
        }

    # ------------------------------------------------------------------
    # Circuit breaker helper
    # ------------------------------------------------------------------

    @staticmethod
    def _cb_allow(breaker: Any) -> bool:
        if _HAS_CIRCUIT_BREAKER:
            return breaker.allow_request()
        return not breaker.is_open

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        try:
            data: Dict[str, Any] = {"_active_index": self._active_index}
            for i, s in self._states.items():
                data[str(i)] = {
                    k: getattr(s, k)
                    for k in ("failure_count", "consecutive_failures", "last_failure_time",
                              "cooling_until", "total_calls", "success_count")
                }
            os.makedirs(os.path.dirname(self._state_path) or ".", exist_ok=True)
            with open(self._state_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save failover state: %s", exc)

    def _load_state(self) -> None:
        if self._state_path is None or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path) as f:
                data = json.load(f)
            self._active_index = data.pop("_active_index", 0)
            for i_str, entry in data.items():
                i = int(i_str)
                if i in self._states:
                    s = self._states[i]
                    for k, v in entry.items():
                        if hasattr(s, k):
                            setattr(s, k, v)
            logger.info("Restored failover state from %s", self._state_path)
        except Exception as exc:
            logger.warning("Failed to load failover state: %s", exc)
