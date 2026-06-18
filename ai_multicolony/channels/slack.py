"""Slack integration channel.

Features:
* Message sending/receiving
* Block Kit support (sections, actions, inputs)
* Thread support
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from ..types import (
    ChannelType,
    ChannelMessage,
    MessageFormat,
    BlockElement,
)

logger = logging.getLogger(__name__)


class SlackIntegration:
    """Slack integration for agent communication.

    Parameters
    ----------
    token : str
        The Slack bot token (xoxb-...).
    signing_secret : str
        The Slack signing secret for request verification.
    """

    def __init__(
        self,
        token: str = "",
        signing_secret: str = "",
    ):
        self.token = token
        self.signing_secret = signing_secret
        self._connected = False
        self._messages: List[Dict[str, Any]] = []
        self._threads: Dict[str, List[Dict[str, Any]]] = {}  # thread_ts → messages
        self._channel_handlers: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._reaction_handlers: List[Callable[..., Coroutine[Any, Any, Any]]] = []
        self._bot_user_id: str = ""

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to Slack (simulated: would call auth.test)."""
        if not self.token:
            self._connected = False
            return False
        self._connected = True
        self._bot_user_id = "U_MULTICOLONY"
        logger.info("Slack integration connected")
        return True

    async def disconnect(self) -> None:
        """Disconnect from Slack."""
        self._connected = False
        logger.info("Slack integration disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Message sending ────────────────────────────────────────────────────

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False,
        format: MessageFormat = MessageFormat.MARKDOWN,
    ) -> Dict[str, Any]:
        """Send a text message to a Slack channel.

        Parameters
        ----------
        channel : str
            Channel ID or name (e.g., #general or C12345678).
        text : str
            Message text (max 40000 characters).
        thread_ts : str, optional
            Parent message timestamp for threaded replies.
        reply_broadcast : bool
            If replying in thread, also post to the channel.
        format : MessageFormat
            Formatting mode.

        Returns
        -------
        dict with success status and message metadata.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        if len(text) > 40000:
            text = text[:39997] + "..."

        ts = f"{datetime.now(timezone.utc).timestamp():.6f}"

        msg = {
            "channel": channel,
            "text": text,
            "ts": ts,
            "message_id": f"sl-{len(self._messages)}",
            "user": self._bot_user_id,
            "type": "message",
            "subtype": "bot_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if thread_ts:
            msg["thread_ts"] = thread_ts
            msg["reply_broadcast"] = reply_broadcast
            # Track in thread
            if thread_ts not in self._threads:
                self._threads[thread_ts] = []
            self._threads[thread_ts].append(msg)

        self._messages.append(msg)
        logger.debug("Slack message sent to %s: %s", channel, text[:80])
        return {
            "success": True,
            "message_id": msg["message_id"],
            "ts": ts,
            "channel": channel,
        }

    async def send_blocks(
        self,
        channel: str,
        blocks: List[BlockElement],
        thread_ts: Optional[str] = None,
        fallback_text: str = "",
    ) -> Dict[str, Any]:
        """Send a message using Slack Block Kit.

        Parameters
        ----------
        channel : str
            Channel ID or name.
        blocks : list[BlockElement]
            List of block elements.
        thread_ts : str, optional
            Thread timestamp for replies.
        fallback_text : str
            Fallback text for notifications.

        Returns
        -------
        dict with success status.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        ts = f"{datetime.now(timezone.utc).timestamp():.6f}"

        # Convert BlockElement models to Slack API format
        slack_blocks = []
        for block in blocks:
            b: Dict[str, Any] = {"type": block.type}
            if block.text:
                b["text"] = {"type": "mrkdwn", "text": block.text}
            if block.fields:
                b["fields"] = [
                    {"type": "mrkdwn", "text": f.get("text", "")}
                    for f in block.fields
                ]
            slack_blocks.append(b)

        msg = {
            "channel": channel,
            "blocks": slack_blocks,
            "text": fallback_text,
            "ts": ts,
            "message_id": f"sl-{len(self._messages)}",
            "user": self._bot_user_id,
            "type": "message",
            "subtype": "bot_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if thread_ts:
            msg["thread_ts"] = thread_ts
            if thread_ts not in self._threads:
                self._threads[thread_ts] = []
            self._threads[thread_ts].append(msg)

        self._messages.append(msg)
        logger.debug("Slack blocks sent to %s (%d blocks)", channel, len(blocks))
        return {
            "success": True,
            "message_id": msg["message_id"],
            "ts": ts,
            "channel": channel,
        }

    # ── Thread support ─────────────────────────────────────────────────────

    async def get_thread_replies(self, thread_ts: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get replies in a thread."""
        return self._threads.get(thread_ts, [])[:limit]

    async def reply_in_thread(
        self,
        channel: str,
        thread_ts: str,
        text: str,
        broadcast: bool = False,
    ) -> Dict[str, Any]:
        """Reply to a specific thread.

        Parameters
        ----------
        channel : str
            Channel containing the thread.
        thread_ts : str
            Timestamp of the parent message.
        text : str
            Reply text.
        broadcast : bool
            If True, also post to the main channel.
        """
        return await self.send_message(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            reply_broadcast=broadcast,
        )

    # ── Message receiving ──────────────────────────────────────────────────

    async def receive_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent messages."""
        return self._messages[-limit:]

    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming Slack event (from Events API or socket mode).

        Handles message events and dispatches to registered handlers.
        """
        event_type = event.get("type", "")

        if event_type == "message":
            # Ignore bot's own messages
            if event.get("bot_id") or event.get("user") == self._bot_user_id:
                return None

            channel = event.get("channel", "")
            text = event.get("text", "")
            user = event.get("user", "")
            ts = event.get("ts", "")
            thread_ts = event.get("thread_ts")

            incoming = {
                "channel": channel,
                "text": text,
                "user": user,
                "ts": ts,
                "thread_ts": thread_ts,
                "direction": "incoming",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._messages.append(incoming)

            # Track threads
            if thread_ts:
                if thread_ts not in self._threads:
                    self._threads[thread_ts] = []
                self._threads[thread_ts].append(incoming)

            # Dispatch to channel handler
            handler = self._channel_handlers.get(channel)
            if handler:
                try:
                    await handler(channel, text, user, thread_ts)
                except Exception as exc:
                    logger.error("Slack channel handler error: %s", exc)

            return incoming

        elif event_type == "reaction_added":
            emoji = event.get("reaction", "")
            item = event.get("item", {})
            user = event.get("user", "")
            for handler in self._reaction_handlers:
                try:
                    await handler(item.get("channel", ""), item.get("ts", ""), user, emoji)
                except Exception as exc:
                    logger.error("Slack reaction handler error: %s", exc)

        return None

    def register_channel_handler(
        self,
        channel: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for messages in a specific channel.

        Handler receives (channel, text, user, thread_ts).
        """
        self._channel_handlers[channel] = handler

    def register_reaction_handler(
        self,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for reaction events.

        Handler receives (channel, item_ts, user, emoji).
        """
        self._reaction_handlers.append(handler)

    # ── ChannelMessage conversion ──────────────────────────────────────────

    async def send_channel_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send a ChannelMessage (universal format)."""
        if message.block_elements:
            return await self.send_blocks(
                channel=message.channel_id or message.recipient_id,
                blocks=message.block_elements,
                thread_ts=message.thread_id,
                fallback_text=message.text,
            )
        return await self.send_message(
            channel=message.channel_id or message.recipient_id,
            text=message.text,
            thread_ts=message.thread_id,
        )

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return channel statistics."""
        return {
            "channel": "slack",
            "connected": self._connected,
            "messages": len(self._messages),
            "threads": len(self._threads),
            "channel_handlers": len(self._channel_handlers),
        }
