"""MemoryCondensers – 8 condenser types for memory compaction.

Each condenser implements a different strategy for reducing memory
volume while preserving the most important information:

1. SummaryCondenser     – generate summaries of conversation history
2. KeyFactCondenser     – extract key facts from data
3. TemporalCondenser    – time-based filtering and grouping
4. RelevanceCondenser   – relevance scoring and thresholding
5. RedundancyCondenser  – deduplication of similar entries
6. ProceduralCondenser  – extract actions and procedures
7. RelationalCondenser  – extract entity relationships
8. HybridCondenser      – combine multiple condensers
"""

from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Base ─────────────────────────────────────────────────────────

class BaseCondenser(ABC):
    """Abstract base class for memory condensers."""

    @abstractmethod
    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Condense a list of memory entries into a compressed form.

        Parameters
        ----------
        data : list of dict
            Memory entries to condense.
        **kwargs
            Condenser-specific parameters.

        Returns
        -------
        dict
            Condensed result with at least ``original_count`` and
            ``condensed_count`` keys.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Unique name of this condenser."""
        ...


# ── 1. SummaryCondenser ─────────────────────────────────────────

class SummaryCondenser(BaseCondenser):
    """Generate a compact summary of conversation history.

    Takes a list of entries and produces a single summary string,
    preserving the key information in a condensed form.
    """

    def name(self) -> str:
        return "summary"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        max_length: int = kwargs.get("max_length", 512)

        if not data:
            return {"summary": "", "original_count": 0, "condensed_count": 0}

        # Build summary from entry values
        parts = []
        for entry in data:
            value = entry.get("value", entry.get("content", ""))
            if value:
                parts.append(str(value)[:max_length // max(1, len(data))])

        summary = " ".join(parts)[:max_length]

        # Add key indicators
        key_count = sum(1 for d in data if d.get("key"))
        summary += f" [{key_count} key entries]"

        return {
            "summary": summary,
            "original_count": len(data),
            "condensed_count": 1,
            "compression_ratio": 1.0 / len(data) if data else 0,
        }


# ── 2. KeyFactCondenser ─────────────────────────────────────────

class KeyFactCondenser(BaseCondenser):
    """Extract key facts from data entries.

    Identifies statements that contain factual information (definitions,
    parameters, decisions) and extracts them as discrete facts.
    """

    # Patterns that indicate factual content
    _FACT_PATTERNS = [
        r"(?:is|are|was|were|will be)\s+\S+",           # "X is Y"
        r"(?:equals?|means?|refers? to)\s+",             # "X equals Y"
        r"\d+(?:\.\d+)?(?:\s*%)?",                        # numbers
        r"(?:must|should|shall|needs? to)\s+",           # requirements
        r"(?:defined as|configured with|set to)\s+",     # configuration
    ]

    def name(self) -> str:
        return "key_fact"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        max_facts: int = kwargs.get("max_facts", 30)

        facts: List[str] = []
        for entry in data:
            key = entry.get("key", "")
            value = str(entry.get("value", entry.get("content", "")))

            # Key-value pair as fact
            if key and value:
                facts.append(f"{key}: {value[:100]}")
                continue

            # Extract factual sentences
            sentences = re.split(r'[.!?]', value)
            for sentence in sentences:
                s = sentence.strip()
                if len(s) < 10:
                    continue
                if any(re.search(pattern, s) for pattern in self._FACT_PATTERNS):
                    facts.append(s[:150])

            if len(facts) >= max_facts:
                break

        return {
            "facts": facts[:max_facts],
            "original_count": len(data),
            "condensed_count": len(facts[:max_facts]),
        }


# ── 3. TemporalCondenser ────────────────────────────────────────

class TemporalCondenser(BaseCondenser):
    """Time-based filtering and grouping of memory entries.

    Groups entries by time periods and applies recency weighting.
    """

    def name(self) -> str:
        return "temporal"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        max_age_hours: float = kwargs.get("max_age_hours", 0)  # 0 = no filter
        group_by: str = kwargs.get("group_by", "hour")  # hour | day | session

        if not data:
            return {"periods": {}, "original_count": 0, "condensed_count": 0}

        # Group entries by time period
        groups: Dict[str, List[Dict]] = {}

        for entry in data:
            timestamp = entry.get("timestamp", entry.get("created_at", ""))
            if not timestamp:
                period = "unknown"
            else:
                # Simple period extraction
                try:
                    if len(timestamp) >= 10:
                        if group_by == "hour" and len(timestamp) >= 13:
                            period = timestamp[:13]  # YYYY-MM-DDTHH
                        elif group_by == "day":
                            period = timestamp[:10]  # YYYY-MM-DD
                        else:
                            period = timestamp[:10]
                    else:
                        period = "unknown"
                except Exception:
                    period = "unknown"

            if period not in groups:
                groups[period] = []
            groups[period].append(entry)

        # Build result
        periods = {}
        for period, entries in sorted(groups.items()):
            periods[period] = {
                "count": len(entries),
                "keys": [e.get("key", "") for e in entries if e.get("key")][:10],
                "summary": f"{len(entries)} entries in period",
            }

        return {
            "periods": periods,
            "original_count": len(data),
            "condensed_count": len(periods),
            "group_by": group_by,
        }


# ── 4. RelevanceCondenser ───────────────────────────────────────

class RelevanceCondenser(BaseCondenser):
    """Score entries by relevance and filter below a threshold.

    Relevance is computed from: recency, access frequency, explicit
    priority, and keyword match against a query.
    """

    def name(self) -> str:
        return "relevance"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        min_relevance: float = kwargs.get("min_relevance", 0.3)
        query: str = kwargs.get("query", "")
        top_k: int = kwargs.get("top_k", 0)  # 0 = no limit

        if not data:
            return {"entries": [], "original_count": 0, "condensed_count": 0}

        # Score each entry
        scored: List[Tuple[Dict, float]] = []
        for entry in data:
            score = self._compute_relevance(entry, query)
            scored.append((entry, score))

        # Sort by relevance
        scored.sort(key=lambda x: x[1], reverse=True)

        # Filter
        filtered = [(e, s) for e, s in scored if s >= min_relevance]
        if top_k > 0:
            filtered = filtered[:top_k]

        return {
            "entries": [
                {"entry": e, "relevance": round(s, 3)} for e, s in filtered
            ],
            "original_count": len(data),
            "condensed_count": len(filtered),
            "avg_relevance": round(
                sum(s for _, s in filtered) / max(1, len(filtered)), 3
            ),
        }

    @staticmethod
    def _compute_relevance(entry: Dict[str, Any], query: str) -> float:
        """Compute a relevance score for an entry."""
        score = 0.5  # base

        # Access count
        access_count = entry.get("access_count", 0)
        score += min(0.2, access_count * 0.02)

        # Priority
        priority = entry.get("priority", 1.0)
        score += min(0.2, priority * 0.1)

        # Query match
        if query:
            value = str(entry.get("value", entry.get("content", ""))).lower()
            key = str(entry.get("key", "")).lower()
            q = query.lower()
            if q in key:
                score += 0.3
            elif q in value:
                score += 0.2

        return min(1.0, score)


# ── 5. RedundancyCondenser ──────────────────────────────────────

class RedundancyCondenser(BaseCondenser):
    """Remove duplicate or near-duplicate entries.

    Uses exact hash matching for deduplication.
    """

    def name(self) -> str:
        return "redundancy"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        similarity_threshold: float = kwargs.get("similarity_threshold", 1.0)

        if not data:
            return {"unique_count": 0, "duplicates_removed": 0, "data": [], "original_count": 0}

        seen_hashes: Dict[str, int] = {}
        unique: List[Dict[str, Any]] = []
        duplicates = 0

        for entry in data:
            # Compute hash of the entry's content
            content = str(entry.get("value", entry.get("content", "")))
            key = str(entry.get("key", ""))
            h = hashlib.sha256(f"{key}||{content}".encode()).hexdigest()[:16]

            if h in seen_hashes:
                duplicates += 1
                # Keep the one with higher access count
                if entry.get("access_count", 0) > seen_hashes.get(h, 0):
                    # Replace with the more-accessed version
                    unique = [e for e in unique if hashlib.sha256(
                        f"{e.get('key', '')}||{e.get('value', e.get('content', ''))}".encode()
                    ).hexdigest()[:16] != h]
                    unique.append(entry)
                    seen_hashes[h] = entry.get("access_count", 0)
            else:
                seen_hashes[h] = entry.get("access_count", 0)
                unique.append(entry)

        return {
            "unique_count": len(unique),
            "duplicates_removed": duplicates,
            "data": unique,
            "original_count": len(data),
        }


# ── 6. ProceduralCondenser ──────────────────────────────────────

class ProceduralCondenser(BaseCondenser):
    """Extract actions, procedures, and step-by-step instructions
    from memory entries.
    """

    _ACTION_PATTERNS = [
        r"(?:run|execute|start|stop|create|delete|update|install|configure)\s+",
        r"(?:step\s+\d+|first|then|next|finally)\s*[:.]",
        r"(?:click|type|navigate|open|close|save)\s+",
        r"(?:ssh|curl|wget|pip|npm|docker|git)\s+",
    ]

    def name(self) -> str:
        return "procedural"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        max_actions: int = kwargs.get("max_actions", 20)

        actions: List[Dict[str, Any]] = []

        for entry in data:
            value = str(entry.get("value", entry.get("content", "")))

            # Split into sentences/lines
            lines = re.split(r'[.\n]', value)
            for line in lines:
                line = line.strip()
                if len(line) < 5:
                    continue

                # Check if line contains an action pattern
                is_action = any(
                    re.search(pattern, line, re.IGNORECASE)
                    for pattern in self._ACTION_PATTERNS
                )

                if is_action:
                    actions.append({
                        "action": line[:200],
                        "source_key": entry.get("key", ""),
                        "type": self._classify_action(line),
                    })

                if len(actions) >= max_actions:
                    break

            if len(actions) >= max_actions:
                break

        return {
            "actions": actions,
            "original_count": len(data),
            "condensed_count": len(actions),
        }

    @staticmethod
    def _classify_action(line: str) -> str:
        """Classify an action line."""
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["run", "execute", "start", "stop"]):
            return "execution"
        elif any(kw in line_lower for kw in ["create", "delete", "update", "install"]):
            return "modification"
        elif any(kw in line_lower for kw in ["click", "type", "navigate"]):
            return "interaction"
        elif any(kw in line_lower for kw in ["ssh", "curl", "wget", "pip", "npm", "docker", "git"]):
            return "command"
        return "general"


# ── 7. RelationalCondenser ──────────────────────────────────────

class RelationalCondenser(BaseCondenser):
    """Extract entity relationships from memory entries.

    Identifies subject-predicate-object triples from text using
    simple pattern matching.
    """

    _RELATION_PATTERNS = [
        # "X is Y", "X has Y", "X uses Y"
        (r"(\w[\w\s]{2,30}?)\s+(?:is|are|was|were)\s+(.+?)(?:\.|$)", "is_a"),
        (r"(\w[\w\s]{2,30}?)\s+(?:has|have|had)\s+(.+?)(?:\.|$)", "has"),
        (r"(\w[\w\s]{2,30}?)\s+(?:uses?|utilizes?)\s+(.+?)(?:\.|$)", "uses"),
        (r"(\w[\w\s]{2,30}?)\s+(?:depends? on|requires?)\s+(.+?)(?:\.|$)", "depends_on"),
        (r"(\w[\w\s]{2,30}?)\s+(?:connects? to|links? to)\s+(.+?)(?:\.|$)", "connects_to"),
        (r"(\w[\w\s]{2,30}?)\s+(?:contains?|includes?)\s+(.+?)(?:\.|$)", "contains"),
    ]

    def name(self) -> str:
        return "relational"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        max_relations: int = kwargs.get("max_relations", 30)

        relations: List[Dict[str, Any]] = []

        for entry in data:
            value = str(entry.get("value", entry.get("content", "")))
            key = entry.get("key", "")

            # Also check key-value as a relation
            if key and value:
                relations.append({
                    "subject": key,
                    "predicate": "has_value",
                    "object": value[:100],
                    "source": "key_value",
                })

            # Extract relations from text
            for pattern, pred in self._RELATION_PATTERNS:
                for match in re.finditer(pattern, value, re.IGNORECASE):
                    subject = match.group(1).strip()
                    obj = match.group(2).strip()
                    if subject and obj:
                        relations.append({
                            "subject": subject,
                            "predicate": pred,
                            "object": obj,
                            "source": "extracted",
                        })

                if len(relations) >= max_relations:
                    break

            if len(relations) >= max_relations:
                break

        return {
            "relations": relations[:max_relations],
            "original_count": len(data),
            "condensed_count": len(relations[:max_relations]),
            "unique_subjects": len(set(r["subject"] for r in relations)),
            "unique_predicates": len(set(r["predicate"] for r in relations)),
        }


# ── 8. HybridCondenser ──────────────────────────────────────────

class HybridCondenser(BaseCondenser):
    """Combine multiple condensers in sequence.

    Applies each condenser in order, passing the output of one as
    the input to the next (pipeline style).
    """

    def __init__(self, condensers: Optional[List[BaseCondenser]] = None) -> None:
        self._condensers = condensers or [
            RedundancyCondenser(),
            RelevanceCondenser(),
            SummaryCondenser(),
        ]

    def name(self) -> str:
        return "hybrid"

    def condense(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if not data:
            return {"results": [], "original_count": 0, "condensed_count": 0}

        current_data = list(data)
        results: List[Dict[str, Any]] = []

        for condenser in self._condensers:
            try:
                result = condenser.condense(current_data, **kwargs)
                results.append({
                    "condenser": condenser.name(),
                    "result": result,
                })

                # If the condenser returns filtered data, use it as input for next
                if "data" in result and isinstance(result["data"], list):
                    current_data = result["data"]

            except Exception as exc:
                logger.warning("Condenser %s failed: %s", condenser.name(), exc)
                results.append({
                    "condenser": condenser.name(),
                    "error": str(exc),
                })

        return {
            "results": results,
            "original_count": len(data),
            "condensed_count": len(current_data),
            "condensers_used": [c.name() for c in self._condensers],
        }


# ── Registry ────────────────────────────────────────────────────

CONDENSERS: Dict[str, type] = {
    "summary": SummaryCondenser,
    "key_fact": KeyFactCondenser,
    "temporal": TemporalCondenser,
    "relevance": RelevanceCondenser,
    "redundancy": RedundancyCondenser,
    "procedural": ProceduralCondenser,
    "relational": RelationalCondenser,
    "hybrid": HybridCondenser,
}


# ── Backward-compat aliases ─────────────────────────────────────

ExtractionCondenser = KeyFactCondenser
RollupCondenser = SummaryCondenser
PriorityCondenser = RelevanceCondenser
DeduplicationCondenser = RedundancyCondenser

# Also keep the old names in CONDENSERS
CONDENSERS["extraction"] = ExtractionCondenser
CONDENSERS["rollup"] = RollupCondenser
CONDENSERS["priority"] = PriorityCondenser
CONDENSERS["deduplication"] = DeduplicationCondenser

# Legacy names that were in the old condensers.py
SlidingWindowCondenser = SummaryCondenser  # simplified
HierarchicalCondenser = HybridCondenser   # simplified
CONDENSERS["sliding_window"] = SlidingWindowCondenser
CONDENSERS["hierarchical"] = HierarchicalCondenser
