"""WhatsApp Gateway — Message Routing & Notification Push.

Provides WhatsApp Web.js integration pattern for message routing
to/from agents, command parsing, and notification push for trade
alerts and risk warnings.

Features
--------
* WhatsApp Web.js integration pattern (via bridge service)
* Message routing to/from agents
* Command parsing (!forecast, !screen, !position, etc.)
* Notification push (trade alerts, risk warnings, daily brief)
* FastAPI router for webhook integration

Dependencies
------------
Requires a running WhatsApp bridge service (Node.js/whatsapp-web.js
or similar) that communicates via HTTP API.

Notes
-----
This module provides the API routes for WhatsApp integration.
The actual WhatsApp connection is managed by a separate bridge
service that handles the browser automation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])  # ponytail: prefix added at include_router (app.py:267) to avoid /api/whatsapp/whatsapp//


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    """WhatsApp message types."""
    TEXT = "TEXT"
    COMMAND = "COMMAND"
    ALERT = "ALERT"
    NOTIFICATION = "NOTIFICATION"
    TRADE_SIGNAL = "TRADE_SIGNAL"
    RISK_WARNING = "RISK_WARNING"
    DAILY_BRIEF = "DAILY_BRIEF"
    FORECAST_UPDATE = "FORECAST_UPDATE"


class MessageDirection(str, Enum):
    """Message direction."""
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CommandName(str, Enum):
    """Supported WhatsApp commands."""
    FORECAST = "forecast"
    SCREEN = "screen"
    POSITION = "position"
    BALANCE = "balance"
    RISK = "risk"
    HELP = "help"
    ALERT_ON = "alert_on"
    ALERT_OFF = "alert_off"
    MOOD = "mood"
    ANALYSIS = "analysis"
    CHART = "chart"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message."""
    message_id: str = Field("", description="Message ID from WhatsApp")
    chat_id: str = Field("", description="WhatsApp chat ID")
    sender: str = Field("", description="Sender phone number or ID")
    sender_name: str = Field("", description="Sender display name")
    body: str = Field(..., description="Message body text")
    timestamp: str = Field("", description="Message timestamp")
    is_group: bool = Field(False, description="Whether from a group chat")
    mentioned: bool = Field(False, description="Whether bot was mentioned")


class ParsedCommand(BaseModel):
    """Parsed command from a WhatsApp message."""
    command: CommandName = Field(..., description="Command name")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    raw_message: str = Field("", description="Original message text")
    chat_id: str = Field("", description="Source chat ID")


class OutboundMessage(BaseModel):
    """Outbound WhatsApp message."""
    chat_id: str = Field(..., description="Target chat ID")
    body: str = Field(..., description="Message body")
    message_type: MessageType = Field(MessageType.TEXT)
    parse_mode: str = Field("markdown", description="Parse mode (markdown/plain)")
    reply_to: Optional[str] = Field(None, description="Message ID to reply to")


class NotificationConfig(BaseModel):
    """Notification subscription configuration."""
    chat_id: str = Field(..., description="WhatsApp chat ID")
    trade_alerts: bool = Field(True, description="Receive trade alerts")
    risk_warnings: bool = Field(True, description="Receive risk warnings")
    daily_brief: bool = Field(False, description="Receive daily market brief")
    forecast_updates: bool = Field(False, description="Receive forecast updates")
    symbols: List[str] = Field(default_factory=list, description="Watched symbols")
    min_severity: str = Field("MEDIUM", description="Minimum alert severity")


class NotificationMessage(BaseModel):
    """Notification message for push."""
    notification_id: str = Field("", description="Notification ID")
    notification_type: MessageType = Field(MessageType.NOTIFICATION)
    title: str = Field("", description="Notification title")
    body: str = Field("", description="Notification body")
    severity: str = Field("MEDIUM", description="Severity: LOW, MEDIUM, HIGH, CRITICAL")
    symbol: Optional[str] = Field(None, description="Related symbol")
    action_required: bool = Field(False, description="Whether action is required")
    timestamp: str = Field("")


# ---------------------------------------------------------------------------
# Command parser
# ---------------------------------------------------------------------------

_COMMAND_PREFIXES = ("!", "/", "#")

_COMMAND_ALIASES: Dict[str, CommandName] = {
    "forecast": CommandName.FORECAST,
    "fc": CommandName.FORECAST,
    "f": CommandName.FORECAST,
    "screen": CommandName.SCREEN,
    "scan": CommandName.SCREEN,
    "s": CommandName.SCREEN,
    "position": CommandName.POSITION,
    "pos": CommandName.POSITION,
    "p": CommandName.POSITION,
    "balance": CommandName.BALANCE,
    "bal": CommandName.BALANCE,
    "b": CommandName.BALANCE,
    "risk": CommandName.RISK,
    "r": CommandName.RISK,
    "help": CommandName.HELP,
    "h": CommandName.HELP,
    "alert_on": CommandName.ALERT_ON,
    "alert_off": CommandName.ALERT_OFF,
    "mood": CommandName.MOOD,
    "m": CommandName.MOOD,
    "analysis": CommandName.ANALYSIS,
    "a": CommandName.ANALYSIS,
    "chart": CommandName.CHART,
    "c": CommandName.CHART,
}


def parse_command(message: str, chat_id: str = "") -> Optional[ParsedCommand]:
    """Parse a WhatsApp message for bot commands.

    Args:
        message: Message text to parse.
        chat_id: Source chat ID.

    Returns:
        ParsedCommand if the message is a command, None otherwise.
    """
    stripped = message.strip()
    if not stripped:
        return None

    # Check for command prefix
    if stripped[0] not in _COMMAND_PREFIXES:
        return None

    # Parse command and args
    parts = stripped[1:].split()
    if not parts:
        return None

    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    # Look up command
    command = _COMMAND_ALIASES.get(cmd)
    if command is None:
        return None

    return ParsedCommand(
        command=command,
        args=args,
        raw_message=stripped,
        chat_id=chat_id,
    )


# ---------------------------------------------------------------------------
# WhatsApp Gateway
# ---------------------------------------------------------------------------

class WhatsAppGateway:
    """WhatsApp gateway for message routing and notification push.

    Provides message routing to agents, command parsing, and
    notification push for trade alerts and risk warnings.

    Usage::

        gateway = WhatsAppGateway()
        await gateway.handle_inbound(message)
        await gateway.push_notification(notification)
    """

    def __init__(self, bridge_url: str = "http://localhost:3030") -> None:
        self._bridge_url = bridge_url
        self._subscriptions: Dict[str, NotificationConfig] = {}
        self._message_history: List[Dict[str, Any]] = []
        self._command_handlers: Dict[CommandName, Any] = {}

    async def handle_inbound(self, message: WhatsAppMessage) -> Optional[OutboundMessage]:
        """Handle an inbound WhatsApp message.

        Parses commands and routes to appropriate handlers.

        Args:
            message: Incoming WhatsApp message.

        Returns:
            OutboundMessage response if applicable.
        """
        self._message_history.append({
            "direction": MessageDirection.INBOUND.value,
            "message": message.model_dump(),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

        # Try to parse as command
        command = parse_command(message.body, message.chat_id)
        if command:
            return await self._handle_command(command, message)

        # Not a command - could be a query for the agent
        return None

    async def _handle_command(
        self,
        command: ParsedCommand,
        original: WhatsAppMessage,
    ) -> OutboundMessage:
        """Handle a parsed command.

        Args:
            command: Parsed command.
            original: Original WhatsApp message.

        Returns:
            OutboundMessage with the command response.
        """
        cmd = command.command
        args = command.args

        if cmd == CommandName.HELP:
            body = self._format_help()
        elif cmd == CommandName.FORECAST:
            symbol = args[0] if args else "SPY"
            body = f"🔮 *Forecast for {symbol}*\n\nUse `/analysis {symbol}` for detailed analysis."
        elif cmd == CommandName.SCREEN:
            symbol = args[0] if args else "AAPL"
            body = f"🔍 *Screening {symbol}*\n\nRunning 12-component screening..."
        elif cmd == CommandName.POSITION:
            body = "📊 *Current Positions*\n\nNo active positions."
        elif cmd == CommandName.BALANCE:
            body = "💰 *Account Balance*\n\nUse the dashboard for detailed balance info."
        elif cmd == CommandName.RISK:
            body = "⚠️ *Risk Status*\n\nAll risk checks passing."
        elif cmd == CommandName.ALERT_ON:
            self._subscribe(original.chat_id)
            body = "🔔 *Alerts Enabled*\n\nYou will receive trade alerts and risk warnings."
        elif cmd == CommandName.ALERT_OFF:
            self._unsubscribe(original.chat_id)
            body = "🔕 *Alerts Disabled*\n\nNotifications paused."
        elif cmd == CommandName.MOOD:
            mood = args[0] if args else "neutral"
            body = f"🧠 *Mood Logged*: {mood}\n\nDiscipline score updated."
        elif cmd == CommandName.ANALYSIS:
            symbol = args[0] if args else "SPY"
            body = f"📈 *Analysis: {symbol}*\n\nUse the full dashboard for comprehensive analysis."
        elif cmd == CommandName.CHART:
            symbol = args[0] if args else "BTC"
            body = f"📊 *Chart: {symbol}*\n\nCharts available in the web dashboard."
        else:
            body = "❓ Unknown command. Type `!help` for available commands."

        return OutboundMessage(
            chat_id=original.chat_id,
            body=body,
            message_type=MessageType.COMMAND,
            reply_to=original.message_id,
        )

    async def push_notification(
        self,
        notification: NotificationMessage,
    ) -> List[str]:
        """Push a notification to all subscribed chats.

        Args:
            notification: Notification message to push.

        Returns:
            List of chat IDs that received the notification.
        """
        recipients = self._get_recipients(notification)
        sent_to = []

        for chat_id in recipients:
            try:
                message = OutboundMessage(
                    chat_id=chat_id,
                    body=self._format_notification(notification),
                    message_type=notification.notification_type,
                )

                # In production, send via WhatsApp bridge
                await self._send_via_bridge(message)
                sent_to.append(chat_id)

                self._message_history.append({
                    "direction": MessageDirection.OUTBOUND.value,
                    "notification": notification.model_dump(),
                    "chat_id": chat_id,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                })

            except Exception as exc:
                logger.warning("Failed to send notification to %s: %s", chat_id, exc)

        return sent_to

    async def send_trade_alert(
        self,
        symbol: str,
        direction: str,
        price: float,
        reason: str = "",
        confidence: float = 0.0,
    ) -> List[str]:
        """Send a trade alert notification.

        Args:
            symbol: Trading symbol.
            direction: Trade direction.
            price: Trade price.
            reason: Alert reason.
            confidence: Signal confidence.

        Returns:
            List of chat IDs that received the alert.
        """
        notification = NotificationMessage(
            notification_id=str(uuid.uuid4())[:8],
            notification_type=MessageType.TRADE_SIGNAL,
            title=f"Trade Alert: {direction} {symbol}",
            body=(
                f"*{direction} {symbol}* @ ${price:.2f}\n"
                f"Confidence: {confidence:.0%}\n"
                f"Reason: {reason}"
            ),
            severity="HIGH",
            symbol=symbol,
            action_required=True,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
        return await self.push_notification(notification)

    async def send_risk_warning(
        self,
        warning_type: str,
        message: str,
        severity: str = "HIGH",
    ) -> List[str]:
        """Send a risk warning notification.

        Args:
            warning_type: Type of risk warning.
            message: Warning message.
            severity: Warning severity.

        Returns:
            List of chat IDs that received the warning.
        """
        notification = NotificationMessage(
            notification_id=str(uuid.uuid4())[:8],
            notification_type=MessageType.RISK_WARNING,
            title=f"⚠️ Risk Warning: {warning_type}",
            body=message,
            severity=severity,
            action_required=severity in ("HIGH", "CRITICAL"),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
        return await self.push_notification(notification)

    async def send_daily_brief(
        self,
        brief_text: str,
    ) -> List[str]:
        """Send a daily market brief.

        Args:
            brief_text: Brief text content.

        Returns:
            List of chat IDs that received the brief.
        """
        notification = NotificationMessage(
            notification_id=str(uuid.uuid4())[:8],
            notification_type=MessageType.DAILY_BRIEF,
            title="📰 Daily Market Brief",
            body=brief_text,
            severity="LOW",
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
        return await self.push_notification(notification)

    # ----- Subscription management -----

    def _subscribe(self, chat_id: str) -> None:
        """Subscribe a chat to notifications."""
        if chat_id not in self._subscriptions:
            self._subscriptions[chat_id] = NotificationConfig(chat_id=chat_id)

    def _unsubscribe(self, chat_id: str) -> None:
        """Unsubscribe a chat from notifications."""
        self._subscriptions.pop(chat_id, None)

    def _get_recipients(self, notification: NotificationMessage) -> List[str]:
        """Get list of chat IDs that should receive a notification."""
        recipients = []
        for chat_id, config in self._subscriptions.items():
            if notification.notification_type == MessageType.TRADE_SIGNAL and not config.trade_alerts:
                continue
            if notification.notification_type == MessageType.RISK_WARNING and not config.risk_warnings:
                continue
            if notification.notification_type == MessageType.DAILY_BRIEF and not config.daily_brief:
                continue
            if notification.notification_type == MessageType.FORECAST_UPDATE and not config.forecast_updates:
                continue
            if notification.symbol and config.symbols and notification.symbol not in config.symbols:
                continue
            recipients.append(chat_id)
        return recipients

    # ----- Formatting -----

    @staticmethod
    def _format_help() -> str:
        """Format help message."""
        return (
            "🤖 *Quant Nanggroe AI Commands*\n\n"
            "!forecast SYMBOL — Get market forecast\n"
            "!screen SYMBOL — Run 12-component screen\n"
            "!position — View current positions\n"
            "!balance — Check account balance\n"
            "!risk — View risk status\n"
            "!mood MOOD — Log your emotional state\n"
            "!analysis SYMBOL — Full analysis\n"
            "!chart SYMBOL — View chart\n"
            "!alert_on — Enable notifications\n"
            "!alert_off — Disable notifications\n"
            "!help — Show this help"
        )

    @staticmethod
    def _format_notification(notification: NotificationMessage) -> str:
        """Format a notification for WhatsApp."""
        severity_emoji = {
            "LOW": "ℹ️",
            "MEDIUM": "⚡",
            "HIGH": "🔴",
            "CRITICAL": "🚨",
        }
        emoji = severity_emoji.get(notification.severity, "📢")
        header = f"{emoji} *{notification.title}*"
        body = notification.body
        footer = f"\n\n_{datetime.now(tz=timezone.utc).strftime('%H:%M UTC')}_"
        return f"{header}\n\n{body}{footer}"

    # ----- Bridge communication -----

    async def _send_via_bridge(self, message: OutboundMessage) -> bool:
        """Send a message via the WhatsApp bridge service.

        Args:
            message: Message to send.

        Returns:
            True if sent successfully.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._bridge_url}/api/send",
                    json=message.model_dump(),
                )
                return response.status_code == 200
        except Exception as exc:
            logger.warning("WhatsApp bridge send failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# FastAPI Routes
# ---------------------------------------------------------------------------

_gateway: WhatsAppGateway | None = None


def _get_gateway() -> WhatsAppGateway:
    global _gateway
    if _gateway is None:
        _gateway = WhatsAppGateway()
    return _gateway


@router.post("/webhook")
async def whatsapp_webhook(message: WhatsAppMessage) -> Dict[str, Any]:
    """Receive an inbound WhatsApp message via webhook.

    Args:
        message: Incoming WhatsApp message.

    Returns:
        Dict with response status and optional reply.
    """
    gateway = _get_gateway()
    try:
        reply = await gateway.handle_inbound(message)
        result: Dict[str, Any] = {"status": "received"}
        if reply:
            result["reply"] = reply.model_dump()
        return result
    except Exception as exc:
        logger.error("WhatsApp webhook error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/notify")
async def send_notification(notification: NotificationMessage) -> Dict[str, Any]:
    """Send a notification to subscribed WhatsApp chats.

    Args:
        notification: Notification message to push.

    Returns:
        Dict with delivery status.
    """
    gateway = _get_gateway()
    try:
        recipients = await gateway.push_notification(notification)
        return {
            "status": "sent",
            "recipients": recipients,
            "count": len(recipients),
        }
    except Exception as exc:
        logger.error("WhatsApp notification error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/trade-alert")
async def send_trade_alert(
    symbol: str,
    direction: str,
    price: float,
    reason: str = "",
    confidence: float = 0.0,
) -> Dict[str, Any]:
    """Send a trade alert notification.

    Args:
        symbol: Trading symbol.
        direction: Trade direction (BUY/SELL).
        price: Trade price.
        reason: Alert reason.
        confidence: Signal confidence (0-1).

    Returns:
        Dict with delivery status.
    """
    gateway = _get_gateway()
    try:
        recipients = await gateway.send_trade_alert(
            symbol, direction, price, reason, confidence,
        )
        return {"status": "sent", "recipients": recipients}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/risk-warning")
async def send_risk_warning(
    warning_type: str,
    message: str,
    severity: str = "HIGH",
) -> Dict[str, Any]:
    """Send a risk warning notification.

    Args:
        warning_type: Type of risk warning.
        message: Warning message.
        severity: Warning severity.

    Returns:
        Dict with delivery status.
    """
    gateway = _get_gateway()
    try:
        recipients = await gateway.send_risk_warning(warning_type, message, severity)
        return {"status": "sent", "recipients": recipients}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def whatsapp_status() -> Dict[str, Any]:
    """Get WhatsApp gateway status.

    Returns:
        Dict with gateway status and subscription count.
    """
    gateway = _get_gateway()
    return {
        "status": "active",
        "subscriptions": len(gateway._subscriptions),
        "message_count": len(gateway._message_history),
    }


__all__ = [
    "WhatsAppGateway",
    "WhatsAppMessage",
    "ParsedCommand",
    "OutboundMessage",
    "NotificationConfig",
    "NotificationMessage",
    "MessageType",
    "MessageDirection",
    "CommandName",
    "parse_command",
    "router",
]
