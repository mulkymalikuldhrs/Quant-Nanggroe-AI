"""Macro provider stub — delegated or fallback."""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MacroProvider:
    def __init__(self):
        self._inner: Any = None

    def _lazy_init(self):
        if self._inner is not None:
            return
        try:
            from quant_nanggroe.data.providers.macro_provider import MacroProvider as _NewMP
            self._inner = _NewMP()
        except Exception as exc:
            logger.debug("MacroProvider lazy init failed: %s", exc)
            self._inner = None

    def get_macro_snapshot(self) -> Dict:
        return {}

    def is_available(self) -> bool:
        return True

    def __repr__(self) -> str:
        return "MacroProvider(delegated)"
