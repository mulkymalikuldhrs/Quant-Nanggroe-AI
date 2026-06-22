"""Commitment of Traders (COT) analysis — thin wrapper.

Provides positioning scores and extreme readings from CFTC data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class COTParser:
    """Parse and analyze COT reports for futures positioning."""

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            from quant_nanggroe.engine.data.cot_provider import COTDataProvider
            self._provider = COTDataProvider()
        return self._provider

    def get_positioning(self, symbol: str) -> Dict[str, Any]:
        provider = self._get_provider()
        return provider.get_positioning(symbol)

    def get_extreme_readings(self) -> List[Dict[str, Any]]:
        provider = self._get_provider()
        return provider.get_extreme_readings()
