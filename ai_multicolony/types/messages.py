"""Message type definitions for the AI MultiColony Ecosystem.

Merges Nanobot MessageBus patterns with standard LLM message formats.
Defines Message, InboundMessage, OutboundMessage, and MessageType.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages in the system."""

    # LLM conversation
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"

    # Internal bus
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"

    # Channel
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"

    # Control
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    CONTROL = "control"


class MessageRole(str, Enum):
    """Roles for conversation messages (OpenAI-compatible)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class Message(BaseModel):
    """A conversation message following the OpenAI chat format."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str | list[dict[str, Any]] = ""
    name: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict format suitable for LLM API calls."""
        result: dict[str, Any] = {"role": self.role.value}
        if isinstance(self.content, str):
            result["content"] = self.content
        else:
            result["content"] = self.content
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


class BusMessagePriority(str, Enum):
    """Priority levels for bus messages."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BusMessage(BaseModel):
    """A message on the internal event/message bus.

    Following Nanobot MessageBus pattern.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    recipient: Optional[str] = None
    channel: str = "default"
    message_type: MessageType = MessageType.NOTIFICATION
    content: dict[str, Any] = Field(default_factory=dict)
    priority: BusMessagePriority = BusMessagePriority.NORMAL
    timestamp: float = Field(default_factory=time.time)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class InboundMessage(BaseModel):
    """An inbound message from an external channel.

    Following Nanobot InboundMessage pattern.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_type: str
    channel_id: str
    sender_id: str
    sender_name: Optional[str] = None
    content: str
    content_type: MessageType = MessageType.TEXT
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    model_config = {"arbitrary_types_allowed": True}

    def to_bus_message(self) -> BusMessage:
        """Convert to a BusMessage for internal routing."""
        return BusMessage(
            sender=self.sender_id,
            channel=self.channel_type,
            message_type=MessageType.NOTIFICATION,
            content={
                "channel_type": self.channel_type,
                "channel_id": self.channel_id,
                "sender_name": self.sender_name,
                "content": self.content,
                "content_type": self.content_type.value,
                "attachments": self.attachments,
            },
            metadata=self.metadata,
        )


class OutboundMessage(BaseModel):
    """An outbound message to an external channel.

    Following Nanobot OutboundMessage pattern.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_type: str
    channel_id: str
    recipient_id: str
    content: str
    content_type: MessageType = MessageType.TEXT
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    model_config = {"arbitrary_types_allowed": True}
