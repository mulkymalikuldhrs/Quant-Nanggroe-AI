"""Memory type definitions for the AI MultiColony Ecosystem.

Implements Letta-style memory paging with OpenHands condenser patterns.
Defines MemoryPage, MemoryType, CondenserType, and SessionState.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory in the system."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    CONVERSATION = "conversation"
    TOOL_HISTORY = "tool_history"
    PLAN = "plan"


class CondenserType(str, Enum):
    """Types of memory condensers available.

    Alias for MemoryCondenserType, ported from OpenHands condenser implementations.
    """

    NOOP = "noop"
    RECENT = "recent"
    OBSERVATION = "observation"
    LLM = "llm"
    AMORTIZED = "amortized"
    BROWSER_OUTPUT = "browser_output"
    LLMLINGUA = "llmlingua"
    EVENT_MASK = "event_mask"


# Backward-compatible alias
MemoryCondenserType = CondenserType


class MemoryPage(BaseModel):
    """A page of memory following Letta-style paging.

    Memory is organized into pages that can be loaded/unloaded
    to manage context window usage efficiently.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = Field(default=0)
    memory_type: MemoryType = MemoryType.WORKING
    title: str = ""
    content: str = ""
    summary: Optional[str] = None
    token_count: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0
    is_active: bool = False
    parent_page_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class MemoryEntry(BaseModel):
    """A single memory entry/record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.EPISODIC
    agent_id: str = ""
    content: str = ""
    summary: Optional[str] = None
    embedding: Optional[list[float]] = None
    page_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance_score: Optional[float] = None
    source: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class SessionState(str, Enum):
    """State of a memory session."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"
    EVICTED = "evicted"


class MemorySession(BaseModel):
    """A memory session that groups related memory pages and entries.

    Sessions provide isolation between different agent runs or tasks,
    ensuring that memory from one context doesn't bleed into another.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    state: SessionState = SessionState.ACTIVE
    page_ids: list[str] = Field(default_factory=list)
    entry_ids: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    closed_at: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def add_page(self, page_id: str, token_count: int = 0) -> None:
        """Add a page to this session."""
        self.page_ids.append(page_id)
        self.total_tokens += token_count
        self.updated_at = time.time()

    def add_entry(self, entry_id: str) -> None:
        """Add an entry to this session."""
        self.entry_ids.append(entry_id)
        self.updated_at = time.time()

    def close(self) -> None:
        """Close the session."""
        self.state = SessionState.CLOSED
        self.closed_at = time.time()
        self.updated_at = time.time()


class MemoryQuery(BaseModel):
    """A query against the memory system."""

    query: str
    memory_types: list[MemoryType] = Field(default_factory=list)
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    use_vector_search: bool = False
    time_range_start: Optional[float] = None
    time_range_end: Optional[float] = None

    model_config = {"arbitrary_types_allowed": True}


class MemoryQueryResult(BaseModel):
    """Result of a memory query."""

    entries: list[MemoryEntry] = Field(default_factory=list)
    total_count: int = 0
    query: Optional[MemoryQuery] = None
    execution_time: Optional[float] = None

    model_config = {"arbitrary_types_allowed": True}
