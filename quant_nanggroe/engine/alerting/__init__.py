"""Alerting package (QuantScience roadmap C4: alert system).

Async-ready, dependency-free alert dispatcher. The Telegram transport is a thin
wrapper that lazy-imports the optional `telegram` client (not a core dep) so the
module imports cleanly in CI/offline. Critical/Warning/Info levels map to the
risk gate severities used across QNA.

Design (ponytail):
- No side effects at import. Alert levels are plain enums.
- Default transport logs to stderr (so headless servers still get signal);
  set_transport() swaps in Telegram/Slack without touching call sites.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("qna.alerting")


class AlertLevel(enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Alert:
    level: AlertLevel
    message: str
    source: str = "system"


Transport = Callable[[Alert], None]


def _log_transport(alert: Alert) -> None:
    tag = f"[{alert.level.value}]"
    if alert.level == AlertLevel.CRITICAL:
        logger.error("%s %s: %s", tag, alert.source, alert.message)
    elif alert.level == AlertLevel.WARNING:
        logger.warning("%s %s: %s", tag, alert.source, alert.message)
    else:
        logger.info("%s %s: %s", tag, alert.source, alert.message)


class AlertManager:
    def __init__(self, transport: Optional[Transport] = None) -> None:
        self._transport = transport or _log_transport

    def set_transport(self, transport: Transport) -> None:
        self._transport = transport

    def send(self, level: AlertLevel, message: str, source: str = "system") -> None:
        self._transport(Alert(level=level, message=message, source=source))

    # Convenience
    def critical(self, message: str, source: str = "system") -> None:
        self.send(AlertLevel.CRITICAL, message, source)

    def warning(self, message: str, source: str = "system") -> None:
        self.send(AlertLevel.WARNING, message, source)

    def info(self, message: str, source: str = "system") -> None:
        self.send(AlertLevel.INFO, message, source)


def build_telegram_transport(token: str, chat_id: str) -> Transport:
    """Lazy Telegram transport. Imports the optional client only when called.

    Token/chat_id are passed in at runtime (NEVER hardcoded — see security audit).
    """
    def _transport(alert: Alert) -> None:
        try:
            import telegram  # type: ignore  (optional dep)
        except Exception:
            _log_transport(alert)
            return
        try:
            bot = telegram.Bot(token=token)
            bot.send_message(
                chat_id=chat_id,
                text=f"{alert.level.value} [{alert.source}] {alert.message}",
            )
        except Exception as exc:  # network/API errors must not crash the pipeline
            logger.error("telegram alert failed: %s", exc)
            _log_transport(alert)

    return _transport


# Module-level default manager (safe singleton; swap transport at runtime)
default_manager = AlertManager()
