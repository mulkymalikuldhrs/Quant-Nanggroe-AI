"""Multi-channel messaging tool for the AI MultiColony Ecosystem.

Provides messaging capabilities across multiple channels
(Telegram, Discord, Slack, WhatsApp) with send/receive,
channel selection, message formatting, and channel registration.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, ChannelError
from ai_multicolony.types.messages import InboundMessage, MessageType, OutboundMessage
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


def _format_message(
    content: str,
    format_type: str = "text",
    channel_type: str = "text",
) -> str:
    """Format a message for a specific channel.

    Args:
        content: The raw message content.
        format_type: Desired format (text, markdown, html, json).
        channel_type: The target channel type.

    Returns:
        Formatted message string.
    """
    if format_type == "markdown":
        # Ensure markdown is preserved
        return content
    elif format_type == "html":
        # Simple markdown-to-HTML conversion
        import re
        html = content
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
        html = re.sub(r"\n", "<br>", html)
        return html
    elif format_type == "json":
        return json.dumps({"text": content, "timestamp": time.time()})
    else:
        return content


class ChannelTool(BaseTool):
    """Multi-channel messaging tool.

    Features:
    - Send messages to external channels (Telegram, Discord, Slack, WhatsApp)
    - Receive/poll messages from channels
    - List connected channels and their status
    - Channel-specific formatting
    - Message queue for offline channels
    - Register/unregister channel instances
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._channels: dict[str, Any] = {}
        self._message_queue: list[dict[str, Any]] = []
        self._max_queue_size = self._config.get("max_queue_size", 1000)

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="channel",
            description=(
                "Send and receive messages across multiple channels "
                "(Telegram, Discord, Slack, WhatsApp) with formatting"
            ),
            tool_type=ToolType.CHANNEL,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "Channel action: send, receive, list, status, "
                        "format, register, unregister"
                    ),
                    required=True,
                    enum=["send", "receive", "list", "status", "format", "register", "unregister"],
                ),
                ToolParameter(
                    name="channel_type",
                    type="string",
                    description="Channel type: telegram, discord, slack, whatsapp",
                    required=False,
                    enum=["telegram", "discord", "slack", "whatsapp"],
                ),
                ToolParameter(
                    name="recipient_id",
                    type="string",
                    description="Recipient ID (chat ID, channel ID, user ID)",
                    required=False,
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message content to send",
                    required=False,
                ),
                ToolParameter(
                    name="content_type",
                    type="string",
                    description="Content type: text, image, file, markdown",
                    required=False,
                    default="text",
                    enum=["text", "image", "file", "markdown"],
                ),
                ToolParameter(
                    name="format_type",
                    type="string",
                    description="Output format (for format action): text, markdown, html, json",
                    required=False,
                    default="text",
                    enum=["text", "markdown", "html", "json"],
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of messages to retrieve (for receive action)",
                    required=False,
                    default=10,
                ),
                ToolParameter(
                    name="reply_to",
                    type="string",
                    description="Message ID to reply to",
                    required=False,
                ),
            ],
            tags=["channel", "messaging", "communication"],
            requires_permission="channel.send",
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a channel action."""
        action = tool_call.arguments.get("action", "")

        dispatch = {
            "send": self._send,
            "receive": self._receive,
            "list": self._list,
            "status": self._status,
            "format": self._format,
            "register": self._register,
            "unregister": self._unregister,
        }

        handler = dispatch.get(action)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error=f"Unknown channel action: {action}",
            )
        return await handler(tool_call)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _send(self, tool_call: ToolCall) -> ToolResult:
        """Send a message to a channel."""
        channel_type = tool_call.arguments.get("channel_type", "")
        recipient_id = tool_call.arguments.get("recipient_id", "")
        message = tool_call.arguments.get("message", "")
        content_type_str = tool_call.arguments.get("content_type", "text")
        reply_to = tool_call.arguments.get("reply_to")

        if not channel_type:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error="channel_type is required for send action",
            )
        if not message:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error="message is required for send action",
            )

        # Map content type
        content_type_map = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "file": MessageType.FILE,
            "markdown": MessageType.TEXT,  # Markdown is sent as text
        }
        content_type = content_type_map.get(content_type_str, MessageType.TEXT)

        # Format message for the channel if needed
        formatted_message = message
        if channel_type == "discord" and content_type_str == "markdown":
            # Discord supports markdown natively
            pass
        elif channel_type == "slack":
            # Slack uses mrkdwn
            formatted_message = message
        elif channel_type == "telegram":
            # Telegram supports MarkdownV2 / HTML
            formatted_message = _format_message(message, "html", channel_type)
        elif channel_type == "whatsapp":
            # WhatsApp supports basic formatting
            formatted_message = _format_message(message, "text", channel_type)

        # Create outbound message
        outbound = OutboundMessage(
            channel_type=channel_type,
            channel_id=channel_type,
            recipient_id=recipient_id or "default",
            content=formatted_message,
            content_type=content_type,
            reply_to_message_id=reply_to,
        )

        # Try to route through the connected channel
        channel = self._channels.get(channel_type)
        if channel:
            try:
                # Channel instances may have different send interfaces
                if hasattr(channel, "send"):
                    success = await channel.send(outbound)
                elif hasattr(channel, "send_message"):
                    success = await channel.send_message(
                        recipient_id=recipient_id,
                        content=formatted_message,
                        content_type=content_type_str,
                    )
                else:
                    success = False

                if success:
                    return ToolResult(
                        tool_call_id=tool_call.id, tool_name="channel",
                        success=True,
                        output=f"Message sent to {channel_type}/{recipient_id}",
                        metadata={"outbound_id": outbound.id, "channel": channel_type},
                    )
                else:
                    return ToolResult(
                        tool_call_id=tool_call.id, tool_name="channel",
                        success=False,
                        error=f"Channel {channel_type} reported send failure",
                    )
            except Exception as e:
                # Queue the message for later delivery
                self._enqueue_message(outbound)
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="channel",
                    success=True,
                    output=f"Message queued for {channel_type}/{recipient_id} (channel error: {e})",
                    metadata={"outbound_id": outbound.id, "queued": True},
                )
        else:
            # No channel connected, queue the message
            self._enqueue_message(outbound)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True,
                output=f"Message queued for {channel_type}/{recipient_id} (no active channel)",
                metadata={"outbound_id": outbound.id, "queued": True},
            )

    async def _receive(self, tool_call: ToolCall) -> ToolResult:
        """Receive/poll messages from a channel."""
        channel_type = tool_call.arguments.get("channel_type", "")
        limit = tool_call.arguments.get("limit", 10)

        channel = self._channels.get(channel_type) if channel_type else None

        messages: list[dict[str, Any]] = []

        if channel and hasattr(channel, "get_messages"):
            try:
                inbound_messages = await channel.get_messages(limit=limit)
                for msg in inbound_messages:
                    if isinstance(msg, InboundMessage):
                        messages.append({
                            "id": msg.id[:8],
                            "sender": msg.sender_name or msg.sender_id,
                            "content": msg.content[:500],
                            "type": msg.content_type.value,
                            "timestamp": msg.timestamp,
                        })
                    elif isinstance(msg, dict):
                        messages.append(msg)
            except Exception as e:
                logger.warning("channel_receive_error", channel=channel_type, error=str(e))

        # Also check queued messages
        queued = [
            q for q in self._message_queue
            if not channel_type or q.get("channel_type") == channel_type
        ][:limit]

        messages.extend(queued)

        if not messages:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True,
                output="No messages available",
                metadata={"channel": channel_type, "count": 0},
            )

        # Format messages
        lines = []
        for m in messages[:limit]:
            lines.append(
                f"  [{m.get('channel_type', channel_type)}] "
                f"{m.get('sender', 'unknown')}: {m.get('content', '')[:200]}"
            )

        output = f"Messages ({len(messages)}):\n" + "\n".join(lines)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="channel",
            success=True, output=output,
            metadata={"count": len(messages), "channel": channel_type},
        )

    async def _list(self, tool_call: ToolCall) -> ToolResult:
        """List connected channels."""
        channels = list(self._channels.keys())
        if channels:
            details = []
            for name in channels:
                ch = self._channels[name]
                info = ""
                if hasattr(ch, "get_info"):
                    try:
                        info = str(ch.get_info())
                    except Exception:
                        info = "info unavailable"
                details.append(f"  {name}: {info}" if info else f"  {name}")
            output = "Connected channels:\n" + "\n".join(details)
        else:
            output = "No channels connected"

        queue_count = len(self._message_queue)
        if queue_count:
            output += f"\n\nQueued messages: {queue_count}"

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="channel",
            success=True, output=output,
            metadata={"channel_count": len(channels), "queue_size": queue_count},
        )

    async def _status(self, tool_call: ToolCall) -> ToolResult:
        """Get detailed channel status."""
        channel_type = tool_call.arguments.get("channel_type", "")

        if channel_type:
            channel = self._channels.get(channel_type)
            if channel is None:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="channel",
                    success=False, error=f"Channel not found: {channel_type}",
                )

            info: dict[str, Any] = {"type": channel_type, "connected": True}
            if hasattr(channel, "get_info"):
                try:
                    info.update(channel.get_info())
                except Exception:
                    pass
            if hasattr(channel, "is_connected"):
                info["connected"] = channel.is_connected()

            output = "\n".join(f"  {k}: {v}" for k, v in info.items())
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True, output=f"Channel '{channel_type}' status:\n{output}",
                metadata=info,
            )
        else:
            # All channels
            all_info: dict[str, Any] = {}
            for name, ch in self._channels.items():
                ch_info: dict[str, Any] = {"type": name, "connected": True}
                if hasattr(ch, "get_info"):
                    try:
                        ch_info.update(ch.get_info())
                    except Exception:
                        pass
                all_info[name] = ch_info

            if all_info:
                lines = []
                for name, info in all_info.items():
                    lines.append(f"  {name}: connected={info.get('connected', 'unknown')}")
                output = "Channel Status:\n" + "\n".join(lines)
            else:
                output = "No channels connected"

            output += f"\nQueued messages: {len(self._message_queue)}"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True, output=output,
                metadata=all_info,
            )

    async def _format(self, tool_call: ToolCall) -> ToolResult:
        """Format a message for a specific channel without sending."""
        message = tool_call.arguments.get("message", "")
        format_type = tool_call.arguments.get("format_type", "text")
        channel_type = tool_call.arguments.get("channel_type", "text")

        if not message:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error="message is required for format action",
            )

        formatted = _format_message(message, format_type, channel_type)
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="channel",
            success=True, output=formatted,
            metadata={"format_type": format_type, "channel_type": channel_type},
        )

    async def _register(self, tool_call: ToolCall) -> ToolResult:
        """Register a channel (metadata only — actual channel instance
        should be registered via ``register_channel()`` method).

        This action records that a channel of the given type should be
        expected, but the actual channel instance must be registered
        programmatically.
        """
        channel_type = tool_call.arguments.get("channel_type", "")
        if not channel_type:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error="channel_type is required",
            )

        if channel_type in self._channels:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True, output=f"Channel '{channel_type}' is already registered",
            )

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="channel",
            success=True,
            output=f"Channel '{channel_type}' noted. Register the actual instance via register_channel().",
        )

    async def _unregister(self, tool_call: ToolCall) -> ToolResult:
        """Unregister a channel."""
        channel_type = tool_call.arguments.get("channel_type", "")
        if not channel_type:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=False, error="channel_type is required",
            )

        if channel_type in self._channels:
            del self._channels[channel_type]
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="channel",
                success=True, output=f"Unregistered channel: {channel_type}",
            )
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="channel",
            success=False, error=f"Channel not found: {channel_type}",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_channel(self, channel_type: str, channel: Any) -> None:
        """Register a channel instance.

        Args:
            channel_type: The channel type identifier.
            channel: The channel instance (should have send/get_info methods).
        """
        self._channels[channel_type] = channel
        logger.info("channel_registered", channel_type=channel_type)

    def unregister_channel(self, channel_type: str) -> None:
        """Unregister a channel instance.

        Args:
            channel_type: The channel type to unregister.
        """
        self._channels.pop(channel_type, None)
        logger.info("channel_unregistered", channel_type=channel_type)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _enqueue_message(self, outbound: OutboundMessage) -> None:
        """Add an outbound message to the delivery queue.

        Args:
            outbound: The message to queue.
        """
        self._message_queue.append({
            "id": outbound.id,
            "channel_type": outbound.channel_type,
            "recipient_id": outbound.recipient_id,
            "content": outbound.content[:500],
            "content_type": outbound.content_type.value,
            "timestamp": outbound.timestamp,
        })

        # Trim queue if too large
        if len(self._message_queue) > self._max_queue_size:
            self._message_queue = self._message_queue[-self._max_queue_size:]
