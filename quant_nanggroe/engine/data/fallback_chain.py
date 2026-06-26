"""Data fallback chain with circuit breaker support.

Tries providers in priority order. Skips providers whose circuit
breaker is open. Tracks per-provider success/failure stats.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional

from quant_nanggroe.engine.data.provider_interface import (
    DataCategory, DataRequest, DataResponse, QNAProviderBase,
)


class CircuitBreaker:
    """Per-provider circuit breaker with auto-reset."""

    def __init__(self, max_failures: int = 3, reset_seconds: int = 30) -> None:
        self._max_failures = max_failures
        self._reset_seconds = reset_seconds
        self._failures: Dict[str, int] = defaultdict(int)
        self._last_failure: Dict[str, float] = {}

    def can_try(self, provider_name: str) -> bool:
        failures = self._failures.get(provider_name, 0)
        if failures >= self._max_failures:
            elapsed = time.time() - self._last_failure.get(provider_name, 0)
            if elapsed > self._reset_seconds:
                self._failures[provider_name] = 0
                return True
            return False
        return True

    def record_failure(self, provider_name: str) -> None:
        self._failures[provider_name] += 1
        self._last_failure[provider_name] = time.time()

    def record_success(self, provider_name: str) -> None:
        self._failures[provider_name] = 0

    def status(self, provider_name: str) -> Dict:
        return {
            "state": "open" if not self.can_try(provider_name) else "closed",
            "failures": self._failures.get(provider_name, 0),
        }


class DataFallbackChain:
    """Try providers in order. Fall through on failure. Skip open circuits."""

    def __init__(self, providers: List[QNAProviderBase]) -> None:
        self.providers = providers
        self.circuit_breaker = CircuitBreaker()
        self._stats: Dict[str, Dict] = defaultdict(
            lambda: {"success": 0, "failure": 0, "skip": 0}
        )

    def fetch(self, request: DataRequest) -> DataResponse:
        for provider in self.providers:
            if not self.circuit_breaker.can_try(provider.name):
                self._stats[provider.name]["skip"] += 1
                continue
            try:
                resp = provider.fetch(request)
                self.circuit_breaker.record_success(provider.name)
                self._stats[provider.name]["success"] += 1
                resp.provider = provider.name
                return resp
            except Exception:
                self.circuit_breaker.record_failure(provider.name)
                self._stats[provider.name]["failure"] += 1

        raise RuntimeError("All providers failed")

    def get_stats(self) -> Dict[str, Dict]:
        return dict(self._stats)


_registry_instance = None


def create_default_chain(
    registry=None,
    category: Optional[DataCategory] = None,
) -> DataFallbackChain:
    if registry is None:
        from quant_nanggroe.engine.data.provider_registry import ProviderRegistry
        global _registry_instance
        if _registry_instance is None:
            _registry_instance = ProviderRegistry()
        registry = _registry_instance

    providers = registry.get_by_category(category) if category is not None else []
    if not providers:
        providers = list(registry._providers.values())

    return DataFallbackChain(providers)
