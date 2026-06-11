"""ChannelTool – multi-platform messaging and webhook management.

Autonomy levels:
  - L1: send, list_channels
  - L2: receive, manage_webhooks
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)

# Supported channel types
SUPPORTED_CHANNELS = {"telegram", "whatsapp", "discord", "slack"}


class WebhookEntry:
    """Registered webhook."""

    def __init__(
        self,
        webhook_id: str,
        channel: str,
        url: str,
        events: Optional[List[str]] = None,
        secret: str = "",
    ) -> None:
        self.webhook_id = webhook_id
        self.channel = channel
        self.url = url
        self.events = events or ["message"]
        self.secret = secret
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.active: bool = True
        self.call_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "channel": self.channel,
            "url": self.url,
            "events": self.events,
            "active": self.active,
            "created_at": self.created_at,
            "call_count": self.call_count,
        }


class MessageRecord:
    """Record of a sent or received message."""

    def __init__(
        self,
        message_id: str,
        channel: str,
        direction: str,
        content: str,
        recipient: str = "",
        sender: str = "",
        metadata: Optional[Dict] = None,
    ) -> None:
        self.message_id = message_id
        self.channel = channel
        self.direction = direction  # "sent" or "received"
        self.content = content
        self.recipient = recipient
        self.sender = sender
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "channel": self.channel,
            "direction": self.direction,
            "content": self.content[:200],  # truncate for display
            "recipient": self.recipient,
            "sender": self.sender,
            "timestamp": self.timestamp,
        }


class ChannelTool(MCPTool):
    """Multi-platform messaging: Telegram, WhatsApp, Discord, Slack.

    Also supports webhook registration and management.

    Actions
    -------
    send            : send a message (L1)
    receive         : receive / poll messages (L2)
    list_channels   : list available channels (L1)
    manage_webhooks : register / list / delete webhooks (L2)
    history         : get message history (L1)
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "comm.channel"

    def category(self) -> str:
        return "communication"

    def autonomy_level(self) -> int:
        return 1

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action", "channel"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send", "receive", "list_channels", "manage_webhooks", "history"],
                    "description": "Channel action",
                },
                "channel": {
                    "type": "string",
                    "enum": ["telegram", "whatsapp", "discord", "slack"],
                    "description": "Target channel platform",
                },
                "message": {
                    "type": "string",
                    "description": "Message content to send",
                },
                "recipient": {
                    "type": "string",
                    "description": "Recipient identifier (user ID, channel ID, etc.)",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Max messages to retrieve",
                },
                "webhook_action": {
                    "type": "string",
                    "enum": ["register", "list", "delete"],
                    "description": "Webhook sub-action",
                },
                "webhook_url": {
                    "type": "string",
                    "description": "Webhook URL to register",
                },
                "webhook_id": {
                    "type": "string",
                    "description": "Webhook ID to delete",
                },
                "webhook_events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Events to subscribe to",
                },
                "parse_mode": {
                    "type": "string",
                    "enum": ["text", "markdown", "html"],
                    "default": "text",
                    "description": "Message parse mode",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "data": {"type": "object"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 9001, "message": "Unsupported channel"},
            {"code": 9002, "message": "Message delivery failed"},
            {"code": 9003, "message": "Recipient not found"},
            {"code": 9004, "message": "Webhook registration failed"},
            {"code": 9005, "message": "Webhook not found"},
            {"code": 9006, "message": "Channel not connected"},
        ]

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__()
        self._messages: List[MessageRecord] = []
        self._webhooks: Dict[str, WebhookEntry] = {}
        self._channel_status: Dict[str, str] = {
            ch: "connected" for ch in SUPPORTED_CHANNELS
        }

    # ── Autonomy mapping ─────────────────────────────────────────

    @staticmethod
    def action_autonomy(action: str) -> int:
        mapping = {
            "send": 1, "list_channels": 1, "history": 1,
            "receive": 2, "manage_webhooks": 2,
        }
        return mapping.get(action, 2)

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        channel: str = params["channel"]
        autonomy = context.get("autonomy_level", 0)
        required = self.action_autonomy(action)

        if autonomy < required:
            self.record_call(False)
            return {
                "success": False,
                "message_id": "",
                "data": {"error": f"Action '{action}' requires L{required}, current L{autonomy}"},
            }

        if channel not in SUPPORTED_CHANNELS:
            self.record_call(False)
            return {
                "success": False,
                "message_id": "",
                "data": {"error": f"Unsupported channel: {channel}"},
            }

        dispatch = {
            "send": self._send,
            "receive": self._receive,
            "list_channels": self._list_channels,
            "manage_webhooks": self._manage_webhooks,
            "history": self._history,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {
                "success": False,
                "message_id": "",
                "data": {"error": f"Unknown action: {action}"},
            }

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {"success": False, "message_id": "", "data": {"error": str(exc)}}

    # ── Send ─────────────────────────────────────────────────────

    async def _send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channel = params["channel"]
        message = params.get("message", "")
        recipient = params.get("recipient", "")
        parse_mode = params.get("parse_mode", "text")

        if not message:
            return {"success": False, "message_id": "", "data": {"error": "No message content provided"}}

        # Check channel status
        if self._channel_status.get(channel) != "connected":
            return {"success": False, "message_id": "", "data": {"error": f"Channel {channel} not connected"}}

        # Generate message ID
        msg_id = f"msg-{channel}-{uuid.uuid4().hex[:8]}"

        # Record the message
        record = MessageRecord(
            message_id=msg_id,
            channel=channel,
            direction="sent",
            content=message,
            recipient=recipient,
            metadata={"parse_mode": parse_mode},
        )
        self._messages.append(record)

        # Simulate delivery
        logger.info("Message sent to %s via %s: %s", recipient or "broadcast", channel, msg_id)

        return {
            "success": True,
            "message_id": msg_id,
            "data": {
                "channel": channel,
                "recipient": recipient,
                "timestamp": record.timestamp,
                "parse_mode": parse_mode,
            },
        }

    # ── Receive ──────────────────────────────────────────────────

    async def _receive(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channel = params["channel"]
        limit = params.get("limit", 10)

        # Simulate receiving messages
        received = [
            m for m in self._messages
            if m.channel == channel and m.direction == "received"
        ]

        # Generate a simulated incoming message if none exist
        if not received:
            msg_id = f"msg-recv-{uuid.uuid4().hex[:8]}"
            simulated = MessageRecord(
                message_id=msg_id,
                channel=channel,
                direction="received",
                content=f"Simulated incoming message on {channel}",
                sender="user-123",
            )
            self._messages.append(simulated)
            received = [simulated]

        messages = [m.to_dict() for m in received[-limit:]]

        return {
            "success": True,
            "message_id": received[-1].message_id if received else "",
            "data": {
                "messages": messages,
                "count": len(messages),
                "channel": channel,
            },
        }

    # ── List channels ────────────────────────────────────────────

    async def _list_channels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channels = [
            {
                "name": ch,
                "status": self._channel_status.get(ch, "unknown"),
                "supported": True,
            }
            for ch in sorted(SUPPORTED_CHANNELS)
        ]
        return {
            "success": True,
            "message_id": "",
            "data": {"channels": channels, "count": len(channels)},
        }

    # ── Webhook management ───────────────────────────────────────

    async def _manage_webhooks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        webhook_action = params.get("webhook_action", "list")
        channel = params["channel"]

        if webhook_action == "register":
            url = params.get("webhook_url", "")
            events = params.get("webhook_events", ["message"])

            if not url:
                return {"success": False, "message_id": "", "data": {"error": "Webhook URL is required"}}

            webhook_id = f"wh-{uuid.uuid4().hex[:8]}"
            secret = hashlib.sha256(f"{webhook_id}:{url}".encode()).hexdigest()[:16]

            entry = WebhookEntry(
                webhook_id=webhook_id,
                channel=channel,
                url=url,
                events=events,
                secret=secret,
            )
            self._webhooks[webhook_id] = entry

            return {
                "success": True,
                "message_id": "",
                "data": {
                    "webhook_id": webhook_id,
                    "url": url,
                    "channel": channel,
                    "events": events,
                    "secret": secret,
                },
            }

        elif webhook_action == "delete":
            webhook_id = params.get("webhook_id", "")
            if webhook_id not in self._webhooks:
                return {"success": False, "message_id": "", "data": {"error": f"Webhook not found: {webhook_id}"}}
            del self._webhooks[webhook_id]
            return {"success": True, "message_id": "", "data": {"deleted": webhook_id}}

        elif webhook_action == "list":
            webhooks = [
                w.to_dict() for w in self._webhooks.values()
                if w.channel == channel
            ]
            return {
                "success": True,
                "message_id": "",
                "data": {"webhooks": webhooks, "count": len(webhooks)},
            }

        return {"success": False, "message_id": "", "data": {"error": f"Unknown webhook action: {webhook_action}"}}

    # ── History ──────────────────────────────────────────────────

    async def _history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        channel = params["channel"]
        limit = params.get("limit", 10)

        messages = [
            m.to_dict() for m in self._messages
            if m.channel == channel
        ]

        return {
            "success": True,
            "message_id": "",
            "data": {
                "messages": messages[-limit:],
                "total": len(messages),
                "channel": channel,
            },
        }
