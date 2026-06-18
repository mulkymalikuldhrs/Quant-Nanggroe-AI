"""Base class for intelligence source providers.

Defines the :class:`SourceProvider` interface that all source implementations
must follow.  Every source supports async ``fetch`` (targeted query) and
``scan`` (broad sweep) operations, and exposes metadata about the kinds
of intelligence it can gather.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class SourceCategory(str, Enum):
    """Broad categories of intelligence sources."""
    GEOPOLITICAL = "geopolitical"
    ECONOMIC = "economic"
    CONFLICT = "conflict"
    SATELLITE = "satellite"
    MARKET = "market"
    SOCIAL = "social"
    CYBER = "cyber"
    ENVIRONMENTAL = "environmental"
    SUPPLY_CHAIN = "supply_chain"
    DEMOGRAPHIC = "demographic"


class SourceReliability(str, Enum):
    """Reliability rating for a source (NATO-style scale)."""
    RELIABLE = "reliable"           # A – completely reliable
    USUALLY_RELIABLE = "usually_reliable"  # B
    FAIRLY_RELIABLE = "fairly_reliable"    # C
    NOT_USUALLY_RELIABLE = "not_usually_reliable"  # D
    UNRELIABLE = "unreliable"       # E
    UNABLE_TO_JUDGE = "unable_to_judge"  # F


class SourceStatus(str, Enum):
    """Operational status of a source provider."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"


# ── Data models ──────────────────────────────────────────────────────────────


class SourceItem(BaseModel):
    """A single intelligence item from a source."""

    model_config = ConfigDict(frozen=False)

    item_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    source_name: str = ""
    category: SourceCategory = SourceCategory.GEOPOLITICAL
    reliability: SourceReliability = SourceReliability.FAIRLY_RELIABLE
    title: str = ""
    summary: str = ""
    content: str = ""
    url: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    relevance_score: float = 0.0
    confidence: float = 0.0
    tags: List[str] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for serialization."""
        return {
            "item_id": self.item_id,
            "source_name": self.source_name,
            "category": self.category.value,
            "reliability": self.reliability.value,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }


class SourceResult(BaseModel):
    """Result from a source fetch or scan operation."""

    model_config = ConfigDict(frozen=False)

    source_name: str = ""
    category: SourceCategory = SourceCategory.GEOPOLITICAL
    items: List[SourceItem] = Field(default_factory=list)
    total_available: int = 0
    fetched_count: int = 0
    errors: List[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        """True if at least one item was fetched and no critical errors."""
        return len(self.items) > 0 and len(self.errors) == 0


class SourceConfig(BaseModel):
    """Configuration for a source provider."""

    model_config = ConfigDict(frozen=False)

    enabled: bool = True
    rate_limit_per_minute: int = 60
    timeout_s: float = 30.0
    max_items: int = 100
    cache_ttl_s: int = 300
    retry_count: int = 3
    retry_delay_s: float = 1.0
    extra: Dict[str, Any] = Field(default_factory=dict)


# ── Abstract base ────────────────────────────────────────────────────────────


class SourceProvider(ABC):
    """Abstract base class for all intelligence source providers.

    Subclasses must implement:
    * :meth:`fetch` – targeted query for specific information
    * :meth:`scan`  – broad sweep for new intelligence

    Optional overrides:
    * :meth:`health_check` – verify source availability
    * :meth:`validate_config` – validate source-specific configuration
    """

    def __init__(
        self,
        name: str,
        category: SourceCategory,
        reliability: SourceReliability = SourceReliability.FAIRLY_RELIABLE,
        config: Optional[SourceConfig] = None,
    ):
        self.name = name
        self.category = category
        self.reliability = reliability
        self.config = config or SourceConfig()
        self._status: SourceStatus = SourceStatus.ACTIVE
        self._last_fetch: Optional[datetime] = None
        self._last_scan: Optional[datetime] = None
        self._fetch_count: int = 0
        self._scan_count: int = 0
        self._error_count: int = 0
        self._cache: Dict[str, Any] = {}

    # ── Abstract methods ────────────────────────────────────────────────

    @abstractmethod
    async def fetch(self, query: str, max_items: int = 50, **kwargs: Any) -> SourceResult:
        """Fetch intelligence items matching a specific query.

        Parameters
        ----------
        query:
            Search query string.
        max_items:
            Maximum number of items to return.
        **kwargs:
            Source-specific parameters.

        Returns
        -------
        SourceResult
            Result containing matched items.
        """

    @abstractmethod
    async def scan(self, max_items: int = 100, **kwargs: Any) -> SourceResult:
        """Perform a broad sweep for new intelligence.

        Parameters
        ----------
        max_items:
            Maximum number of items to return.
        **kwargs:
            Source-specific parameters.

        Returns
        -------
        SourceResult
            Result containing latest items.
        """

    # ── Health / validation ─────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Check whether the source is reachable and operational.

        Returns
        -------
        dict
            ``{"status": SourceStatus, "latency_ms": float, "error": str|None}``
        """
        return {
            "status": self._status,
            "latency_ms": 0.0,
            "error": None,
        }

    def validate_config(self) -> List[str]:
        """Validate the source configuration.

        Returns
        -------
        list[str]
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        if self.config.rate_limit_per_minute < 1:
            errors.append("rate_limit_per_minute must be >= 1")
        if self.config.timeout_s <= 0:
            errors.append("timeout_s must be > 0")
        if self.config.max_items < 1:
            errors.append("max_items must be >= 1")
        return errors

    # ── Helpers ─────────────────────────────────────────────────────────

    def _make_item(self, **kwargs: Any) -> SourceItem:
        """Create a SourceItem pre-populated with this provider's metadata."""
        defaults = {
            "source_name": self.name,
            "category": self.category,
            "reliability": self.reliability,
        }
        defaults.update(kwargs)
        return SourceItem(**defaults)

    def _make_result(self, items: Optional[List[SourceItem]] = None, **kwargs: Any) -> SourceResult:
        """Create a SourceResult pre-populated with this provider's metadata."""
        defaults = {
            "source_name": self.name,
            "category": self.category,
        }
        defaults.update(kwargs)
        if items is not None:
            defaults["items"] = items
            defaults["fetched_count"] = len(items)
        return SourceResult(**defaults)

    def _record_fetch(self) -> None:
        """Record a fetch operation."""
        self._fetch_count += 1
        self._last_fetch = datetime.now(timezone.utc)

    def _record_scan(self) -> None:
        """Record a scan operation."""
        self._scan_count += 1
        self._last_scan = datetime.now(timezone.utc)

    def _record_error(self) -> None:
        """Record an error."""
        self._error_count += 1
        if self._error_count > 10:
            self._status = SourceStatus.DEGRADED

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def status(self) -> SourceStatus:
        """Current operational status of the source."""
        return self._status

    @property
    def stats(self) -> Dict[str, Any]:
        """Provider statistics."""
        return {
            "name": self.name,
            "category": self.category.value,
            "reliability": self.reliability.value,
            "status": self._status.value,
            "fetch_count": self._fetch_count,
            "scan_count": self._scan_count,
            "error_count": self._error_count,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
        }

    def __repr__(self) -> str:
        return (
            f"SourceProvider(name={self.name!r}, category={self.category.value!r}, "
            f"status={self._status.value!r})"
        )
