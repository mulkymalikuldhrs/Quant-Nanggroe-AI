"""
Research Memory — Cached Research Results with TTL
===================================================
Stores and retrieves research findings with time-to-live (TTL)
caching, symbol-based indexing, and automatic expiration.

Features:
    - Symbol-based research storage and retrieval
    - TTL-based cache expiration (stale research is rejected)
    - Category and tag organization
    - Confidence scoring with decay
    - Deduplication of research entries
    - Bulk operations for efficiency
    - Statistics and monitoring

Use cases:
    - Cache fundamental analysis results
    - Store sentiment analysis outputs
    - Persist macro research between sessions
    - Avoid redundant API calls for recent data

Usage:
    memory = ResearchMemory(default_ttl_hours=4)
    memory.add_research("AAPL", {
        "category": "fundamental",
        "title": "Q4 Earnings Analysis",
        "content": "Revenue beat by 5%...",
        "confidence": 0.85,
    })
    research = memory.get_research("AAPL", max_age_hours=2)
    for entry in research:
        print(f"{entry.title}: {entry.confidence:.0%}")
"""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class ResearchEntry(BaseModel):
    """A single research entry with TTL metadata."""

    id: str = ""
    symbol: str
    category: str = "general"  # fundamental, technical, macro, sentiment, crypto
    title: str = ""
    content: str
    source: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Whether this entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def age_hours(self) -> float:
        """Age of this entry in hours."""
        delta = datetime.now() - self.created_at
        return delta.total_seconds() / 3600

    @property
    def effective_confidence(self) -> float:
        """
        Confidence adjusted for age (decays over time).

        Uses exponential decay: conf * e^(-0.1 * age_hours)
        Half-life ≈ 7 hours
        """
        import math
        decay_factor = math.exp(-0.1 * self.age_hours)
        return self.confidence * decay_factor


class ResearchStats(BaseModel):
    """Statistics about the research memory."""

    total_entries: int = 0
    total_symbols: int = 0
    expired_entries: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_age_hours: float = 0.0
    total_accesses: int = 0


# ══════════════════════════════════════════════════════════════════════
# RESEARCH MEMORY
# ══════════════════════════════════════════════════════════════════════


class ResearchMemory:
    """
    Persistent research memory with TTL-based caching.

    Stores research results indexed by symbol with automatic
    expiration, confidence decay, and category organization.

    Args:
        default_ttl_hours: Default time-to-live for research entries
        max_entries_per_symbol: Maximum entries per symbol (FIFO eviction)
        max_total_entries: Maximum total entries across all symbols
        confidence_decay_rate: Rate of confidence decay per hour

    Example:
        memory = ResearchMemory(default_ttl_hours=4)
        memory.add_research("AAPL", {
            "category": "fundamental",
            "title": "Earnings Analysis",
            "content": "Strong Q4 results...",
            "confidence": 0.85,
            "tags": ["earnings", "tech"],
        })
        results = memory.get_research("AAPL", max_age_hours=2)
    """

    def __init__(
        self,
        default_ttl_hours: float = 4.0,
        max_entries_per_symbol: int = 50,
        max_total_entries: int = 10_000,
        confidence_decay_rate: float = 0.1,
    ) -> None:
        self._default_ttl = timedelta(hours=default_ttl_hours)
        self._max_per_symbol = max_entries_per_symbol
        self._max_total = max_total_entries
        self._decay_rate = confidence_decay_rate

        # Primary storage: symbol -> list of entries
        self._entries: dict[str, list[ResearchEntry]] = defaultdict(list)

        # Index: entry_id -> (symbol, index) for O(1) lookup
        self._id_index: dict[str, tuple[str, int]] = {}

        # Tag index: tag -> set of entry_ids
        self._tag_index: dict[str, set[str]] = defaultdict(set)

        # Category index: category -> set of entry_ids
        self._category_index: dict[str, set[str]] = defaultdict(set)

        logger.info(
            "ResearchMemory initialized (ttl=%.1fh, max/symbol=%d, max_total=%d)",
            default_ttl_hours, max_entries_per_symbol, max_total_entries,
        )

    # ══════════════════════════════════════════════════════════════════
    # ADD RESEARCH
    # ══════════════════════════════════════════════════════════════════

    def add_research(
        self,
        symbol: str,
        research_data: dict[str, Any] | ResearchEntry,
        ttl_hours: float | None = None,
    ) -> ResearchEntry:
        """
        Add a research entry for a symbol.

        Args:
            symbol: Trading symbol
            research_data: Dict with research data or ResearchEntry object.
                Dict keys: category, title, content, source, confidence, tags, metadata
            ttl_hours: Time-to-live in hours (overrides default)

        Returns:
            The created ResearchEntry

        Raises:
            ValueError: If required fields are missing
        """
        symbol = symbol.upper().strip()

        # Normalize input
        if isinstance(research_data, ResearchEntry):
            entry = research_data.model_copy()
            entry.symbol = symbol
        elif isinstance(research_data, dict):
            content = research_data.get("content", research_data.get("text", ""))
            if not content:
                raise ValueError("Research data must include 'content' or 'text' field")

            entry = ResearchEntry(
                id=self._generate_id(symbol, content),
                symbol=symbol,
                category=research_data.get("category", "general"),
                title=research_data.get("title", ""),
                content=content,
                source=research_data.get("source", ""),
                confidence=float(research_data.get("confidence", 0.5)),
                tags=research_data.get("tags", []),
                metadata=research_data.get("metadata", {}),
            )
        else:
            raise ValueError(f"Invalid research_data type: {type(research_data)}")

        # Set expiration
        ttl = timedelta(hours=ttl_hours) if ttl_hours is not None else self._default_ttl
        entry.expires_at = entry.created_at + ttl

        # Check for duplicate
        if entry.id in self._id_index:
            logger.debug("Duplicate research entry: %s", entry.id)
            # Update existing entry
            existing_symbol, existing_idx = self._id_index[entry.id]
            if existing_idx < len(self._entries[existing_symbol]):
                self._entries[existing_symbol][existing_idx] = entry
                self._update_indices(entry)
                return entry

        # Add to storage
        self._entries[symbol].append(entry)
        idx = len(self._entries[symbol]) - 1
        self._id_index[entry.id] = (symbol, idx)

        # Update indices
        self._update_indices(entry)

        # Enforce limits
        self._enforce_per_symbol_limit(symbol)
        self._enforce_total_limit()

        logger.info(
            "Added research for %s: category=%s, title=%s, confidence=%.2f",
            symbol, entry.category, entry.title[:30], entry.confidence,
        )

        return entry

    def add_research_batch(
        self,
        entries: list[tuple[str, dict[str, Any]]],
    ) -> list[ResearchEntry]:
        """
        Add multiple research entries at once.

        Args:
            entries: List of (symbol, research_data) tuples

        Returns:
            List of created ResearchEntry objects
        """
        results = []
        for symbol, data in entries:
            try:
                entry = self.add_research(symbol, data)
                results.append(entry)
            except Exception as exc:
                logger.warning("Failed to add research for %s: %s", symbol, exc)
        return results

    # ══════════════════════════════════════════════════════════════════
    # GET RESEARCH
    # ══════════════════════════════════════════════════════════════════

    def get_research(
        self,
        symbol: str,
        max_age_hours: float | None = None,
        category: str | None = None,
        min_confidence: float = 0.0,
        include_expired: bool = False,
        limit: int | None = None,
    ) -> list[ResearchEntry]:
        """
        Retrieve research entries for a symbol.

        Args:
            symbol: Trading symbol
            max_age_hours: Maximum age in hours (None = no limit)
            category: Optional category filter
            min_confidence: Minimum confidence threshold
            include_expired: Whether to include expired entries
            limit: Maximum number of entries to return

        Returns:
            List of matching ResearchEntry objects, sorted by confidence (descending)
        """
        symbol = symbol.upper().strip()
        entries = self._entries.get(symbol, [])

        results = []
        cutoff = datetime.now() - timedelta(hours=max_age_hours) if max_age_hours else None

        for entry in entries:
            # Filter expired
            if not include_expired and entry.is_expired:
                continue

            # Filter by age
            if cutoff and entry.created_at < cutoff:
                continue

            # Filter by category
            if category and entry.category != category:
                continue

            # Filter by confidence (use effective confidence with decay)
            if entry.effective_confidence < min_confidence:
                continue

            # Update access stats
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            results.append(entry)

        # Sort by effective confidence (highest first)
        results.sort(key=lambda e: e.effective_confidence, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_latest(
        self,
        symbol: str,
        category: str | None = None,
    ) -> ResearchEntry | None:
        """
        Get the most recent research entry for a symbol.

        Args:
            symbol: Trading symbol
            category: Optional category filter

        Returns:
            Most recent ResearchEntry, or None
        """
        entries = self.get_research(
            symbol, category=category, include_expired=False
        )
        if not entries:
            return None

        # Sort by creation time, most recent first
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[0]

    def get_by_id(self, entry_id: str) -> ResearchEntry | None:
        """
        Get a research entry by its ID.

        Args:
            entry_id: Entry identifier

        Returns:
            ResearchEntry or None
        """
        location = self._id_index.get(entry_id)
        if location is None:
            return None

        symbol, idx = location
        entries = self._entries.get(symbol, [])
        if idx < len(entries) and entries[idx].id == entry_id:
            entry = entries[idx]
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            return entry

        return None

    # ══════════════════════════════════════════════════════════════════
    # SEARCH
    # ══════════════════════════════════════════════════════════════════

    def search_by_tag(self, tag: str, limit: int = 20) -> list[ResearchEntry]:
        """
        Search research entries by tag.

        Args:
            tag: Tag to search for
            limit: Maximum results

        Returns:
            List of matching ResearchEntry objects
        """
        entry_ids = self._tag_index.get(tag.lower(), set())
        results = []

        for entry_id in entry_ids:
            entry = self.get_by_id(entry_id)
            if entry and not entry.is_expired:
                results.append(entry)

        results.sort(key=lambda e: e.effective_confidence, reverse=True)
        return results[:limit]

    def search_by_category(
        self,
        category: str,
        symbol: str | None = None,
        limit: int = 20,
    ) -> list[ResearchEntry]:
        """
        Search research entries by category.

        Args:
            category: Category to search for
            symbol: Optional symbol filter
            limit: Maximum results

        Returns:
            List of matching ResearchEntry objects
        """
        if symbol:
            return self.get_research(
                symbol, category=category, limit=limit
            )

        entry_ids = self._category_index.get(category, set())
        results = []

        for entry_id in entry_ids:
            entry = self.get_by_id(entry_id)
            if entry and not entry.is_expired:
                results.append(entry)

        results.sort(key=lambda e: e.effective_confidence, reverse=True)
        return results[:limit]

    def search_by_content(
        self,
        query: str,
        symbol: str | None = None,
        limit: int = 10,
    ) -> list[ResearchEntry]:
        """
        Search research entries by content (substring match).

        Args:
            query: Search query (case-insensitive)
            symbol: Optional symbol filter
            limit: Maximum results

        Returns:
            List of matching ResearchEntry objects
        """
        query_lower = query.lower()
        results = []

        symbols = [symbol.upper()] if symbol else list(self._entries.keys())

        for sym in symbols:
            for entry in self._entries.get(sym, []):
                if entry.is_expired:
                    continue
                if (
                    query_lower in entry.content.lower()
                    or query_lower in entry.title.lower()
                ):
                    results.append(entry)

        results.sort(key=lambda e: e.effective_confidence, reverse=True)
        return results[:limit]

    # ══════════════════════════════════════════════════════════════════
    # DELETE AND CLEANUP
    # ══════════════════════════════════════════════════════════════════

    def delete_research(self, entry_id: str) -> bool:
        """
        Delete a specific research entry.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if entry was found and deleted
        """
        location = self._id_index.get(entry_id)
        if location is None:
            return False

        symbol, idx = location
        entries = self._entries.get(symbol, [])
        if idx < len(entries) and entries[idx].id == entry_id:
            entry = entries[idx]

            # Remove from indices
            self._id_index.pop(entry_id, None)
            for tag in entry.tags:
                self._tag_index.get(tag.lower(), set()).discard(entry_id)
            self._category_index.get(entry.category, set()).discard(entry_id)

            # Remove from list (mark as None to preserve indices)
            entries[idx] = None  # type: ignore

            logger.debug("Deleted research entry: %s", entry_id)
            return True

        return False

    def clear_symbol(self, symbol: str) -> int:
        """
        Clear all research entries for a symbol.

        Args:
            symbol: Symbol to clear

        Returns:
            Number of entries removed
        """
        symbol = symbol.upper()
        entries = self._entries.get(symbol, [])
        count = len([e for e in entries if e is not None])

        # Remove from indices
        for entry in entries:
            if entry is not None:
                self._id_index.pop(entry.id, None)
                for tag in entry.tags:
                    self._tag_index.get(tag.lower(), set()).discard(entry.id)
                self._category_index.get(entry.category, set()).discard(entry.id)

        self._entries.pop(symbol, None)
        logger.info("Cleared %d entries for symbol %s", count, symbol)
        return count

    def clear_all(self) -> None:
        """Clear all research entries."""
        self._entries.clear()
        self._id_index.clear()
        self._tag_index.clear()
        self._category_index.clear()
        logger.info("Cleared all research entries")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of expired entries removed
        """
        expired_ids = []

        for symbol, entries in self._entries.items():
            for entry in entries:
                if entry is not None and entry.is_expired:
                    expired_ids.append(entry.id)

        for entry_id in expired_ids:
            self.delete_research(entry_id)

        if expired_ids:
            logger.info("Cleaned up %d expired research entries", len(expired_ids))

        return len(expired_ids)

    # ══════════════════════════════════════════════════════════════════
    # STATISTICS
    # ══════════════════════════════════════════════════════════════════

    def get_stats(self) -> ResearchStats:
        """Get statistics about the research memory."""
        total = 0
        expired = 0
        categories: dict[str, int] = defaultdict(int)
        confidences = []
        ages = []
        total_accesses = 0

        for entries in self._entries.values():
            for entry in entries:
                if entry is None:
                    continue
                total += 1
                if entry.is_expired:
                    expired += 1
                categories[entry.category] += 1
                confidences.append(entry.effective_confidence)
                ages.append(entry.age_hours)
                total_accesses += entry.access_count

        return ResearchStats(
            total_entries=total,
            total_symbols=len(self._entries),
            expired_entries=expired,
            categories=dict(categories),
            avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
            avg_age_hours=sum(ages) / len(ages) if ages else 0.0,
            total_accesses=total_accesses,
        )

    @property
    def symbols(self) -> list[str]:
        """Get all symbols with research entries."""
        return list(self._entries.keys())

    @property
    def entry_count(self) -> int:
        """Total number of entries (including expired)."""
        return sum(
            len([e for e in entries if e is not None])
            for entries in self._entries.values()
        )

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _update_indices(self, entry: ResearchEntry) -> None:
        """Update tag and category indices for an entry."""
        for tag in entry.tags:
            self._tag_index[tag.lower()].add(entry.id)
        self._category_index[entry.category].add(entry.id)

    def _enforce_per_symbol_limit(self, symbol: str) -> None:
        """Evict oldest entries if per-symbol limit exceeded."""
        entries = self._entries.get(symbol, [])
        while len([e for e in entries if e is not None]) > self._max_per_symbol:
            # Find and remove the oldest entry
            oldest = None
            oldest_idx = -1
            for i, e in enumerate(entries):
                if e is not None and (oldest is None or e.created_at < oldest.created_at):
                    oldest = e
                    oldest_idx = i

            if oldest is not None:
                self.delete_research(oldest.id)
            else:
                break

    def _enforce_total_limit(self) -> None:
        """Evict oldest entries across all symbols if total limit exceeded."""
        while self.entry_count > self._max_total:
            # Find oldest entry across all symbols
            oldest = None
            for entries in self._entries.values():
                for e in entries:
                    if e is not None and (oldest is None or e.created_at < oldest.created_at):
                        oldest = e

            if oldest:
                self.delete_research(oldest.id)
            else:
                break

    @staticmethod
    def _generate_id(symbol: str, content: str) -> str:
        """Generate a unique entry ID from content hash."""
        raw = f"{symbol}:{content[:200]}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
