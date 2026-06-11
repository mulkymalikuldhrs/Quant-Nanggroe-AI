"""Session memory for Quant Nanggroe AI agents.

Provides in-memory and persistent storage for agent session state,
enabling context preservation across iterations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionMemory:
    """
    Session-level memory for agent context preservation.

    Stores agent outputs, market state, and decisions within a trading session.
    Supports both in-memory and file-based persistence.

    Usage:
        memory = SessionMemory(session_id="session_2024_01_01")
        memory.store("researcher", {"analysis": "BTC trending upward"})
        context = memory.get_context("researcher")
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        persist_dir: Optional[str] = None,
        max_entries: int = 100,
    ):
        """
        Initialize session memory.

        Args:
            session_id: Unique session identifier
            persist_dir: Directory for file-based persistence
            max_entries: Maximum entries per agent before compaction
        """
        self._session_id = session_id or datetime.now(timezone.utc).strftime("session_%Y%m%d_%H%M%S")
        self._persist_dir = Path(persist_dir) if persist_dir else None
        self._max_entries = max_entries
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata: Dict[str, Any] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
        }

    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self._session_id

    def store(self, agent_name: str, data: Dict[str, Any]) -> None:
        """
        Store agent output in session memory.

        Args:
            agent_name: Name of the agent producing the output
            data: Output data to store
        """
        if agent_name not in self._store:
            self._store[agent_name] = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self._store[agent_name].append(entry)

        # Compaction: keep only the most recent entries
        if len(self._store[agent_name]) > self._max_entries:
            self._store[agent_name] = self._store[agent_name][-self._max_entries:]

        logger.debug(f"Stored {agent_name} output in session {self._session_id}")

    def get_context(
        self,
        agent_name: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recent context for an agent.

        Args:
            agent_name: Agent name to get context for
            limit: Maximum number of entries to return

        Returns:
            List of recent entries for the agent
        """
        entries = self._store.get(agent_name, [])
        return entries[-limit:]

    def get_latest(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the most recent entry for an agent."""
        entries = self._store.get(agent_name, [])
        return entries[-1] if entries else None

    def get_all_context(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all stored context."""
        return self._store

    def clear(self, agent_name: Optional[str] = None) -> None:
        """Clear memory for a specific agent or all agents."""
        if agent_name:
            self._store.pop(agent_name, None)
        else:
            self._store.clear()

    def save(self) -> None:
        """Persist session memory to disk."""
        if not self._persist_dir:
            return
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._persist_dir / f"{self._session_id}.json"
        with open(filepath, "w") as f:
            json.dump(
                {"metadata": self._metadata, "store": self._store},
                f,
                indent=2,
                default=str,
            )
        logger.info(f"Session memory saved to {filepath}")

    def load(self, session_id: Optional[str] = None) -> bool:
        """Load session memory from disk."""
        if not self._persist_dir:
            return False
        sid = session_id or self._session_id
        filepath = self._persist_dir / f"{sid}.json"
        if not filepath.exists():
            return False
        with open(filepath) as f:
            data = json.load(f)
        self._metadata = data.get("metadata", {})
        self._store = data.get("store", {})
        logger.info(f"Session memory loaded from {filepath}")
        return True

    def summary(self) -> Dict[str, int]:
        """Get a summary of stored entries per agent."""
        return {agent: len(entries) for agent, entries in self._store.items()}
