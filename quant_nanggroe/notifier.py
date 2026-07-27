"""
Legacy synchronous Telegram notifier (urllib).

Used by live_engine.py for heartbeat, error, and trade alert messages.

For the async signal analysis pipeline with full trade signal formatting,
see agents/telegram_bot.py (TelegramSignalBot — aiohttp-based).

This file is kept as the lightweight sync path; telegram_bot.py is the
unified implementation for signal-oriented workflows.
"""

import functools
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("QNA.Notifier")

TELEGRAM_BOTS = [
    {"name": "autobot", "token": os.environ.get("QNA_TELEGRAM_BOT_TOKEN_AUTOBOT", "")},
    {"name": "traderbot", "token": os.environ.get("QNA_TELEGRAM_BOT_TOKEN_TRADERBOT", "")},
]
CHAT_ID = os.environ.get("QNA_TELEGRAM_CHAT_ID", "")


@functools.lru_cache(maxsize=1)
def validate_telegram_config() -> tuple[bool, str]:
    """Validate Telegram configuration (cached — warns only once per session).

    Returns:
        Tuple of (is_valid, message). ``is_valid`` is True when at least one
        bot token is set and CHAT_ID is set.
    """
    configured_bots = [b for b in TELEGRAM_BOTS if b["token"]]
    if not configured_bots:
        return False, (
            "No Telegram bot tokens configured. Set QNA_TELEGRAM_BOT_TOKEN_AUTOBOT "
            "and/or QNA_TELEGRAM_BOT_TOKEN_TRADERBOT environment variables."
        )
    if not CHAT_ID:
        return False, (
            "No Telegram chat ID configured. Set QNA_TELEGRAM_CHAT_ID "
            "environment variable."
        )
    return True, f"Telegram configured: {len(configured_bots)} bot(s), chat_id={CHAT_ID[:8]}..."


def ensure_telegram() -> bool:
    """Verify Telegram config at startup. Logs a clear warning if missing.

    Returns:
        True if configuration is valid, False otherwise.
    """
    is_valid, msg = validate_telegram_config()
    if is_valid:
        log.info("Telegram notifier ready — %s", msg)
    else:
        log.warning("Telegram notifier DISABLED — %s", msg)
    return is_valid


def send_telegram(message: str, bot_index: int = 0) -> bool:
    is_valid, msg = validate_telegram_config()
    if not is_valid:
        log.warning("send_telegram skipped — %s", msg)
        return False
    if bot_index >= len(TELEGRAM_BOTS):
        return False
    bot = TELEGRAM_BOTS[bot_index]
    url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode()
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read().decode())
            if result.get("ok"):
                return True
            log.debug("Telegram error: %s", result)
            return False
    except Exception as e:
        log.debug("Telegram send failed: %s", e)
        if bot_index < len(TELEGRAM_BOTS) - 1:
            return send_telegram(message, bot_index + 1)
        return False


def format_trade_alert(action: str, symbol: str, price: float,
                       qty: float, strategy: str, pnl: float = None) -> str:
    emoji = {"buy": "🟢", "sell": "🔴", "close": "⚪"}.get(action, "🔵")
    msg = f"{emoji} <b>QNA {action.upper()}</b>\n"
    msg += f"• {symbol} @ ${price:.2f}\n"
    msg += f"• Size: {qty:.4f}\n"
    msg += f"• Strategy: {strategy}"
    if pnl is not None:
        msg += f"\n• PnL: ${pnl:.2f}"
    return msg


def format_heartbeat(cycle: int, balance: float, portfolio: float,
                     drawdown: float, positions: int, errors: int) -> str:
    msg = f"🤖 <b>QNA Cycle {cycle}</b>\n"
    msg += f"• Balance: ${balance:.2f}\n"
    msg += f"• Portfolio: ${portfolio:.2f}\n"
    msg += f"• Drawdown: {drawdown:.2%}\n"
    msg += f"• Positions: {positions}\n"
    msg += f"• Errors: {errors}"
    return msg


def format_error_message(error: str, cycle: int) -> str:
    return f"🚨 <b>QNA ERROR Cycle {cycle}</b>\n<code>{error[:200]}</code>"
