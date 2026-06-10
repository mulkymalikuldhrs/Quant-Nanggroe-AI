"""
Market Research Skill — Market-wide research and trend detection via MCP
=======================================================================

Ported from mnemosyne MCP server pattern and memory pipeline.
Provides market research capabilities with persistent memory for
cross-session knowledge tracking.

Adapted from:
  - mnemosyne/mcp-server/index.ts (search, pattern detection tools)
  - mnemosyne/src/lib/memory/pipeline.ts (8-phase memory pipeline)
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.agents.mcp_protocol import MCPTool

logger = logging.getLogger(__name__)


class ResearchNote(BaseModel):
    """A research note stored in memory."""
    key: str
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    stored_at: str = ""
    relevance_score: float = 0.0


class MarketResearchSkill(MCPTool):
    """
    MCP skill for market research with persistent memory.

    Provides web search integration, research note storage/retrieval,
    pattern detection across stored research, and decision tracking.
    Inspired by mnemosyne's 8-phase memory pipeline, adapted for
    financial research workflows.
    """

    def __init__(self) -> None:
        self._memory: dict[str, dict[str, Any]] = {}
        self._memory_timestamps: dict[str, float] = {}
        self._hash_dedup: set[str] = set()

    @property
    def name(self) -> str:
        return "market_research"

    @property
    def description(self) -> str:
        return (
            "Conduct market research with persistent memory. Store and retrieve "
            "research notes, detect patterns across stored findings, search web "
            "for market intelligence, and track investment decisions."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "web_search",
                        "memory_store",
                        "memory_retrieve",
                        "memory_search",
                        "memory_list",
                        "memory_delete",
                        "detect_patterns",
                    ],
                    "description": "The research action to perform.",
                },
                "query": {
                    "type": "string",
                    "description": "Search query for web search or memory search.",
                },
                "key": {
                    "type": "string",
                    "description": "Memory key for store/retrieve/delete.",
                },
                "title": {
                    "type": "string",
                    "description": "Title for memory store.",
                },
                "value": {
                    "type": "object",
                    "description": "Data to store in memory.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["research", "market-intelligence", "memory", "search"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a market research action."""
        action = kwargs.get("action")
        if not action:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError("'action' is required for market_research skill")

        if action == "web_search":
            return await self._web_search(kwargs)
        elif action == "memory_store":
            return self._memory_store(kwargs)
        elif action == "memory_retrieve":
            return self._memory_retrieve(kwargs)
        elif action == "memory_search":
            return self._memory_search(kwargs)
        elif action == "memory_list":
            return self._memory_list()
        elif action == "memory_delete":
            return self._memory_delete(kwargs)
        elif action == "detect_patterns":
            return self._detect_patterns()
        else:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError(f"Unknown market_research action: '{action}'")

    async def _web_search(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Search the web for market intelligence."""
        query = kwargs.get("query", "")
        if not query:
            return {"error": "Query is required for web_search"}

        # Try using the sentiment/news tools for market-specific search
        try:
            from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool
            st = SentimentTool()
            result = await st.analyze(symbol=query)
            return {"source": "sentiment_tool", "query": query, "results": result}
        except Exception as e:
            logger.warning("Sentiment tool search failed: %s", e)

        return {
            "query": query,
            "results": [],
            "message": "Web search requires sentiment tool or external search provider",
        }

    def _memory_store(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Store a research note with hash-based dedup (mnemosyne pipeline Phase 4-5)."""
        key = kwargs.get("key", "")
        title = kwargs.get("title", "")
        value = kwargs.get("value")
        if not key or value is None:
            return {"error": "'key' and 'value' are required for memory_store"}

        tags = kwargs.get("tags", [])

        # Hash dedup (Phase 5 from mnemosyne memory pipeline)
        content_str = f"{title}||{value}"
        content_hash = hashlib.md5(content_str.encode()).hexdigest()
        if content_hash in self._hash_dedup:
            return {"status": "duplicate", "key": key, "message": "Content already exists"}

        self._hash_dedup.add(content_hash)

        from datetime import datetime, timezone
        entry = {
            "title": title,
            "value": value,
            "tags": tags,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "hash": content_hash,
        }
        self._memory[str(key)] = entry
        self._memory_timestamps[str(key)] = time.monotonic()
        return {"status": "stored", "key": str(key), "hash": content_hash}

    def _memory_retrieve(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Retrieve a research note by key."""
        key = kwargs.get("key", "")
        if not key:
            return {"error": "'key' is required for memory_retrieve"}
        entry = self._memory.get(str(key))
        if entry is None:
            return {"status": "not_found", "key": str(key)}
        return {"status": "found", "key": str(key), **entry}

    def _memory_search(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Search across stored research notes (mnemosyne keyword + tag matching)."""
        query = kwargs.get("query", "")
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        for mem_key, entry in self._memory.items():
            searchable = (
                f"{mem_key} {entry.get('title', '')} "
                f"{str(entry.get('value', ''))} "
                f"{' '.join(entry.get('tags', []))}"
            ).lower()
            if query_lower in searchable:
                score = self._compute_relevance(query_lower, entry)
                results.append({"key": mem_key, "score": round(score, 3), **entry})

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return {"results": results, "count": len(results), "query": query}

    def _memory_list(self) -> dict[str, Any]:
        """List all stored research notes."""
        entries = [
            {
                "key": k,
                "title": v.get("title", ""),
                "tags": v.get("tags", []),
                "stored_at": v.get("stored_at"),
            }
            for k, v in self._memory.items()
        ]
        return {"entries": entries, "count": len(entries)}

    def _memory_delete(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Delete a research note."""
        key = kwargs.get("key", "")
        if not key:
            return {"error": "'key' is required for memory_delete"}
        if str(key) in self._memory:
            del self._memory[str(key)]
            self._memory_timestamps.pop(str(key), None)
            return {"status": "deleted", "key": str(key)}
        return {"status": "not_found", "key": str(key)}

    def _detect_patterns(self) -> dict[str, Any]:
        """Detect patterns across stored research (mnemosyne pattern detection)."""
        patterns: list[str] = []

        if not self._memory:
            return {"patterns": ["No research notes stored yet."]}

        # Tag frequency analysis
        tag_freq: dict[str, int] = {}
        for entry in self._memory.values():
            for tag in entry.get("tags", []):
                tag_freq[tag] = tag_freq.get(tag, 0) + 1

        frequent = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)
        if frequent:
            patterns.append(
                "Recurring topics: "
                + ", ".join(f'"{t}" ({c})' for t, c in frequent[:5])
            )

        # Title keyword analysis
        title_words: dict[str, int] = {}
        for entry in self._memory.values():
            for word in re.findall(r"\b\w{4,}\b", entry.get("title", "").lower()):
                title_words[word] = title_words.get(word, 0) + 1

        recurring = sorted(title_words.items(), key=lambda x: x[1], reverse=True)
        if recurring and recurring[0][1] >= 2:
            patterns.append(
                "Common themes: "
                + ", ".join(f'"{w}"' for w, _ in recurring[:5])
            )

        patterns.append(f"Total research notes: {len(self._memory)}")

        return {"patterns": patterns}

    @staticmethod
    def _compute_relevance(query: str, entry: dict[str, Any]) -> float:
        """Compute relevance score (mnemosyne relevance scoring algorithm)."""
        score = 0.0
        title = entry.get("title", "").lower()
        value_str = str(entry.get("value", "")).lower()
        tags = [t.lower() for t in entry.get("tags", [])]

        if query in title:
            score += 0.4
        if query in value_str:
            score += 0.2
        for token in query.split():
            if token in title:
                score += 0.1
        if any(query in tag or tag in query for tag in tags):
            score += 0.2

        return min(score, 1.0)
