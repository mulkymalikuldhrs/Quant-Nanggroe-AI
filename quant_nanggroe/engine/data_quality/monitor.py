"""Data Quality Monitor — tracks staleness and health for all data providers.

Watches TTLCache-backed providers in tradebobby/. Each provider's cache
carries its own TTL; this monitor records last_fetch success per provider
and flags staleness when cache expiry exceeds the threshold.

Usage::

    from quant_nanggroe.engine.data_quality import DataQualityMonitor

    dq = DataQualityMonitor(default_stale_threshold=600)  # 10 min
    dq.record_success("macro_pulse")
    health = dq.get_health()
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    """Runtime state for a single data provider."""
    name: str
    last_success: Optional[float] = None  # monotonic ts of last successful fetch
    last_failure: Optional[float] = None  # monotonic ts of last failure
    failure_count: int = 0
    success_count: int = 0
    last_error: str = ""
    stale_threshold: float = 600.0  # seconds before data considered stale
    expected_keys: list[str] = field(default_factory=list)

    @property
    def age_seconds(self) -> Optional[float]:
        """Seconds since last_success. None if never succeeded."""
        if self.last_success is None:
            return None
        return time.monotonic() - self.last_success

    @property
    def is_stale(self) -> bool:
        """True if data is older than stale_threshold or never fetched."""
        age = self.age_seconds
        if age is None:
            return True
        return age > self.stale_threshold

    @property
    def status(self) -> str:
        """Human-readable status: healthy, stale, degraded, failed."""
        if self.last_success is None:
            return "failed" if self.failure_count > 0 else "pending"
        if self.failure_count > 0:
            return "degraded"
        if self.is_stale:
            return "stale"
        return "healthy"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        age = self.age_seconds
        return {
            "name": self.name,
            "status": self.status,
            "last_success_epoch": self.last_success,
            "last_success_iso": (
                datetime.fromtimestamp(self.last_success, tz=timezone.utc).isoformat()
                if self.last_success is not None
                else None
            ),
            "last_failure_epoch": self.last_failure,
            "last_failure_iso": (
                datetime.fromtimestamp(self.last_failure, tz=timezone.utc).isoformat()
                if self.last_failure is not None
                else None
            ),
            "staleness_seconds": round(age, 1) if age is not None else None,
            "stale_threshold_seconds": self.stale_threshold,
            "is_stale": self.is_stale,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.failure_count,
            "last_error": self.last_error,
            "expected_keys": self.expected_keys,
        }


class DataQualityMonitor:
    """Thread-safe monitor for data provider health and staleness.

    Integrates with the existing TTLCache pattern — providers record
    success/failure after cache operations. The monitor itself does NOT
    perform fetches; it only tracks outcomes reported by callers.
    """

    # Default stale thresholds per provider (seconds), aligned with each
    # provider's _CACHE TTL where possible.
    DEFAULT_THRESHOLDS: dict[str, float] = {
        # tradebobby providers
        "macro_pulse": 600,        # TTL 300, threshold 2x → 10 min
        "crypto_pulse": 600,       # TTL 300
        "cvd": 300,                # TTL 120, threshold 2.5x
        "liquidity_wall": 120,     # in-memory deque, no TTL
        "currency_strength": 600,  # TTL 300
        "etf_flows": 3600,         # TTL 1800, threshold 2x → 1 hr
        "news_scanner": 600,       # estimated
        "onchain_btc": 600,        # estimated
        "reddit_mania": 1200,      # estimated
        "derivatives": 600,        # estimated
        "econ_calendar": 1800,     # event-based, less frequent
        "earnings_cal": 3600,     # daily events
        # COT provider (terminal.py /cot endpoint)
        "cot": 86400,              # 24h — weekly COT data
    }

    # Expected keys per provider for missing-value detection
    EXPECTED_KEYS: dict[str, list[str]] = {
        "macro_pulse": ["vix", "us10y", "us3m", "dxy"],
        "crypto_pulse": ["current", "btc_dominance"],
        "cvd": ["symbols", "summary"],
        "currency_strength": ["strength", "ranking"],
        "etf_flows": ["etfs", "groups", "signals"],
        "cot": ["markets"],
    }

    def __init__(self, default_stale_threshold: float = 600.0) -> None:
        self._default_threshold = default_stale_threshold
        self._providers: dict[str, ProviderState] = {}
        self._lock = threading.Lock()
        # Seed known providers
        for name, thresh in self.DEFAULT_THRESHOLDS.items():
            self._providers[name] = ProviderState(
                name=name,
                stale_threshold=thresh,
                expected_keys=self.EXPECTED_KEYS.get(name, []),
            )

    def register_provider(self, name: str, stale_threshold: float = 600.0,
                         expected_keys: list[str] | None = None) -> None:
        """Register a new provider or update an existing one's config."""
        with self._lock:
            self._providers[name] = ProviderState(
                name=name,
                stale_threshold=stale_threshold,
                expected_keys=expected_keys or [],
            )

    def record_success(self, provider_name: str, data: Any | None = None) -> None:
        """Record a successful fetch for a provider.

        If `data` is provided, checks for missing expected keys
        and logs warnings (does NOT fail — graceful degradation).
        """
        with self._lock:
            state = self._providers.get(provider_name)
            if state is None:
                state = ProviderState(
                    name=provider_name,
                    stale_threshold=self._default_threshold,
                    expected_keys=self.EXPECTED_KEYS.get(provider_name, []),
                )
                self._providers[provider_name] = state

            now = time.monotonic()
            state.last_success = now
            state.success_count += 1
            state.failure_count = 0  # reset consecutive failures
            state.last_error = ""

            # Missing-value detection (if data provided and expected_keys set)
            if data is not None and state.expected_keys:
                missing = self._detect_missing(data, state.expected_keys)
                if missing:
                    logger.warning(
                        "data_quality_missing_keys: provider=%s, missing=%s",
                        provider_name, missing,
                    )

    def record_failure(self, provider_name: str, error: str = "") -> None:
        """Record a failed fetch for a provider."""
        with self._lock:
            state = self._providers.get(provider_name)
            if state is None:
                state = ProviderState(
                    name=provider_name,
                    stale_threshold=self._default_threshold,
                    expected_keys=self.EXPECTED_KEYS.get(provider_name, []),
                )
                self._providers[provider_name] = state

            now = time.monotonic()
            state.last_failure = now
            state.failure_count += 1
            state.last_error = error or "unknown error"

    @staticmethod
    def _detect_missing(data: Any, expected_keys: list[str]) -> list[str]:
        """Check if expected keys are present in the data (best-effort)."""
        if not isinstance(data, dict):
            return expected_keys  # can't introspect — report all as missing
        missing = []
        for k in expected_keys:
            if k not in data or data[k] is None:
                missing.append(k)
        return missing

    def get_provider_state(self, provider_name: str) -> Optional[ProviderState]:
        """Get the ProviderState for a provider, or None if not registered."""
        with self._lock:
            return self._providers.get(provider_name)

    def get_health(self) -> dict[str, Any]:
        """Return health summary for all tracked providers.

        Returns::
            {
                "timestamp": ISO string,
                "overall_status": "healthy" | "degraded" | "stale" | "offline",
                "total_providers": N,
                "healthy_count": N,
                "stale_count": N,
                "degraded_count": N,
                "failed_count": N,
                "providers": { name: ProviderState.to_dict() },
            }
        """
        with self._lock:
            provider_dicts: dict[str, dict[str, Any]] = {}
            healthy = 0
            stale = 0
            degraded = 0
            failed = 0

            for name, state in self._providers.items():
                d = state.to_dict()
                provider_dicts[name] = d
                s = state.status
                if s == "healthy":
                    healthy += 1
                elif s == "stale":
                    stale += 1
                elif s == "degraded":
                    degraded += 1
                else:  # failed or pending
                    failed += 1

            total = len(self._providers)
            if failed == total and total > 0:
                overall = "offline"
            elif failed > 0 or stale > 0 or degraded > 0:
                overall = "degraded" if stale == 0 else "stale"
            else:
                overall = "healthy"

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": overall,
                "total_providers": total,
                "healthy_count": healthy,
                "stale_count": stale,
                "degraded_count": degraded,
                "failed_count": failed,
                "providers": provider_dicts,
            }

    def check_data_integrity(self, provider_name: str, data: Any) -> dict[str, Any]:
        """Validate data from a provider: missing keys, null values, stale timestamps.

        Returns a dict with `valid` (bool), `issues` (list of str), `score` (0-100).
        """
        state = self.get_provider_state(provider_name)
        issues: list[str] = []
        score = 100

        if state is None:
            return {"valid": True, "issues": [], "score": 100}  # unknown provider, no checks

        # Missing expected keys
        if state.expected_keys:
            missing = self._detect_missing(data, state.expected_keys)
            if missing:
                issues.append(f"missing_keys: {missing}")
                score -= 20

        # Staleness check
        if state.is_stale:
            age = state.age_seconds
            issues.append(f"stale: {age:.1f}s old (threshold {state.stale_threshold}s)")
            score = max(0, score - 30)

        # Null/empty data
        if data is None:
            issues.append("data_is_none")
            score = 0
        elif isinstance(data, dict) and not data:
            issues.append("data_is_empty_dict")
            score = max(0, score - 25)
        elif isinstance(data, (list, str)) and not data:
            issues.append("data_is_empty")
            score = max(0, score - 25)

        return {
            "valid": score >= 50,
            "issues": issues,
            "score": max(0, score),
        }


# ── Module-level singleton ───────────────────────────────────────────────────

_monitor: DataQualityMonitor | None = None


def get_monitor() -> DataQualityMonitor:
    """Get or create the global DataQualityMonitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = DataQualityMonitor()
    return _monitor
