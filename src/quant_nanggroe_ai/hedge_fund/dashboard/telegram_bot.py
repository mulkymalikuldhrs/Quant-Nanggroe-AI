"""
Telegram Bot Integration for AI Hedge Fund v2.2
================================================

Features:
- Real-time signal notifications
- Portfolio updates
- Trade execution commands
- Market analysis on demand
- Multi-account support

Usage:
    python3 -m src.dashboard.telegram_bot
    Set TELEGRAM_BOT_TOKEN environment variable
"""

import sys
import os
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    SIGNAL = "signal"
    TRADE = "trade"
    ALERT = "alert"
    PORTFOLIO = "portfolio"
    SYSTEM = "system"


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""

    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False
    notify_signals: bool = True
    notify_trades: bool = True
    notify_alerts: bool = True
    notify_portfolio: bool = False


@dataclass
class SignalMessage:
    """Signal notification message"""

    symbol: str
    signal_type: str
    confidence: float
    price: float
    stop_loss: float
    take_profit: List[float]
    timestamp: datetime = field(default_factory=datetime.now)


class TelegramBotBase(ABC):
    """Abstract base class for Telegram bot"""

    @abstractmethod
    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def send_signal(self, signal: SignalMessage, chat_id: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def start_polling(self):
        pass


class TelegramBot(TelegramBotBase):
    """Telegram Bot implementation using python-telegram-bot"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        self.config = config or TelegramConfig()
        self._bot = None
        self._application = None
        self._handlers: List[Callable] = []
        self._running = False

    def _init_bot(self):
        """Initialize the bot"""
        try:
            from telegram import Update, Bot
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                CallbackContext,
                filters,
            )

            if not self.config.bot_token:
                logger.warning("Telegram bot token not configured")
                return False

            self._Bot = Bot
            self._Update = Update
            self._CallbackContext = CallbackContext
            self._Application = Application
            self._CommandHandler = CommandHandler
            self._MessageHandler = MessageHandler
            self._filters = filters

            return True

        except ImportError:
            logger.error("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
            return False

    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """Send a text message"""
        if not self.config.enabled or not self.config.bot_token:
            return False

        try:
            import requests

            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
            data = {
                "chat_id": chat_id or self.config.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }

            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_signal(self, signal: SignalMessage, chat_id: Optional[str] = None) -> bool:
        """Send a signal notification"""
        emoji = {
            "STRONG_BUY": "🟢🟢",
            "BUY": "🟢",
            "HOLD": "🟡",
            "SELL": "🔴",
            "STRONG_SELL": "🔴🔴",
        }.get(signal.signal_type, "⚪")

        tp_text = "\n".join([f"  🎯 TP{i + 1}: ${tp:,.5f}" for i, tp in enumerate(signal.take_profit[:3])])

        text = f"""<b>{emoji} AI HEDGE FUND SIGNAL</b>

<b>Symbol:</b> {signal.symbol}
<b>Signal:</b> {signal.signal_type}
<b>Confidence:</b> {signal.confidence:.0%}
<b>Current Price:</b> ${signal.price:,.5f}

<b>📊 Trade Levels:</b>
  🎯 Entry: ${signal.price:,.5f}
  🛑 Stop Loss: ${signal.stop_loss:,.5f}
{tp_text}

<i>Generated at {signal.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</i>"""

        return self.send_message(text, chat_id)

    def send_portfolio_update(self, portfolio: Dict, chat_id: Optional[str] = None) -> bool:
        """Send portfolio update"""
        balance = portfolio.get("balance", 0)
        equity = portfolio.get("equity", 0)
        pnl = portfolio.get("floating_pnl", 0)
        pnl_pct = portfolio.get("floating_pnl_pct", 0)
        positions = portfolio.get("open_positions", 0)

        pnl_emoji = "🟢" if pnl >= 0 else "🔴"

        text = f"""<b>📊 PORTFOLIO UPDATE</b>

<b>Balance:</b> ${balance:,.2f}
<b>Equity:</b> ${equity:,.2f}
{pnl_emoji} <b>P&L:</b> ${pnl:,.2f} ({pnl_pct:.2f}%)
<b>Open Positions:</b> {positions}

<i>Updated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>"""

        return self.send_message(text, chat_id)

    def send_trade_notification(self, trade: Dict, chat_id: Optional[str] = None) -> bool:
        """Send trade notification"""
        action = trade.get("action", "UNKNOWN")
        symbol = trade.get("symbol", "Unknown")
        price = trade.get("price", 0)
        quantity = trade.get("quantity", 0)
        pnl = trade.get("pnl", 0)

        emoji = "🟢" if action == "BUY" else "🔴"

        text = f"""<b>{emoji} TRADE EXECUTED</b>

<b>Action:</b> {action}
<b>Symbol:</b> {symbol}
<b>Price:</b> ${price:,.5f}
<b>Quantity:</b> {quantity}
<b>P&L:</b> ${pnl:,.2f}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>"""

        return self.send_message(text, chat_id)

    def start_polling(self):
        """Start bot polling (placeholder for full implementation)"""
        if not self._init_bot():
            logger.warning("Telegram bot initialization failed")
            return

        logger.info("Telegram bot polling started (basic mode)")
        self._running = True


class MockTelegramBot(TelegramBotBase):
    """Mock Telegram bot for testing without API"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        self.config = config or TelegramConfig()
        self.messages: List[Dict] = []
        self._running = False

    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """Store message locally"""
        self.messages.append(
            {
                "type": "message",
                "text": text,
                "chat_id": chat_id or self.config.chat_id,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"[MOCK TELEGRAM] Message queued: {text[:50]}...")
        return True

    def send_signal(self, signal: SignalMessage, chat_id: Optional[str] = None) -> bool:
        """Store signal locally"""
        self.messages.append(
            {
                "type": "signal",
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,
                "confidence": signal.confidence,
                "timestamp": signal.timestamp.isoformat(),
            }
        )
        logger.info(f"[MOCK TELEGRAM] Signal queued: {signal.signal_type} {signal.symbol}")
        return True

    def send_portfolio_update(self, portfolio: Dict, chat_id: Optional[str] = None) -> bool:
        """Store portfolio update"""
        self.messages.append(
            {
                "type": "portfolio",
                "balance": portfolio.get("balance", 0),
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"[MOCK TELEGRAM] Portfolio update queued")
        return True

    def send_trade_notification(self, trade: Dict, chat_id: Optional[str] = None) -> bool:
        """Store trade notification"""
        self.messages.append(
            {
                "type": "trade",
                "action": trade.get("action", "UNKNOWN"),
                "symbol": trade.get("symbol", "Unknown"),
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"[MOCK TELEGRAM] Trade notification queued")
        return True

    def start_polling(self):
        """Mock polling"""
        self._running = True
        logger.info("Mock Telegram bot started (no actual messages sent)")

    def get_messages(self) -> List[Dict]:
        """Get all stored messages"""
        return self.messages

    def clear_messages(self):
        """Clear message history"""
        self.messages = []


class NotificationManager:
    """Manages all notifications"""

    def __init__(self):
        self._bot: Optional[TelegramBotBase] = None
        self._config = TelegramConfig()
        self._subscribers: List[str] = []
        self._signal_callbacks: List[Callable] = []

    def initialize(self, bot_token: str = "", chat_id: str = "", use_mock: bool = True):
        """Initialize notification manager"""
        self._config.bot_token = bot_token
        self._config.chat_id = chat_id
        self._config.enabled = bool(bot_token and chat_id)

        if use_mock or not bot_token:
            self._bot = MockTelegramBot(self._config)
            logger.info("Using mock Telegram bot (no actual messages)")
        else:
            self._bot = TelegramBot(self._config)
            if not self._bot._init_bot():
                self._bot = MockTelegramBot(self._config)
                logger.warning("Falling back to mock Telegram bot")

    def send_signal(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        price: float,
        stop_loss: float,
        take_profit: List[float],
    ) -> bool:
        """Send a signal notification"""
        if not self._config.enabled or not self._config.notify_signals:
            return False

        signal = SignalMessage(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        result = self._bot.send_signal(signal)

        for callback in self._signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")

        return result

    def send_portfolio_update(self, portfolio: Dict) -> bool:
        """Send portfolio update"""
        if not self._config.enabled or not self._config.notify_portfolio:
            return False
        return self._bot.send_portfolio_update(portfolio)

    def send_trade_notification(self, trade: Dict) -> bool:
        """Send trade notification"""
        if not self._config.enabled or not self._config.notify_trades:
            return False
        return self._bot.send_trade_notification(trade)

    def send_alert(self, alert_type: str, message: str) -> bool:
        """Send custom alert"""
        if not self._config.enabled or not self._config.notify_alerts:
            return False

        text = f"<b>⚠️ ALERT: {alert_type}</b>\n\n{message}"
        return self._bot.send_message(text)

    def add_signal_callback(self, callback: Callable):
        """Add callback for signal notifications"""
        self._signal_callbacks.append(callback)

    def get_bot(self) -> TelegramBotBase:
        """Get bot instance"""
        return self._bot


def get_notification_manager() -> NotificationManager:
    """Get notification manager singleton"""
    if not hasattr(NotificationManager, "_instance"):
        NotificationManager._instance = NotificationManager()
    return NotificationManager._instance


def main():
    """Test the Telegram bot integration"""
    print("=== Telegram Bot Integration Test ===\n")

    manager = get_notification_manager()
    manager.initialize(use_mock=True)

    bot = manager.get_bot()

    print("1. Testing signal notification...")
    signal_sent = manager.send_signal(
        symbol="AAPL",
        signal_type="BUY",
        confidence=0.75,
        price=258.21,
        stop_loss=245.30,
        take_profit=[263.37, 271.12],
    )
    print(f"   Signal sent: {signal_sent}")

    print("\n2. Testing portfolio update...")
    portfolio = {
        "balance": 10000.0,
        "equity": 10250.0,
        "floating_pnl": 250.0,
        "floating_pnl_pct": 2.5,
        "open_positions": 3,
    }
    pf_sent = manager.send_portfolio_update(portfolio)
    print(f"   Portfolio update sent: {pf_sent}")

    print("\n3. Testing trade notification...")
    trade = {
        "action": "BUY",
        "symbol": "AAPL",
        "price": 258.21,
        "quantity": 10,
        "pnl": 0,
    }
    trade_sent = manager.send_trade_notification(trade)
    print(f"   Trade notification sent: {trade_sent}")

    print("\n4. Testing alert...")
    alert_sent = manager.send_alert("RISK", "Daily loss limit approaching (4%)")
    print(f"   Alert sent: {alert_sent}")

    print("\n5. Messages in queue:")
    if isinstance(bot, MockTelegramBot):
        messages = bot.get_messages()
        for msg in messages:
            print(f"   - {msg['type']}: {msg.get('symbol', msg.get('action', 'update'))}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
