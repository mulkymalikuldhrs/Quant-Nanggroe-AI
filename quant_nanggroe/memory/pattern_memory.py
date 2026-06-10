"""Pattern Memory for Quant Nanggroe AI.

Detects, stores, and retrieves recurring trading patterns from historical
data. Provides pattern recognition across market conditions, enabling
agents to learn from past market behaviors and similar setups.
"""

from __future__ import annotations

import json
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of trading patterns."""
    CHART = "chart"                 # Price chart patterns (head & shoulders, double top, etc.)
    VOLUME = "volume"               # Volume-based patterns
    MOMENTUM = "momentum"           # Momentum divergence / convergence patterns
    MEAN_REVERSION = "mean_reversion"  # Overextension / reversion patterns
    BREAKOUT = "breakout"           # Breakout / breakdown patterns
    REGIME_CHANGE = "regime_change" # Market regime transition patterns
    CORRELATION = "correlation"     # Cross-asset correlation patterns
    EVENT = "event"                 # Event-driven patterns (earnings, halving, etc.)


@dataclass
class Pattern:
    """A detected trading pattern with metadata.

    Attributes:
        id: Unique pattern identifier.
        pattern_type: Type classification.
        name: Human-readable pattern name.
        description: Detailed pattern description.
        conditions: Market conditions that define this pattern.
        outcome: Expected outcome when this pattern occurs.
        historical_occurrences: Number of times this pattern occurred.
        win_rate: Win rate when trading this pattern.
        avg_return: Average return when this pattern occurs.
        confidence: Confidence level in this pattern (0.0-1.0).
        symbols: Symbols where this pattern was observed.
        timeframe: Timeframe of the pattern.
        tags: Additional tags for categorization.
        created_at: When this pattern was first detected.
        updated_at: When this pattern was last updated.
    """
    id: str
    pattern_type: PatternType
    name: str
    description: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)
    historical_occurrences: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    confidence: float = 0.0
    symbols: List[str] = field(default_factory=list)
    timeframe: str = "1d"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize pattern to dictionary."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "outcome": self.outcome,
            "historical_occurrences": self.historical_occurrences,
            "win_rate": self.win_rate,
            "avg_return": self.avg_return,
            "confidence": self.confidence,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pattern:
        """Deserialize pattern from dictionary."""
        return cls(
            id=data["id"],
            pattern_type=PatternType(data.get("pattern_type", "chart")),
            name=data["name"],
            description=data.get("description", ""),
            conditions=data.get("conditions", {}),
            outcome=data.get("outcome", {}),
            historical_occurrences=data.get("historical_occurrences", 0),
            win_rate=data.get("win_rate", 0.0),
            avg_return=data.get("avg_return", 0.0),
            confidence=data.get("confidence", 0.0),
            symbols=data.get("symbols", []),
            timeframe=data.get("timeframe", "1d"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class PatternMemory:
    """
    Pattern memory for detecting and storing recurring trading patterns.

    Maintains a library of observed market patterns with historical
    performance data, enabling agents to recognize similar setups
    and make informed decisions based on past outcomes.

    Features:
    - Pattern detection and storage
    - Similarity matching
    - Performance tracking (win rate, avg return)
    - Pattern evolution (updating with new occurrences)
    - Persistence to disk
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        """Initialize pattern memory.

        Args:
            persist_path: Path for persistence directory.
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._patterns: Dict[str, Pattern] = {}
        self._type_index: Dict[PatternType, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}

    @property
    def size(self) -> int:
        """Number of stored patterns."""
        return len(self._patterns)

    def add_pattern(
        self,
        name: str,
        pattern_type: PatternType,
        description: str,
        conditions: Optional[Dict[str, Any]] = None,
        outcome: Optional[Dict[str, Any]] = None,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1d",
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
    ) -> Pattern:
        """Add a new pattern to memory.

        Args:
            name: Pattern name.
            pattern_type: Type classification.
            description: Detailed description.
            conditions: Market conditions defining this pattern.
            outcome: Expected outcome.
            symbols: Symbols where observed.
            timeframe: Pattern timeframe.
            tags: Additional tags.
            confidence: Initial confidence level.

        Returns:
            The created Pattern.
        """
        # Generate unique ID
        pattern_id = f"P-{pattern_type.value}-{hashlib.md5(name.encode()).hexdigest()[:8]}"

        # Check for existing pattern with same name
        for existing in self._patterns.values():
            if existing.name == name and existing.pattern_type == pattern_type:
                # Update existing pattern
                existing.historical_occurrences += 1
                existing.updated_at = datetime.now().isoformat()
                if symbols:
                    existing.symbols = list(set(existing.symbols + symbols))
                if tags:
                    existing.tags = list(set(existing.tags + tags))
                logger.debug(f"Updated existing pattern: {name}")
                return existing

        pattern = Pattern(
            id=pattern_id,
            pattern_type=pattern_type,
            name=name,
            description=description,
            conditions=conditions or {},
            outcome=outcome or {},
            symbols=symbols or [],
            timeframe=timeframe,
            tags=tags or [],
            confidence=confidence,
            historical_occurrences=1,
        )

        self._patterns[pattern_id] = pattern

        # Update indices
        if pattern_type not in self._type_index:
            self._type_index[pattern_type] = []
        self._type_index[pattern_type].append(pattern_id)

        for tag in pattern.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(pattern_id)

        logger.debug(f"Added pattern: {name} ({pattern_type.value})")
        return pattern

    def record_outcome(
        self,
        pattern_id: str,
        was_successful: bool,
        return_pct: float = 0.0,
    ) -> bool:
        """Record a trade outcome for a pattern.

        Updates the pattern's win rate and average return based on
        the new observation.

        Args:
            pattern_id: Pattern identifier.
            was_successful: Whether the trade was successful.
            return_pct: Return percentage of the trade.

        Returns:
            True if pattern was found and updated.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            return False

        # Update statistics using running average
        n = pattern.historical_occurrences
        old_wr = pattern.win_rate
        old_ar = pattern.avg_return

        pattern.win_rate = (old_wr * (n - 1) + (1.0 if was_successful else 0.0)) / n
        pattern.avg_return = (old_ar * (n - 1) + return_pct) / n
        pattern.updated_at = datetime.now().isoformat()

        # Adjust confidence based on sample size and win rate
        min_samples = 10
        if n >= min_samples:
            pattern.confidence = min(pattern.win_rate * (1 + min(n / 50, 1.0)), 1.0)

        return True

    def find_similar(
        self,
        conditions: Dict[str, Any],
        pattern_type: Optional[PatternType] = None,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> List[Tuple[Pattern, float]]:
        """Find patterns similar to the given conditions.

        Uses a simple condition-matching similarity metric.

        Args:
            conditions: Current market conditions to match.
            pattern_type: Optional filter by pattern type.
            min_confidence: Minimum pattern confidence.
            limit: Maximum results.

        Returns:
            List of (pattern, similarity_score) tuples.
        """
        results: List[Tuple[Pattern, float]] = []

        for pattern in self._patterns.values():
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
            if pattern.confidence < min_confidence:
                continue

            # Compute similarity as overlap of conditions
            score = self._compute_similarity(conditions, pattern.conditions)
            if score > 0.0:
                results.append((pattern, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_by_type(self, pattern_type: PatternType) -> List[Pattern]:
        """Get all patterns of a specific type."""
        ids = self._type_index.get(pattern_type, [])
        return [self._patterns[pid] for pid in ids if pid in self._patterns]

    def get_by_tag(self, tag: str) -> List[Pattern]:
        """Get all patterns with a specific tag."""
        ids = self._tag_index.get(tag.lower(), [])
        return [self._patterns[pid] for pid in ids if pid in self._patterns]

    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern by ID."""
        return self._patterns.get(pattern_id)

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern from memory."""
        pattern = self._patterns.pop(pattern_id, None)
        if pattern is None:
            return False

        # Clean indices
        if pattern.pattern_type in self._type_index:
            try:
                self._type_index[pattern.pattern_type].remove(pattern_id)
            except ValueError:
                pass

        for tag in pattern.tags:
            if tag in self._tag_index:
                try:
                    self._tag_index[tag].remove(pattern_id)
                except ValueError:
                    pass

        return True

    @staticmethod
    def _compute_similarity(
        conditions_a: Dict[str, Any],
        conditions_b: Dict[str, Any],
    ) -> float:
        """Compute similarity between two condition sets.

        Simple Jaccard-like similarity on matching keys.

        Args:
            conditions_a: First condition set.
            conditions_b: Second condition set.

        Returns:
            Similarity score (0.0-1.0).
        """
        if not conditions_a or not conditions_b:
            return 0.0

        common_keys = set(conditions_a.keys()) & set(conditions_b.keys())
        if not common_keys:
            return 0.0

        matches = 0
        for key in common_keys:
            val_a = conditions_a[key]
            val_b = conditions_b[key]

            if val_a == val_b:
                matches += 1
            elif isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                # Numeric similarity
                denom = max(abs(val_a), abs(val_b), 1e-10)
                if abs(val_a - val_b) / denom < 0.2:  # Within 20%
                    matches += 0.8

        return matches / max(len(common_keys), 1)

    def stats(self) -> Dict[str, Any]:
        """Get pattern memory statistics."""
        type_counts = {}
        for ptype, ids in self._type_index.items():
            type_counts[ptype.value] = len(ids)

        return {
            "total_patterns": len(self._patterns),
            "type_distribution": type_counts,
            "tag_count": len(self._tag_index),
            "avg_confidence": (
                sum(p.confidence for p in self._patterns.values())
                / max(len(self._patterns), 1)
            ),
            "avg_win_rate": (
                sum(p.win_rate for p in self._patterns.values())
                / max(len(self._patterns), 1)
            ),
        }

    def save(self) -> None:
        """Persist pattern memory to disk."""
        if not self._persist_path:
            return
        self._persist_path.mkdir(parents=True, exist_ok=True)
        filepath = self._persist_path / "pattern_memory.json"
        data = {pid: p.to_dict() for pid, p in self._patterns.items()}
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Pattern memory saved: {len(self._patterns)} patterns")

    def load(self) -> bool:
        """Load pattern memory from disk."""
        if not self._persist_path:
            return False
        filepath = self._persist_path / "pattern_memory.json"
        if not filepath.exists():
            return False

        with open(filepath) as f:
            data = json.load(f)

        for pid, pdata in data.items():
            pattern = Pattern.from_dict(pdata)
            self._patterns[pid] = pattern

            # Rebuild indices
            if pattern.pattern_type not in self._type_index:
                self._type_index[pattern.pattern_type] = []
            self._type_index[pattern.pattern_type].append(pid)

            for tag in pattern.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(pid)

        logger.info(f"Pattern memory loaded: {len(self._patterns)} patterns")
        return True
