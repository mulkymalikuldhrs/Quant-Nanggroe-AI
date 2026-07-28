import asyncio
import logging

from quant_nanggroe.notifier import send_telegram as _sync_send

log = logging.getLogger(__name__)


async def send_telegram(message: str) -> bool:
    try:
        return await asyncio.to_thread(_sync_send, message)
    except Exception as exc:
        log.warning("send_telegram failed: %s", exc)
        return False
