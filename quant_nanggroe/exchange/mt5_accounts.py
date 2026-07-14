"""Auto-register MT5 accounts (Exness / Valutrades / etc) into ExchangeManager.

Baca config/mt5_accounts.yaml, buat MT5Broker per akun, register ke
ExchangeManager. Dipanggil dari app lifespan startup — non-fatal kalau MT5
terminal belum jalan (broker tetap terdaftar, connect ditunda).
"""

from __future__ import annotations

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config", "mt5_accounts.yaml",
)


def load_mt5_accounts(em) -> List[str]:
    """Register all MT5 accounts from YAML into the given ExchangeManager.

    Returns list of registered account names.
    """
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML missing — skip MT5 account auto-load")
        return []

    if not os.path.exists(_CONFIG_PATH):
        logger.info("No mt5_accounts.yaml found at %s — skip", _CONFIG_PATH)
        return []

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    accounts = data.get("accounts") or []
    if not accounts:
        return []

    from quant_nanggroe.exchange.factory import ExchangeFactory

    registered: List[str] = []
    for acc in accounts:
        name = acc.get("name")
        if not name:
            continue
        if name in em._registrations:
            continue
        try:
            broker = ExchangeFactory().create(
                "mt5",
                api_key=acc.get("login"),
                api_secret=acc.get("password"),
                passphrase=acc.get("server"),
            )
            em.register(name, broker, role=acc.get("role", "primary"))
            registered.append(name)
            logger.info("Registered MT5 account: %s", name)
        except Exception as exc:
            logger.warning("Failed to register MT5 account %s: %s", name, exc)

    return registered
