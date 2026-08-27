"""Finnhub provider stub — delegated or fallback."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FinnhubProvider:
    def __init__(self):
        self._inner: Any = None

    def _lazy_init(self):
        if self._inner is not None:
            return
        try:
            from quant_nanggroe.data.providers.finnhub_provider import FinnhubProvider as _NewFP
            self._inner = _NewFP()
        except Exception as exc:
            logger.debug("FinnhubProvider lazy init failed: %s", exc)
            self._inner = None

    def is_available(self) -> bool:
        return True

    def company_news(self, symbol: str, _from: str, _to: str) -> List[Dict]:
        return []

    def market_news(self, category: str = "general") -> List[Dict]:
        return []

    def __repr__(self) -> str:
        return "FinnhubProvider(delegated)"
