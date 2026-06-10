"""Episodic Memory for Quant Nanggroe AI.

Stores and retrieves experiential trading episodes — sequences of
events, decisions, and outcomes that form a narrative memory.
Agents can recall similar past episodes to inform current decisions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EpisodeType(str, Enum):
    """Types of trading episodes."""
    TRADE = "trade"                     # Complete trade lifecycle
    MARKET_EVENT = "market_event"       # Significant market event
    REGIME_CHANGE = "regime_change"     # Market regime transition
    ERROR = "error"                     # Mistake / error episode
    LEARNING = "learning"               # Agent learning event
    COUNCIL_DEBATE = "council_debate"   # Council debate outcome
    RISK_EVENT = "risk_event"           # Risk threshold breach
    DISCOVERY = "discovery"             # New pattern / insight discovered


@dataclass
class EpisodeStep:
    """A single step within an episode.

    Attributes:
        timestamp: When this step occurred.
        agent: Agent that performed this step.
        action: Action taken.
        observation: What was observed.
        reasoning: Reasoning behind the action.
        outcome: Immediate outcome.
    """
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent: str = ""
    action: str = ""
    observation: str = ""
    reasoning: str = ""
    outcome: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "observation": self.observation,
            "reasoning": self.reasoning,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EpisodeStep:
        return cls(
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            agent=data.get("agent", ""),
            action=data.get("action", ""),
            observation=data.get("observation", ""),
            reasoning=data.get("reasoning", ""),
            outcome=data.get("outcome", ""),
        )


@dataclass
class Episode:
    """A complete trading episode with narrative structure.

    An episode represents a meaningful trading experience — from the
    initial observation through the decision process to the outcome.
    These narratives help agents learn from past experiences.

    Attributes:
        id: Unique episode identifier.
        episode_type: Type classification.
        title: Episode title/summary.
        description: Detailed description.
        steps: Sequence of steps in the episode.
        symbols: Symbols involved.
        market_conditions: Market conditions at episode time.
        outcome: Final outcome of the episode.
        lessons_learned: Key takeaways from this episode.
        emotional_valence: Positive/negative experience (0.0-1.0).
        importance: How important this episode is (0.0-1.0).
        tags: Categorization tags.
        created_at: When the episode was recorded.
    """
    id: str
    episode_type: EpisodeType
    title: str
    description: str = ""
    steps: List[EpisodeStep] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    emotional_valence: float = 0.5
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_step(
        self,
        agent: str,
        action: str,
        observation: str = "",
        reasoning: str = "",
        outcome: str = "",
    ) -> None:
        """Add a step to this episode.

        Args:
            agent: Agent performing the step.
            action: Action taken.
            observation: What was observed.
            reasoning: Reasoning for the action.
            outcome: Immediate outcome.
        """
        step = EpisodeStep(
            agent=agent,
            action=action,
            observation=observation,
            reasoning=reasoning,
            outcome=outcome,
        )
        self.steps.append(step)

    def add_lesson(self, lesson: str) -> None:
        """Add a lesson learned from this episode."""
        self.lessons_learned.append(lesson)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize episode to dictionary."""
        return {
            "id": self.id,
            "episode_type": self.episode_type.value,
            "title": self.title,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "symbols": self.symbols,
            "market_conditions": self.market_conditions,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "emotional_valence": self.emotional_valence,
            "importance": self.importance,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Episode:
        """Deserialize episode from dictionary."""
        steps = [EpisodeStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=data["id"],
            episode_type=EpisodeType(data.get("episode_type", "trade")),
            title=data["title"],
            description=data.get("description", ""),
            steps=steps,
            symbols=data.get("symbols", []),
            market_conditions=data.get("market_conditions", {}),
            outcome=data.get("outcome", {}),
            lessons_learned=data.get("lessons_learned", []),
            emotional_valence=data.get("emotional_valence", 0.5),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


class EpisodicMemory:
    """
    Episodic memory for storing and retrieving trading narratives.

    Stores experiential episodes — complete sequences of observations,
    decisions, and outcomes — that agents can recall to inform
    current decisions. This is the "narrative memory" of the
    trading system.

    Features:
    - Episode storage with narrative structure
    - Similarity-based episode retrieval
    - Lesson extraction from episodes
    - Emotional valence tracking
    - Importance-weighted recall
    - Persistence to disk
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        """Initialize episodic memory.

        Args:
            persist_path: Path for persistence directory.
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._episodes: Dict[str, Episode] = {}
        self._type_index: Dict[EpisodeType, List[str]] = {}
        self._symbol_index: Dict[str, List[str]] = {}
        self._episode_counter: int = 0

    @property
    def size(self) -> int:
        """Number of stored episodes."""
        return len(self._episodes)

    def record_episode(
        self,
        title: str,
        episode_type: EpisodeType,
        description: str = "",
        symbols: Optional[List[str]] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        emotional_valence: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> Episode:
        """Record a new episode.

        Args:
            title: Episode title/summary.
            episode_type: Type classification.
            description: Detailed description.
            symbols: Symbols involved.
            market_conditions: Market conditions.
            importance: Episode importance (0.0-1.0).
            emotional_valence: Positive/negative valence (0.0-1.0).
            tags: Categorization tags.

        Returns:
            The created Episode.
        """
        self._episode_counter += 1
        episode_id = f"EP-{self._episode_counter:06d}"

        episode = Episode(
            id=episode_id,
            episode_type=episode_type,
            title=title,
            description=description,
            symbols=symbols or [],
            market_conditions=market_conditions or {},
            importance=importance,
            emotional_valence=emotional_valence,
            tags=tags or [],
        )

        self._episodes[episode_id] = episode

        # Update indices
        if episode_type not in self._type_index:
            self._type_index[episode_type] = []
        self._type_index[episode_type].append(episode_id)

        for symbol in (symbols or []):
            sym_upper = symbol.upper()
            if sym_upper not in self._symbol_index:
                self._symbol_index[sym_upper] = []
            self._symbol_index[sym_upper].append(episode_id)

        logger.debug(f"Recorded episode: {title} ({episode_type.value})")
        return episode

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by ID."""
        return self._episodes.get(episode_id)

    def recall_similar(
        self,
        symbols: Optional[List[str]] = None,
        episode_type: Optional[EpisodeType] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[Episode]:
        """Recall episodes matching the given criteria.

        Args:
            symbols: Filter by symbols involved.
            episode_type: Filter by episode type.
            market_conditions: Match similar market conditions.
            min_importance: Minimum importance threshold.
            limit: Maximum results.

        Returns:
            List of matching episodes sorted by relevance.
        """
        candidates = set(self._episodes.keys())

        # Filter by type
        if episode_type:
            type_ids = set(self._type_index.get(episode_type, []))
            candidates = candidates & type_ids

        # Filter by symbols
        if symbols:
            sym_ids: set = set()
            for symbol in symbols:
                sym_ids.update(self._symbol_index.get(symbol.upper(), []))
            if sym_ids:
                candidates = candidates & sym_ids

        # Score and rank
        scored: List[Tuple[Episode, float]] = []
        for eid in candidates:
            episode = self._episodes.get(eid)
            if episode is None:
                continue
            if episode.importance < min_importance:
                continue

            score = episode.importance

            # Boost for condition similarity
            if market_conditions and episode.market_conditions:
                common = set(market_conditions.keys()) & set(episode.market_conditions.keys())
                if common:
                    matches = sum(
                        1 for k in common
                        if market_conditions[k] == episode.market_conditions[k]
                    )
                    score += matches / len(common) * 0.3

            # Boost for lessons learned
            score += len(episode.lessons_learned) * 0.05

            scored.append((episode, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [ep for ep, _ in scored[:limit]]

    def get_lessons(
        self,
        symbols: Optional[List[str]] = None,
        episode_type: Optional[EpisodeType] = None,
        limit: int = 50,
    ) -> List[str]:
        """Get lessons learned from past episodes.

        Args:
            symbols: Filter by symbols.
            episode_type: Filter by episode type.
            limit: Maximum lessons to return.

        Returns:
            List of lesson strings.
        """
        episodes = self.recall_similar(
            symbols=symbols,
            episode_type=episode_type,
            limit=limit,
        )

        lessons = []
        for episode in episodes:
            lessons.extend(episode.lessons_learned)

        return lessons[:limit]

    def get_episodes_by_type(self, episode_type: EpisodeType) -> List[Episode]:
        """Get all episodes of a specific type."""
        ids = self._type_index.get(episode_type, [])
        return [self._episodes[eid] for eid in ids if eid in self._episodes]

    def get_episodes_by_symbol(self, symbol: str) -> List[Episode]:
        """Get all episodes involving a symbol."""
        ids = self._symbol_index.get(symbol.upper(), [])
        return [self._episodes[eid] for eid in ids if eid in self._episodes]

    def get_recent(self, limit: int = 10) -> List[Episode]:
        """Get the most recently recorded episodes."""
        episodes = sorted(
            self._episodes.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )
        return episodes[:limit]

    def stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        type_counts = {}
        for etype, ids in self._type_index.items():
            type_counts[etype.value] = len(ids)

        total_lessons = sum(len(ep.lessons_learned) for ep in self._episodes.values())
        avg_valence = (
            sum(ep.emotional_valence for ep in self._episodes.values())
            / max(len(self._episodes), 1)
        )

        return {
            "total_episodes": len(self._episodes),
            "type_distribution": type_counts,
            "total_lessons_learned": total_lessons,
            "avg_emotional_valence": round(avg_valence, 3),
            "symbol_count": len(self._symbol_index),
        }

    def save(self) -> None:
        """Persist episodic memory to disk."""
        if not self._persist_path:
            return
        self._persist_path.mkdir(parents=True, exist_ok=True)
        filepath = self._persist_path / "episodic_memory.json"
        data = {
            "episodes": {eid: ep.to_dict() for eid, ep in self._episodes.items()},
            "episode_counter": self._episode_counter,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Episodic memory saved: {len(self._episodes)} episodes")

    def load(self) -> bool:
        """Load episodic memory from disk."""
        if not self._persist_path:
            return False
        filepath = self._persist_path / "episodic_memory.json"
        if not filepath.exists():
            return False

        with open(filepath) as f:
            data = json.load(f)

        self._episode_counter = data.get("episode_counter", 0)

        for eid, edata in data.get("episodes", {}).items():
            episode = Episode.from_dict(edata)
            self._episodes[eid] = episode

            # Rebuild indices
            if episode.episode_type not in self._type_index:
                self._type_index[episode.episode_type] = []
            self._type_index[episode.episode_type].append(eid)

            for symbol in episode.symbols:
                sym_upper = symbol.upper()
                if sym_upper not in self._symbol_index:
                    self._symbol_index[sym_upper] = []
                self._symbol_index[sym_upper].append(eid)

        logger.info(f"Episodic memory loaded: {len(self._episodes)} episodes")
        return True
