"""Base channel and implementations for multi-channel communication.

From Nanobot BaseChannel pattern - provides abstract interface for
Telegram, WhatsApp, Discord, Slack channels with graceful fallback
when channel SDKs are not installed.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.exceptions import ChannelError
from ai_multicolony.types.messages import BusMessage, InboundMessage, MessageType, OutboundMessage

logger = get_logger(__name__)


class BaseChannel(ABC):
    """Abstract base class for communication channels.

    All channel implementations (Telegram, Discord, Slack, WhatsApp)
    must implement this interface.
    """

    def __init__(self, channel_type: str, channel_id: str, config: Optional[dict[str, Any]] = None) -> None:
        self.channel_type = channel_type
        self.channel_id = channel_id
        self._config = config or {}
        self._running = False
        self._message_queue: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._inbound_handlers: list[Any] = []
        self._sent_count = 0
        self._received_count = 0

    @property
    def is_running(self) -> bool:
        """Whether the channel is currently active."""
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start the channel and begin listening for messages."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        ...

    @abstractmethod
    async def send(self, message: OutboundMessage) -> bool:
        """Send a message through this channel.

        Args:
            message: The outbound message to send.

        Returns:
            True if the message was sent successfully.
        """
        ...

    @abstractmethod
    async def receive(self) -> Optional[InboundMessage]:
        """Receive the next inbound message.

        Returns:
            The next inbound message, or None if no messages available.
        """
        ...

    def on_inbound(self, handler: Any) -> None:
        """Register a handler for inbound messages.

        Args:
            handler: Callable to handle inbound messages.
        """
        self._inbound_handlers.append(handler)

    async def _dispatch_inbound(self, message: InboundMessage) -> None:
        """Dispatch an inbound message to all registered handlers.

        Args:
            message: The inbound message to dispatch.
        """
        self._received_count += 1
        for handler in self._inbound_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(
                    "channel_handler_error",
                    channel=self.channel_type,
                    handler=str(handler),
                    error=str(e),
                )

    async def queue_outbound(self, message: OutboundMessage) -> None:
        """Queue an outbound message for sending.

        Args:
            message: The message to queue.
        """
        await self._message_queue.put(message)

    async def process_outbound_queue(self) -> int:
        """Process all queued outbound messages.

        Returns:
            Number of messages processed.
        """
        count = 0
        while not self._message_queue.empty():
            try:
                message = self._message_queue.get_nowait()
                await self.send(message)
                count += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error("channel_send_error", channel=self.channel_type, error=str(e))
        return count

    def get_info(self) -> dict[str, Any]:
        """Get channel information."""
        return {
            "channel_type": self.channel_type,
            "channel_id": self.channel_id,
            "is_running": self._running,
            "queued_messages": self._message_queue.qsize(),
            "sent_count": self._sent_count,
            "received_count": self._received_count,
        }


class TelegramChannel(BaseChannel):
    """Telegram channel implementation.

    Uses python-telegram-bot for communication. Falls back to
    HTTP-based polling via aiohttp when the SDK is not available.
    """

    def __init__(self, channel_id: str, bot_token: str, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(channel_type="telegram", channel_id=channel_id, config=config)
        self._bot_token = bot_token
        self._bot: Optional[Any] = None
        self._app: Optional[Any] = None
        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()

    async def start(self) -> None:
        """Start the Telegram bot."""
        try:
            from telegram.ext import ApplicationBuilder

            self._app = ApplicationBuilder().token(self._bot_token).build()
            self._bot = self._app.bot

            # Register message handler
            from telegram.ext import MessageHandler, filters
            async def handle_message(update: Any, context: Any) -> None:
                if update.message and update.message.text:
                    inbound = InboundMessage(
                        channel_type="telegram",
                        channel_id=str(update.message.chat_id),
                        sender_id=str(update.message.from_user.id),
                        sender_name=update.message.from_user.username or update.message.from_user.first_name,
                        content=update.message.text,
                    )
                    await self._inbound_queue.put(inbound)
                    await self._dispatch_inbound(inbound)

            self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            await self._app.initialize()
            await self._app.start()
            if self._app.updater:
                await self._app.updater.start_polling()

            self._running = True
            logger.info("telegram_channel_started", channel_id=self.channel_id)

        except ImportError:
            logger.warning("telegram_sdk_not_installed", message="pip install python-telegram-bot")
            self._running = True  # Mark as running for graceful degradation

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            try:
                if self._app.updater and self._app.updater.running:
                    await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning("telegram_stop_error", error=str(e))
        self._running = False

    async def send(self, message: OutboundMessage) -> bool:
        """Send a message via Telegram."""
        try:
            if self._bot:
                await self._bot.send_message(
                    chat_id=message.recipient_id,
                    text=message.content,
                )
                self._sent_count += 1
                return True
            else:
                # Fallback: use aiohttp to send via Telegram Bot API
                return await self._send_via_api(message)
        except Exception as e:
            logger.error("telegram_send_error", error=str(e))
            return False

    async def _send_via_api(self, message: OutboundMessage) -> bool:
        """Send via Telegram Bot API as fallback."""
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            payload = {
                "chat_id": message.recipient_id,
                "text": message.content,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        self._sent_count += 1
                        return True
                    else:
                        logger.error("telegram_api_error", status=resp.status)
                        return False
        except ImportError:
            logger.error("aiohttp_not_installed")
            return False

    async def receive(self) -> Optional[InboundMessage]:
        """Receive the next inbound Telegram message."""
        try:
            return self._inbound_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None


class DiscordChannel(BaseChannel):
    """Discord channel implementation.

    Uses discord.py for communication. Falls back to logging
    when the SDK is not available.
    """

    def __init__(self, channel_id: str, bot_token: str, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(channel_type="discord", channel_id=channel_id, config=config)
        self._bot_token = bot_token
        self._client: Optional[Any] = None
        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()

    async def start(self) -> None:
        """Start the Discord bot."""
        try:
            import discord

            intents = discord.Intents.default()
            intents.message_content = True
            self._client = discord.Client(intents=intents)

            @self._client.event
            async def on_message(message: discord.Message) -> None:
                if message.author.bot:
                    return
                inbound = InboundMessage(
                    channel_type="discord",
                    channel_id=str(message.channel.id),
                    sender_id=str(message.author.id),
                    sender_name=message.author.name,
                    content=message.content,
                )
                await self._inbound_queue.put(inbound)
                await self._dispatch_inbound(inbound)

            # Start the client in a background task
            asyncio.ensure_future(self._client.start(self._bot_token))
            self._running = True
            logger.info("discord_channel_started", channel_id=self.channel_id)

        except ImportError:
            logger.warning("discord_sdk_not_installed", message="pip install discord.py")
            self._running = True

    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning("discord_stop_error", error=str(e))
        self._running = False

    async def send(self, message: OutboundMessage) -> bool:
        """Send a message via Discord."""
        try:
            if self._client:
                channel = self._client.get_channel(int(message.recipient_id))
                if channel:
                    await channel.send(message.content)
                    self._sent_count += 1
                    return True
            logger.warning("discord_send_no_client", channel_id=message.recipient_id)
            return False
        except Exception as e:
            logger.error("discord_send_error", error=str(e))
            return False

    async def receive(self) -> Optional[InboundMessage]:
        """Receive the next inbound Discord message."""
        try:
            return self._inbound_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None


class SlackChannel(BaseChannel):
    """Slack channel implementation.

    Uses slack-bolt for communication. Falls back to
    HTTP-based API calls when the SDK is not available.
    """

    def __init__(self, channel_id: str, bot_token: str, app_token: Optional[str] = None,
                 config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(channel_type="slack", channel_id=channel_id, config=config)
        self._bot_token = bot_token
        self._app_token = app_token
        self._app: Optional[Any] = None
        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()

    async def start(self) -> None:
        """Start the Slack bot."""
        try:
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

            self._app = AsyncApp(token=self._bot_token)

            @self._app.event("message")
            async def handle_message(event: dict, say: Any) -> None:
                inbound = InboundMessage(
                    channel_type="slack",
                    channel_id=event.get("channel", ""),
                    sender_id=event.get("user", ""),
                    content=event.get("text", ""),
                )
                await self._inbound_queue.put(inbound)
                await self._dispatch_inbound(inbound)

            if self._app_token:
                handler = AsyncSocketModeHandler(self._app, self._app_token)
                asyncio.ensure_future(handler.start_async())

            self._running = True
            logger.info("slack_channel_started", channel_id=self.channel_id)

        except ImportError:
            logger.warning("slack_sdk_not_installed", message="pip install slack-bolt")
            self._running = True

    async def stop(self) -> None:
        """Stop the Slack bot."""
        self._running = False

    async def send(self, message: OutboundMessage) -> bool:
        """Send a message via Slack."""
        try:
            if self._app and self._app.client:
                self._app.client.chat_postMessage(
                    channel=message.recipient_id,
                    text=message.content,
                )
                self._sent_count += 1
                return True
            else:
                return await self._send_via_api(message)
        except Exception as e:
            logger.error("slack_send_error", error=str(e))
            return False

    async def _send_via_api(self, message: OutboundMessage) -> bool:
        """Send via Slack Web API as fallback."""
        try:
            import aiohttp
            url = "https://slack.com/api/chat.postMessage"
            headers = {"Authorization": f"Bearer {self._bot_token}"}
            payload = {
                "channel": message.recipient_id,
                "text": message.content,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        self._sent_count += 1
                        return True
                    return False
        except ImportError:
            return False

    async def receive(self) -> Optional[InboundMessage]:
        """Receive the next inbound Slack message."""
        try:
            return self._inbound_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None


class WhatsAppChannel(BaseChannel):
    """WhatsApp channel implementation.

    Uses the WhatsApp Business API (via HTTP) for communication.
    No additional SDK required - uses aiohttp for API calls.
    """

    def __init__(self, channel_id: str, phone_number_id: str, access_token: str,
                 verify_token: Optional[str] = None, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(channel_type="whatsapp", channel_id=channel_id, config=config)
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._verify_token = verify_token
        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()

    async def start(self) -> None:
        """Start the WhatsApp channel."""
        self._running = True
        logger.info("whatsapp_channel_started", channel_id=self.channel_id)

    async def stop(self) -> None:
        """Stop the WhatsApp channel."""
        self._running = False

    async def send(self, message: OutboundMessage) -> bool:
        """Send a message via WhatsApp Business API."""
        try:
            import aiohttp
            url = f"https://graph.facebook.com/v18.0/{self._phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": message.recipient_id,
                "type": "text",
                "text": {"body": message.content},
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        self._sent_count += 1
                        return True
                    else:
                        body = await resp.text()
                        logger.error("whatsapp_api_error", status=resp.status, body=body[:200])
                        return False
        except ImportError:
            logger.error("aiohttp_not_installed_for_whatsapp")
            return False
        except Exception as e:
            logger.error("whatsapp_send_error", error=str(e))
            return False

    def handle_webhook(self, data: dict[str, Any]) -> None:
        """Process incoming webhook data from WhatsApp.

        Args:
            data: The webhook payload from WhatsApp.
        """
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    messages = change.get("value", {}).get("messages", [])
                    for msg in messages:
                        inbound = InboundMessage(
                            channel_type="whatsapp",
                            channel_id=self.channel_id,
                            sender_id=msg.get("from", ""),
                            content=msg.get("text", {}).get("body", ""),
                            content_type=MessageType.TEXT,
                        )
                        self._inbound_queue.put_nowait(inbound)
                        asyncio.ensure_future(self._dispatch_inbound(inbound))
        except Exception as e:
            logger.error("whatsapp_webhook_error", error=str(e))

    async def receive(self) -> Optional[InboundMessage]:
        """Receive the next inbound WhatsApp message."""
        try:
            return self._inbound_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None


def create_channel(channel_type: str, **kwargs: Any) -> BaseChannel:
    """Factory function to create a channel by type.

    Args:
        channel_type: The channel type ("telegram", "discord", "slack", "whatsapp").
        **kwargs: Channel-specific configuration.

    Returns:
        A BaseChannel instance.

    Raises:
        ChannelError: If the channel type is not supported.
    """
    channel_map: dict[str, type[BaseChannel]] = {
        "telegram": TelegramChannel,
        "discord": DiscordChannel,
        "slack": SlackChannel,
        "whatsapp": WhatsAppChannel,
    }

    cls = channel_map.get(channel_type)
    if cls is None:
        raise ChannelError(
            f"Unsupported channel type: {channel_type}. Supported: {list(channel_map.keys())}",
            channel_type=channel_type,
        )

    return cls(**kwargs)
