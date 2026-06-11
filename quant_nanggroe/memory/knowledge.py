"""Knowledge base for Quant Nanggroe AI.

Provides persistent knowledge storage with search capabilities
for agents to retrieve relevant market knowledge and past insights.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Persistent knowledge base for trading insights and market knowledge.

    Stores categorized knowledge entries with timestamps and metadata,
    enabling agents to build and retrieve institutional memory over time.

    Usage:
        kb = KnowledgeBase()
        kb.add(
            category="market_regime",
            title="BTC 2024 Halving Cycle",
            content="Post-halving supply shock typically takes 6-12 months...",
            tags=["btc", "halving", "cycle"],
        )
        results = kb.search("halving cycle", category="market_regime")
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._persist_path = Path(persist_path) if persist_path else None
        self._entries: List[Dict[str, Any]] = []
        self._id_counter: int = 0

    def add(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Add a knowledge entry.

        Args:
            category: Knowledge category
            title: Entry title
            content: Entry content
            tags: Optional tags for search
            source: Source of the knowledge
            confidence: Confidence level (0.0-1.0)
            metadata: Additional metadata

        Returns:
            Entry ID
        """
        self._id_counter += 1
        entry = {
            "id": self._id_counter,
            "category": category,
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._entries.append(entry)
        logger.debug(f"Added knowledge entry: {category}/{title}")
        return self._id_counter

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base entries.

        Args:
            query: Search query (matched against title and content)
            category: Filter by category
            tags: Filter by tags (any match)
            limit: Maximum results to return

        Returns:
            List of matching entries sorted by relevance
        """
        query_lower = query.lower()
        results = []

        for entry in self._entries:
            score = 0.0

            # Category filter
            if category and entry["category"] != category:
                continue

            # Tag filter
            if tags and not any(t in entry["tags"] for t in tags):
                continue

            # Text matching
            if query_lower in entry["title"].lower():
                score += 2.0
            if query_lower in entry["content"].lower():
                score += 1.0
            if any(query_lower in tag.lower() for tag in entry["tags"]):
                score += 1.5

            if score > 0:
                results.append({**entry, "relevance_score": score})

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    def get(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific knowledge entry by ID."""
        for entry in self._entries:
            if entry["id"] == entry_id:
                return entry
        return None

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all entries in a category."""
        return [e for e in self._entries if e["category"] == category]

    def update(self, entry_id: int, content: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
        """Update an existing knowledge entry."""
        for entry in self._entries:
            if entry["id"] == entry_id:
                if content:
                    entry["content"] = content
                if tags:
                    entry["tags"] = tags
                entry["updated_at"] = datetime.now().isoformat()
                return True
        return False

    def delete(self, entry_id: int) -> bool:
        """Delete a knowledge entry."""
        self._entries = [e for e in self._entries if e["id"] != entry_id]
        return True

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(e["category"] for e in self._entries))

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        categories = {}
        for e in self._entries:
            categories[e["category"]] = categories.get(e["category"], 0) + 1
        return {
            "total_entries": len(self._entries),
            "categories": categories,
        }

    def save(self) -> None:
        """Persist knowledge base to disk."""
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w") as f:
            json.dump(
                {"entries": self._entries, "id_counter": self._id_counter},
                f,
                indent=2,
                default=str,
            )

    def load(self) -> bool:
        """Load knowledge base from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return False
        with open(self._persist_path) as f:
            data = json.load(f)
        self._entries = data.get("entries", [])
        self._id_counter = data.get("id_counter", 0)
        return True
