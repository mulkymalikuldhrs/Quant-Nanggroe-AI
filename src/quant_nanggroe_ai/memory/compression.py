"""
Memory Compression — adapted from agenticSeek memory system.

Provides:
  - Conversation memory management with push/get/clear operations
  - Automatic memory compression when context grows too large
  - Summarization-based compression (lightweight, no heavy ML deps)
  - Session save/load for conversation persistence
  - Integration hooks for quant_nanggroe_ai.memory module

Adapted from agenticSeek/sources/memory.py which uses:
  - LED (Longformer Encoder-Decoder) for summarization
  - Context size estimation based on model parameters
  - Adaptive compression thresholds

This version uses a lightweight summarization approach that falls back
to truncation when no summarization model is available.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    """Roles for conversation messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ConversationMessage:
    """A single conversation message."""
    role: MessageRole
    content: str
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.timestamp:
            d["timestamp"] = self.timestamp
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationMessage:
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Compression strategies
# ---------------------------------------------------------------------------

class CompressionStrategy(str, Enum):
    """Available compression strategies."""
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"


# ---------------------------------------------------------------------------
# Compressible Memory
# ---------------------------------------------------------------------------

class CompressibleMemory:
    """
    Conversation memory with automatic compression.

    Adapted from agenticSeek Memory class which uses:
      - LED model (pszemraj/led-base-book-summary) for summarization
      - Context size estimation: ctx = base_ctx * (model_size / base_size) ^ 1.5
      - Compression triggers when content exceeds estimated context
      - Per-message compression for messages > 1024 chars

    This version provides the same interface with configurable compression:
      - TRUNCATE: Simple truncation to max_chars
      - SUMMARIZE: Uses a callable summarizer (inject your own model)
    """

    DEFAULT_MAX_CHARS = 4096
    COMPRESS_THRESHOLD_CHARS = 1024

    def __init__(
        self,
        system_prompt: str = "",
        max_context_chars: int = DEFAULT_MAX_CHARS,
        compression_strategy: CompressionStrategy = CompressionStrategy.TRUNCATE,
        summarizer: Optional[Callable[[str], str]] = None,
        session_dir: str = "conversations",
    ) -> None:
        """
        Args:
            system_prompt: Initial system prompt.
            max_context_chars: Maximum characters before compression triggers.
            compression_strategy: How to compress when limits exceeded.
            summarizer: Optional callable(text) -> summary for SUMMARIZE strategy.
            session_dir: Directory for saving/loading sessions.
        """
        self.messages: List[ConversationMessage] = []
        self.max_context_chars = max_context_chars
        self.compression_strategy = compression_strategy
        self.summarizer = summarizer
        self.session_dir = session_dir
        self._session_time = datetime.now()
        self._session_id = f"{int(time.time() * 1000)}"

        if system_prompt:
            self.messages.append(ConversationMessage(
                role=MessageRole.SYSTEM,
                content=system_prompt,
                timestamp=self._now(),
            ))

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def push(
        self,
        role: MessageRole | str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Push a message to memory.

        Args:
            role: Message role (MessageRole or string).
            content: Message content.
            metadata: Optional metadata dict.

        Returns:
            Index of the added message.
        """
        if isinstance(role, str):
            role = MessageRole(role)

        # Check for duplicate
        if self.messages and self.messages[-1].content == content:
            logger.debug("Duplicate message detected, skipping push.")
            return len(self.messages) - 1

        msg = ConversationMessage(
            role=role,
            content=content,
            timestamp=self._now(),
            metadata=metadata or {},
        )
        self.messages.append(msg)

        # Auto-compress if exceeding limit
        total_chars = sum(len(m.content) for m in self.messages)
        if total_chars > self.max_context_chars * 1.5:
            logger.info(
                f"Memory ({total_chars} chars) exceeds limit "
                f"({self.max_context_chars * 1.5}), compressing..."
            )
            self.compress()

        return len(self.messages) - 1

    def get(self) -> List[Dict[str, Any]]:
        """Get all messages as dicts (for LLM API compatibility)."""
        return [m.to_dict() for m in self.messages]

    def get_messages(self) -> List[ConversationMessage]:
        """Get all messages as ConversationMessage objects."""
        return list(self.messages)

    def clear(self, keep_system: bool = True) -> None:
        """Clear memory, optionally keeping system prompt."""
        if keep_system and self.messages and self.messages[0].role == MessageRole.SYSTEM:
            self.messages = [self.messages[0]]
        else:
            self.messages = []

    def clear_section(self, start: int, end: int) -> None:
        """
        Clear a section of memory (excluding system message).

        Args:
            start: Start index (0-based, after system message).
            end: End index (exclusive, after system message).
        """
        # Adjust indices for system message offset
        offset = 1 if self.messages and self.messages[0].role == MessageRole.SYSTEM else 0
        actual_start = max(0, start) + offset
        actual_end = min(end, len(self.messages)) + offset
        self.messages = self.messages[:actual_start] + self.messages[actual_end:]

    def compress(self) -> None:
        """
        Compress memory by summarizing or truncating long messages.

        Adapted from agenticSeek's compress() which:
          1. Skips system messages
          2. Summarizes messages > 1024 chars using LED model
          3. Replaces original content with summary
        """
        for i, msg in enumerate(self.messages):
            if msg.role == MessageRole.SYSTEM:
                continue
            if len(msg.content) > self.COMPRESS_THRESHOLD_CHARS:
                compressed = self._compress_text(msg.content)
                if compressed != msg.content:
                    logger.info(
                        f"Compressed message {i}: "
                        f"{len(msg.content)} → {len(compressed)} chars"
                    )
                    msg.content = compressed

    def save(self, agent_type: str = "default") -> str:
        """
        Save conversation to a JSON file.

        Returns:
            Path to saved file.
        """
        save_dir = os.path.join(self.session_dir, agent_type)
        os.makedirs(save_dir, exist_ok=True)
        filename = f"memory_{self._session_time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        path = os.path.join(save_dir, filename)

        data = {
            "session_id": self._session_id,
            "messages": [m.to_dict() for m in self.messages],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved memory to {path}")
        return path

    def load(self, agent_type: str = "default") -> bool:
        """
        Load the most recent conversation session.

        Returns:
            True if session was loaded successfully.
        """
        load_dir = os.path.join(self.session_dir, agent_type)
        if not os.path.exists(load_dir):
            return False

        # Find most recent session file
        files = [
            f for f in os.listdir(load_dir)
            if f.startswith("memory_") and f.endswith(".json")
        ]
        if not files:
            return False

        files.sort(reverse=True)
        path = os.path.join(load_dir, files[0])

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.messages = [ConversationMessage.from_dict(m) for m in data.get("messages", [])]
            # Remove last message if it's a user message (incomplete conversation)
            if self.messages and self.messages[-1].role == MessageRole.USER:
                self.messages.pop()
            logger.info(f"Loaded memory from {path} ({len(self.messages)} messages)")
            return True
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load memory from {path}: {e}")
            return False

    # -------------------------------------------------------------------
    # Context estimation (from agenticSeek pattern)
    # -------------------------------------------------------------------

    @staticmethod
    def estimate_context_size(model_name: str) -> Optional[int]:
        """
        Estimate context window size from model name.

        Adapted from agenticSeek's get_ideal_ctx():
          - Extracts parameter count (e.g., "14b" → 14)
          - Uses power-law scaling: ctx = 4096 * (size/7)^1.5
          - Rounds to nearest power of 2

        Args:
            model_name: Model name string (e.g., "deepseek-r1:14b", "gpt-4o-mini").

        Returns:
            Estimated context size in tokens, or None if can't determine.
        """
        import math
        import re

        match = re.search(r"(\d+)b", model_name, re.IGNORECASE)
        if not match:
            return None

        model_size = int(match.group(1))
        base_size = 7
        base_context = 4096
        scaling_factor = 1.5

        context_size = int(base_context * (model_size / base_size) ** scaling_factor)
        context_size = 2 ** round(math.log2(context_size))

        return context_size

    def total_chars(self) -> int:
        """Total characters across all messages."""
        return sum(len(m.content) for m in self.messages)

    # -------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------

    def _compress_text(self, text: str) -> str:
        """Compress a single text using configured strategy."""
        if self.compression_strategy == CompressionStrategy.NONE:
            return text

        if self.compression_strategy == CompressionStrategy.SUMMARIZE and self.summarizer:
            try:
                summary = self.summarizer(text)
                if summary and len(summary) < len(text):
                    return summary
            except Exception as e:
                logger.warning(f"Summarization failed, falling back to truncation: {e}")

        # Default: truncate
        half = self.max_context_chars // 2
        if len(text) <= half:
            return text
        return text[:half] + f"\n...[compressed, {len(text) - half} chars omitted]...\n"

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
