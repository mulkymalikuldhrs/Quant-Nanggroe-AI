"""L2: Episodic memory for the Multi-Colony Ecosystem.

This module implements episodic memory (Layer 2) inspired by
Letta/MemGPT-style memory management with TokenJuice-style compression.

Episodic memory stores sequences of events and interactions as episodes,
enabling agents to recall past experiences and compress older episodes
to manage context window usage.

Memory Hierarchy:
    L1: Working memory (immediate context, not stored here)
    L2: Episodic memory (this module - event sequences)
    L3: Semantic memory (facts and knowledge)
    L4: Procedural memory (skills and procedures)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class EpisodeType(str, Enum):
    """Types of episodes that can be stored."""

    CONVERSATION = "conversation"
    TASK_EXECUTION = "task_execution"
    DECISION = "decision"
    OBSERVATION = "observation"
    ERROR = "error"
    LEARNING = "learning"
    HANDOFF = "handoff"


class EpisodeImportance(str, Enum):
    """Importance levels for episodes."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Episode(BaseModel):
    """A single episode in episodic memory.

    An episode represents a discrete event or interaction that an agent
    has experienced. Episodes can be compressed to save space while
    retaining key information.

    Attributes:
        episode_id: Unique identifier for the episode.
        agent_id: ID of the agent that experienced this episode.
        colony_id: ID of the colony where this episode occurred.
        episode_type: Type of episode.
        importance: Importance level for retention decisions.
        title: Short summary title.
        content: Full episode content/description.
        summary: Compressed summary (set after compression).
        context: Additional context (state, environment, etc.).
        participants: IDs of other agents/entities involved.
        tags: Tags for search and categorization.
        token_count: Estimated token count of the content.
        is_compressed: Whether this episode has been compressed.
        parent_episode_id: ID of the parent episode (for splits).
        child_episode_ids: IDs of child episodes (for compression groups).
        created_at: When the episode was created.
        accessed_at: When the episode was last accessed.
        access_count: Number of times the episode has been recalled.
    """

    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    colony_id: str = ""
    episode_type: EpisodeType = EpisodeType.OBSERVATION
    importance: EpisodeImportance = EpisodeImportance.MEDIUM
    title: str = ""
    content: str = ""
    summary: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    participants: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    token_count: int = 0
    is_compressed: bool = False
    parent_episode_id: str | None = None
    child_episode_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0


class CompressionResult(BaseModel):
    """Result of an episodic memory compression operation.

    Attributes:
        original_episode_ids: IDs of the episodes that were compressed.
        compressed_episode_id: ID of the new compressed episode.
        original_token_count: Total tokens before compression.
        compressed_token_count: Total tokens after compression.
        compression_ratio: Ratio of compressed/original token count.
    """

    original_episode_ids: list[str]
    compressed_episode_id: str
    original_token_count: int = 0
    compressed_token_count: int = 0
    compression_ratio: float = 0.0


class EpisodicMemory:
    """L2 Episodic memory with TokenJuice-style compression.

    This class manages episodic memory for agents, providing methods
    to store episodes, recall them based on various criteria, and
    compress older episodes to manage token budgets.

    Example::

        memory = EpisodicMemory(agent_id="agent-1", token_budget=8000)
        ep_id = await memory.store_episode(
            title="Code review completed",
            content="Reviewed PR #42...",
            episode_type=EpisodeType.TASK_EXECUTION,
        )
        episodes = await memory.recall_episodes(query="code review")
        result = await memory.compress()
    """

    def __init__(
        self,
        agent_id: str = "",
        colony_id: str = "",
        token_budget: int = 8000,
        compression_threshold: float = 0.8,
    ) -> None:
        """Initialize episodic memory.

        Args:
            agent_id: ID of the agent this memory belongs to.
            colony_id: ID of the colony this memory is associated with.
            token_budget: Maximum token count before compression triggers.
            compression_threshold: Fraction of budget at which to compress.
        """
        self._agent_id = agent_id
        self._colony_id = colony_id
        self._token_budget = token_budget
        self._compression_threshold = compression_threshold
        self._episodes: dict[str, Episode] = {}
        self._log = logger.bind(
            agent_id=agent_id,
            component="episodic_memory",
        )

    @property
    def total_token_count(self) -> int:
        """Total token count across all episodes."""
        return sum(ep.token_count for ep in self._episodes.values())

    @property
    def episode_count(self) -> int:
        """Number of stored episodes."""
        return len(self._episodes)

    @property
    def utilization(self) -> float:
        """Memory utilization as a fraction of token budget (0.0-1.0)."""
        if self._token_budget == 0:
            return 0.0
        return min(self.total_token_count / self._token_budget, 1.0)

    @property
    def needs_compression(self) -> bool:
        """Whether the memory exceeds the compression threshold."""
        return self.utilization >= self._compression_threshold

    async def store_episode(
        self,
        title: str,
        content: str,
        episode_type: EpisodeType = EpisodeType.OBSERVATION,
        importance: EpisodeImportance = EpisodeImportance.MEDIUM,
        context: dict[str, Any] | None = None,
        participants: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Store a new episode in memory.

        Args:
            title: Short summary title.
            content: Full episode content.
            episode_type: Type of episode.
            importance: Importance level.
            context: Additional context.
            participants: IDs of other participants.
            tags: Tags for categorization.

        Returns:
            The episode_id of the stored episode.
        """
        # Estimate token count (rough: ~4 chars per token)
        token_count = len(content) // 4

        episode = Episode(
            agent_id=self._agent_id,
            colony_id=self._colony_id,
            episode_type=episode_type,
            importance=importance,
            title=title,
            content=content,
            context=context or {},
            participants=participants or [],
            tags=tags or [],
            token_count=token_count,
        )

        self._episodes[episode.episode_id] = episode

        self._log.info(
            "episode_stored",
            episode_id=episode.episode_id,
            title=title,
            token_count=token_count,
            utilization=self.utilization,
        )

        # Auto-compress if needed
        if self.needs_compression:
            self._log.info("auto_compression_triggered", utilization=self.utilization)
            await self.compress()

        return episode.episode_id

    async def recall_episodes(
        self,
        query: str | None = None,
        episode_type: EpisodeType | None = None,
        importance: EpisodeImportance | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        since: datetime | None = None,
    ) -> list[Episode]:
        """Recall episodes matching the given criteria.

        Args:
            query: Text to search in title and content.
            episode_type: Filter by episode type.
            importance: Filter by minimum importance level.
            tags: Filter by tags (episodes must have ALL tags).
            limit: Maximum number of episodes to return.
            since: Only return episodes after this timestamp.

        Returns:
            A list of matching episodes, sorted by recency.
        """
        episodes = list(self._episodes.values())

        # Filter by query
        if query is not None:
            query_lower = query.lower()
            episodes = [
                ep for ep in episodes
                if query_lower in ep.title.lower()
                or query_lower in ep.content.lower()
                or (ep.summary and query_lower in ep.summary.lower())
            ]

        # Filter by type
        if episode_type is not None:
            episodes = [ep for ep in episodes if ep.episode_type == episode_type]

        # Filter by importance
        if importance is not None:
            importance_order = [
                EpisodeImportance.LOW,
                EpisodeImportance.MEDIUM,
                EpisodeImportance.HIGH,
                EpisodeImportance.CRITICAL,
            ]
            min_idx = importance_order.index(importance)
            episodes = [
                ep for ep in episodes
                if importance_order.index(ep.importance) >= min_idx
            ]

        # Filter by tags
        if tags is not None:
            episodes = [
                ep for ep in episodes
                if all(t in ep.tags for t in tags)
            ]

        # Filter by timestamp
        if since is not None:
            episodes = [ep for ep in episodes if ep.created_at >= since]

        # Sort by recency
        episodes.sort(key=lambda ep: ep.created_at, reverse=True)

        # Apply limit
        episodes = episodes[:limit]

        # Update access tracking
        now = datetime.now(timezone.utc)
        for ep in episodes:
            ep.accessed_at = now
            ep.access_count += 1

        return episodes

    async def get_episode(self, episode_id: str) -> Episode:
        """Get a specific episode by ID.

        Args:
            episode_id: ID of the episode.

        Returns:
            The episode.

        Raises:
            EpisodeNotFoundError: If the episode is not found.
        """
        if episode_id not in self._episodes:
            raise EpisodeNotFoundError(f"Episode {episode_id} not found.")

        ep = self._episodes[episode_id]
        ep.accessed_at = datetime.now(timezone.utc)
        ep.access_count += 1
        return ep

    async def compress(
        self,
        strategy: str = "oldest_first",
        group_size: int = 5,
    ) -> CompressionResult | None:
        """Compress episodes to reduce token usage (TokenJuice-style).

        Compression merges groups of older, less important episodes into
        summarized episodes, significantly reducing token count while
        preserving key information.

        Args:
            strategy: Compression strategy ('oldest_first', 'least_accessed',
                'lowest_importance').
            group_size: Number of episodes to merge per compression group.

        Returns:
            The compression result, or None if no compression was needed.
        """
        # Get uncompressed episodes sorted by strategy
        candidates = [
            ep for ep in self._episodes.values() if not ep.is_compressed
        ]

        if len(candidates) < group_size:
            self._log.info("insufficient_episodes_for_compression", count=len(candidates))
            return None

        # Sort by strategy
        if strategy == "oldest_first":
            candidates.sort(key=lambda ep: ep.created_at)
        elif strategy == "least_accessed":
            candidates.sort(key=lambda ep: ep.access_count)
        elif strategy == "lowest_importance":
            importance_order = [
                EpisodeImportance.LOW,
                EpisodeImportance.MEDIUM,
                EpisodeImportance.HIGH,
                EpisodeImportance.CRITICAL,
            ]
            candidates.sort(key=lambda ep: importance_order.index(ep.importance))

        # Take the first group for compression
        group = candidates[:group_size]
        original_tokens = sum(ep.token_count for ep in group)

        # Create compressed summary
        titles = [ep.title for ep in group]
        summaries = []
        for ep in group:
            if ep.summary:
                summaries.append(ep.summary)
            else:
                # Take first 200 chars as partial summary
                summaries.append(ep.content[:200] + "..." if len(ep.content) > 200 else ep.content)

        compressed_content = " | ".join(
            f"[{ep.episode_type.value}] {ep.title}: {s}"
            for ep, s in zip(group, summaries)
        )
        compressed_summary = f"Compressed {len(group)} episodes: " + ", ".join(titles)

        # Estimate compressed token count (typically 30-50% of original)
        compressed_tokens = len(compressed_content) // 4

        # Create compressed episode
        compressed_episode = Episode(
            agent_id=self._agent_id,
            colony_id=self._colony_id,
            episode_type=EpisodeType.LEARNING,
            importance=EpisodeImportance.MEDIUM,
            title=compressed_summary,
            content=compressed_content,
            summary=compressed_summary,
            token_count=compressed_tokens,
            is_compressed=True,
            child_episode_ids=[ep.episode_id for ep in group],
            tags=list({t for ep in group for t in ep.tags}),
        )

        # Mark original episodes as compressed
        for ep in group:
            ep.is_compressed = True

        # Store compressed episode
        self._episodes[compressed_episode.episode_id] = compressed_episode

        result = CompressionResult(
            original_episode_ids=[ep.episode_id for ep in group],
            compressed_episode_id=compressed_episode.episode_id,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=(
                compressed_tokens / original_tokens if original_tokens > 0 else 0.0
            ),
        )

        self._log.info(
            "episodes_compressed",
            original_count=len(group),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=result.compression_ratio,
        )

        return result

    async def delete_episode(self, episode_id: str) -> None:
        """Delete an episode from memory.

        Args:
            episode_id: ID of the episode to delete.

        Raises:
            EpisodeNotFoundError: If the episode is not found.
        """
        if episode_id not in self._episodes:
            raise EpisodeNotFoundError(f"Episode {episode_id} not found.")

        del self._episodes[episode_id]
        self._log.info("episode_deleted", episode_id=episode_id)

    def clear(self) -> None:
        """Clear all episodes from memory."""
        self._episodes.clear()
        self._log.info("episodic_memory_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            A dictionary of memory statistics.
        """
        return {
            "agent_id": self._agent_id,
            "episode_count": self.episode_count,
            "total_token_count": self.total_token_count,
            "token_budget": self._token_budget,
            "utilization": round(self.utilization, 3),
            "needs_compression": self.needs_compression,
            "compressed_count": sum(
                1 for ep in self._episodes.values() if ep.is_compressed
            ),
        }


class EpisodeNotFoundError(Exception):
    """Raised when an episode is not found in memory."""
