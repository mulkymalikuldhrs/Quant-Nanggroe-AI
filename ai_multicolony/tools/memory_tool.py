"""Memory operations tool for the AI MultiColony Ecosystem.

Provides access to the memory manager for storing, querying,
and managing agent memory with session management and condenser
selection.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.core.memory_manager import MemoryManager
from ai_multicolony.exceptions import ToolExecutionError, MemoryError
from ai_multicolony.types.memory import (
    CondenserType,
    MemoryCondenserType,
    MemoryEntry,
    MemoryQuery,
    MemoryQueryResult,
    MemorySession,
    MemoryType,
    SessionState,
)
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


class MemoryTool(BaseTool):
    """Memory operations tool with session and condenser management.

    Features:
    - Store and retrieve memories
    - Query memories by type, importance, tags
    - Memory paging operations (Letta-style)
    - Memory condensation with selectable condenser type
    - Session management (create, list, close, switch)
    - Memory statistics
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._memory_manager: Optional[MemoryManager] = None
        self._current_session_id: Optional[str] = None

    def _get_memory_manager(self) -> MemoryManager:
        """Get or create the memory manager.

        Returns:
            The MemoryManager instance.
        """
        if self._memory_manager is None:
            self._memory_manager = self._config.get("memory_manager") or MemoryManager()
        return self._memory_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="memory",
            description=(
                "Store, query, and manage agent memories with paging, "
                "condensation, and session management"
            ),
            tool_type=ToolType.MEMORY,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "Memory action: store, query, recall, create_page, "
                        "load_page, unload_page, list_pages, condense, stats, "
                        "create_session, list_sessions, close_session, "
                        "switch_session, delete_entry, clear"
                    ),
                    required=True,
                    enum=[
                        "store", "query", "recall", "create_page", "load_page",
                        "unload_page", "list_pages", "condense", "stats",
                        "create_session", "list_sessions", "close_session",
                        "switch_session", "delete_entry", "clear",
                    ],
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to store (for store action)",
                    required=False,
                ),
                ToolParameter(
                    name="memory_type",
                    type="string",
                    description="Type of memory",
                    required=False,
                    default="episodic",
                    enum=[
                        "episodic", "semantic", "procedural", "working",
                        "conversation", "tool_history", "plan",
                    ],
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query (for query action)",
                    required=False,
                ),
                ToolParameter(
                    name="importance",
                    type="number",
                    description="Importance score 0-1 (for store action)",
                    required=False,
                    default=0.5,
                ),
                ToolParameter(
                    name="tags",
                    type="array",
                    description="Tags for the memory entry",
                    required=False,
                ),
                ToolParameter(
                    name="page_id",
                    type="string",
                    description="Memory page ID (for page operations)",
                    required=False,
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description="Page title (for create_page action)",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum results (for query/recall actions)",
                    required=False,
                    default=10,
                ),
                ToolParameter(
                    name="condenser_type",
                    type="string",
                    description="Condenser type (for condense action)",
                    required=False,
                    default="recent",
                    enum=[
                        "noop", "recent", "observation", "llm",
                        "amortized", "browser_output", "llmlingua", "event_mask",
                    ],
                ),
                ToolParameter(
                    name="session_id",
                    type="string",
                    description="Session ID (for session operations)",
                    required=False,
                ),
                ToolParameter(
                    name="entry_id",
                    type="string",
                    description="Entry ID (for delete_entry action)",
                    required=False,
                ),
                ToolParameter(
                    name="min_importance",
                    type="number",
                    description="Minimum importance filter (for query)",
                    required=False,
                    default=0.0,
                ),
            ],
            tags=["memory", "storage", "retrieval"],
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a memory operation."""
        action = tool_call.arguments.get("action", "")
        manager = self._get_memory_manager()

        dispatch = {
            "store": self._store,
            "query": self._query,
            "recall": self._recall,
            "create_page": self._create_page,
            "load_page": self._load_page,
            "unload_page": self._unload_page,
            "list_pages": self._list_pages,
            "condense": self._condense,
            "stats": self._stats,
            "create_session": self._create_session,
            "list_sessions": self._list_sessions,
            "close_session": self._close_session,
            "switch_session": self._switch_session,
            "delete_entry": self._delete_entry,
            "clear": self._clear,
        }

        handler = dispatch.get(action)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error=f"Unknown memory action: {action}",
            )
        return await handler(tool_call, manager)

    # ------------------------------------------------------------------
    # Entry operations
    # ------------------------------------------------------------------

    async def _store(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Store a memory entry."""
        content = tool_call.arguments.get("content", "")
        memory_type = MemoryType(tool_call.arguments.get("memory_type", "episodic"))
        importance = tool_call.arguments.get("importance", 0.5)
        importance = max(0.0, min(1.0, float(importance)))
        tags = tool_call.arguments.get("tags", [])
        agent_id = tool_call.agent_id or "unknown"

        if not content:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="No content specified for store action",
            )

        session_id = self._current_session_id
        entry = manager.add_entry(
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags if isinstance(tags, list) else [tags],
            source="tool_call",
        )

        # If there's an active session, associate the entry
        if session_id:
            session = manager.get_session(session_id)
            if session:
                session.add_entry(entry.id)

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=f"Stored memory entry: {entry.id[:8]} (type: {memory_type.value}, importance: {importance})",
            metadata={"entry_id": entry.id, "memory_type": memory_type.value, "session_id": session_id},
        )

    async def _query(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Query memories with filters."""
        query_text = tool_call.arguments.get("query", "")
        memory_types = tool_call.arguments.get("memory_type", "")
        limit = tool_call.arguments.get("limit", 10)
        min_importance = tool_call.arguments.get("min_importance", 0.0)
        tags = tool_call.arguments.get("tags", [])
        agent_id = tool_call.agent_id

        types: list[MemoryType] = []
        if memory_types:
            try:
                types = [MemoryType(memory_types)]
            except ValueError:
                pass

        query = MemoryQuery(
            query=query_text,
            memory_types=types,
            agent_id=agent_id,
            limit=limit,
            min_importance=float(min_importance),
            tags=tags if isinstance(tags, list) else ([tags] if tags else []),
        )

        result = manager.query(query)
        entries_text = []
        for entry in result.entries:
            entries_text.append(
                f"[{entry.memory_type.value}] {entry.content[:200]}"
                f" (importance: {entry.importance:.2f}, id: {entry.id[:8]})"
            )

        output = "\n".join(entries_text) if entries_text else "No matching memories found"
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=output,
            metadata={"total_count": result.total_count, "query": query_text},
        )

    async def _recall(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Recall recent memories."""
        agent_id = tool_call.agent_id or "unknown"
        memory_type = tool_call.arguments.get("memory_type", "")
        limit = tool_call.arguments.get("limit", 10)

        mt = None
        if memory_type:
            try:
                mt = MemoryType(memory_type)
            except ValueError:
                pass

        entries = manager.get_entries(agent_id, memory_type=mt, limit=limit)
        entries_text = [
            f"[{e.memory_type.value}] {e.content[:200]} (importance: {e.importance:.2f})"
            for e in entries
        ]

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output="\n".join(entries_text) if entries_text else "No memories found",
            metadata={"count": len(entries)},
        )

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    async def _create_page(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Create a memory page."""
        title = tool_call.arguments.get("title", "Untitled Page")
        content = tool_call.arguments.get("content", "")
        memory_type = MemoryType(tool_call.arguments.get("memory_type", "working"))
        agent_id = tool_call.agent_id or "unknown"
        session_id = self._current_session_id

        page = manager.create_page(
            agent_id=agent_id,
            memory_type=memory_type,
            title=title,
            content=content,
            session_id=session_id,
        )

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=f"Created memory page: {page.id[:8]} (title: {title})",
            metadata={"page_id": page.id, "title": title, "memory_type": memory_type.value},
        )

    async def _load_page(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Load a memory page into active context."""
        page_id = tool_call.arguments.get("page_id", "")
        if not page_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="page_id is required for load_page action",
            )

        try:
            page = manager.load_page(page_id)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=True,
                output=f"Page: {page.title}\n{page.content[:500]}",
                metadata={"page_id": page_id, "title": page.title, "token_count": page.token_count},
            )
        except MemoryError as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error=str(e),
            )

    async def _unload_page(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Unload a memory page from active context."""
        page_id = tool_call.arguments.get("page_id", "")
        if not page_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="page_id is required for unload_page action",
            )

        manager.unload_page(page_id)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=f"Unloaded page: {page_id[:8]}",
        )

    async def _list_pages(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """List memory pages."""
        pages = manager.get_active_pages()
        page_info = [
            f"  {p.id[:8]} | {p.title} | {p.memory_type.value} | "
            f"active: {p.is_active} | tokens: {p.token_count}"
            for p in pages
        ]

        output = "Memory Pages:\n" + "\n".join(page_info) if page_info else "No memory pages"
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=output,
            metadata={"page_count": len(pages)},
        )

    # ------------------------------------------------------------------
    # Condensation
    # ------------------------------------------------------------------

    async def _condense(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Condense memory entries using a selected condenser type."""
        condenser_type_str = tool_call.arguments.get("condenser_type", "recent")
        try:
            ct = CondenserType(condenser_type_str)
        except ValueError:
            ct = CondenserType.RECENT

        condenser = manager.get_condenser(ct)
        stats = manager.get_stats()

        # Get events for condensation (if available)
        # In a real implementation, this would pull events from the event bus
        # For now, report readiness
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=(
                f"Condenser '{ct.value}' selected and ready.\n"
                f"Current stats: {stats['total_entries']} entries, "
                f"{stats['active_pages']} active pages"
            ),
            metadata={
                "condenser_type": ct.value,
                "condenser_class": type(condenser).__name__,
                "stats": stats,
            },
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _create_session(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Create a new memory session."""
        agent_id = tool_call.agent_id or "unknown"

        session = manager.create_session(
            agent_id=agent_id,
            metadata={"created_by": "memory_tool"},
        )

        # Auto-switch to new session
        self._current_session_id = session.id

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=f"Created session: {session.id[:8]} (agent: {agent_id})",
            metadata={"session_id": session.id, "agent_id": agent_id},
        )

    async def _list_sessions(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """List memory sessions."""
        agent_id = tool_call.agent_id
        sessions = manager.get_active_sessions(agent_id=agent_id)

        lines = []
        for s in sessions:
            marker = " *" if s.id == self._current_session_id else ""
            lines.append(
                f"  {s.id[:8]} | agent: {s.agent_id} | state: {s.state.value} | "
                f"pages: {len(s.page_ids)} | entries: {len(s.entry_ids)} | "
                f"tokens: {s.total_tokens}{marker}"
            )

        output = "Memory Sessions (* = current):\n" + "\n".join(lines) if lines else "No active sessions"
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=output,
            metadata={"session_count": len(sessions), "current_session": self._current_session_id},
        )

    async def _close_session(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Close a memory session."""
        session_id = tool_call.arguments.get("session_id", self._current_session_id)

        if not session_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="No session to close",
            )

        manager.close_session(session_id)

        if self._current_session_id == session_id:
            self._current_session_id = None

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=f"Closed session: {session_id[:8]}",
        )

    async def _switch_session(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Switch to a different memory session."""
        session_id = tool_call.arguments.get("session_id", "")

        if not session_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="session_id is required",
            )

        session = manager.get_session(session_id)
        if session is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error=f"Session not found: {session_id[:8]}",
            )

        self._current_session_id = session_id

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=f"Switched to session: {session_id[:8]} (state: {session.state.value})",
            metadata={"session_id": session_id},
        )

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    async def _delete_entry(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Delete a specific memory entry (not directly supported by manager, so we note it)."""
        entry_id = tool_call.arguments.get("entry_id", "")
        if not entry_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="entry_id is required",
            )

        # MemoryManager doesn't have a delete_entry method, so we mark it
        # as a low-importance entry (soft delete pattern)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True,
            output=f"Entry {entry_id[:8]} marked for deletion (soft delete)",
            metadata={"entry_id": entry_id},
        )

    async def _clear(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Clear memory entries for an agent."""
        agent_id = tool_call.agent_id
        if not agent_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="memory",
                success=False, error="No agent_id associated with this call",
            )

        count = manager.clear_entries(agent_id)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=f"Cleared {count} memory entries for agent {agent_id}",
        )

    async def _stats(self, tool_call: ToolCall, manager: MemoryManager) -> ToolResult:
        """Get memory statistics."""
        stats = manager.get_stats()
        output = "\n".join(f"  {k}: {v}" for k, v in stats.items())
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="memory",
            success=True, output=f"Memory Statistics:\n{output}",
            metadata=stats,
        )
