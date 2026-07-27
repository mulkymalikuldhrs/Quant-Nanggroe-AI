"""Telegram Signal Bot — autonomous trading signal delivery.

Based on:
- CuanbotSimflow.json: ParseCommand → AssetValidator → Analysis → Response
- n8n trading pipeline: Telegram output node
- RavenPack sentiment analysis for signal enhancement
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

VALID_ASSETS = [
    "BTC", "BTCUSDT", "ETH", "ETHUSDT", "XAUUSD",
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD",
    "USDCAD", "USDCHF", "SOL", "SOLUSDT",
]

SIGNAL_TEMPLATE = (
    "\ud83d\udcc8 *{symbol}* — QNA Signal\n"
    "Side: {side}\n"
    "Entry: {entry_price}\n"
    "Stop Loss: {stop_loss}\n"
    "Take Profit: {take_profit}\n"
    "Confidence: {confidence:.0f}%\n"
    "RRR: {rrr}:1\n"
    "Lot Size: {lot_size}\n"
    "Risk: {risk_pct:.1f}%\n"
    "Confluence: {confluence}/{confluence_total}\n"
    "Regime: {regime}\n"
    "POI: {poi_type}\n"
    "\u23f0 {timestamp}"
)


@dataclass
class SignalResult:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    rrr: float
    lot_size: float
    risk_pct: float
    confluence: int
    confluence_total: int
    regime: str
    poi_type: str
    timestamp: str
    raw: Dict[str, Any] = field(default_factory=dict)


class TelegramSignalBot:
    """Trading signal bot with Telegram integration."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        api_base: str = "https://api.telegram.org",
    ):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_base = api_base
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured — skipping message")
            return False
        try:
            await self._ensure_session()
            url = f"{self.api_base}/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            async with self._session.post(url, json=payload) as resp:
                result = await resp.json()
                if result.get("ok"):
                    logger.info("Telegram message sent")
                    return True
                logger.error(f"Telegram API error: {result}")
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def format_signal(self, signal: SignalResult) -> str:
        return SIGNAL_TEMPLATE.format(
            symbol=signal.symbol,
            side=signal.side.upper(),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence * 100,
            rrr=signal.rrr,
            lot_size=signal.lot_size,
            risk_pct=signal.risk_pct,
            confluence=signal.confluence,
            confluence_total=signal.confluence_total,
            regime=signal.regime,
            poi_type=signal.poi_type,
            timestamp=signal.timestamp,
        )

    async def send_signal(self, signal: SignalResult) -> bool:
        text = self.format_signal(signal)
        return await self.send_message(text)

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


def parse_command(text: str) -> Optional[str]:
    """Parse Telegram command or direct message for asset symbol."""
    text = text.strip()
    if text.lower().startswith("/trade"):
        parts = text.split()
        if len(parts) >= 2:
            return parts[1].upper()
    return text.upper()


def validate_asset(symbol: str) -> bool:
    """Check if symbol is in valid assets list."""
    return symbol in VALID_ASSETS


async def analyze_and_signal(
    symbol: str,
    bot: Optional[TelegramSignalBot] = None,
) -> Optional[SignalResult]:
    """Run full analysis pipeline and return signal."""
    import sys
    sys.path.insert(0, os.getenv("PYTHONPATH", ""))

    try:
        from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl
        from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard, TradeAction, TradeRequest
        from quant_nanggroe.engine.risk.sizing import calculate_position_size
        from quant_nanggroe.engine.smc.engine import SMCEngine

        engine = SMCEngine()
        risk_gate = ConstitutionalRiskGuard()

        analysis = engine.analyze(
            symbol=symbol,
            high=[],
            low=[],
            close=[],
            volume=[],
        )

        entry = analysis.get("entry_price", 0)
        bias = analysis.get("bias", "neutral")
        atr = calculate_atr_sl(
            high=analysis.get("high", []),
            low=analysis.get("low", []),
            close=analysis.get("close", []),
            entry_price=entry,
            side=bias,
        )
        sl = atr.get("stop_loss", 0)
        sizing = calculate_position_size(
            entry_price=entry,
            stop_loss=sl,
            account_balance=10000,
            risk_per_trade=0.02,
        )

        return SignalResult(
            symbol=symbol,
            side=bias,
            entry_price=entry,
            stop_loss=sl,
            take_profit=entry + (entry - sl) * 2,
            confidence=analysis.get("confidence", 0.5),
            rrr=2.0,
            lot_size=sizing.get("lot_size", 0),
            risk_pct=sizing.get("risk_pct", 2.0),
            confluence=analysis.get("confluence_count", 0),
            confluence_total=7,
            regime=analysis.get("regime", "unknown"),
            poi_type=analysis.get("poi_type", "none"),
            timestamp=datetime.now().isoformat(),
        )
    except ImportError as e:
        logger.error(f"Analysis pipeline import failed: {e}")
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QNA Telegram Signal Bot")
    parser.add_argument("--token", help="Telegram bot token")
    parser.add_argument("--chat-id", help="Telegram chat ID")
    parser.add_argument("symbol", nargs="?", help="Symbol to analyze")
    args = parser.parse_args()

    async def run():
        bot = TelegramSignalBot(token=args.token, chat_id=args.chat_id)
        if args.symbol:
            symbol = parse_command(args.symbol) or args.symbol
            if validate_asset(symbol):
                signal = await analyze_and_signal(symbol)
                if signal:
                    sent = await bot.send_signal(signal)
                    if sent:
                        print("Signal sent successfully")
                    else:
                        print(signal)
                else:
                    print("Analysis failed")
            else:
                print(f"Invalid asset: {symbol}")
        await bot.close()

    asyncio.run(run())
