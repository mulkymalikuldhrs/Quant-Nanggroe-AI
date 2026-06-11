"""Telegram bot channel.

Features:
* Message sending/receiving
* Command handling (/start, /status, /help)
* Inline keyboard support
* Message formatting (Markdown)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from ..types import (
    ChannelType,
    ChannelMessage,
    MessageFormat,
    InlineKeyboard,
)

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for agent communication.

    Provides a high-level interface for sending/receiving messages,
    handling commands, and rendering inline keyboards.

    Parameters
    ----------
    token : str
        The Telegram bot token from @BotFather.
    api_url : str
        Base URL for the Telegram Bot API.
    """

    def __init__(
        self,
        token: str = "",
        api_url: str = "https://api.telegram.org",
    ):
        self.token = token
        self.api_url = api_url.rstrip("/")
        self._connected = False
        self._messages: List[Dict[str, Any]] = []
        self._command_handlers: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._message_handlers: List[Callable[..., Coroutine[Any, Any, Any]]] = []
        self._offset: int = 0
        self._bot_info: Dict[str, Any] = {}
        self._chat_ids: Dict[str, Dict[str, Any]] = {}  # chat_id → metadata

        # Register built-in commands
        self._register_builtin_commands()

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to the Telegram Bot API.

        In production, this would call ``getMe`` to validate the token.
        """
        if not self.token:
            self._connected = False
            return False

        # Simulated: would call self.api_url + "/bot" + self.token + "/getMe"
        self._connected = True
        self._bot_info = {"id": "bot", "username": "multicolony_bot", "first_name": "MultiColony"}
        logger.info("Telegram bot connected: @%s", self._bot_info.get("username", "?"))
        return self._connected

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        self._connected = False
        logger.info("Telegram bot disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Message sending ────────────────────────────────────────────────────

    async def send_message(
        self,
        chat_id: str,
        text: str,
        format: MessageFormat = MessageFormat.MARKDOWN,
        reply_to: Optional[str] = None,
        inline_keyboard: Optional[List[List[InlineKeyboard]]] = None,
    ) -> Dict[str, Any]:
        """Send a text message to a chat.

        Parameters
        ----------
        chat_id : str
            Target chat ID.
        text : str
            Message content.
        format : MessageFormat
            Message format (plain, Markdown, HTML).
        reply_to : str, optional
            Message ID to reply to.
        inline_keyboard : list[list[InlineKeyboard]], optional
            Inline keyboard buttons.

        Returns
        -------
        dict with success status and message_id.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        # Validate message length (Telegram limit: 4096)
        if len(text) > 4096:
            text = text[:4093] + "..."

        # Format parse mode
        parse_mode = ""
        if format == MessageFormat.MARKDOWN:
            parse_mode = "MarkdownV2"
        elif format == MessageFormat.HTML:
            parse_mode = "HTML"

        msg = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "message_id": f"tg-{len(self._messages)}",
            "date": datetime.now(timezone.utc).isoformat(),
            "from": self._bot_info,
        }

        if reply_to:
            msg["reply_to_message_id"] = reply_to

        if inline_keyboard:
            msg["reply_markup"] = {
                "inline_keyboard": [
                    [
                        {"text": btn.text, "callback_data": btn.callback_data, "url": btn.url}
                        for btn in row
                    ]
                    for row in inline_keyboard
                ]
            }

        self._messages.append(msg)

        # Track chat
        if chat_id not in self._chat_ids:
            self._chat_ids[chat_id] = {"first_seen": datetime.now(timezone.utc).isoformat()}

        logger.debug("Telegram message sent to %s: %s", chat_id, text[:80])
        return {"success": True, "message_id": msg["message_id"]}

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        format: MessageFormat = MessageFormat.MARKDOWN,
    ) -> Dict[str, Any]:
        """Edit an existing message."""
        for msg in self._messages:
            if msg.get("chat_id") == chat_id and msg.get("message_id") == message_id:
                msg["text"] = text[:4096]
                msg["edited"] = True
                return {"success": True, "message_id": message_id}
        return {"success": False, "error": "Message not found"}

    async def delete_message(self, chat_id: str, message_id: str) -> Dict[str, Any]:
        """Delete a message."""
        for i, msg in enumerate(self._messages):
            if msg.get("chat_id") == chat_id and msg.get("message_id") == message_id:
                self._messages.pop(i)
                return {"success": True}
        return {"success": False, "error": "Message not found"}

    # ── Message receiving ──────────────────────────────────────────────────

    async def receive_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent messages (simulated polling)."""
        return self._messages[-limit:]

    async def process_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming Telegram update (webhook or polling).

        Handles commands and dispatches to registered handlers.
        """
        message = update.get("message", {})
        if not message:
            return None

        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        from_user = message.get("from", {})
        message_id = str(message.get("message_id", ""))

        # Store incoming message
        incoming = {
            "chat_id": chat_id,
            "text": text,
            "from": from_user,
            "message_id": message_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "direction": "incoming",
        }
        self._messages.append(incoming)

        # Command handling
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            handler = self._command_handlers.get(command)
            if handler:
                try:
                    result = await handler(chat_id, args, from_user)
                    return result
                except Exception as exc:
                    logger.error("Command handler error for %s: %s", command, exc)
                    return await self.send_message(chat_id, f"Error processing command: {exc}")

        # General message handlers
        for handler in self._message_handlers:
            try:
                await handler(chat_id, text, from_user)
            except Exception as exc:
                logger.error("Message handler error: %s", exc)

        return None

    # ── Command handling ───────────────────────────────────────────────────

    def register_command(
        self,
        command: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a command handler.

        The handler receives (chat_id, args, from_user).
        """
        if not command.startswith("/"):
            command = "/" + command
        self._command_handlers[command] = handler

    def register_message_handler(
        self,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a handler for all non-command messages."""
        self._message_handlers.append(handler)

    def _register_builtin_commands(self) -> None:
        """Register the built-in /start, /status, /help commands."""
        self._command_handlers["/start"] = self._cmd_start
        self._command_handlers["/status"] = self._cmd_status
        self._command_handlers["/help"] = self._cmd_help

    async def _cmd_start(self, chat_id: str, args: str, from_user: Dict) -> Dict[str, Any]:
        """Handle /start command."""
        welcome = (
            "🤖 *Welcome to MultiColony\\!*\n\n"
            "I am an autonomous agent colony assistant\\.\n"
            "Use /help to see available commands\\."
        )
        return await self.send_message(chat_id, welcome, format=MessageFormat.MARKDOWN)

    async def _cmd_status(self, chat_id: str, args: str, from_user: Dict) -> Dict[str, Any]:
        """Handle /status command."""
        status_text = (
            "📊 *Colony Status*\n\n"
            f"Connected: {self._connected}\n"
            f"Messages: {len(self._messages)}\n"
            f"Chats: {len(self._chat_ids)}\n"
            f"Commands: {', '.join(self._command_handlers.keys())}"
        )
        return await self.send_message(chat_id, status_text, format=MessageFormat.MARKDOWN)

    async def _cmd_help(self, chat_id: str, args: str, from_user: Dict) -> Dict[str, Any]:
        """Handle /help command."""
        help_text = (
            "📖 *Available Commands*\n\n"
            "/start \\- Start the bot\n"
            "/status \\- Show colony status\n"
            "/help \\- Show this help message\n"
        )
        return await self.send_message(chat_id, help_text, format=MessageFormat.MARKDOWN)

    # ── ChannelMessage conversion ──────────────────────────────────────────

    async def send_channel_message(self, message: ChannelMessage) -> Dict[str, Any]:
        """Send a ChannelMessage (universal format)."""
        return await self.send_message(
            chat_id=message.recipient_id or message.channel_id,
            text=message.text,
            format=message.format,
            reply_to=message.reply_to,
            inline_keyboard=message.inline_keyboard,
        )

    # ── Inline keyboard helpers ────────────────────────────────────────────

    @staticmethod
    def make_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> List[List[InlineKeyboard]]:
        """Build inline keyboard from a simple dict specification."""
        return [
            [InlineKeyboard(**btn) for btn in row]
            for row in buttons
        ]

    # ── Markdown helpers ───────────────────────────────────────────────────

    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        special = r"_*[]()~`>#+-=|{}.!"
        return "".join(f"\\{c}" if c in special else c for c in text)

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return channel statistics."""
        return {
            "channel": "telegram",
            "connected": self._connected,
            "messages_sent": len(self._messages),
            "chats": len(self._chat_ids),
            "commands_registered": len(self._command_handlers),
        }
