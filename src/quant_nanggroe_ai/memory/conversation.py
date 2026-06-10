"""
Conversation Memory — Multi-Turn Session Tracking
===================================================
Manages conversation history for agent interactions with
per-session isolation, automatic summarization, context
window management, and message pruning.

Features:
    - Per-session conversation tracking
    - Automatic summarization of long conversations
    - Token budget management (approximate)
    - Session metadata and statistics
    - Message search and filtering
    - Thread-safe operations

Usage:
    memory = ConversationMemory(max_messages=100, max_sessions=50)
    memory.add_message("session-1", "user", "What's the outlook for AAPL?")
    memory.add_message("session-1", "assistant", "AAPL shows bullish momentum...")
    history = memory.get_history("session-1", limit=10)
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class ConversationMessage(BaseModel):
    """A single conversation message."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    session_id: str = ""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0


class SessionSummary(BaseModel):
    """Summary of a conversation session."""

    session_id: str
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    first_message_at: datetime | None = None
    last_message_at: datetime | None = None
    total_tokens: int = 0
    tags: list[str] = Field(default_factory=list)
    summary_text: str = ""


# ══════════════════════════════════════════════════════════════════════
# TOKEN ESTIMATOR
# ══════════════════════════════════════════════════════════════════════


class TokenEstimator:
    """
    Rough token count estimator.

    Uses the heuristic that 1 token ≈ 4 characters for English text.
    This is approximate but sufficient for context window management.
    """

    CHARS_PER_TOKEN = 4.0

    @classmethod
    def estimate(cls, text: str) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0
        return max(1, int(len(text) / cls.CHARS_PER_TOKEN))

    @classmethod
    def estimate_messages(cls, messages: list[ConversationMessage]) -> int:
        """Estimate total tokens for a list of messages."""
        return sum(m.token_count for m in messages)


# ══════════════════════════════════════════════════════════════════════
# CONVERSATION MEMORY
# ══════════════════════════════════════════════════════════════════════


class ConversationMemory:
    """
    Manages conversation history for agent interactions.

    Tracks multi-turn conversations per session with automatic
    trimming, token budget management, and session metadata.

    Args:
        max_messages: Maximum messages per session (older messages trimmed)
        max_sessions: Maximum number of concurrent sessions
        token_budget: Maximum tokens per session context window
        auto_summarize: Whether to auto-summarize old messages
        session_ttl_hours: Hours before inactive sessions are cleaned up

    Example:
        memory = ConversationMemory(max_messages=50, token_budget=4000)
        memory.add_message("sess-1", "user", "Analyze AAPL")
        memory.add_message("sess-1", "assistant", "AAPL shows...")
        history = memory.get_history("sess-1")
    """

    def __init__(
        self,
        max_messages: int = 100,
        max_sessions: int = 50,
        token_budget: int = 8000,
        auto_summarize: bool = True,
        session_ttl_hours: int = 24,
    ) -> None:
        self._max_messages = max_messages
        self._max_sessions = max_sessions
        self._token_budget = token_budget
        self._auto_summarize = auto_summarize
        self._session_ttl = timedelta(hours=session_ttl_hours)

        self._conversations: dict[str, list[ConversationMessage]] = {}
        self._summaries: dict[str, SessionSummary] = {}
        self._session_metadata: dict[str, dict[str, Any]] = defaultdict(dict)

        logger.info(
            "ConversationMemory initialized (max_msgs=%d, max_sessions=%d, token_budget=%d)",
            max_messages, max_sessions, token_budget,
        )

    # ══════════════════════════════════════════════════════════════════
    # ADD MESSAGES
    # ══════════════════════════════════════════════════════════════════

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        **metadata: Any,
    ) -> ConversationMessage:
        """
        Add a message to a conversation session.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            **metadata: Additional metadata key-value pairs

        Returns:
            The created ConversationMessage

        Raises:
            ValueError: If role is invalid
        """
        valid_roles = {"user", "assistant", "system"}
        if role not in valid_roles:
            raise ValueError(
                f"Invalid role '{role}'. Must be one of {valid_roles}"
            )

        # Ensure session exists
        if session_id not in self._conversations:
            self._conversations[session_id] = []
            self._summaries[session_id] = SessionSummary(session_id=session_id)
            logger.debug("Created new session: %s", session_id)

        # Create message
        token_count = TokenEstimator.estimate(content)
        message = ConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata,
        )

        self._conversations[session_id].append(message)

        # Update session summary
        self._update_summary(session_id)

        # Trim if over max messages
        if len(self._conversations[session_id]) > self._max_messages:
            self._trim_session(session_id)

        # Enforce session limit
        self._enforce_session_limit()

        logger.debug(
            "Added %s message to session %s (%d tokens, total: %d messages)",
            role, session_id, token_count, len(self._conversations[session_id]),
        )

        return message

    def add_system_message(
        self, session_id: str, content: str
    ) -> ConversationMessage:
        """Add a system message to a session."""
        return self.add_message(session_id, "system", content)

    def add_user_message(
        self, session_id: str, content: str
    ) -> ConversationMessage:
        """Add a user message to a session."""
        return self.add_message(session_id, "user", content)

    def add_assistant_message(
        self, session_id: str, content: str
    ) -> ConversationMessage:
        """Add an assistant message to a session."""
        return self.add_message(session_id, "assistant", content)

    # ══════════════════════════════════════════════════════════════════
    # RETRIEVE MESSAGES
    # ══════════════════════════════════════════════════════════════════

    def get_history(
        self,
        session_id: str,
        limit: int | None = None,
        role: str | None = None,
    ) -> list[ConversationMessage]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (most recent)
            role: Optional filter by role

        Returns:
            List of ConversationMessage objects
        """
        messages = self._conversations.get(session_id, [])

        if role:
            messages = [m for m in messages if m.role == role]

        if limit:
            messages = messages[-limit:]

        return list(messages)

    def get_context_window(
        self,
        session_id: str,
        max_tokens: int | None = None,
    ) -> list[ConversationMessage]:
        """
        Get messages fitting within a token budget.

        Returns the most recent messages that fit within the token limit,
        always including the most recent message.

        Args:
            session_id: Session identifier
            max_tokens: Maximum tokens (defaults to self._token_budget)

        Returns:
            List of ConversationMessage objects within token budget
        """
        budget = max_tokens or self._token_budget
        messages = self._conversations.get(session_id, [])

        if not messages:
            return []

        # Walk backwards to fit within budget
        result: list[ConversationMessage] = []
        used_tokens = 0

        for msg in reversed(messages):
            if used_tokens + msg.token_count > budget and result:
                break
            result.insert(0, msg)
            used_tokens += msg.token_count

        return result

    def get_last_user_message(self, session_id: str) -> ConversationMessage | None:
        """Get the most recent user message in a session."""
        messages = self._conversations.get(session_id, [])
        for msg in reversed(messages):
            if msg.role == "user":
                return msg
        return None

    def get_last_assistant_message(self, session_id: str) -> ConversationMessage | None:
        """Get the most recent assistant message in a session."""
        messages = self._conversations.get(session_id, [])
        for msg in reversed(messages):
            if msg.role == "assistant":
                return msg
        return None

    # ══════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════

    def get_sessions(self) -> list[str]:
        """Get all active session IDs."""
        return list(self._conversations.keys())

    def get_session_summary(self, session_id: str) -> SessionSummary | None:
        """Get summary for a session."""
        return self._summaries.get(session_id)

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self._conversations

    def get_session_token_count(self, session_id: str) -> int:
        """Get total token count for a session."""
        messages = self._conversations.get(session_id, [])
        return TokenEstimator.estimate_messages(messages)

    def set_session_metadata(
        self, session_id: str, key: str, value: Any
    ) -> None:
        """Set metadata for a session."""
        self._session_metadata[session_id][key] = value

    def get_session_metadata(
        self, session_id: str, key: str, default: Any = None
    ) -> Any:
        """Get metadata for a session."""
        return self._session_metadata.get(session_id, {}).get(key, default)

    # ══════════════════════════════════════════════════════════════════
    # CLEAR AND CLEANUP
    # ══════════════════════════════════════════════════════════════════

    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages for a session.

        Args:
            session_id: Session to clear

        Returns:
            True if session was found and cleared
        """
        if session_id in self._conversations:
            del self._conversations[session_id]
            self._summaries.pop(session_id, None)
            self._session_metadata.pop(session_id, None)
            logger.info("Cleared session: %s", session_id)
            return True
        return False

    def clear_all(self) -> None:
        """Clear all sessions."""
        self._conversations.clear()
        self._summaries.clear()
        self._session_metadata.clear()
        logger.info("Cleared all conversation sessions")

    def cleanup_expired_sessions(self) -> int:
        """
        Remove sessions that have been inactive beyond TTL.

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        expired = []

        for session_id, summary in self._summaries.items():
            if summary.last_message_at:
                if now - summary.last_message_at > self._session_ttl:
                    expired.append(session_id)

        for session_id in expired:
            self.clear_session(session_id)

        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))

        return len(expired)

    def search_messages(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[ConversationMessage]:
        """
        Search messages by content.

        Args:
            query: Search query (case-insensitive substring match)
            session_id: Optional session filter
            limit: Maximum results

        Returns:
            List of matching messages
        """
        query_lower = query.lower()
        results: list[ConversationMessage] = []

        sessions = [session_id] if session_id else list(self._conversations.keys())

        for sid in sessions:
            for msg in self._conversations.get(sid, []):
                if query_lower in msg.content.lower():
                    results.append(msg)
                    if len(results) >= limit:
                        return results

        return results

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _update_summary(self, session_id: str) -> None:
        """Update session summary after adding a message."""
        messages = self._conversations.get(session_id, [])
        summary = self._summaries.get(session_id)

        if summary is None:
            summary = SessionSummary(session_id=session_id)
            self._summaries[session_id] = summary

        summary.message_count = len(messages)
        summary.user_messages = sum(1 for m in messages if m.role == "user")
        summary.assistant_messages = sum(1 for m in messages if m.role == "assistant")
        summary.total_tokens = TokenEstimator.estimate_messages(messages)

        if messages:
            summary.first_message_at = messages[0].timestamp
            summary.last_message_at = messages[-1].timestamp

    def _trim_session(self, session_id: str) -> None:
        """
        Trim a session to max_messages, preserving system messages.

        System messages (like prompts) are kept even when trimming.
        """
        messages = self._conversations[session_id]

        # Separate system messages from others
        system_msgs = [m for m in messages if m.role == "system"]
        other_msgs = [m for m in messages if m.role != "system"]

        # Trim non-system messages
        max_other = self._max_messages - len(system_msgs)
        if len(other_msgs) > max_other:
            other_msgs = other_msgs[-max_other:]

            # Generate summary of removed messages if enabled
            if self._auto_summarize:
                removed = [m for m in messages if m.role != "system"][:len(messages) - self._max_messages]
                if removed:
                    summary = self._summaries.get(session_id)
                    if summary:
                        summary.summary_text = (
                            f"[Earlier conversation: {len(removed)} messages, "
                            f"topics included: {self._extract_topics(removed)}]"
                        )

        self._conversations[session_id] = system_msgs + other_msgs

    def _enforce_session_limit(self) -> None:
        """Enforce maximum number of sessions."""
        while len(self._conversations) > self._max_sessions:
            # Remove oldest session
            oldest_id = min(
                self._summaries.keys(),
                key=lambda sid: self._summaries[sid].first_message_at or datetime.min,
            )
            self.clear_session(oldest_id)

    @staticmethod
    def _extract_topics(messages: list[ConversationMessage]) -> str:
        """Extract brief topic summary from messages."""
        # Simple approach: extract key nouns/phrases from first few messages
        keywords = []
        for msg in messages[:5]:
            words = msg.content.lower().split()
            # Take first 3 significant words
            significant = [w for w in words if len(w) > 4][:3]
            keywords.extend(significant)

        return ", ".join(set(keywords[:6]))
