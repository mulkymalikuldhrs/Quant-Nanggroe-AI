"""Source orchestration manager.

Provides the :class:`SourceManager` that coordinates all intelligence
sources, runs sweeps, aggregates results, deduplicates items, and
scores relevance across the full source portfolio.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ConfigDict

from .base import (
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceProvider,
    SourceReliability,
    SourceResult,
    SourceStatus,
)
from .osint import OSINTSource
from .economic import EconomicSource
from .market import MarketSource

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────────────────


class SweepResult(BaseModel):
    """Result from a full source sweep."""

    model_config = ConfigDict(frozen=False)

    sweep_id: str = ""
    total_items: int = 0
    deduplicated_items: int = 0
    items_by_category: Dict[str, int] = Field(default_factory=dict)
    items_by_source: Dict[str, int] = Field(default_factory=dict)
    errors_by_source: Dict[str, List[str]] = Field(default_factory=dict)
    elapsed_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        """True if any items were collected."""
        return self.total_items > 0


class AggregatedResult(BaseModel):
    """Aggregated and scored intelligence result."""

    model_config = ConfigDict(frozen=False)

    items: List[SourceItem] = Field(default_factory=list)
    total_items: int = 0
    high_relevance_count: int = 0
    average_relevance: float = 0.0
    average_confidence: float = 0.0
    categories_covered: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0


# ── Manager ──────────────────────────────────────────────────────────────────


class SourceManager:
    """Orchestrates all intelligence sources.

    Manages source registration, sweep execution, result aggregation,
    deduplication, and relevance scoring.

    Usage::

        manager = SourceManager()
        manager.register(OSINTSource())
        manager.register(EconomicSource())
        manager.register(MarketSource())

        result = await manager.sweep_all(max_items=200)
        scored = manager.aggregate_and_score(result)
    """

    def __init__(self, config: Optional[SourceConfig] = None):
        self._sources: Dict[str, SourceProvider] = {}
        self._config = config or SourceConfig()
        self._seen_hashes: Set[str] = set()
        self._max_seen = 50000
        self._sweep_count: int = 0
        self._last_sweep: Optional[datetime] = None

    # ── Registration ────────────────────────────────────────────────────

    def register(self, source: SourceProvider) -> None:
        """Register a source provider.

        Parameters
        ----------
        source:
            SourceProvider instance to register.
        """
        if source.name in self._sources:
            logger.warning("Source '%s' already registered, replacing", source.name)
        self._sources[source.name] = source
        logger.info("Registered source: %s (%s)", source.name, source.category.value)

    def unregister(self, name: str) -> bool:
        """Unregister a source by name.

        Returns
        -------
        bool
            True if the source was found and removed.
        """
        if name in self._sources:
            del self._sources[name]
            logger.info("Unregistered source: %s", name)
            return True
        return False

    def get_source(self, name: str) -> Optional[SourceProvider]:
        """Look up a registered source by name."""
        return self._sources.get(name)

    @property
    def sources(self) -> Dict[str, SourceProvider]:
        """All registered sources."""
        return dict(self._sources)

    @property
    def source_count(self) -> int:
        """Number of registered sources."""
        return len(self._sources)

    # ── Sweep operations ────────────────────────────────────────────────

    async def sweep_all(self, max_items: int = 200) -> SweepResult:
        """Run a sweep across all registered sources concurrently.

        Parameters
        ----------
        max_items:
            Maximum total items to collect.

        Returns
        -------
        SweepResult
            Aggregated sweep result with deduplication stats.
        """
        start = time.monotonic()
        self._sweep_count += 1
        self._last_sweep = datetime.now(timezone.utc)

        all_items: List[SourceItem] = []
        errors_by_source: Dict[str, List[str]] = {}
        items_by_source: Dict[str, int] = {}
        items_by_category: Dict[str, int] = {}

        if not self._sources:
            return SweepResult(
                sweep_id=f"sweep-{self._sweep_count}",
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

        per_source = max(1, max_items // len(self._sources))

        # Run all sources concurrently
        tasks = {}
        for name, source in self._sources.items():
            tasks[name] = asyncio.create_task(
                source.scan(max_items=per_source),
            )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (name, _task), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                errors_by_source[name] = [str(result)]
                continue
            if not isinstance(result, SourceResult):
                continue

            items_by_source[name] = len(result.items)
            for error in result.errors:
                errors_by_source.setdefault(name, []).append(error)

            for item in result.items:
                cat = item.category.value
                items_by_category[cat] = items_by_category.get(cat, 0) + 1
                all_items.append(item)

        # Deduplicate
        deduped = self._deduplicate(all_items)

        elapsed = (time.monotonic() - start) * 1000
        return SweepResult(
            sweep_id=f"sweep-{self._sweep_count}",
            total_items=len(all_items),
            deduplicated_items=len(deduped),
            items_by_category=items_by_category,
            items_by_source=items_by_source,
            errors_by_source=errors_by_source,
            elapsed_ms=elapsed,
        )

    async def fetch_all(self, query: str, max_items: int = 100) -> AggregatedResult:
        """Fetch from all sources with a targeted query.

        Parameters
        ----------
        query:
            Search query string.
        max_items:
            Maximum total items.

        Returns
        -------
        AggregatedResult
            Aggregated and scored results.
        """
        start = time.monotonic()
        all_items: List[SourceItem] = []

        if not self._sources:
            return AggregatedResult(elapsed_ms=(time.monotonic() - start) * 1000)

        per_source = max(1, max_items // len(self._sources))

        tasks = {}
        for name, source in self._sources.items():
            tasks[name] = asyncio.create_task(
                source.fetch(query, max_items=per_source),
            )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        sources_used: List[str] = []
        categories: Set[str] = set()

        for (name, _task), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                continue
            if not isinstance(result, SourceResult):
                continue

            sources_used.append(name)
            for item in result.items:
                categories.add(item.category.value)
                all_items.append(item)

        # Deduplicate and score
        deduped = self._deduplicate(all_items)
        scored = self._score_relevance(deduped, query)

        # Sort by relevance (descending)
        scored.sort(key=lambda i: i.relevance_score, reverse=True)
        scored = scored[:max_items]

        high_relevance = sum(1 for i in scored if i.relevance_score >= 0.7)
        avg_relevance = sum(i.relevance_score for i in scored) / max(1, len(scored))
        avg_confidence = sum(i.confidence for i in scored) / max(1, len(scored))

        elapsed = (time.monotonic() - start) * 1000
        return AggregatedResult(
            items=scored,
            total_items=len(scored),
            high_relevance_count=high_relevance,
            average_relevance=round(avg_relevance, 3),
            average_confidence=round(avg_confidence, 3),
            categories_covered=sorted(categories),
            sources_used=sources_used,
            elapsed_ms=elapsed,
        )

    # ── Scoring and deduplication ───────────────────────────────────────

    def _deduplicate(self, items: List[SourceItem]) -> List[SourceItem]:
        """Remove duplicate items based on content hash."""
        seen: Set[str] = set()
        deduped: List[SourceItem] = []

        for item in items:
            h = self._hash_item(item)
            if h not in seen:
                seen.add(h)
                self._seen_hashes.add(h)
                deduped.append(item)

        # Prune seen hashes
        if len(self._seen_hashes) > self._max_seen:
            excess = len(self._seen_hashes) - self._max_seen
            for _ in range(excess):
                try:
                    self._seen_hashes.pop()
                except KeyError:
                    break

        return deduped

    def _score_relevance(self, items: List[SourceItem], query: str) -> List[SourceItem]:
        """Score items for relevance to a query.

        Adjusts relevance_score based on query term overlap,
        source reliability, and item recency.
        """
        if not query:
            return items

        query_terms = set(query.lower().split())
        reliability_weights = {
            SourceReliability.RELIABLE: 1.0,
            SourceReliability.USUALLY_RELIABLE: 0.9,
            SourceReliability.FAIRLY_RELIABLE: 0.7,
            SourceReliability.NOT_USUALLY_RELIABLE: 0.5,
            SourceReliability.UNRELIABLE: 0.3,
            SourceReliability.UNABLE_TO_JUDGE: 0.5,
        }

        for item in items:
            # Query term overlap
            text = f"{item.title} {item.summary}".lower()
            text_terms = set(text.split())
            overlap = len(query_terms & text_terms)
            term_score = min(1.0, overlap / max(1, len(query_terms)))

            # Reliability boost
            rel_weight = reliability_weights.get(item.reliability, 0.5)

            # Combined score
            item.relevance_score = round(
                0.6 * term_score + 0.3 * item.relevance_score + 0.1 * rel_weight,
                3,
            )

        return items

    @staticmethod
    def _hash_item(item: SourceItem) -> str:
        """Create a content hash for deduplication."""
        key = f"{item.source_name}:{item.title}:{item.summary[:200]}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    # ── Health ──────────────────────────────────────────────────────────

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered sources."""
        results: Dict[str, Dict[str, Any]] = {}
        for name, source in self._sources.items():
            try:
                results[name] = await source.health_check()
            except Exception as exc:
                results[name] = {"status": SourceStatus.OFFLINE, "error": str(exc)}
        return results

    # ── Convenience factory ─────────────────────────────────────────────

    @classmethod
    def create_default(cls) -> SourceManager:
        """Create a SourceManager with all built-in sources registered."""
        manager = cls()
        manager.register(OSINTSource())
        manager.register(EconomicSource())
        manager.register(MarketSource())
        return manager

    @property
    def stats(self) -> Dict[str, Any]:
        """Manager statistics."""
        return {
            "source_count": self.source_count,
            "sources": list(self._sources.keys()),
            "sweep_count": self._sweep_count,
            "last_sweep": self._last_sweep.isoformat() if self._last_sweep else None,
            "seen_hashes": len(self._seen_hashes),
        }
