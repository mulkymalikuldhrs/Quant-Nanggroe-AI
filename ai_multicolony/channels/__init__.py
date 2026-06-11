"""Communication channels for AI-MultiColony.

Provides integrations with Telegram, WhatsApp, Discord, and Slack,
each with full message sending/receiving, platform-specific features,
and universal ChannelMessage support.
"""

from .telegram import TelegramBot
from .whatsapp import WhatsAppGateway
from .discord import DiscordBot
from .slack import SlackIntegration

__all__ = [
    "TelegramBot",
    "WhatsAppGateway",
    "DiscordBot",
    "SlackIntegration",
]
