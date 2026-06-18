"""AutoGen framework adapter for AI-MultiColony.

Provides an adapter that wraps AutoGen-style multi-agent
conversations into the AI-MultiColony ecosystem, enabling
seamless integration with AutoGen's conversational agent
patterns.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class AutoGenRole(str, Enum):
    """AutoGen agent role types."""
    ASSISTANT = "assistant"
    USER_PROXY = "user_proxy"
    GROUP_CHAT_MANAGER = "group_chat_manager"
    PLANNER = "planner"
    CRITIC = "critic"
    EXECUTOR = "executor"


class ConversationStatus(str, Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ERROR = "error"
    MAX_ROUNDS_REACHED = "max_rounds_reached"


# ── Models ───────────────────────────────────────────────────────────────────


class AutoGenAgent(BaseModel):
    """An AutoGen-style agent definition."""
    model_config = ConfigDict(frozen=False)

    agent_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    role: AutoGenRole = AutoGenRole.ASSISTANT
    system_message: str = ""
    max_consecutive_auto_reply: int = 10
    human_input_mode: str = "NEVER"  # ALWAYS, TERMINATE, NEVER
    code_execution: bool = False


class ChatMessage(BaseModel):
    """A message in an AutoGen conversation."""
    model_config = ConfigDict(frozen=False)

    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender: str = ""
    receiver: str = ""
    content: str = ""
    round_number: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationResult(BaseModel):
    """Result from an AutoGen conversation."""
    model_config = ConfigDict(frozen=False)

    conversation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: ConversationStatus = ConversationStatus.ACTIVE
    participants: List[str] = Field(default_factory=list)
    messages: List[ChatMessage] = Field(default_factory=list)
    rounds_completed: int = 0
    max_rounds: int = 10
    summary: str = ""
    errors: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── AutoGen Adapter ──────────────────────────────────────────────────────────


class AutoGenAdapter:
    """Adapter for AutoGen-style multi-agent conversations.

    Translates AutoGen concepts (conversational agents, group chats,
    message passing) into AI-MultiColony execution patterns.

    Usage::

        adapter = AutoGenAdapter()
        adapter.add_agent(AutoGenAgent(name="Assistant", role=AutoGenRole.ASSISTANT))
        adapter.add_agent(AutoGenAgent(name="User", role=AutoGenRole.USER_PROXY))
        result = await adapter.chat("Analyze this data", max_rounds=5)
    """

    def __init__(self, max_rounds: int = 10):
        self._agents: Dict[str, AutoGenAgent] = {}
        self._max_rounds = max_rounds
        self._response_map: Dict[str, Callable] = {}
        self._conversations: List[ConversationResult] = []

    def add_agent(self, agent: AutoGenAgent) -> None:
        """Add an agent to the conversation."""
        self._agents[agent.name] = agent
        logger.debug("Added AutoGen agent: %s (%s)", agent.name, agent.role.value)

    def register_response(self, agent_name: str, response_fn: Callable) -> None:
        """Register a custom response function for an agent."""
        self._response_map[agent_name] = response_fn

    async def chat(
        self,
        initial_message: str,
        max_rounds: Optional[int] = None,
        participants: Optional[List[str]] = None,
    ) -> ConversationResult:
        """Run a multi-agent conversation.

        Parameters
        ----------
        initial_message:
            The initial message to start the conversation.
        max_rounds:
            Maximum conversation rounds.
        participants:
            Specific agents to include (all if None).

        Returns
        -------
        ConversationResult
            Conversation result with all messages.
        """
        import time
        start = time.monotonic()

        rounds = max_rounds or self._max_rounds
        result = ConversationResult(
            max_rounds=rounds,
            participants=participants or list(self._agents.keys()),
        )

        # Create initial message
        first_agent = result.participants[0] if result.participants else "User"
        messages: List[ChatMessage] = [
            ChatMessage(
                sender="User",
                receiver=first_agent,
                content=initial_message,
                round_number=0,
            )
        ]

        # Run conversation rounds
        for round_num in range(1, rounds + 1):
            round_messages: List[ChatMessage] = []

            for agent_name in result.participants:
                agent = self._agents.get(agent_name)
                if agent is None:
                    continue

                # Get response
                response_fn = self._response_map.get(agent_name)
                if response_fn:
                    try:
                        if asyncio.iscoroutinefunction(response_fn):
                            response = await response_fn(
                                messages=messages,
                                agent=agent,
                                round_number=round_num,
                            )
                        else:
                            response = response_fn(
                                messages=messages,
                                agent=agent,
                                round_number=round_num,
                            )
                    except Exception as e:
                        result.errors.append(f"Agent {agent_name} error: {e}")
                        continue
                else:
                    response = f"[{agent_name}] Processing round {round_num}"

                # Determine next agent
                next_idx = (result.participants.index(agent_name) + 1) % len(result.participants)
                next_agent = result.participants[next_idx]

                msg = ChatMessage(
                    sender=agent_name,
                    receiver=next_agent,
                    content=str(response),
                    round_number=round_num,
                )
                messages.append(msg)
                round_messages.append(msg)

            result.rounds_completed = round_num

            # Check for termination
            if any("TERMINATE" in m.content for m in round_messages):
                result.status = ConversationStatus.COMPLETED
                break

        if result.rounds_completed >= rounds and result.status == ConversationStatus.ACTIVE:
            result.status = ConversationStatus.MAX_ROUNDS_REACHED

        result.messages = messages
        result.duration_ms = (time.monotonic() - start) * 1000

        # Generate summary
        if messages:
            result.summary = messages[-1].content[:200]

        self._conversations.append(result)
        return result

    async def group_chat(
        self,
        message: str,
        manager_name: str = "Manager",
        max_rounds: Optional[int] = None,
    ) -> ConversationResult:
        """Run a group chat with a manager agent.

        The manager selects which agent speaks next.

        Parameters
        ----------
        message:
            Initial message.
        manager_name:
            Name of the managing agent.
        max_rounds:
            Maximum rounds.

        Returns
        -------
        ConversationResult
            Group chat result.
        """
        # Add a manager if not present
        if manager_name not in self._agents:
            self.add_agent(AutoGenAgent(
                name=manager_name,
                role=AutoGenRole.GROUP_CHAT_MANAGER,
                system_message="You are the group chat manager.",
            ))

        return await self.chat(message, max_rounds=max_rounds)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def agents(self) -> Dict[str, AutoGenAgent]:
        return dict(self._agents)

    @property
    def conversations(self) -> List[ConversationResult]:
        return list(self._conversations)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "agent_count": len(self._agents),
            "total_conversations": len(self._conversations),
            "max_rounds": self._max_rounds,
        }
