"""QNA alerting subsystem (Archive upgrade C4).

Exposes ``default_manager`` consumed by ``quant_nanggroe.agents.graph``
(lazy-imported, fail-soft). Sends critical/warning/info alerts to Telegram
when ``QNA_TELEGRAM_TOKEN`` + ``QNA_TELEGRAM_CHAT_ID`` are set; otherwise
the manager is a no-op (logs locally). Fail-safe: any send error is swallowed
so alerting can never break the trading pipeline.
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger("qna.alerting")


class AlertManager:
    """Thread-safe alert dispatcher. No-op until Telegram creds are present."""

    _lock = threading.Lock()

    def __init__(self) -> None:
        self._token = os.environ.get("QNA_TELEGRAM_TOKEN", "")
        self._chat_id = os.environ.get("QNA_TELEGRAM_CHAT_ID", "")
        self._enabled = bool(self._token and self._chat_id)
        self._session = None
        if self._enabled:
            try:
                import requests  # lazy dep; optional
                self._session = requests.Session()
            except Exception as exc:  # pragma: no cover
                logger.warning("alerting: requests unavailable (%s) — no-op", exc)
                self._enabled = False
        else:
            logger.info("alerting: disabled (set QNA_TELEGRAM_TOKEN + QNA_TELEGRAM_CHAT_ID to enable)")

    def _send(self, level: str, message: str) -> None:
        if not self._enabled or self._session is None:
            logger.log(
                logging.CRITICAL if level == "critical" else logging.WARNING,
                "ALERT[%s]: %s", level, message,
            )
            return
        try:
            url = f"https://api.telegram.org/bot{self._token}/sendMessage"
            self._session.post(
                url,
                json={"chat_id": self._chat_id, "text": f"[{level.upper()}] {message}"},
                timeout=5,
            )
        except Exception as exc:  # fail-soft: never break caller
            logger.warning("alerting send failed (%s): %s", exc, message)

    def critical(self, message: str) -> None:
        with self._lock:
            self._send("critical", message)

    def warning(self, message: str) -> None:
        with self._lock:
            self._send("warning", message)

    def info(self, message: str) -> None:
        with self._lock:
            self._send("info", message)


# Module-level singleton consumed by graph.py
default_manager = AlertManager()
