"""
Telegram Notification Integration for AI Quant Hedge Fund
Real-time trading signals and alerts via Telegram
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging
import json
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Telegram message types."""
    SIGNAL = "signal"
    ORDER = "order"
    POSITION = "position"
    ALERT = "alert"
    DAILY_REPORT = "daily_report"
    ERROR = "error"
    INFO = "info"


@dataclass
class TelegramConfig:
    """Telegram notification configuration."""
    bot_token: str
    chat_id: str
    enabled: bool = True
    signal_channel: str = None
    alert_channel: str = None
    parse_mode: str = "HTML"
    disable_web_preview: bool = True


@dataclass
class TradeSignal:
    """Trade signal for notifications."""
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    reasoning: List[str]
    risk_reward_ratio: float
    timestamp: datetime = None


class TelegramNotifier:
    """
    Telegram notification service for trading alerts.
    
    Features:
    - Real-time trade signals
    - Position updates
    - Daily reports
    - Error alerts
    - Markdown/HTML formatting
    - Async support
    """
    
    def __init__(self, config: TelegramConfig = None):
        self.config = config
        self.base_url = "https://api.telegram.org/bot"
        self.session: Optional[aiohttp.ClientSession] = None
        
        self._message_queue: List[Dict] = []
        self._worker_task = None
        self._running = False
    
    async def start(self) -> None:
        """Start the notifier and background worker."""
        if not self.config or not self.config.enabled:
            logger.warning("Telegram notifier disabled")
            return
        
        self.session = aiohttp.ClientSession()
        self._running = True
        self._worker_task = asyncio.create_task(self._message_worker())
        
        logger.info("Telegram notifier started")
        
        await self.send_message(
            "🚀 <b>AI Quant Hedge Fund</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Trading system initialized\n"
            "📊 Monitoring active\n"
            "🔔 Notifications enabled",
            message_type=MessageType.INFO
        )
    
    async def stop(self) -> None:
        """Stop the notifier."""
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("Telegram notifier stopped")
    
    async def send_signal(
        self,
        signal: TradeSignal,
        mode: str = "semi_auto"
    ) -> bool:
        """
        Send a trade signal notification.
        
        Args:
            signal: Trade signal details
            mode: Trading mode (manual, semi_auto, full_auto)
            
        Returns:
            bool: Success status
        """
        emoji = "🟢" if signal.side.upper() == "BUY" else "🔴" if signal.side.upper() == "SELL" else "🟡"
        mode_emoji = "👤" if mode == "manual" else "⚡" if mode == "semi_auto" else "🤖"
        
        confidence_bar = "█" * int(signal.confidence * 10) + "░" * (10 - int(signal.confidence * 10))
        
        reasoning = "\n".join([f"• {r}" for r in signal.reasoning[:3]])
        
        message = (
            f"{emoji} <b>TRADE SIGNAL</b> {mode_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>SYM:</b> {signal.symbol}\n"
            f"<b>SIDE:</b> {signal.side}\n"
            f"<b>ENTRY:</b> {signal.entry_price:.5f}\n"
            f"<b>SL:</b> {signal.stop_loss:.5f}\n"
            f"<b>TP:</b> {signal.take_profit:.5f}\n"
            f"<b>RR:</b> 1:{signal.risk_reward_ratio:.2f}\n\n"
            f"<b>STRATEGY:</b> {signal.strategy}\n"
            f"<b>CONFIDENCE:</b> {confidence_bar} {signal.confidence:.0%}\n\n"
            f"<b>REASONING:</b>\n{reasoning}\n\n"
            f"<i>🤖 AI Quant Hedge Fund v2.0</i>"
        )
        
        return await self.send_message(message, message_type=MessageType.SIGNAL)
    
    async def send_position_update(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_pct: float,
        action: str = "UPDATE"
    ) -> bool:
        """
        Send position update notification.
        
        Args:
            symbol: Trading symbol
            side: Position side (LONG/SHORT)
            pnl: Profit/Loss amount
            pnl_pct: PnL percentage
            action: Update action (OPEN, UPDATE, CLOSE)
        """
        action_emojis = {
            "OPEN": "🆕",
            "UPDATE": "🔄",
            "CLOSE": "❌"
        }
        
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        message = (
            f"{action_emojis.get(action, '📊')} <b>POSITION {action}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>SYM:</b> {symbol}\n"
            f"<b>SIDE:</b> {side}\n"
            f"<b>PnL:</b> {pnl_emoji} ${pnl:+.2f} ({pnl_pct:+.2f}%)\n\n"
            f"<i>🤖 AI Quant Hedge Fund</i>"
        )
        
        return await self.send_message(message, message_type=MessageType.POSITION)
    
    async def send_daily_report(
        self,
        stats: Dict,
        trades: List[Dict]
    ) -> bool:
        """
        Send daily performance report.
        
        Args:
            stats: Daily statistics
            trades: List of trades
        """
        win_rate = stats.get("win_rate", 0)
        profit_factor = stats.get("profit_factor", 0)
        total_pnl = stats.get("total_pnl", 0)
        daily_pnl = stats.get("daily_pnl", 0)
        num_trades = stats.get("total_trades", 0)
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        win_emoji = "✅" if win_rate >= 50 else "⚠️"
        
        today_trades = [t for t in trades if t.get("exit_time", "").startswith(datetime.now().strftime("%Y-%m-%d"))]
        
        message = (
            f"📊 <b>DAILY REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>DATE:</b> {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"<b>PERFORMANCE:</b>\n"
            f"  {pnl_emoji} <b>Total PnL:</b> ${total_pnl:+.2f}\n"
            f"  📈 <b>Daily PnL:</b> ${daily_pnl:+.2f}\n"
            f"  {win_emoji} <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"  📊 <b>Profit Factor:</b> {profit_factor:.2f}\n"
            f"  🎯 <b>Trades:</b> {num_trades}\n\n"
        )
        
        if today_trades:
            wins = sum(1 for t in today_trades if t.get("pnl", 0) > 0)
            losses = len(today_trades) - wins
            message += (
                f"<b>TODAY'S TRADES:</b>\n"
                f"  ✅ Wins: {wins}\n"
                f"  ❌ Losses: {losses}\n\n"
            )
        
        message += f"<i>🤖 AI Quant Hedge Fund v2.0</i>"
        
        return await self.send_message(message, message_type=MessageType.DAILY_REPORT)
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info"
    ) -> bool:
        """
        Send an alert notification.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity (info, warning, error)
        """
        severity_emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "critical": "🛑"
        }
        
        emoji = severity_emojis.get(severity, "📢")
        
        full_message = (
            f"{emoji} <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{message}\n\n"
            f"<i>🤖 AI Quant Hedge Fund</i>"
        )
        
        return await self.send_message(full_message, message_type=MessageType.ALERT)
    
    async def send_error(
        self,
        error: str,
        context: str = ""
    ) -> bool:
        """Send error notification."""
        message = (
            f"🚨 <b>SYSTEM ERROR</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>ERROR:</b>\n{error}\n\n"
            f"<b>CONTEXT:</b>\n{context if context else 'N/A'}\n\n"
            f"<i>🤖 AI Quant Hedge Fund</i>"
        )
        
        return await self.send_message(message, message_type=MessageType.ERROR)
    
    async def send_message(
        self,
        message: str,
        message_type: MessageType = MessageType.INFO
    ) -> bool:
        """
        Send a message to Telegram.
        
        Args:
            message: Message content (HTML formatted)
            message_type: Type of message
            
        Returns:
            bool: Success status
        """
        if not self.config or not self.config.enabled:
            return False
        
        if self._running:
            self._message_queue.append({
                "message": message,
                "type": message_type.value,
                "timestamp": datetime.now().isoformat()
            })
            return True
        
        return await self._send_telegram_message(message)
    
    async def _send_telegram_message(self, message: str) -> bool:
        """Send message directly to Telegram."""
        if not self.session:
            logger.warning("Telegram session not initialized")
            return False
        
        try:
            url = f"{self.base_url}{self.config.bot_token}/sendMessage"
            
            data = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": self.config.parse_mode,
                "disable_web_page_preview": self.config.disable_web_preview
            }
            
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                
                if result.get("ok"):
                    logger.debug("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def _message_worker(self) -> None:
        """Background worker to process message queue."""
        while self._running:
            try:
                if self._message_queue:
                    message_data = self._message_queue.pop(0)
                    await self._send_telegram_message(message_data["message"])
                    
                    await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message worker error: {e}")
                await asyncio.sleep(1)
    
    async def test_connection(self) -> bool:
        """Test Telegram connection."""
        if not self.config or not self.config.bot_token:
            return False
        
        try:
            url = f"{self.base_url}{self.config.bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    result = await response.json()
                    return result.get("ok", False)
                    
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class SignalFormatter:
    """Format trade signals for various outputs."""
    
    @staticmethod
    def to_telegram(signal: TradeSignal, mode: str = "semi_auto") -> str:
        """Format signal for Telegram."""
        emoji = "🟢" if signal.side.upper() == "BUY" else "🔴"
        mode_emoji = "👤" if mode == "manual" else "⚡" if mode == "semi_auto" else "🤖"
        
        return (
            f"{emoji} <b>TRADE SIGNAL</b> {mode_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>SYM:</b> {signal.symbol}\n"
            f"<b>SIDE:</b> {signal.side}\n"
            f"<b>ENTRY:</b> {signal.entry_price:.5f}\n"
            f"<b>SL:</b> {signal.stop_loss:.5f}\n"
            f"<b>TP:</b> {signal.take_profit:.5f}\n"
            f"<b>RR:</b> 1:{signal.risk_reward_ratio:.2f}\n"
            f"<b>STRATEGY:</b> {signal.strategy}\n"
            f"<b>CONFIDENCE:</b> {signal.confidence:.0%}"
        )
    
    @staticmethod
    def to_slack(signal: TradeSignal) -> str:
        """Format signal for Slack."""
        emoji = ":green_circle:" if signal.side.upper() == "BUY" else ":red_circle:"
        
        return (
            f"{emoji} *TRADE SIGNAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*SYM:* {signal.symbol}\n"
            f"*SIDE:* {signal.side}\n"
            f"*ENTRY:* {signal.entry_price:.5f}\n"
            f"*SL:* {signal.stop_loss:.5f}\n"
            f"*TP:* {signal.take_profit:.5f}\n"
            f"*RR:* 1:{signal.risk_reward_ratio:.2f}\n"
            f"*STRATEGY:* {signal.strategy}\n"
            f"*CONFIDENCE:* {signal.confidence:.0%}"
        )


def create_telegram_notifier(
    bot_token: str,
    chat_id: str,
    enabled: bool = True
) -> TelegramNotifier:
    """Factory function to create Telegram notifier."""
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
        enabled=enabled
    )
    return TelegramNotifier(config)


if __name__ == "__main__":
    import os
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        notifier = create_telegram_notifier(bot_token, chat_id)
        
        signal = TradeSignal(
            symbol="EURUSD",
            side="BUY",
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.1000,
            confidence=0.75,
            strategy="ICT SMC",
            reasoning=["Order block identified", "Liquidity sweep completed", "FVG bullish"],
            risk_reward_ratio=3.0
        )
        
        async def main():
            await notifier.start()
            await notifier.send_signal(signal, "semi_auto")
            await asyncio.sleep(2)
            await notifier.stop()
        
        asyncio.run(main())
    else:
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
