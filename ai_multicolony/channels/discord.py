"""Discord bot channel.

Features:
* Message sending/receiving
* Embed support (rich embeds with fields, colors, footers)
* Reaction handling
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from ..types import (
    ChannelType,
    ChannelMessage,
    MessageFormat,
    EmbedField,
)

logger = logging.getLogger(__name__)


class DiscordBot:
    """Discord bot for agent communication.

    Parameters
    ----------
    token : str
        The Discord bot token.
    application_id : str
        The Discord application ID.
    """

    def __init__(
        self,
        token: str = "",
        application_id: str = "",
    ):
        self.token = token
        self.application_id = application_id
        self._connected = False
        self._messages: List[Dict[str, Any]] = []
        self._reactions: Dict[str, List[Dict[str, Any]]] = {}  # message_id → reactions
        self._guild_id: str = ""
        self._channel_handlers: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._reaction_handlers: List[Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._bot_user: Dict[str, Any] = {}

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to Discord (simulated: would use discord.py gateway)."""
        if not self.token:
            self._connected = False
            return False
        self._connected = True
        self._bot_user = {"id": "bot", "username": "MultiColony", "discriminator": "0001"}
        logger.info("Discord bot connected: %s", self._bot_user.get("username"))
        return True

    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        self._connected = False
        logger.info("Discord bot disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Message sending ────────────────────────────────────────────────────

    async def send_message(
        self,
        channel_id: str,
        text: str,
        format: MessageFormat = MessageFormat.MARKDOWN,
    ) -> Dict[str, Any]:
        """Send a text message to a Discord channel.

        Discord natively supports Markdown formatting.

        Parameters
        ----------
        channel_id : str
            The channel ID to send to.
        text : str
            Message content (max 2000 characters for regular messages).
        format : MessageFormat
            Formatting mode (Discord uses Markdown).

        Returns
        -------
        dict with success status and message_id.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        # Discord message limit
        if len(text) > 2000:
            text = text[:1997] + "..."

        msg = {
            "channel_id": channel_id,
            "content": text,
            "message_id": f"dc-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": self._bot_user,
            "type": "text",
        }
        self._messages.append(msg)
        logger.debug("Discord message sent to channel %s: %s", channel_id, text[:80])
        return {"success": True, "message_id": msg["message_id"]}

    async def send_embed(
        self,
        channel_id: str,
        title: str,
        description: str = "",
        color: int = 0x00FF00,
        fields: Optional[List[EmbedField]] = None,
        footer: str = "",
        thumbnail_url: str = "",
        image_url: str = "",
    ) -> Dict[str, Any]:
        """Send a rich embed message.

        Parameters
        ----------
        channel_id : str
            Target channel.
        title : str
            Embed title (max 256 chars).
        description : str
            Embed description (max 4096 chars).
        color : int
            Embed sidebar color as RGB int.
        fields : list[EmbedField], optional
            Embed fields (max 25).
        footer : str
            Footer text.
        thumbnail_url : str
            URL for the thumbnail image.
        image_url : str
            URL for the main image.

        Returns
        -------
        dict with success status and message_id.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        embed: Dict[str, Any] = {
            "title": title[:256],
            "description": description[:4096],
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if fields:
            embed["fields"] = [
                {"name": f.name[:256], "value": f.value[:1024], "inline": f.inline}
                for f in fields[:25]
            ]

        if footer:
            embed["footer"] = {"text": footer[:2048]}

        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        if image_url:
            embed["image"] = {"url": image_url}

        msg = {
            "channel_id": channel_id,
            "embeds": [embed],
            "message_id": f"dc-{len(self._messages)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": self._bot_user,
            "type": "embed",
        }
        self._messages.append(msg)
        logger.debug("Discord embed sent to channel %s: %s", channel_id, title)
        return {"success": True, "message_id": msg["message_id"]}

    # ── Reaction handling ──────────────────────────────────────────────────

    async def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        """Add a reaction to a message.

        Parameters
        ----------
        channel_id : str
            The channel containing the message.
        message_id : str
            The message to react to.
        emoji : str
            The emoji to add (unicode or custom :name:id).
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        key = f"{channel_id}:{message_id}"
        if key not in self._reactions:
            self._reactions[key] = []
        self._reactions[key].append({
            "emoji": emoji,
            "user_id": self._bot_user.get("id", "bot"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"success": True}

    async def remove_reaction(self, channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        """Remove a reaction from a message."""
        key = f"{channel_id}:{message_id}"
        if key in self._reactions:
            self._reactions[key] = [
                r for r in self._reactions[key]
                if not (r["emoji"] == emoji and r["user_id"] == self._bot_user.get("id"))
            ]
        return {"success": True}

    async def get_reactions(self, channel_id: str, message_id: str) -> List[Dict[str, Any]]:
        """Get all reactions for a message."""
        key = f"{channel_id}:{message_id}"
        return self._reactions.get(key, [])

    def register_reaction_handler(
        self,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for reaction events.

        Handler receives (channel_id, message_id, user_id, emoji, action).
        """
        self._reaction_handlers.append(handler)

    async def process_reaction_event(
        self,
        channel_id: str,
        message_id: str,
        user_id: str,
        emoji: str,
        action: str = "add",
    ) -> None:
        """Process a reaction event (add/remove)."""
        key = f"{channel_id}:{message_id}"
        if action == "add":
            if key not in self._reactions:
                self._reactions[key] = []
            self._reactions[key].append({
                "emoji": emoji,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        elif action == "remove":
            if key in self._reactions:
                self._reactions[key] = [
                    r for r in self._reactions[key]
                    if not (r["emoji"] == emoji and r["user_id"] == user_id)
                ]

        for handler in self._reaction_handlers:
            try:
                await handler(channel_id, message_id, user_id, emoji, action)
            except Exception as exc:
                logger.error("Reaction handler error: %s", exc)

    # ── Message receiving ──────────────────────────────────────────────────

    async def receive_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent messages."""
        return self._messages[-limit:]

    async def process_message_event(self, event: Dict[str, Any]) -> None:
        """Process an incoming Discord message event."""
        channel_id = str(event.get("channel_id", ""))
        content = event.get("content", "")
        author = event.get("author", {})
        message_id = str(event.get("id", ""))

        incoming = {
            "channel_id": channel_id,
            "content": content,
            "author": author,
            "message_id": message_id,
            "direction": "incoming",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(incoming)

        # Dispatch to channel handler
        handler = self._channel_handlers.get(channel_id)
        if handler:
            try:
                await handler(channel_id, content, author)
            except Exception as exc:
                logger.error("Discord channel handler error: %s", exc)

    def register_channel_handler(
        self,
        channel_id: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for messages in a specific channel."""
        self._channel_handlers[channel_id] = handler

    # ── ChannelMessage conversion ──────────────────────────────────────────

    async def send_channel_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send a ChannelMessage (universal format)."""
        if message.embed_fields:
            return await self.send_embed(
                channel_id=message.channel_id,
                title=message.text[:256] if message.text else "Embed",
                fields=message.embed_fields,
            )
        return await self.send_message(
            channel_id=message.channel_id or message.recipient_id,
            text=message.text,
            format=message.format,
        )

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return channel statistics."""
        return {
            "channel": "discord",
            "connected": self._connected,
            "messages": len(self._messages),
            "reactions": sum(len(r) for r in self._reactions.values()),
            "guild_id": self._guild_id,
        }
