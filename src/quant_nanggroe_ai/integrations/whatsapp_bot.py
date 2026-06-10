"""
WhatsApp Bot Integration
==========================
Python integration for the Dhaher Trading Plan AI WhatsApp bot.

Ported from Trading-Plan-AI-Interactive v11.1.4 "Production Hardened":
  - whatsapp_bot/index.js (Node.js → Python adaptation)
  - Command handlers: !intel, !summary, !forecast, !cot, !reflect, !ping
  - Notification endpoint for sending proactive alerts
  - Emotional lockout notification triggers

This module provides:
1. **WhatsAppBot** — Full bot client with command routing
2. **Notification helpers** — For sending proactive alerts

The original Node.js bot uses `whatsapp-web.js` with Puppeteer for
QR-code-based WhatsApp Web authentication. This Python adaptation
uses the `whatsapp_api_client` pattern (HTTP-based) which works
with the WhatsApp Business API or a running instance of the
Node.js bot server.

All import paths use the quant_nanggroe_ai package.

Usage::

    from quant_nanggroe_ai.integrations.whatsapp_bot import WhatsAppBot

    bot = WhatsAppBot(
        api_url="https://your-bot-server.example.com",
        api_key="your-bot-api-key",
    )

    # Send a notification
    bot.send_notification("+1234567890", "Trade signal: BUY EURUSD @ 1.0850")

    # Format an AI summary for WhatsApp
    summary = {"final_bias": "BULLISH", "confidence_score": 8, ...}
    message = bot.format_summary_message("EURUSD", summary)

    # Format a forecast for WhatsApp
    forecast = {"bias": "BULLISH", "probability": 75, ...}
    message = bot.format_forecast_message("GOLD", forecast)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Data Models
# ══════════════════════════════════════════════════════════════════════


@dataclass
class WhatsAppMessage:
    """A WhatsApp message payload."""

    to: str  # Phone number or chat ID
    message: str
    timestamp: str = ""


@dataclass
class CommandResult:
    """Result of processing a WhatsApp command."""

    command: str
    symbol: str = "EURUSD"
    reply: str = ""
    success: bool = True
    error: str = ""


# ══════════════════════════════════════════════════════════════════════
# WhatsApp Bot
# ══════════════════════════════════════════════════════════════════════


class WhatsAppBot:
    """
    WhatsApp bot integration for trading notifications and commands.

    This class provides:
    - Notification sending via the WhatsApp bot server's HTTP endpoint
    - Message formatting for AI summaries, forecasts, COT data
    - Command parsing and routing (mirrors the Node.js bot's command set)
    - Integration with TradingPlanClient for data fetching

    Args:
        api_url: URL of the running WhatsApp bot server (Node.js).
        api_key: BOT_API_KEY for authentication.
        gas_url: Optional Google Apps Script URL for direct API calls.
        timeout: HTTP request timeout in seconds.

    Example::

        bot = WhatsAppBot(
            api_url="http://localhost:3000",
            api_key="secret-key",
        )

        # Send a proactive notification
        bot.send_notification(
            to="+1234567890",
            message="Trade signal: BUY EURUSD @ 1.0850",
        )
    """

    # Command map: WhatsApp command → GAS API action
    COMMAND_MAP: dict[str, str] = {
        "intel": "getAiMasterSummary",
        "summary": "getAiMasterSummary",
        "forecast": "getForecast",
        "plan": "getForecast",
        "cot": "getAiMasterSummary",
    }

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        gas_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_url = api_url or os.environ.get("WHATSAPP_BOT_URL", "")
        self.api_key = api_key or os.environ.get("BOT_API_KEY", "")
        self.gas_url = gas_url or os.environ.get("GAS_URL", "")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Notification Sending
    # ------------------------------------------------------------------

    def send_notification(self, to: str, message: str) -> dict[str, Any]:
        """
        Send a proactive notification via the WhatsApp bot server.

        Args:
            to: Phone number (with country code, no +) or chat ID.
            message: The message text to send.

        Returns:
            Dict with status and details.

        Raises:
            ConnectionError: If the bot server is unreachable.
        """
        if not self.api_url:
            logger.warning("WhatsApp bot URL not configured; notification not sent")
            return {"status": "error", "message": "Bot URL not configured"}

        payload = {
            "to": to,
            "message": message,
            "apiKey": self.api_key,
        }

        try:
            # The Node.js bot exposes POST /send and POST /notify
            for endpoint in ["/send", "/notify"]:
                url = f"{self.api_url.rstrip('/')}{endpoint}"
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=self.timeout,
                    )
                    if response.status_code == 200:
                        logger.info("WhatsApp notification sent to %s", to)
                        return {"status": "success", "to": to}
                    if response.status_code == 401:
                        return {"status": "error", "message": "Unauthorized: invalid API key"}
                except requests.exceptions.ConnectionError:
                    continue

            return {"status": "error", "message": "All endpoints unreachable"}

        except requests.exceptions.Timeout:
            return {"status": "error", "message": f"Request timed out after {self.timeout}s"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Message Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def format_summary_message(symbol: str, summary: dict[str, Any]) -> str:
        """
        Format an AI master summary as a WhatsApp message.

        Args:
            symbol: The trading pair symbol.
            summary: Dict from TradingPlanClient.get_ai_summary().

        Returns:
            Formatted WhatsApp message string.
        """
        bias = summary.get("final_bias", "N/A")
        confidence = summary.get("confidence_score", "N/A")
        signal = summary.get("signal", {})
        thesis = summary.get("technical_thesis", "No thesis available.")

        lines = [
            f"*AI ANALYSIS: {symbol}*",
            "",
            f"*Bias:* {bias}",
            f"*Confidence:* {confidence}/10",
            "",
            f"*Thesis:*",
            thesis[:300],  # WhatsApp has message length limits
        ]

        if signal and signal.get("active"):
            lines.extend([
                "",
                "*Recommended Setup:*",
                f"  Entry: {signal.get('entry', 'N/A')}",
                f"  SL: {signal.get('stop_loss', 'N/A')}",
                f"  TP: {signal.get('take_profit', 'N/A')}",
            ])

        return "\n".join(lines)

    @staticmethod
    def format_forecast_message(symbol: str, forecast: dict[str, Any]) -> str:
        """
        Format a forecast result as a WhatsApp message.

        Args:
            symbol: The trading pair symbol.
            forecast: Dict from TradingPlanClient.get_forecast().

        Returns:
            Formatted WhatsApp message string.
        """
        bias = forecast.get("bias", "N/A")
        probability = forecast.get("probability", "N/A")
        entry_zone = forecast.get("entry_zone", "N/A")
        sl = forecast.get("stop_loss", "N/A")
        tp = forecast.get("take_profit", "N/A")

        return "\n".join([
            f"*AI Forecast: {symbol}*",
            "",
            f"*Bias:* {bias}",
            f"*Probability:* {probability}%",
            "",
            f"*Entry Zone:* {entry_zone}",
            f"*SL:* {sl} | *TP:* {tp}",
        ])

    @staticmethod
    def format_cot_message(symbol: str, cot_data: dict[str, Any]) -> str:
        """
        Format COT data as a WhatsApp message.

        Args:
            symbol: The trading pair symbol.
            cot_data: COT report data dict.

        Returns:
            Formatted WhatsApp message string.
        """
        long_pos = cot_data.get("nonCommercialLong", "N/A")
        short_pos = cot_data.get("nonCommercialShort", "N/A")
        net = cot_data.get("netPosition", "N/A")
        bias = cot_data.get("bias", "N/A")

        return "\n".join([
            f"*COT Intelligence: {symbol}*",
            "",
            f"*Non-Commercial Long:* {long_pos:,}" if isinstance(long_pos, int) else f"*Long:* {long_pos}",
            f"*Non-Commercial Short:* {short_pos:,}" if isinstance(short_pos, int) else f"*Short:* {short_pos}",
            f"*Net Position:* {net:,}" if isinstance(net, int) else f"*Net:* {net}",
            f"*Bias:* {bias}",
        ])

    @staticmethod
    def format_violation_alert(violation_count: int) -> str:
        """
        Format an emotional lockout alert message.

        Args:
            violation_count: Number of consecutive violations.

        Returns:
            Alert message string.
        """
        return (
            f"MANDATORY BREAK: You've had {violation_count} consecutive "
            f"violations. Emotional lockout activated. Reflect on your process."
        )

    # ------------------------------------------------------------------
    # Command Processing (for incoming WhatsApp messages)
    # ------------------------------------------------------------------

    def parse_command(self, text: str) -> tuple[str, str]:
        """
        Parse an incoming WhatsApp message into a command and symbol.

        Supported commands (mirrors Node.js bot):
        - ``!intel EURUSD`` or ``!summary GBPUSD``
        - ``!forecast GOLD`` or ``!plan EURUSD``
        - ``!cot EURUSD``
        - ``!reflect``
        - ``!ping``

        Args:
            text: Raw message text.

        Returns:
            Tuple of (command, symbol).
        """
        text = text.strip()
        if not text.startswith("!"):
            return "", ""

        parts = text[1:].split()
        if not parts:
            return "", ""

        command = parts[0].lower()
        symbol = parts[1].upper() if len(parts) > 1 else "EURUSD"
        return command, symbol

    def process_command(self, text: str) -> CommandResult:
        """
        Process an incoming WhatsApp command and return a formatted reply.

        Args:
            text: Raw message text from WhatsApp.

        Returns:
            CommandResult with the formatted reply.
        """
        command, symbol = self.parse_command(text)

        if not command:
            return CommandResult(command="", reply="", success=False, error="Not a command")

        # Handle simple commands that don't need API calls
        if command == "ping":
            return CommandResult(command="ping", reply="pong")
        if command == "reflect":
            return CommandResult(
                command="reflect",
                reply="Reflection mode: How was your discipline today? (Good/Average/Poor)",
            )

        # Look up the API action
        action = self.COMMAND_MAP.get(command)
        if not action:
            return CommandResult(
                command=command,
                success=False,
                error=f"Unknown command: !{command}",
            )

        # Fetch data from GAS backend
        if not self.gas_url:
            return CommandResult(
                command=command,
                symbol=symbol,
                success=False,
                error="GAS URL not configured. Set gas_url or GAS_URL env var.",
            )

        try:
            payload: dict[str, Any] = {
                "action": action,
                "data": {
                    "symbol": symbol,
                    "pair": symbol,
                    "timeframe": "H4",
                    "days": 3,
                    "apiKey": self.api_key,
                },
            }
            response = requests.post(
                self.gas_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") != "success":
                return CommandResult(
                    command=command,
                    symbol=symbol,
                    success=False,
                    error=result.get("message", "API error"),
                )

            data = result.get("data", {})
            # Handle stringified JSON from GAS
            if isinstance(data, str):
                data = json.loads(data)

            # Format the response based on command type
            if command in ("intel", "summary"):
                reply = self.format_summary_message(symbol, data)
            elif command == "cot":
                reply = self.format_cot_message(symbol, data)
            elif command in ("forecast", "plan"):
                reply = self.format_forecast_message(symbol, data)
            else:
                reply = json.dumps(data, indent=2)[:500]

            return CommandResult(command=command, symbol=symbol, reply=reply)

        except requests.exceptions.RequestException as exc:
            return CommandResult(
                command=command,
                symbol=symbol,
                success=False,
                error=f"Failed to connect to AI engine: {exc}",
            )
        except json.JSONDecodeError:
            return CommandResult(
                command=command,
                symbol=symbol,
                success=False,
                error="Failed to parse API response",
            )


# ══════════════════════════════════════════════════════════════════════
# Convenience Factory
# ══════════════════════════════════════════════════════════════════════


def create_bot_from_env() -> WhatsAppBot:
    """
    Create a :class:`WhatsAppBot` from environment variables.

    Env vars:
        WHATSAPP_BOT_URL: WhatsApp bot server URL.
        BOT_API_KEY: API key for authentication.
        GAS_URL: Google Apps Script URL (optional).

    Returns:
        Configured WhatsAppBot instance.
    """
    return WhatsAppBot(
        api_url=os.environ.get("WHATSAPP_BOT_URL", ""),
        api_key=os.environ.get("BOT_API_KEY", ""),
        gas_url=os.environ.get("GAS_URL", ""),
    )


# ══════════════════════════════════════════════════════════════════════
# Module-level demo
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    bot = create_bot_from_env()

    # Test command parsing
    for cmd in ["!intel EURUSD", "!forecast GOLD", "!ping", "!reflect", "!cot GBPUSD"]:
        command, symbol = bot.parse_command(cmd)
        print(f"  {cmd} → command={command}, symbol={symbol}")

    # Test message formatting
    sample_summary = {
        "final_bias": "BULLISH",
        "confidence_score": 8,
        "technical_thesis": "Strong uptrend with support at 1.0800.",
        "signal": {"active": True, "entry": 1.0850, "stop_loss": 1.0800, "take_profit": 1.0950},
    }
    print("\n" + bot.format_summary_message("EURUSD", sample_summary))
