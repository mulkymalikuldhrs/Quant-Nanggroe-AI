import os
import json
import logging
import urllib.request
import urllib.error

log = logging.getLogger("QNA.Notifier")

TELEGRAM_BOTS = [
    {"name": "autobot", "token": os.environ.get("QNA_TELEGRAM_BOT_TOKEN_AUTOBOT", "")},
    {"name": "traderbot", "token": os.environ.get("QNA_TELEGRAM_BOT_TOKEN_TRADERBOT", "")},
]
CHAT_ID = os.environ.get("QNA_TELEGRAM_CHAT_ID", "")


def send_telegram(message: str, bot_index: int = 0) -> bool:
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
            log.debug(f"Telegram error: {result}")
            return False
    except Exception as e:
        log.debug(f"Telegram send failed: {e}")
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
