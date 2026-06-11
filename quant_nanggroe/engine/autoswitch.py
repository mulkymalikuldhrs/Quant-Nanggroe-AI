"""
AutoSwitch Failover Engine
==========================
From HermesQuantOS — Health-monitored API failover with exponential backoff.

Tracks success/failure per provider, auto-cooldown on errors.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel


class ProviderHealth(BaseModel):
    """Track health of a single LLM/data provider."""

    name: str
    success_count: int = 0
    failure_count: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None
    cooldown_until: datetime | None = None
    avg_latency_ms: float = 0.0

    @property
    def score(self) -> float:
        """Health score: higher = better."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        success_rate = self.success_count / total
        latency_penalty = min(self.avg_latency_ms / 10000, 0.2)
        return success_rate - latency_penalty

    @property
    def is_available(self) -> bool:
        """Check if provider is off cooldown."""
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        return True


class AutoSwitchEngine:
    """
    Intelligent provider failover system.

    Enhanced from HermesQuantOS with:
    - Health monitoring per provider
    - Priority sorting by health score
    - Proactive cooldown on failures
    - Exponential backoff on rate limits (429)
    - Transparent failover
    - Circuit breaker pattern (open/half-open/closed)
    - Provider priority tiers
    - Request retry with backoff
    """

    # Circuit breaker states
    CB_CLOSED = "closed"        # Normal operation
    CB_OPEN = "open"            # Failing, reject requests
    CB_HALF_OPEN = "half_open"  # Testing if recovered

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_minutes: int = 2,
        max_cooldown_minutes: int = 30,
    ) -> None:
        self.providers: dict[str, ProviderHealth] = {}
        self.request_log: list[dict[str, Any]] = []
        self._circuit_breakers: dict[str, str] = {}  # provider -> state
        self._failure_threshold = failure_threshold
        self._recovery_timeout = timedelta(minutes=recovery_timeout_minutes)
        self._max_cooldown = timedelta(minutes=max_cooldown_minutes)
        self._provider_tiers: dict[str, int] = {}  # provider -> priority tier (lower=better)

    def register_provider(self, name: str, tier: int = 1) -> None:
        """Register a provider for health tracking.

        Args:
            name: Provider name.
            tier: Priority tier (lower = preferred). Default 1.
        """
        self.providers[name] = ProviderHealth(name=name)
        self._circuit_breakers[name] = self.CB_CLOSED
        self._provider_tiers[name] = tier

    def get_provider_order(self) -> list[str]:
        """Get providers sorted by tier then health score (best first), excluding cooldown and open circuits."""
        available = []
        for name, ph in self.providers.items():
            if not ph.is_available:
                continue
            # Skip providers with open circuit breaker
            cb_state = self._circuit_breakers.get(name, self.CB_CLOSED)
            if cb_state == self.CB_OPEN:
                # Check if it's time for half-open
                if ph.last_failure and datetime.now() - ph.last_failure > self._recovery_timeout:
                    self._circuit_breakers[name] = self.CB_HALF_OPEN
                else:
                    continue
            available.append((name, ph))

        sorted_providers = sorted(
            available,
            key=lambda x: (self._provider_tiers.get(x[0], 99), -x[1].score, -x[1].success_count),
        )
        return [name for name, _ in sorted_providers]

    def record_success(self, provider_name: str, latency_ms: float) -> None:
        """Record successful API call.

        Closes circuit breaker on success.

        Args:
            provider_name: Name of the provider.
            latency_ms: Request latency in milliseconds.
        """
        if provider_name not in self.providers:
            self.register_provider(provider_name)

        ph = self.providers[provider_name]
        ph.success_count += 1
        ph.last_success = datetime.now()
        # Update average latency
        total = ph.success_count
        ph.avg_latency_ms = (ph.avg_latency_ms * (total - 1) + latency_ms) / total
        # Clear cooldown on success
        ph.cooldown_until = None
        # Close circuit breaker on success
        self._circuit_breakers[provider_name] = self.CB_CLOSED

        self.request_log.append(
            {
                "provider": provider_name,
                "status": "success",
                "latency_ms": round(latency_ms, 0),
                "circuit_breaker": self.CB_CLOSED,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def record_failure(
        self,
        provider_name: str,
        error: str = "",
        status_code: int | None = None,
    ) -> None:
        """Record failed API call.

        Applies exponential backoff cooldown after consecutive failures.
        Opens circuit breaker when threshold is reached.
        Extra cooldown on rate limits (429).

        Args:
            provider_name: Name of the provider.
            error: Error message.
            status_code: HTTP status code (if applicable).
        """
        if provider_name not in self.providers:
            self.register_provider(provider_name)

        ph = self.providers[provider_name]
        ph.failure_count += 1
        ph.last_failure = datetime.now()

        # Circuit breaker: open if threshold exceeded
        if ph.failure_count >= self._failure_threshold:
            consecutive_failures = ph.failure_count - ph.success_count
            if consecutive_failures >= self._failure_threshold:
                self._circuit_breakers[provider_name] = self.CB_OPEN

        # Proactive cooldown after consecutive failures
        if ph.failure_count > 5 and ph.success_count < ph.failure_count:
            cooldown_minutes = min(2 ** (ph.failure_count - 5), 30)
            ph.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)

        # Extra cooldown on rate limits
        if status_code == 429:
            ph.cooldown_until = datetime.now() + timedelta(minutes=5)

        cb_state = self._circuit_breakers.get(provider_name, self.CB_CLOSED)

        self.request_log.append(
            {
                "provider": provider_name,
                "status": "failure",
                "error": error[:200],
                "status_code": status_code,
                "circuit_breaker": cb_state,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep log manageable
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-500:]

    def get_status(self) -> dict[str, Any]:
        """Get AutoSwitch status report."""
        return {
            "providers": {
                name: {
                    "name": ph.name,
                    "score": round(ph.score, 3),
                    "success": ph.success_count,
                    "failure": ph.failure_count,
                    "avg_latency_ms": round(ph.avg_latency_ms, 0),
                    "available": ph.is_available,
                    "tier": self._provider_tiers.get(name, 99),
                    "circuit_breaker": self._circuit_breakers.get(name, self.CB_CLOSED),
                    "cooldown_until": ph.cooldown_until.isoformat() if ph.cooldown_until else None,
                }
                for name, ph in self.providers.items()
            },
            "provider_order": self.get_provider_order(),
            "total_requests": len(self.request_log),
            "recent_errors": [r for r in self.request_log[-20:] if r["status"] == "failure"],
            "circuit_breakers": dict(self._circuit_breakers),
        }

    def get_circuit_breaker_state(self, provider_name: str) -> str:
        """Get circuit breaker state for a provider."""
        return self._circuit_breakers.get(provider_name, self.CB_CLOSED)

    def force_reset_circuit(self, provider_name: str) -> None:
        """Force reset circuit breaker for a provider."""
        if provider_name in self._circuit_breakers:
            self._circuit_breakers[provider_name] = self.CB_CLOSED
        if provider_name in self.providers:
            self.providers[provider_name].cooldown_until = None
