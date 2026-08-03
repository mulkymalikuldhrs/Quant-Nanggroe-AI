"""QNA alerting subsystem (Archive upgrade C4).

Exposes ``AlertManager``, ``AlertLevel``, and ``build_telegram_transport``.
The manager is transport-agnostic: pass any callable ``transport(alert)`` to
dispatch. ``build_telegram_transport(token, chat_id)`` returns a transport that
posts to Telegram (fail-soft: missing ``requests`` dep falls back to logging).

``default_manager`` is the module-level singleton consumed (lazy, fail-soft) by
``quant_nanggroe.agents.graph``.
"""
from __future__ import annotations

import enum
import logging
import os

logger = logging.getLogger("qna.alerting")


class AlertLevel(enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Alert:
    """Immutable alert record."""

    __slots__ = ("level", "message")

    def __init__(self, level: AlertLevel, message: str) -> None:
        self.level = level
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover
        return f"Alert(level={self.level.value}, message={self.message!r})"


class AlertManager:
    """Dispatch alerts to a transport callable. Fail-soft by default."""

    def __init__(self, transport=None) -> None:
        self._transport = transport

    def _emit(self, level: AlertLevel, message: str) -> None:
        alert = Alert(level, message)
        if self._transport is not None:
            try:
                self._transport(alert)
                return
            except Exception as exc:  # fail-soft: never break caller
                logger.warning("alerting transport failed (%s): %s", exc, message)
        logger.log(
            logging.CRITICAL if level is AlertLevel.CRITICAL else logging.WARNING,
            "ALERT[%s]: %s", level.value, message,
        )

    def critical(self, message: str) -> None:
        self._emit(AlertLevel.CRITICAL, message)

    def warning(self, message: str) -> None:
        self._emit(AlertLevel.WARNING, message)

    def info(self, message: str) -> None:
        self._emit(AlertLevel.INFO, message)


def build_telegram_transport(token: str, chat_id: str):
    """Return a transport callable that posts alerts to Telegram.

    Fail-soft: if ``requests`` is unavailable, the returned callable logs
    instead of raising. Never crashes the caller.
    """
    def _transport(alert: Alert) -> None:
        try:
            import requests  # lazy optional dep
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": f"[{alert.level.value.upper()}] {alert.message}"},
                timeout=5,
            )
        except Exception as exc:  # pragma: no cover - fall back to log
            logger.warning("telegram transport unavailable (%s): %s", exc, alert.message)
    return _transport


# Module-level singleton (fail-soft: no transport -> logs locally).
default_manager = AlertManager(
    build_telegram_transport(
        os.environ.get("QNA_TELEGRAM_TOKEN", ""),
        os.environ.get("QNA_TELEGRAM_CHAT_ID", ""),
    )
    if os.environ.get("QNA_TELEGRAM_TOKEN") and os.environ.get("QNA_TELEGRAM_CHAT_ID")
    else None
)
