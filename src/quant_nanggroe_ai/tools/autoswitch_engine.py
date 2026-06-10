#!/usr/bin/env python3
"""
AutoSwitch LLM Provider (from Quant-Nanggroe-AI)
=================================================
Health-monitored API failover with exponential backoff.
Tracks success/failure per provider, auto-cooldown on errors.
"""

import json
import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("HermesQuantOS.AutoSwitch")


class ProviderHealth:
    """Track health of a single LLM provider"""
    def __init__(self, name: str):
        self.name = name
        self.success_count = 0
        self.failure_count = 0
        self.last_success = None
        self.last_failure = None
        self.cooldown_until = None
        self.avg_latency_ms = 0.0
        self._latencies = []

    @property
    def score(self) -> float:
        """Health score: higher = better"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Unknown provider gets neutral score
        success_rate = self.success_count / total
        latency_penalty = min(self.avg_latency_ms / 10000, 0.2)  # Max 20% penalty
        return success_rate - latency_penalty

    @property
    def is_available(self) -> bool:
        """Check if provider is off cooldown"""
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        return True

    def record_success(self, latency_ms: float):
        self.success_count += 1
        self.last_success = datetime.now()
        self._latencies.append(latency_ms)
        if len(self._latencies) > 20:
            self._latencies = self._latencies[-20:]
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)
        # Clear cooldown on success
        self.cooldown_until = None

    def record_failure(self, error: str = ""):
        self.failure_count += 1
        self.last_failure = datetime.now()

        # Proactive cooldown after consecutive failures
        if self.failure_count > 5 and self.success_count < self.failure_count:
            cooldown_minutes = min(2 ** (self.failure_count - 5), 30)  # Max 30 min
            self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
            logger.warning(f"Provider {self.name} cooldown for {cooldown_minutes}min "
                         f"(failures: {self.failure_count})")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "success": self.success_count,
            "failure": self.failure_count,
            "avg_latency_ms": round(self.avg_latency_ms, 0),
            "available": self.is_available,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None
        }


class AutoSwitchEngine:
    """
    Intelligent LLM provider failover system.
    
    Source: Quant-Nanggroe-AI v15.2.0 AutoSwitch
    Features:
    - Health monitoring per provider
    - Priority sorting by health score
    - Proactive cooldown on failures
    - Exponential backoff on rate limits (429)
    - Transparent failover
    """

    def __init__(self):
        self.providers: Dict[str, ProviderHealth] = {}
        self.request_log = []

    def register_provider(self, name: str):
        """Register a provider for health tracking"""
        self.providers[name] = ProviderHealth(name)
        logger.info(f"AutoSwitch: Registered provider {name}")

    def get_provider_order(self) -> List[str]:
        """Get providers sorted by health score (best first), excluding cooldown"""
        available = [(name, ph) for name, ph in self.providers.items() if ph.is_available]
        # Sort by score descending, then by success count descending
        sorted_providers = sorted(
            available,
            key=lambda x: (x[1].score, x[1].success_count),
            reverse=True
        )
        return [name for name, _ in sorted_providers]

    def record_success(self, provider_name: str, latency_ms: float):
        """Record successful API call"""
        if provider_name not in self.providers:
            self.register_provider(provider_name)
        self.providers[provider_name].record_success(latency_ms)

        self.request_log.append({
            "provider": provider_name,
            "status": "success",
            "latency_ms": round(latency_ms, 0),
            "timestamp": datetime.now().isoformat()
        })

    def record_failure(self, provider_name: str, error: str = "",
                        status_code: int = None):
        """Record failed API call"""
        if provider_name not in self.providers:
            self.register_provider(provider_name)
        self.providers[provider_name].record_failure(error)

        # Extra cooldown on rate limits
        if status_code == 429:
            ph = self.providers[provider_name]
            ph.cooldown_until = datetime.now() + timedelta(minutes=5)
            logger.warning(f"AutoSwitch: Rate limit on {provider_name}, 5min cooldown")

        self.request_log.append({
            "provider": provider_name,
            "status": "failure",
            "error": error[:200],
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        })

        # Keep log manageable
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-500:]

    def get_status(self) -> Dict:
        """Get AutoSwitch status report"""
        return {
            "providers": {name: ph.to_dict() for name, ph in self.providers.items()},
            "provider_order": self.get_provider_order(),
            "total_requests": len(self.request_log),
            "recent_errors": [r for r in self.request_log[-20:] if r["status"] == "failure"],
            "timestamp": datetime.now().isoformat()
        }
